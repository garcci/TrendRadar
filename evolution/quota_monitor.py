# -*- coding: utf-8 -*-
"""
免费AI额度监控系统 - 实时追踪各Provider使用情况

功能：
1. 查询各免费API剩余额度
2. 生成使用报告
3. 超额预警
4. 成本分析
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class QuotaStatus:
    """额度状态"""
    provider: str
    daily_limit: int
    used: int
    remaining: int
    usage_percent: float
    status: str  # 'normal', 'warning', 'critical'
    estimated_cost_saved: float


class QuotaMonitor:
    """额度监控器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.usage_file = f"{trendradar_path}/evolution/ai_provider_usage.json"
        
        # 免费额度配置
        self.quotas = {
            "cloudflare_workers_ai": {
                "name": "Cloudflare Workers AI",
                "daily_limit": 10000,  # 神经元
                "unit": "neurons",
                "cost_per_unit": 0.0
            },
            "google_gemini": {
                "name": "Google Gemini",
                "daily_limit": 1500,  # 请求次数
                "unit": "requests",
                "cost_per_unit": 0.0
            },
            "modelscope": {
                "name": "魔搭社区",
                "daily_limit": 2000,  # 请求次数
                "unit": "requests",
                "cost_per_unit": 0.0
            },
            "deepseek": {
                "name": "DeepSeek",
                "daily_limit": 0,  # 无免费额度
                "unit": "tokens",
                "cost_per_unit": 0.001  # ¥1/百万tokens
            }
        }
    
    def get_usage_today(self) -> Dict[str, int]:
        """获取今日使用情况"""
        try:
            if not os.path.exists(self.usage_file):
                return {}
            
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            today = datetime.now().strftime("%Y-%m-%d")
            usage = {}
            
            for record in records:
                if record.get("timestamp", "").startswith(today):
                    provider = record.get("provider", "unknown")
                    tokens = record.get("tokens_used", 0)
                    
                    if provider not in usage:
                        usage[provider] = 0
                    usage[provider] += tokens
            
            return usage
        except Exception:
            return {}
    
    def get_quota_status(self) -> List[QuotaStatus]:
        """获取所有Provider额度状态"""
        today_usage = self.get_usage_today()
        statuses = []
        
        total_saved = 0.0
        
        for provider_id, config in self.quotas.items():
            used = today_usage.get(provider_id, 0)
            limit = config["daily_limit"]
            
            if limit > 0:
                remaining = max(0, limit - used)
                percent = (used / limit) * 100 if limit > 0 else 0
                
                if percent < 50:
                    status = "normal"
                elif percent < 80:
                    status = "warning"
                else:
                    status = "critical"
                
                # 估算节省成本（假设不用免费API的成本）
                saved = 0.0
            else:
                remaining = 0
                percent = 100
                status = "paid"
                # DeepSeek的实际花费
                saved = -used / 1_000_000 * config["cost_per_unit"]
            
            statuses.append(QuotaStatus(
                provider=config["name"],
                daily_limit=limit,
                used=used,
                remaining=remaining,
                usage_percent=percent,
                status=status,
                estimated_cost_saved=saved
            ))
        
        return statuses
    
    def generate_report(self) -> str:
        """生成额度报告"""
        statuses = self.get_quota_status()
        
        report = []
        report.append("=" * 60)
        report.append("🎯 免费AI额度监控报告")
        report.append(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        
        total_free_used = 0
        total_cost = 0.0
        
        for s in statuses:
            report.append("")
            
            # 状态图标
            if s.status == "normal":
                icon = "🟢"
            elif s.status == "warning":
                icon = "🟡"
            elif s.status == "critical":
                icon = "🔴"
            else:
                icon = "💰"
            
            report.append(f"{icon} {s.provider}")
            report.append(f"   今日使用: {s.used} / {s.daily_limit} {self._get_unit(s.provider)}")
            
            if s.daily_limit > 0:
                report.append(f"   剩余额度: {s.remaining}")
                report.append(f"   使用率: {s.usage_percent:.1f}%")
                
                # 进度条
                bar_length = 20
                filled = int((s.usage_percent / 100) * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                report.append(f"   [{bar}]")
            else:
                report.append(f"   付费使用: {s.used} tokens")
                if s.estimated_cost_saved < 0:
                    report.append(f"   花费: ¥{abs(s.estimated_cost_saved):.3f}")
                    total_cost += abs(s.estimated_cost_saved)
            
            total_free_used += s.used
        
        report.append("")
        report.append("-" * 60)
        report.append(f"💰 今日AI总花费: ¥{total_cost:.3f}")
        report.append(f"📊 免费额度使用: {total_free_used} units")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def _get_unit(self, provider_name: str) -> str:
        """获取单位"""
        for pid, config in self.quotas.items():
            if config["name"] == provider_name:
                return config["unit"]
        return "units"
    
    def check_alerts(self) -> List[str]:
        """检查预警"""
        alerts = []
        statuses = self.get_quota_status()
        
        for s in statuses:
            if s.status == "critical":
                alerts.append(f"🔴 {s.provider}: 额度即将耗尽 ({s.usage_percent:.0f}%)")
            elif s.status == "warning":
                alerts.append(f"🟡 {s.provider}: 额度使用过半 ({s.usage_percent:.0f}%)")
        
        if not alerts:
            alerts.append("✅ 所有免费API额度充足")
        
        return alerts
    
    def record_usage(self, provider: str, task_type: str, 
                     tokens_used: int, cost: float, 
                     latency: float, success: bool):
        """记录使用情况"""
        try:
            records = []
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            
            records.append({
                "provider": provider,
                "timestamp": datetime.now().isoformat(),
                "task_type": task_type,
                "tokens_used": tokens_used,
                "cost": cost,
                "latency": latency,
                "success": success
            })
            
            # 只保留30天
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            records = [r for r in records if r["timestamp"] > cutoff]
            
            os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[额度监控] 记录使用失败: {e}")


# 便捷函数
def show_quota_report(trendradar_path: str = "."):
    """显示额度报告"""
    monitor = QuotaMonitor(trendradar_path)
    print(monitor.generate_report())
    print()
    for alert in monitor.check_alerts():
        print(alert)


def get_daily_cost(trendradar_path: str = ".") -> float:
    """获取今日成本"""
    monitor = QuotaMonitor(trendradar_path)
    statuses = monitor.get_quota_status()
    
    total_cost = 0.0
    for s in statuses:
        if s.estimated_cost_saved < 0:
            total_cost += abs(s.estimated_cost_saved)
    
    return total_cost


def record_usage(provider: str, task_type: str, 
                tokens_used: int, cost: float, 
                latency: float, success: bool,
                trendradar_path: str = "."):
    """记录使用情况"""
    monitor = QuotaMonitor(trendradar_path)
    monitor.record_usage(provider, task_type, tokens_used, cost, latency, success)
