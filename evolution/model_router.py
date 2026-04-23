# -*- coding: utf-8 -*-
"""
多模型智能路由系统 - 不同任务用最合适的模型

问题：
1. 所有任务都用同一个模型（deepseek-chat）
2. 文章生成需要高质量，但评估/去重用轻量模型就够了
3. 没有根据任务复杂度自动选择模型的机制
4. 成本高：简单任务也花大价钱

解决方案：
1. 任务分类和模型映射
2. 动态降级（好模型失败时自动降级）
3. 成本追踪和优化建议
4. 自动模型选择

DeepSeek 价格参考（百万tokens）：
- deepseek-chat: 输入¥1, 输出¥2
- deepseek-reasoner: 输入¥4, 输出¥16
- deepseek-chat-32k: 输入¥2, 输出¥8
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class TaskType(Enum):
    """任务类型"""
    ARTICLE_GENERATION = "article_generation"  # 文章生成 - 最高质量
    QUALITY_EVALUATION = "quality_evaluation"  # 质量评估 - 中等质量
    CONTENT_DEDUP = "content_dedup"  # 内容去重 - 轻量
    TRANSLATION = "translation"  # 翻译 - 轻量
    SUMMARIZATION = "summarization"  # 摘要 - 轻量
    SYSTEM_DIAGNOSIS = "system_diagnosis"  # 系统诊断 - 中等
    PROMPT_OPTIMIZATION = "prompt_optimization"  # Prompt优化 - 中等
    RSS_ANALYSIS = "rss_analysis"  # RSS分析 - 轻量


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    input_price: float  # 每百万tokens输入价格（元）
    output_price: float  # 每百万tokens输出价格（元）
    quality_score: int  # 质量评分 1-10
    speed_score: int  # 速度评分 1-10
    context_length: int  # 上下文长度
    is_reasoning: bool  # 是否推理模型


@dataclass
class RouteDecision:
    """路由决策"""
    task_type: TaskType
    selected_model: str
    reason: str
    estimated_cost: float
    confidence: float
    fallback_models: List[str]


@dataclass
class UsageRecord:
    """使用记录"""
    timestamp: str
    task_type: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency: float
    success: bool


class ModelRouter:
    """多模型智能路由器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.usage_file = f"{trendradar_path}/evolution/model_usage.json"
        
        # 模型库
        self.models = {
            "deepseek/deepseek-chat": ModelConfig(
                name="deepseek-chat",
                input_price=1.0,
                output_price=2.0,
                quality_score=7,
                speed_score=9,
                context_length=64000,
                is_reasoning=False
            ),
            "deepseek/deepseek-reasoner": ModelConfig(
                name="deepseek-reasoner",
                input_price=4.0,
                output_price=16.0,
                quality_score=10,
                speed_score=5,
                context_length=64000,
                is_reasoning=True
            ),
            "deepseek/deepseek-chat-32k": ModelConfig(
                name="deepseek-chat-32k",
                input_price=2.0,
                output_price=8.0,
                quality_score=7,
                speed_score=8,
                context_length=32000,
                is_reasoning=False
            )
        }
        
        # 默认路由策略
        self.default_routes = {
            TaskType.ARTICLE_GENERATION: {
                "primary": "deepseek/deepseek-reasoner",
                "fallback": ["deepseek/deepseek-chat"],
                "reason": "文章生成需要最高质量，使用推理模型"
            },
            TaskType.QUALITY_EVALUATION: {
                "primary": "deepseek/deepseek-chat",
                "fallback": ["deepseek/deepseek-chat-32k"],
                "reason": "评估任务需要速度，普通模型足够"
            },
            TaskType.CONTENT_DEDUP: {
                "primary": "deepseek/deepseek-chat",
                "fallback": [],
                "reason": "去重是简单任务，用最便宜的模型"
            },
            TaskType.TRANSLATION: {
                "primary": "deepseek/deepseek-chat",
                "fallback": [],
                "reason": "翻译用轻量模型"
            },
            TaskType.SUMMARIZATION: {
                "primary": "deepseek/deepseek-chat",
                "fallback": [],
                "reason": "摘要用轻量模型"
            },
            TaskType.SYSTEM_DIAGNOSIS: {
                "primary": "deepseek/deepseek-reasoner",
                "fallback": ["deepseek/deepseek-chat"],
                "reason": "系统诊断需要深度分析"
            },
            TaskType.PROMPT_OPTIMIZATION: {
                "primary": "deepseek/deepseek-reasoner",
                "fallback": ["deepseek/deepseek-chat"],
                "reason": "Prompt优化需要推理能力"
            },
            TaskType.RSS_ANALYSIS: {
                "primary": "deepseek/deepseek-chat",
                "fallback": [],
                "reason": "RSS分析是结构化任务"
            }
        }
        
        # 自适应配置
        self.adaptive_mode = True  # 是否启用自适应
        self.cost_budget_daily = 5.0  # 每日成本预算（元）
        self.quality_threshold = 7.0  # 质量阈值
    
    def route(self, task_type: TaskType, 
              estimated_input_tokens: int = 0,
              estimated_output_tokens: int = 0) -> RouteDecision:
        """
        路由决策 - 为任务选择最合适的模型
        
        Args:
            task_type: 任务类型
            estimated_input_tokens: 预估输入tokens
            estimated_output_tokens: 预估输出tokens
        
        Returns:
            RouteDecision: 路由决策
        """
        route_config = self.default_routes.get(task_type, self.default_routes[TaskType.ARTICLE_GENERATION])
        
        primary_model = route_config["primary"]
        fallback_models = route_config["fallback"]
        reason = route_config["reason"]
        
        # 自适应调整
        if self.adaptive_mode:
            primary_model, reason = self._adaptive_adjustment(
                task_type, primary_model, estimated_input_tokens, estimated_output_tokens
            )
        
        # 计算预估成本
        model_config = self.models.get(primary_model, self.models["deepseek/deepseek-chat"])
        input_cost = (estimated_input_tokens / 1_000_000) * model_config.input_price
        output_cost = (estimated_output_tokens / 1_000_000) * model_config.output_price
        estimated_cost = input_cost + output_cost
        
        return RouteDecision(
            task_type=task_type,
            selected_model=primary_model,
            reason=reason,
            estimated_cost=estimated_cost,
            confidence=0.8,
            fallback_models=fallback_models
        )
    
    def _adaptive_adjustment(self, task_type: TaskType, 
                            current_model: str,
                            input_tokens: int,
                            output_tokens: int) -> tuple:
        """
        自适应调整模型选择
        
        策略：
        1. 如果今日成本快超预算，降级到便宜模型
        2. 如果近期质量一直很高，可以尝试降级
        3. 如果近期质量低，升级到好模型
        """
        # 检查今日成本
        daily_cost = self._get_daily_cost()
        
        if daily_cost > self.cost_budget_daily * 0.8:
            # 成本快超预算，降级
            if current_model == "deepseek/deepseek-reasoner":
                return "deepseek/deepseek-chat", f"成本接近预算({daily_cost:.2f}元)，降级到chat模型"
        
        # 检查近期质量趋势
        recent_quality = self._get_recent_quality()
        
        if recent_quality and recent_quality > 8.0:
            # 质量很高，可以尝试降级（但文章生成不降）
            if task_type != TaskType.ARTICLE_GENERATION and current_model == "deepseek/deepseek-reasoner":
                return "deepseek/deepseek-chat", f"近期质量优秀({recent_quality:.1f})，降级节省成本"
        
        if recent_quality and recent_quality < 6.0:
            # 质量低，升级
            if current_model == "deepseek/deepseek-chat" and task_type in [
                TaskType.ARTICLE_GENERATION, TaskType.SYSTEM_DIAGNOSIS
            ]:
                return "deepseek/deepseek-reasoner", f"近期质量偏低({recent_quality:.1f})，升级到reasoner"
        
        return current_model, self.default_routes[task_type]["reason"]
    
    def record_usage(self, task_type: TaskType, model: str, 
                    input_tokens: int, output_tokens: int, 
                    latency: float, success: bool):
        """记录模型使用"""
        model_config = self.models.get(model)
        if not model_config:
            return
        
        cost = (input_tokens / 1_000_000) * model_config.input_price + \
               (output_tokens / 1_000_000) * model_config.output_price
        
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            task_type=task_type.value,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency=latency,
            success=success
        )
        
        self._save_usage_record(record)
    
    def get_cost_report(self, days: int = 7) -> Dict:
        """获取成本报告"""
        records = self._load_usage_records(days)
        
        if not records:
            return {
                "total_cost": 0,
                "total_requests": 0,
                "avg_latency": 0,
                "success_rate": 0,
                "by_task": {},
                "by_model": {}
            }
        
        total_cost = sum(r.cost for r in records)
        total_requests = len(records)
        avg_latency = sum(r.latency for r in records) / total_requests
        success_rate = sum(1 for r in records if r.success) / total_requests
        
        # 按任务分类
        by_task = {}
        for r in records:
            by_task[r.task_type] = by_task.get(r.task_type, {"cost": 0, "count": 0})
            by_task[r.task_type]["cost"] += r.cost
            by_task[r.task_type]["count"] += 1
        
        # 按模型分类
        by_model = {}
        for r in records:
            by_model[r.model] = by_model.get(r.model, {"cost": 0, "count": 0})
            by_model[r.model]["cost"] += r.cost
            by_model[r.model]["count"] += 1
        
        return {
            "total_cost": total_cost,
            "total_requests": total_requests,
            "avg_latency": avg_latency,
            "success_rate": success_rate,
            "by_task": by_task,
            "by_model": by_model,
            "period": f"{days}天"
        }
    
    def get_optimization_suggestions(self) -> List[str]:
        """获取成本优化建议"""
        suggestions = []
        report = self.get_cost_report(7)
        
        # 成本分析
        if report["total_cost"] > self.cost_budget_daily * 7:
            suggestions.append(f"⚠️ 周成本({report['total_cost']:.2f}元)超预算，建议检查模型选择")
        
        # 任务分析
        for task, data in report.get("by_task", {}).items():
            avg_cost = data["cost"] / data["count"] if data["count"] > 0 else 0
            if avg_cost > 0.5:  # 单次超过5毛
                suggestions.append(f"💡 {task} 单次成本较高({avg_cost:.2f}元)，考虑降级模型")
        
        # 模型分析
        for model, data in report.get("by_model", {}).items():
            if "reasoner" in model and data["count"] > 10:
                suggestions.append(f"💡 {model} 使用频繁({data['count']}次)，评估是否可以部分降级")
        
        # 延迟分析
        if report["avg_latency"] > 30:
            suggestions.append(f"⚠️ 平均延迟较高({report['avg_latency']:.1f}s)，检查模型或网络")
        
        if not suggestions:
            suggestions.append("✅ 当前模型使用效率良好")
        
        return suggestions
    
    def _get_daily_cost(self) -> float:
        """获取今日成本"""
        records = self._load_usage_records(1)
        return sum(r.cost for r in records)
    
    def _get_recent_quality(self) -> Optional[float]:
        """获取近期质量"""
        try:
            metrics_file = f"{self.trendradar_path}/evolution/metrics_history.json"
            if os.path.exists(metrics_file):
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data:
                    recent = [d for d in data[-7:] if d.get('overall_score')]
                    if recent:
                        return sum(d['overall_score'] for d in recent) / len(recent)
        except Exception:
            pass
        return None
    
    def _save_usage_record(self, record: UsageRecord):
        """保存使用记录"""
        try:
            records = []
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            
            records.append({
                "timestamp": record.timestamp,
                "task_type": record.task_type,
                "model": record.model,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "cost": record.cost,
                "latency": record.latency,
                "success": record.success
            })
            
            # 只保留90天
            cutoff = (datetime.now() - timedelta(days=90)).isoformat()
            records = [r for r in records if r["timestamp"] > cutoff]
            
            os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[模型路由] 保存使用记录失败: {e}")
    
    def _load_usage_records(self, days: int) -> List[UsageRecord]:
        """加载使用记录"""
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


# 便捷函数
def get_model_for_task(task_type_str: str, 
                       input_tokens: int = 0,
                       output_tokens: int = 0,
                       trendradar_path: str = ".") -> str:
    """
    获取任务对应的模型
    
    这是多模型路由系统的入口点
    """
    router = ModelRouter(trendradar_path)
    
    try:
        task = TaskType(task_type_str)
    except ValueError:
        task = TaskType.ARTICLE_GENERATION
    
    decision = router.route(task, input_tokens, output_tokens)
    return decision.selected_model
