# -*- coding: utf-8 -*-
"""
智能调度系统 - 根据内容质量动态调整发布策略

核心理念：
1. 不是所有日子都值得发布文章
2. 低质量内容会损害品牌价值
3. 根据数据质量智能决策：发布/草稿/跳过

决策维度：
- 热点数量：太少则跳过
- 科技占比：太低则跳过或草稿
- RSS健康度：太多失效则降低期望
- 历史评分趋势：连续低分则跳过

调度策略：
- publish: 生成并发布（高质量日）
- draft: 生成但不发布（中等质量日）
- skip: 跳过生成（低质量日）
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class ContentQualityEvaluator:
    """内容质量评估器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.rss_file = f"{trendradar_path}/evolution/rss_health.json"
    
    def evaluate_daily_data(self, news_items_count: int, tech_items_count: int,
                           rss_success_rate: float) -> Dict:
        """
        评估当日数据质量
        
        Args:
            news_items_count: 总热点数
            tech_items_count: 科技热点数
            rss_success_rate: RSS源成功率
            
        返回: 质量评估结果
        """
        scores = {}
        issues = []
        
        # 1. 数量评分 (0-3分)
        if news_items_count >= 100:
            scores["quantity"] = 3
        elif news_items_count >= 50:
            scores["quantity"] = 2
        elif news_items_count >= 20:
            scores["quantity"] = 1
        else:
            scores["quantity"] = 0
            issues.append(f"热点数量不足: {news_items_count}条（需≥20）")
        
        # 2. 科技占比评分 (0-3分)
        tech_ratio = tech_items_count / max(news_items_count, 1)
        if tech_ratio >= 0.5:
            scores["tech_ratio"] = 3
        elif tech_ratio >= 0.3:
            scores["tech_ratio"] = 2
        elif tech_ratio >= 0.15:
            scores["tech_ratio"] = 1
        else:
            scores["tech_ratio"] = 0
            issues.append(f"科技热点占比过低: {tech_ratio*100:.0f}%（需≥15%）")
        
        # 3. RSS健康度评分 (0-2分)
        if rss_success_rate >= 0.8:
            scores["rss_health"] = 2
        elif rss_success_rate >= 0.5:
            scores["rss_health"] = 1
        else:
            scores["rss_health"] = 0
            issues.append(f"RSS源健康度差: {rss_success_rate*100:.0f}%")
        
        # 4. 历史趋势评分 (0-2分)
        trend_score = self._evaluate_history_trend()
        scores["history_trend"] = trend_score
        if trend_score == 0:
            issues.append("近期文章评分持续偏低")
        
        total_score = sum(scores.values())
        
        return {
            "total_score": total_score,
            "max_score": 10,
            "scores": scores,
            "issues": issues,
            "tech_ratio": tech_ratio,
            "rss_success_rate": rss_success_rate
        }
    
    def _evaluate_history_trend(self) -> int:
        """评估历史评分趋势"""
        if not os.path.exists(self.metrics_file):
            return 2  # 无历史数据，默认给满分
        
        try:
            with open(self.metrics_file, 'r') as f:
                metrics = json.load(f)
            
            if len(metrics) < 3:
                return 2
            
            # 取最近3篇评分
            recent_scores = [m.get("overall_score", 7) for m in metrics[-3:]]
            avg_score = sum(recent_scores) / len(recent_scores)
            
            if avg_score >= 7:
                return 2
            elif avg_score >= 5.5:
                return 1
            else:
                return 0
        except Exception:
            return 2


class SmartScheduler:
    """智能调度器"""
    
    # 调度决策阈值
    THRESHOLDS = {
        "publish": 7,   # ≥7分：发布
        "draft": 4,     # 4-6分：草稿
        "skip": 0       # <4分：跳过
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.evaluator = ContentQualityEvaluator(trendradar_path)
        self.decision_log = f"{trendradar_path}/evolution/scheduler_decisions.json"
    
    def make_decision(self, news_items_count: int = 0, tech_items_count: int = 0,
                     rss_success_rate: float = 1.0) -> Dict:
        """
        做出调度决策
        
        返回: {
            "action": "publish|draft|skip",
            "score": 总分,
            "reason": 决策原因,
            "issues": 发现的问题,
            "suggestion": 建议
        }
        """
        evaluation = self.evaluator.evaluate_daily_data(
            news_items_count, tech_items_count, rss_success_rate
        )
        
        score = evaluation["total_score"]
        issues = evaluation["issues"]
        
        # 做出决策
        if score >= self.THRESHOLDS["publish"]:
            action = "publish"
            reason = f"数据质量优秀 ({score}/10)，建议发布"
            suggestion = "正常生成并发布文章"
        elif score >= self.THRESHOLDS["draft"]:
            action = "draft"
            reason = f"数据质量一般 ({score}/10)，建议保存草稿"
            suggestion = "生成文章但不发布，保存到drafts目录"
        else:
            action = "skip"
            reason = f"数据质量不足 ({score}/10)，建议跳过"
            suggestion = "跳过今日生成，等待更好的热点数据"
        
        decision = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "action": action,
            "score": score,
            "reason": reason,
            "issues": issues,
            "suggestion": suggestion,
            "metrics": {
                "news_count": news_items_count,
                "tech_count": tech_items_count,
                "tech_ratio": evaluation["tech_ratio"],
                "rss_success_rate": evaluation["rss_success_rate"]
            }
        }
        
        # 记录决策
        self._log_decision(decision)
        
        return decision
    
    def _log_decision(self, decision: Dict):
        """记录调度决策"""
        decisions = []
        if os.path.exists(self.decision_log):
            with open(self.decision_log, 'r') as f:
                decisions = json.load(f)
        
        decisions.append(decision)
        
        # 只保留最近30天
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        decisions = [d for d in decisions if d["date"] >= cutoff]
        
        with open(self.decision_log, 'w') as f:
            json.dump(decisions, f, ensure_ascii=False, indent=2)
    
    def get_schedule_stats(self) -> Dict:
        """获取调度统计"""
        if not os.path.exists(self.decision_log):
            return {"total": 0, "publish": 0, "draft": 0, "skip": 0}
        
        with open(self.decision_log, 'r') as f:
            decisions = json.load(f)
        
        stats = {
            "total": len(decisions),
            "publish": len([d for d in decisions if d["action"] == "publish"]),
            "draft": len([d for d in decisions if d["action"] == "draft"]),
            "skip": len([d for d in decisions if d["action"] == "skip"])
        }
        
        return stats


# 便捷函数
def should_publish_today(news_count: int = 0, tech_count: int = 0,
                        rss_rate: float = 1.0, trendradar_path: str = ".") -> Tuple[bool, str]:
    """
    判断是否应该在今日发布文章
    
    返回: (是否发布, 原因)
    """
    scheduler = SmartScheduler(trendradar_path)
    decision = scheduler.make_decision(news_count, tech_count, rss_rate)
    
    return decision["action"] == "publish", decision["reason"]


if __name__ == "__main__":
    # 测试
    scheduler = SmartScheduler()
    
    # 场景1: 高质量日
    d1 = scheduler.make_decision(150, 80, 0.9)
    print(f"高质量日: {d1['action']} - {d1['reason']}")
    
    # 场景2: 低质量日
    d2 = scheduler.make_decision(10, 1, 0.3)
    print(f"低质量日: {d2['action']} - {d2['reason']}")
    
    # 场景3: 一般日
    d3 = scheduler.make_decision(50, 15, 0.7)
    print(f"一般日: {d3['action']} - {d3['reason']}")
