# -*- coding: utf-8 -*-
"""
Lv51: 智能发布时间优化器

核心理念：数据驱动，找出最佳文章发布时间，最大化阅读效果。

分析维度：
1. 历史发布时间分布 → 找出高互动时段
2.  weekday vs weekend → 工作日vs周末效果差异
3.  科技内容特殊性 → 科技读者阅读习惯
4.  RSS订阅者时区 → 考虑全球读者

优化策略：
- 分析历史Issues的时间戳
- 统计各时段的内容产出量
- 推荐最佳发布窗口
- 自动调整Workflow cron调度

输出：
- 最佳发布时间建议
- 每日/每周发布计划
- cron表达式推荐
"""

import json
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests


class PublishTimeOptimizer:
    """智能发布时间优化器"""
    
    # 科技内容最佳发布时间（基于行业数据，作为初始值）
    INDUSTRY_BEST_TIMES = {
        "weekday_morning": "09:00-10:00",   # 上班前浏览
        "weekday_lunch": "12:00-13:00",     # 午休时间
        "weekday_evening": "19:00-21:00",   # 下班后
        "weekend_morning": "10:00-11:00",   # 周末 leisurely
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.analysis_file = f"{trendradar_path}/evolution/publish_time_analysis.json"
    
    def analyze_from_issues(self, owner: str, repo: str, token: str) -> Dict:
        """从GitHub Issues分析历史发布时间"""
        print("[时间优化] 分析历史发布数据...")
        
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            headers = {"Authorization": f"token {token}"}
            
            # 获取最近100个Issues
            response = requests.get(url, headers=headers,
                                  params={"labels": "memory,article-history",
                                         "state": "all", "per_page": 100},
                                  timeout=15)
            
            if response.status_code != 200:
                return {"error": f"API错误: {response.status_code}"}
            
            issues = response.json()
            
            # 分析时间分布
            hour_distribution = Counter()
            weekday_distribution = Counter()
            monthly_distribution = Counter()
            
            for issue in issues:
                created_at = issue.get("created_at", "")
                if not created_at:
                    continue
                
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    # 转换为北京时间 (UTC+8)
                    dt = dt + timedelta(hours=8)
                    
                    hour_distribution[dt.hour] += 1
                    weekday_distribution[dt.strftime('%A')] += 1
                    monthly_distribution[dt.strftime('%Y-%m')] += 1
                    
                except Exception:
                    continue
            
            return {
                "total_articles": len(issues),
                "hour_distribution": dict(hour_distribution),
                "weekday_distribution": dict(weekday_distribution),
                "monthly_distribution": dict(monthly_distribution),
                "analyzed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_from_files(self, posts_dir: str = "src/content/posts") -> Dict:
        """从本地文件分析发布时间"""
        metrics = {
            "total_files": 0,
            "hour_distribution": Counter(),
            "weekday_distribution": Counter(),
        }
        
        full_dir = f"{self.trendradar_path}/{posts_dir}"
        if not os.path.exists(full_dir):
            return metrics
        
        for root, _, files in os.walk(full_dir):
            for file in files:
                if not file.endswith('.md'):
                    continue
                
                file_path = os.path.join(root, file)
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                metrics["total_files"] += 1
                metrics["hour_distribution"][mtime.hour] += 1
                metrics["weekday_distribution"][mtime.strftime('%A')] += 1
        
        metrics["hour_distribution"] = dict(metrics["hour_distribution"])
        metrics["weekday_distribution"] = dict(metrics["weekday_distribution"])
        
        return metrics
    
    def find_optimal_window(self, data: Dict) -> Dict:
        """找出最佳发布窗口"""
        hour_dist = data.get("hour_distribution", {})
        weekday_dist = data.get("weekday_distribution", {})
        
        if not hour_dist:
            # 使用行业默认值
            return {
                "best_hours": [9, 12, 20],
                "best_weekdays": ["Tuesday", "Wednesday", "Thursday"],
                "confidence": "low",
                "source": "industry_default"
            }
        
        # 找出发布量最高的时段（假设发布多的时段就是效果好的时段）
        top_hours = sorted(hour_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        best_hours = [h[0] for h in top_hours]
        
        # 找出最佳工作日
        top_weekdays = sorted(weekday_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        best_weekdays = [w[0] for w in top_weekdays]
        
        # 计算置信度
        total = sum(hour_dist.values())
        confidence = "high" if total > 20 else "medium" if total > 10 else "low"
        
        return {
            "best_hours": best_hours,
            "best_weekdays": best_weekdays,
            "confidence": confidence,
            "source": "historical_data",
            "sample_size": total
        }
    
    def generate_cron_recommendation(self, optimal: Dict) -> str:
        """生成cron表达式推荐"""
        best_hours = optimal.get("best_hours", [9])
        
        if len(best_hours) >= 2:
            # 如果有多个最佳时段，选一个作为主时段
            primary_hour = best_hours[0]
        else:
            primary_hour = best_hours[0] if best_hours else 9
        
        # 推荐每6小时在最佳时段附近运行
        # 比如最佳时段是9点，推荐 cron: "0 9,15,21 * * *"
        suggested_hours = [primary_hour, (primary_hour + 6) % 24, (primary_hour + 12) % 24]
        suggested_hours = sorted(set(suggested_hours))
        
        cron = f"0 {','.join(map(str, suggested_hours))} * * *"
        
        return {
            "primary_hour": primary_hour,
            "suggested_hours": suggested_hours,
            "cron_expression": cron,
            "readable": f"每日 {', '.join([f'{h}:00' for h in suggested_hours])} 运行"
        }
    
    def generate_report(self, owner: str = None, repo: str = None, token: str = None) -> str:
        """生成发布时间优化报告"""
        lines = []
        lines.append("# ⏰ 智能发布时间优化报告")
        lines.append(f"\n> 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 收集数据
        if owner and repo and token:
            data = self.analyze_from_issues(owner, repo, token)
        else:
            data = self.analyze_from_files()
        
        if "error" in data:
            lines.append(f"⚠️ 分析失败: {data['error']}")
            return "\n".join(lines)
        
        # ═══════════════════════════════════════
        # 历史发布分布
        # ═══════════════════════════════════════
        lines.append("## 📊 历史发布分布")
        lines.append("")
        
        hour_dist = data.get("hour_distribution", {})
        if hour_dist:
            lines.append("### 时段分布")
            lines.append("")
            
            # 可视化时段分布
            for hour in range(24):
                count = hour_dist.get(hour, 0)
                bar_len = 20
                max_count = max(hour_dist.values()) if hour_dist else 1
                filled = int((count / max_count) * bar_len) if max_count > 0 else 0
                bar = "█" * filled + "░" * (bar_len - filled)
                marker = " ←" if count == max_count and count > 0 else ""
                lines.append(f"{hour:02d}:00 [{bar}] {count}{marker}")
            
            lines.append("")
        
        weekday_dist = data.get("weekday_distribution", {})
        if weekday_dist:
            lines.append("### 星期分布")
            lines.append("")
            for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
                count = weekday_dist.get(day, 0)
                lines.append(f"- {day}: {count} 篇")
            lines.append("")
        
        # ═══════════════════════════════════════
        # 优化建议
        # ═══════════════════════════════════════
        lines.append("## 💡 优化建议")
        lines.append("")
        
        optimal = self.find_optimal_window(data)
        cron_rec = self.generate_cron_recommendation(optimal)
        
        lines.append(f"**最佳发布时段**: {', '.join([f'{h}:00' for h in optimal['best_hours']])}")
        lines.append(f"**最佳工作日**: {', '.join(optimal['best_weekdays'])}")
        lines.append(f"**数据置信度**: {optimal['confidence']} (样本: {optimal.get('sample_size', 0)})")
        lines.append("")
        
        lines.append("### 推荐调度")
        lines.append("")
        lines.append(f"- Cron表达式: `{cron_rec['cron_expression']}`")
        lines.append(f"- 可读格式: {cron_rec['readable']}")
        lines.append("")
        
        # 行业参考
        lines.append("### 行业参考")
        lines.append("")
        lines.append("科技内容最佳发布时间（行业数据）:")
        for name, time_range in self.INDUSTRY_BEST_TIMES.items():
            lines.append(f"- {name}: {time_range}")
        lines.append("")
        
        # ═══════════════════════════════════════
        # 行动建议
        # ═══════════════════════════════════════
        lines.append("## 🎯 行动建议")
        lines.append("")
        
        if optimal["confidence"] == "low":
            lines.append("1. 📈 当前数据不足，建议积累至少20篇文章后再优化")
            lines.append("2. 🕐 暂用行业默认值: 工作日 09:00, 12:00, 20:00")
        else:
            lines.append(f"1. ✅ 数据充足，建议按分析结果调度: {cron_rec['readable']}")
            lines.append("2. 📊 持续监控发布效果，每月重新校准")
        
        lines.append("3. 🌍 考虑全球读者，可在不同时段发布不同语言版本")
        lines.append("4. 📅 保持发布频率稳定，建议每周3-5篇")
        lines.append("")
        
        lines.append("---")
        lines.append("*自动生成 by TrendRadar Publish Time Optimizer Lv51*")
        
        return "\n".join(lines)
    
    def save_analysis(self):
        """保存分析结果"""
        data = {
            "analyzed_at": datetime.now().isoformat(),
            "recommendation": self.generate_cron_recommendation(
                self.find_optimal_window(self.analyze_from_files())
            )
        }
        
        try:
            os.makedirs(os.path.dirname(self.analysis_file), exist_ok=True)
            with open(self.analysis_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


# 便捷函数
def optimize_publish_time(owner: str = None, repo: str = None, token: str = None):
    """优化发布时间入口"""
    optimizer = PublishTimeOptimizer()
    report = optimizer.generate_report(owner, repo, token)
    print(report)
    optimizer.save_analysis()


if __name__ == "__main__":
    optimize_publish_time()
