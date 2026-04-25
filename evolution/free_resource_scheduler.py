# -*- coding: utf-8 -*-
"""
Lv46: 免费资源智能调度器

核心理念：榨干每一滴免费额度，绝不浪费！

策略：
1. 监控所有免费Provider的实时可用性
2. 根据任务类型、模型质量、响应速度智能分配
3. 当主Provider失败时，毫秒级切换到备用
4. 记录各Provider的实际表现，长期优化选择策略
5. 主动使用闲置额度（如Cloudflare额度没用满时，分流部分任务）

免费Provider矩阵：
- GitHub Models: 完全免费，无严格限制，Llama 3.1 8B
- Cloudflare Workers AI: 10,000 neurons/日，速度快
- Google Gemini: 1,500 请求/日，质量高
- Groq: 免费tier，速度极快，Llama 3.1 70B
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests


class FreeResourceScheduler:
    """免费资源智能调度器 - 榨干每一滴免费额度"""
    
    # Provider性能评分（基于历史表现，动态更新）
    PROVIDER_PROFILES = {
        "github_models": {
            "name": "GitHub Models",
            "cost": 0.0,
            "quality_score": 7.5,  # 1-10
            "speed_score": 8.0,
            "reliability_score": 9.0,
            "daily_limit": float('inf'),  # 无严格限制
            "model": "meta-llama-3.1-8b-instruct",
            "strengths": ["summarization", "translation", "code"],
            "weaknesses": ["long_context", "complex_reasoning"]
        },
        "cloudflare": {
            "name": "Cloudflare Workers AI",
            "cost": 0.0,
            "quality_score": 7.0,
            "speed_score": 9.5,
            "reliability_score": 8.5,
            "daily_limit": 10000,
            "unit": "neurons",
            "model": "@cf/meta/llama-3.1-8b-instruct",
            "strengths": ["speed", "summarization", "rss_analysis"],
            "weaknesses": ["complex_generation"]
        },
        "gemini": {
            "name": "Google Gemini",
            "cost": 0.0,
            "quality_score": 8.5,
            "speed_score": 7.0,
            "reliability_score": 6.0,  # 容易429
            "daily_limit": 1500,
            "unit": "requests",
            "model": "gemini-2.0-flash",
            "strengths": ["quality", "translation", "article_generation"],
            "weaknesses": ["rate_limit", "availability"]
        },
        "groq": {
            "name": "Groq",
            "cost": 0.0,
            "quality_score": 8.0,
            "speed_score": 10.0,  # 极快
            "reliability_score": 8.0,
            "daily_limit": float('inf'),  # 免费tier限制较宽松
            "model": "llama-3.1-8b-instant",
            "strengths": ["speed", "real_time", "summarization"],
            "weaknesses": ["availability"]
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.performance_file = f"{trendradar_path}/evolution/provider_performance.json"
        self.load_performance_history()
    
    def load_performance_history(self):
        """加载历史性能数据"""
        if os.path.exists(self.performance_file):
            try:
                with open(self.performance_file, 'r') as f:
                    self.performance = json.load(f)
            except Exception:
                self.performance = {}
        else:
            self.performance = {}
    
    def save_performance_history(self):
        """保存性能数据"""
        try:
            os.makedirs(os.path.dirname(self.performance_file), exist_ok=True)
            with open(self.performance_file, 'w') as f:
                json.dump(self.performance, f, indent=2)
        except Exception:
            pass
    
    def record_performance(self, provider: str, task_type: str, 
                          latency: float, success: bool, quality_hint: float = 0.0):
        """记录Provider性能表现"""
        key = f"{provider}:{task_type}"
        if key not in self.performance:
            self.performance[key] = {
                "calls": 0,
                "successes": 0,
                "total_latency": 0.0,
                "avg_latency": 0.0,
                "quality_score": 7.0,
                "last_updated": datetime.now().isoformat()
            }
        
        perf = self.performance[key]
        perf["calls"] += 1
        if success:
            perf["successes"] += 1
        perf["total_latency"] += latency
        perf["avg_latency"] = perf["total_latency"] / perf["calls"]
        
        # 更新质量评分（移动平均）
        if quality_hint > 0:
            perf["quality_score"] = perf["quality_score"] * 0.9 + quality_hint * 0.1
        
        perf["last_updated"] = datetime.now().isoformat()
        self.save_performance_history()
    
    def get_provider_score(self, provider: str, task_type: str) -> float:
        """
        计算Provider在特定任务上的综合评分
        评分越高越适合该任务
        """
        profile = self.PROVIDER_PROFILES.get(provider)
        if not profile:
            return 0.0
        
        # 基础分
        base_score = profile["quality_score"] * 0.4 + \
                     profile["speed_score"] * 0.3 + \
                     profile["reliability_score"] * 0.3
        
        # 任务匹配度加成
        task_match = 1.0
        if task_type in profile.get("strengths", []):
            task_match = 1.3
        elif task_type in profile.get("weaknesses", []):
            task_match = 0.7
        
        # 历史表现加成
        key = f"{provider}:{task_type}"
        if key in self.performance:
            perf = self.performance[key]
            success_rate = perf["successes"] / perf["calls"] if perf["calls"] > 0 else 0.5
            # 成功率高加分，延迟低加分
            latency_bonus = max(0, 1 - perf["avg_latency"] / 30)  # 30秒为基准
            history_score = success_rate * 0.7 + latency_bonus * 0.3
            base_score = base_score * 0.7 + history_score * 10 * 0.3
        
        # 额度充足度加成
        availability = self._check_availability(provider)
        if availability < 0.3:
            task_match *= 0.1  # 额度不足，大幅降低评分
        elif availability < 0.5:
            task_match *= 0.5
        
        return base_score * task_match
    
    def _check_availability(self, provider: str) -> float:
        """检查Provider额度可用比例（0-1）"""
        profile = self.PROVIDER_PROFILES.get(provider)
        if not profile:
            return 0.0
        
        limit = profile.get("daily_limit", float('inf'))
        if limit == float('inf'):
            return 1.0  # 无限制，完全可用
        
        # 查询今日使用
        try:
            from evolution.quota_monitor import QuotaMonitor
            monitor = QuotaMonitor(self.trendradar_path)
            usage = monitor.get_usage_today()
            used = usage.get(provider, 0)
            return max(0, 1 - used / limit)
        except Exception:
            return 0.5  # 无法检查时保守估计
    
    def select_best_provider(self, task_type: str, 
                            require_high_quality: bool = False) -> str:
        """
        选择最适合当前任务的免费Provider
        
        策略：
        1. 排除额度耗尽的Provider
        2. 根据任务类型匹配最优Provider
        3. 考虑历史成功率
        4. 如需高质量，适当放宽成本考量
        """
        scores = []
        
        for provider_id in self.PROVIDER_PROFILES:
            score = self.get_provider_score(provider_id, task_type)
            
            # 高质量要求时，质量分权重增加
            if require_high_quality:
                profile = self.PROVIDER_PROFILES[provider_id]
                score = score * 0.5 + profile["quality_score"] * 0.5
            
            scores.append((provider_id, score))
        
        # 按评分排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"[额度调度] 任务 '{task_type}' Provider评分:")
        for pid, score in scores:
            avail = self._check_availability(pid)
            print(f"  {pid}: {score:.2f} (可用度: {avail*100:.0f}%)")
        
        # 选择评分最高的可用Provider
        for provider_id, score in scores:
            if score > 0:
                print(f"[额度调度] 选择: {provider_id} (评分: {score:.2f})")
                return provider_id
        
        # 全部不可用时，返回GitHub Models（最可靠的免费Provider）
        print("[额度调度] 警告：所有免费Provider不可用，使用GitHub Models兜底")
        return "github_models"
    
    def get_optimal_strategy(self) -> Dict:
        """生成今日最优使用策略"""
        strategy = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "providers": {},
            "recommendations": []
        }
        
        for provider_id, profile in self.PROVIDER_PROFILES.items():
            avail = self._check_availability(provider_id)
            strategy["providers"][provider_id] = {
                "name": profile["name"],
                "availability": avail,
                "model": profile["model"],
                "recommended_tasks": profile["strengths"]
            }
            
            if avail > 0.8:
                strategy["recommendations"].append(
                    f"{profile['name']} 额度充足 ({avail*100:.0f}%)，可大量使用"
                )
            elif avail > 0.3:
                strategy["recommendations"].append(
                    f"{profile['name']} 额度中等 ({avail*100:.0f}%)，适度使用"
                )
            else:
                strategy["recommendations"].append(
                    f"{profile['name']} 额度紧张 ({avail*100:.0f}%)，谨慎使用"
                )
        
        return strategy
    
    def print_strategy(self):
        """打印今日策略"""
        strategy = self.get_optimal_strategy()
        print("=" * 60)
        print(f"📊 今日免费资源使用策略 ({strategy['date']})")
        print("=" * 60)
        
        for pid, info in strategy["providers"].items():
            bar_len = 20
            filled = int(info["availability"] * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\n{info['name']}")
            print(f"  可用度: [{bar}] {info['availability']*100:.0f}%")
            print(f"  模型: {info['model']}")
            print(f"  适合任务: {', '.join(info['recommended_tasks'])}")
        
        print("\n💡 建议:")
        for rec in strategy["recommendations"]:
            print(f"  • {rec}")
        print("=" * 60)


# ═══════════════════════════════════════════════════════════
# Groq Provider 集成
# ═══════════════════════════════════════════════════════════

class GroqProvider:
    """Groq免费Provider - 极快推理"""
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.enabled = bool(self.api_key)
    
    def chat(self, messages: List[Dict], model: str = "llama-3.1-8b-instant", 
             temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """调用Groq API"""
        if not self.enabled:
            raise Exception("Groq未配置")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(self.API_URL, headers=headers, 
                                json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Groq API错误: {result}")


# 便捷函数
def get_scheduler() -> FreeResourceScheduler:
    """获取调度器实例"""
    return FreeResourceScheduler()


def show_today_strategy():
    """显示今日策略"""
    scheduler = FreeResourceScheduler()
    scheduler.print_strategy()


if __name__ == "__main__":
    show_today_strategy()
