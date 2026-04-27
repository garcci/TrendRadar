# -*- coding: utf-8 -*-
"""
免费AI Provider智能路由系统 - 最大化利用免费额度降低成本

支持的免费API：
1. Cloudflare Workers AI - 10,000神经元/天
   - 模型: Llama-3.1-8B, Mistral-7B
   - 适用: 轻量任务、评估、摘要
   - 成本: ¥0 (免费额度内)

2. Google Gemini API -  generous免费层
   - 模型: Gemini 2.0 Flash
   - 适用: 内容生成、翻译
   - 成本: ¥0 (免费额度内)

3. 魔搭社区 (ModelScope) - 2,000次/天
   - 模型: 多种开源模型
   - 适用: 快速原型、测试
   - 成本: ¥0

4. DeepSeek (付费兜底)
   - 模型: deepseek-chat/reasoner
   - 适用: 高质量文章生成
   - 成本: ¥1-16/百万tokens

路由策略：
- 免费额度充足 → 使用免费API
- 免费额度耗尽 → 降级到DeepSeek
- 任务分类 → 不同任务匹配最优Provider
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ProviderType(Enum):
    """Provider类型"""
    CLOUDFLARE_WORKERS_AI = "cloudflare_workers_ai"
    GOOGLE_GEMINI = "google_gemini"
    MODELSCOPE = "modelscope"
    DEEPSEEK = "deepseek"


@dataclass
class ProviderConfig:
    """Provider配置"""
    name: str
    enabled: bool
    free_quota_daily: int  # 每日免费额度
    quota_unit: str  # 额度单位 (neurons, tokens, requests)
    cost_per_unit: float  # 超出额度后的单位成本
    quality_score: int  # 质量评分 1-10
    speed_score: int  # 速度评分 1-10
    best_for: List[str]  # 最适合的任务类型


@dataclass
class UsageRecord:
    """使用记录"""
    provider: str
    timestamp: str
    task_type: str
    tokens_used: int
    cost: float
    latency: float
    success: bool


class FreeAIRouter:
    """免费AI智能路由器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.usage_file = f"{trendradar_path}/evolution/ai_provider_usage.json"
        
        # 初始化Provider配置
        self.providers = self._init_providers()
        
        # 当日使用统计
        self.today_usage = self._load_today_usage()
    
    def _init_providers(self) -> Dict[ProviderType, ProviderConfig]:
        """初始化Provider配置"""
        return {
            ProviderType.CLOUDFLARE_WORKERS_AI: ProviderConfig(
                name="Cloudflare Workers AI",
                enabled=True,
                free_quota_daily=10000,  # 10,000神经元/天
                quota_unit="neurons",
                cost_per_unit=0.0,  # 超出后$0.011/1000 neurons
                quality_score=6,
                speed_score=9,
                best_for=["summarization", "dedup", "light_generation", "embedding"]
            ),
            ProviderType.GOOGLE_GEMINI: ProviderConfig(
                name="Google Gemini",
                enabled=True,
                free_quota_daily=1500,  # 1,500 requests/day ( generous免费层)
                quota_unit="requests",
                cost_per_unit=0.0,
                quality_score=8,
                speed_score=8,
                best_for=["translation", "content_generation", "analysis"]
            ),
            ProviderType.MODELSCOPE: ProviderConfig(
                name="魔搭社区",
                enabled=True,
                free_quota_daily=2000,  # 2,000次/天
                quota_unit="requests",
                cost_per_unit=0.0,
                quality_score=6,
                speed_score=7,
                best_for=["testing", "prototyping", "light_tasks"]
            ),
            ProviderType.DEEPSEEK: ProviderConfig(
                name="DeepSeek",
                enabled=True,
                free_quota_daily=0,  # 无免费额度
                quota_unit="tokens",
                cost_per_unit=0.001,  # ¥1/百万tokens
                quality_score=9,
                speed_score=7,
                best_for=["article_generation", "quality_evaluation", "complex_reasoning"]
            )
        }
    
    def select_provider(self, task_type: str, 
                       estimated_tokens: int = 0,
                       require_high_quality: bool = False) -> Dict:
        """
        选择最优Provider
        
        策略：
        1. 高质量要求 → DeepSeek (兜底)
        2. 有免费额度 → 优先免费Provider
        3. 任务匹配 → 选择最适合的Provider
        4. 额度耗尽 → 降级到下一个Provider
        """
        # 任务到Provider的映射
        task_mapping = {
            "article_generation": [ProviderType.DEEPSEEK, ProviderType.GOOGLE_GEMINI],
            "quality_evaluation": [ProviderType.CLOUDFLARE_WORKERS_AI, ProviderType.DEEPSEEK],
            "content_dedup": [ProviderType.CLOUDFLARE_WORKERS_AI, ProviderType.MODELSCOPE],
            "translation": [ProviderType.GOOGLE_GEMINI, ProviderType.CLOUDFLARE_WORKERS_AI],
            "summarization": [ProviderType.CLOUDFLARE_WORKERS_AI, ProviderType.GOOGLE_GEMINI],
            "system_diagnosis": [ProviderType.DEEPSEEK, ProviderType.GOOGLE_GEMINI],
            "prompt_optimization": [ProviderType.DEEPSEEK],
            "rss_analysis": [ProviderType.CLOUDFLARE_WORKERS_AI, ProviderType.MODELSCOPE]
        }
        
        candidates = task_mapping.get(task_type, [ProviderType.DEEPSEEK])
        
        # 如果需要高质量，强制使用 DeepSeek（不检查免费额度）
        if require_high_quality:
            deepseek_config = self.providers[ProviderType.DEEPSEEK]
            estimated_cost = (estimated_tokens / 1_000_000) * deepseek_config.cost_per_unit
            return {
                "provider": ProviderType.DEEPSEEK.value,
                "name": deepseek_config.name,
                "cost": estimated_cost,
                "remaining_quota": 0,
                "reason": "高质量要求，强制使用 DeepSeek"
            }
        
        # 选择有免费额度的Provider
        for provider_type in candidates:
            config = self.providers[provider_type]
            
            if not config.enabled:
                continue
            
            used_today = self.today_usage.get(provider_type.value, 0)
            remaining = config.free_quota_daily - used_today
            
            if remaining > 0:
                # 检查是否足够本次使用
                if self._estimate_consumption(provider_type, estimated_tokens) <= remaining:
                    return {
                        "provider": provider_type.value,
                        "name": config.name,
                        "cost": 0.0,
                        "remaining_quota": remaining,
                        "reason": f"使用{config.name}免费额度"
                    }
        
        # 所有免费额度耗尽，使用DeepSeek兜底
        deepseek_config = self.providers[ProviderType.DEEPSEEK]
        estimated_cost = (estimated_tokens / 1_000_000) * deepseek_config.cost_per_unit
        
        return {
            "provider": ProviderType.DEEPSEEK.value,
            "name": deepseek_config.name,
            "cost": estimated_cost,
            "remaining_quota": 0,
            "reason": "免费额度已耗尽，使用DeepSeek付费兜底"
        }
    
    def record_usage(self, provider: str, task_type: str, 
                    tokens_used: int, cost: float, 
                    latency: float, success: bool):
        """记录使用"""
        record = UsageRecord(
            provider=provider,
            timestamp=datetime.now().isoformat(),
            task_type=task_type,
            tokens_used=tokens_used,
            cost=cost,
            latency=latency,
            success=success
        )
        
        self._save_usage(record)
        
        # 更新当日统计
        if provider not in self.today_usage:
            self.today_usage[provider] = 0
        self.today_usage[provider] += tokens_used
    
    def get_cost_report(self) -> Dict:
        """获取成本报告"""
        records = self._load_recent_usage(1)
        
        total_cost = sum(r.cost for r in records)
        free_usage = sum(r.tokens_used for r in records if r.cost == 0)
        paid_usage = sum(r.tokens_used for r in records if r.cost > 0)
        
        # 计算节省
        # 假设所有都走DeepSeek的成本
        hypothetical_cost = sum(r.tokens_used for r in records) / 1_000_000 * 0.001
        saved = hypothetical_cost - total_cost
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_cost": total_cost,
            "free_usage": free_usage,
            "paid_usage": paid_usage,
            "hypothetical_cost": hypothetical_cost,
            "saved": saved,
            "saving_rate": saved / hypothetical_cost if hypothetical_cost > 0 else 0,
            "provider_breakdown": self._get_provider_breakdown(records)
        }
    
    def get_free_quota_status(self) -> Dict:
        """获取免费额度状态"""
        status = {}
        
        for provider_type, config in self.providers.items():
            used = self.today_usage.get(provider_type.value, 0)
            remaining = config.free_quota_daily - used
            usage_rate = used / config.free_quota_daily if config.free_quota_daily > 0 else 1.0
            
            status[provider_type.value] = {
                "name": config.name,
                "daily_quota": config.free_quota_daily,
                "used": used,
                "remaining": remaining,
                "usage_rate": usage_rate,
                "status": "normal" if usage_rate < 0.8 else "warning" if usage_rate < 1.0 else "exhausted"
            }
        
        return status
    
    def _estimate_consumption(self, provider_type: ProviderType, tokens: int) -> int:
        """估算消耗量"""
        if provider_type == ProviderType.CLOUDFLARE_WORKERS_AI:
            # Llama-3.1-8B 约 1000 tokens = 100 neurons
            return max(tokens // 10, 100)
        elif provider_type == ProviderType.GOOGLE_GEMINI:
            return 1  # 按请求计费
        elif provider_type == ProviderType.MODELSCOPE:
            return 1  # 按请求计费
        else:
            return tokens
    
    def _get_provider_breakdown(self, records: List[UsageRecord]) -> Dict:
        """获取Provider使用明细"""
        breakdown = {}
        
        for r in records:
            if r.provider not in breakdown:
                breakdown[r.provider] = {"count": 0, "tokens": 0, "cost": 0}
            breakdown[r.provider]["count"] += 1
            breakdown[r.provider]["tokens"] += r.tokens_used
            breakdown[r.provider]["cost"] += r.cost
        
        return breakdown
    
    def _load_today_usage(self) -> Dict:
        """加载今日使用"""
        records = self._load_recent_usage(1)
        usage = {}
        
        for r in records:
            if r.provider not in usage:
                usage[r.provider] = 0
            usage[r.provider] += r.tokens_used
        
        return usage
    
    def _load_recent_usage(self, days: int) -> List[UsageRecord]:
        """加载最近使用记录"""
        try:
            if not os.path.exists(self.usage_file):
                return []
            
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            records = [r for r in data if r["timestamp"] > cutoff]
            
            return [UsageRecord(**r) for r in records]
        except Exception:
            return []
    
    def _save_usage(self, record: UsageRecord):
        """保存使用记录"""
        try:
            records = []
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            
            records.append({
                "provider": record.provider,
                "timestamp": record.timestamp,
                "task_type": record.task_type,
                "tokens_used": record.tokens_used,
                "cost": record.cost,
                "latency": record.latency,
                "success": record.success
            })
            
            # 只保留30天
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            records = [r for r in records if r["timestamp"] > cutoff]
            
            os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AI路由] 保存使用记录失败: {e}")


# Cloudflare Workers AI 客户端
class CloudflareWorkersAI:
    """Cloudflare Workers AI 客户端"""
    
    def __init__(self, account_id: str = None, api_token: str = None):
        self.account_id = account_id or os.environ.get("CF_ACCOUNT_ID", "")
        self.api_token = api_token or os.environ.get("CF_API_TOKEN", "")
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run"
    
    def chat(self, messages: List[Dict], model: str = "@cf/meta/llama-3.1-8b-instruct") -> str:
        """
        调用Cloudflare Workers AI
        
        Args:
            messages: 消息列表
            model: 模型名称
        
        Returns:
            AI响应内容
        """
        import requests
        
        url = f"{self.base_url}/{model}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        data = {"messages": messages}
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("result", {}).get("response", "")
            else:
                raise Exception(f"API错误: {result.get('errors', [])}")
        except Exception as e:
            raise Exception(f"Cloudflare Workers AI调用失败: {e}")
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.account_id and self.api_token)


# Google Gemini 客户端
class GoogleGeminiClient:
    """Google Gemini API 客户端"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def chat(self, messages: List[Dict], model: str = "gemini-2.0-flash") -> str:
        """
        调用Google Gemini API
        
        Args:
            messages: 消息列表
            model: 模型名称
        
        Returns:
            AI响应内容
        """
        import requests
        
        # 转换消息格式
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        data = {"contents": gemini_messages}
        
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                raise Exception(f"API错误: {result}")
        except Exception as e:
            raise Exception(f"Gemini API调用失败: {e}")
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key)


# 便捷函数
def get_optimal_provider(task_type: str, require_high_quality: bool = False,
                        trendradar_path: str = ".") -> Dict:
    """
    获取最优Provider
    
    这是免费AI路由系统的入口点
    """
    router = FreeAIRouter(trendradar_path)
    return router.select_provider(task_type, require_high_quality=require_high_quality)


def get_daily_cost_report(trendradar_path: str = ".") -> Dict:
    """获取每日成本报告"""
    router = FreeAIRouter(trendradar_path)
    return router.get_cost_report()


def get_quota_status(trendradar_path: str = ".") -> Dict:
    """获取免费额度状态"""
    router = FreeAIRouter(trendradar_path)
    return router.get_free_quota_status()
