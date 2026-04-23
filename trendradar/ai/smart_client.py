# coding=utf-8
"""
智能AI客户端 - 自动选择免费API降低成本

集成策略：
1. 任务分类 → 选择最优Provider
2. 免费API优先 → 降低成本
3. 失败自动降级 → 保证可用性
4. 使用情况记录 → 额度监控
"""

import os
import time
from typing import Any, Dict, List

from .client import AIClient


class SmartAIClient:
    """智能AI客户端 - 多Provider路由"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.task_type = config.get("TASK_TYPE", "article_generation")
        self._init_providers()
    
    def _init_providers(self):
        """初始化各Provider客户端"""
        # DeepSeek（兜底）
        self.deepseek_client = AIClient({
            "MODEL": self.config.get("MODEL", "deepseek/deepseek-chat"),
            "API_KEY": self.config.get("API_KEY") or os.environ.get("AI_API_KEY", ""),
            "API_BASE": self.config.get("API_BASE", ""),
            "TEMPERATURE": self.config.get("TEMPERATURE", 0.7),
            "MAX_TOKENS": self.config.get("MAX_TOKENS", 4000),
        })
        
        # Cloudflare Workers AI
        cf_account = os.environ.get("CF_ACCOUNT_ID", "")
        cf_token = os.environ.get("CF_API_TOKEN", "")
        self.cf_enabled = bool(cf_account and cf_token)
        
        # Google Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        self.gemini_enabled = bool(gemini_key)
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        智能路由调用
        
        策略：
        1. 根据任务类型和配置选择Provider
        2. 免费API优先
        3. 失败时自动降级
        """
        start_time = time.time()
        
        # 确定任务类型
        task_type = kwargs.get("task_type", self.task_type)
        require_high_quality = kwargs.get("require_high_quality", False)
        
        # 路由决策
        provider = self._select_provider(task_type, require_high_quality)
        
        try:
            if provider == "cloudflare" and self.cf_enabled:
                return self._call_cloudflare(messages, kwargs, start_time, task_type)
            elif provider == "gemini" and self.gemini_enabled:
                return self._call_gemini(messages, kwargs, start_time, task_type)
            else:
                return self._call_deepseek(messages, kwargs, start_time, task_type)
        except Exception as e:
            print(f"[SmartAI] {provider} 调用失败: {e}，降级到DeepSeek")
            return self._call_deepseek(messages, kwargs, start_time, task_type)
    
    def _select_provider(self, task_type: str, require_high_quality: bool) -> str:
        """选择Provider"""
        # 高质量要求 → DeepSeek
        if require_high_quality:
            return "deepseek"
        
        # 任务路由
        if task_type in ["summarization", "content_dedup", "rss_analysis"]:
            # 轻量任务优先用Cloudflare
            if self.cf_enabled:
                return "cloudflare"
            elif self.gemini_enabled:
                return "gemini"
        
        elif task_type in ["translation", "quality_evaluation"]:
            # 翻译和评估用Gemini
            if self.gemini_enabled:
                return "gemini"
            elif self.cf_enabled:
                return "cloudflare"
        
        elif task_type == "article_generation":
            # 文章生成默认用DeepSeek，但可尝试Gemini
            if self.gemini_enabled and not require_high_quality:
                return "gemini"
        
        return "deepseek"
    
    def _call_cloudflare(self, messages, kwargs, start_time, task_type):
        """调用Cloudflare Workers AI"""
        import requests
        
        account_id = os.environ.get("CF_ACCOUNT_ID", "")
        api_token = os.environ.get("CF_API_TOKEN", "")
        model = "@cf/meta/llama-3.1-8b-instruct"
        
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, 
                                json={"messages": messages}, 
                                timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("success"):
            content = result.get("result", {}).get("response", "")
            latency = time.time() - start_time
            self._record_usage("cloudflare_workers_ai", task_type, 0, 0, latency, True)
            return content
        else:
            raise Exception(f"Cloudflare API错误: {result.get('errors', [])}")
    
    def _call_gemini(self, messages, kwargs, start_time, task_type):
        """调用Google Gemini"""
        import requests
        
        api_key = os.environ.get("GEMINI_API_KEY", "")
        model = kwargs.get("model", "gemini-2.0-flash")
        
        # 转换消息格式
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        response = requests.post(url, 
                                json={"contents": gemini_messages},
                                timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "candidates" in result and result["candidates"]:
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            latency = time.time() - start_time
            self._record_usage("google_gemini", task_type, 0, 0, latency, True)
            return content
        else:
            raise Exception(f"Gemini API错误: {result}")
    
    def _call_deepseek(self, messages, kwargs, start_time, task_type):
        """调用DeepSeek（兜底）"""
        result = self.deepseek_client.chat(messages, **kwargs)
        latency = time.time() - start_time
        
        # 估算tokens
        input_tokens = sum(len(m["content"]) for m in messages) // 4
        output_tokens = len(result) // 4
        
        self._record_usage("deepseek", task_type, input_tokens, output_tokens, latency, True)
        return result
    
    def _record_usage(self, provider: str, task_type: str, 
                     input_tokens: int, output_tokens: int, 
                     latency: float, success: bool):
        """记录使用情况"""
        try:
            from evolution.quota_monitor import QuotaMonitor
            monitor = QuotaMonitor()
            
            # 计算成本
            cost = 0.0
            if provider == "deepseek":
                cost = (input_tokens / 1_000_000) * 1.0 + (output_tokens / 1_000_000) * 2.0
            
            monitor.record_usage(provider, task_type, input_tokens + output_tokens, cost, latency, success)
        except Exception:
            pass  # 记录失败不影响主流程
