# -*- coding: utf-8 -*-
"""
热点预测增强 - 基于历史趋势和信号预测未来热点

核心理念：
1. 不是所有热点都值得深入分析
2. 预测即将爆发的话题，提前布局
3. 利用历史数据发现周期性趋势

预测信号：
- 历史出现频率：哪些话题反复出现
- 增长趋势：话题热度是上升还是下降
- 跨平台一致性：多个平台同时讨论的话题更可能爆发
- 季节性因素：特定时期的热点（如发布会季、财报季）

输出：
- 趋势预测：哪些话题可能在未来3-7天爆发
- 周期性提醒：历史上的这个时期发生了什么
- 建议关注：基于信号的建议话题列表
"""

import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class TrendPredictor:
    """热点预测器"""
    
    # 科技领域季节性事件（简化版）
    SEASONAL_EVENTS = {
        1: ["CES", "年报季", "新品发布"],
        2: ["MWC", "AI模型更新"],
        3: ["GDC", "春季发布会"],
        4: ["Google I/O", "财报季"],
        5: ["Microsoft Build", " Computex"],
        6: ["WWDC", "E3", "夏季发布会"],
        7: ["Q2财报", "AI安全"],
        8: ["Black Hat", "KDD", "秋季新品"],
        9: ["Apple Event", "IFA", "秋季发布会"],
        10: ["Q3财报", "AI峰会"],
        11: ["双十一", "黑五", "感恩季报"],
        12: ["NeurIPS", "年终总结", "预测展望"]
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.history_file = f"{trendradar_path}/evolution/daily_data_points.json"
    
    def analyze_topic_frequency(self, days: int = 30) -> Dict[str, Dict]:
        """
        分析话题出现频率和趋势
        
        返回: {话题: {"count": 次数, "trend": "上升|下降|稳定", "last_seen": 最后出现日期}}
        """
        if not os.path.exists(self.metrics_file):
            return {}
        
        try:
            with open(self.metrics_file, 'r') as f:
                metrics = json.load(f)
        except Exception:
            return {}
        
        # 提取关键词和话题
        topic_data = []
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        for metric in metrics:
            if metric.get("timestamp", "") < cutoff:
                continue
            
            # 从keywords和hot_topics中提取话题
            for topic in metric.get("keywords", []) + metric.get("hot_topics", []):
                if len(topic) >= 2:
                    topic_data.append({
                        "topic": topic,
                        "date": metric.get("date", ""),
                        "score": metric.get("overall_score", 5)
                    })
        
        # 统计话题频率
        topic_stats = {}
        for item in topic_data:
            topic = item["topic"]
            if topic not in topic_stats:
                topic_stats[topic] = {
                    "count": 0,
                    "dates": [],
                    "scores": []
                }
            topic_stats[topic]["count"] += 1
            topic_stats[topic]["dates"].append(item["date"])
            topic_stats[topic]["scores"].append(item["score"])
        
        # 计算趋势
        results = {}
        for topic, stats in topic_stats.items():
            if stats["count"] >= 2:  # 至少出现2次
                dates = sorted(stats["dates"])
                if len(dates) >= 2:
                    # 简单趋势判断：看最近出现间隔
                    recent_dates = dates[-3:]
                    intervals = []
                    for i in range(1, len(recent_dates)):
                        try:
                            d1 = datetime.strptime(recent_dates[i-1], "%Y-%m-%d")
                            d2 = datetime.strptime(recent_dates[i], "%Y-%m-%d")
                            intervals.append((d2 - d1).days)
                        except:
                            pass
                    
                    if intervals:
                        avg_interval = sum(intervals) / len(intervals)
                        if avg_interval <= 2:
                            trend = "🔥 高频"
                        elif avg_interval <= 5:
                            trend = "📈 上升"
                        else:
                            trend = "📊 稳定"
                    else:
                        trend = "📊 稳定"
                else:
                    trend = "📊 稳定"
                
                results[topic] = {
                    "count": stats["count"],
                    "trend": trend,
                    "last_seen": dates[-1] if dates else "",
                    "avg_score": sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
                }
        
        # 按频率排序
        return dict(sorted(results.items(), key=lambda x: -x[1]["count"])[:20])
    
    def get_seasonal_trends(self) -> List[str]:
        """获取当前月份的季节性趋势"""
        month = datetime.now().month
        return self.SEASONAL_EVENTS.get(month, [])
    
    def predict_trends(self, current_topics: List[str] = None) -> Dict:
        """
        预测未来热点
        
        返回: {
            "hot_topics": [可能爆发的话题],
            "seasonal": [季节性事件],
            "recurring": [周期性出现的话题],
            "suggestion": "预测建议文本"
        }
        """
        # 1. 分析历史频率
        freq_analysis = self.analyze_topic_frequency(days=30)
        
        # 2. 获取季节性趋势
        seasonal = self.get_seasonal_trends()
        
        # 3. 识别周期性话题（出现≥3次且最近7天出现过）
        recurring = []
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        for topic, stats in freq_analysis.items():
            if stats["count"] >= 3 and stats["last_seen"] >= week_ago:
                recurring.append({
                    "topic": topic,
                    "count": stats["count"],
                    "trend": stats["trend"]
                })
        
        # 4. 预测可能爆发的话题
        hot_topics = []
        
        # 频率高且趋势上升的话题
        for topic, stats in freq_analysis.items():
            if "上升" in stats["trend"] or "高频" in stats["trend"]:
                hot_topics.append(topic)
        
        # 结合当前热点
        if current_topics:
            for topic in current_topics:
                if topic in freq_analysis:
                    hot_topics.append(topic)
        
        # 去重
        hot_topics = list(dict.fromkeys(hot_topics))[:10]
        
        return {
            "hot_topics": hot_topics,
            "seasonal": seasonal,
            "recurring": recurring[:5],
            "suggestion": self._generate_suggestion(hot_topics, seasonal, recurring)
        }
    
    def _generate_suggestion(self, hot_topics: List[str], seasonal: List[str], 
                            recurring: List[Dict]) -> str:
        """生成预测建议文本"""
        lines = []
        
        if hot_topics:
            lines.append(f"📈 趋势上升话题: {', '.join(hot_topics[:5])}")
        
        if seasonal:
            lines.append(f"📅 本月季节性事件: {', '.join(seasonal)}")
        
        if recurring:
            topics_str = ', '.join([r['topic'] for r in recurring[:3]])
            lines.append(f"🔄 周期性话题: {topics_str}")
        
        if lines:
            lines.append("💡 建议: 优先关注趋势上升话题，结合季节性事件提供前瞻性分析")
        
        return '\n'.join(lines)
    
    def generate_prompt_insight(self) -> str:
        """
        生成用于Prompt的预测洞察
        
        返回: 可注入到Prompt中的文本
        """
        prediction = self.predict_trends()
        
        if not prediction["hot_topics"] and not prediction["seasonal"]:
            return ""
        
        lines = ["\n### 🔮 趋势预测洞察\n"]
        
        if prediction["hot_topics"]:
            lines.append("**可能持续发酵的话题**:")
            for topic in prediction["hot_topics"][:5]:
                lines.append(f"- {topic}")
            lines.append("")
        
        if prediction["seasonal"]:
            lines.append(f"**本月值得关注的季节性事件**: {', '.join(prediction['seasonal'])}")
            lines.append("")
        
        if prediction["recurring"]:
            lines.append("**周期性出现的热点**（可能再次爆发）:")
            for r in prediction["recurring"][:3]:
                lines.append(f"- {r['topic']} ({r['trend']}, 已出现{r['count']}次)")
            lines.append("")
        
        lines.append("**建议**: 在分析今日热点时，考虑以上话题的延续性和关联性，提供前瞻性判断。\n")
        
        return "\n".join(lines)


# 便捷函数
def get_trend_insight(trendradar_path: str = ".") -> str:
    """获取趋势预测洞察（用于Prompt注入）"""
    predictor = TrendPredictor(trendradar_path)
    return predictor.generate_prompt_insight()


def get_hot_predictions(trendradar_path: str = ".") -> Dict:
    """获取热点预测"""
    predictor = TrendPredictor(trendradar_path)
    return predictor.predict_trends()


if __name__ == "__main__":
    # 测试
    predictor = TrendPredictor()
    prediction = predictor.predict_trends()
    print("=== 热点预测 ===")
    print(f"趋势话题: {prediction['hot_topics'][:5]}")
    print(f"季节性: {prediction['seasonal']}")
    print(f"周期性: {[r['topic'] for r in prediction['recurring'][:3]]}")
    print(f"\n建议:\n{prediction['suggestion']}")
