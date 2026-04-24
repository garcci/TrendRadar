# -*- coding: utf-8 -*-
"""
读者画像分析 - 分析读者偏好，优化内容方向

核心理念：
1. 了解读者对什么内容最感兴趣
2. 根据历史数据优化内容策略
3. 识别高价值话题和低价值话题

分析维度：
- 话题热度: 哪些话题反复出现且评分高
- 内容类型偏好: 技术深度 vs 行业分析 vs 产品评测
- 标签效果: 哪些标签的文章评分更高
- 时间偏好: 什么时段发布效果更好（简化版）

输出：
- 读者偏好报告
- 内容优化建议
- 高价值话题推荐
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ReaderAnalytics:
    """读者画像分析器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
    
    def analyze_topic_preferences(self, days: int = 30) -> Dict:
        """分析话题偏好"""
        if not os.path.exists(self.metrics_file):
            return {"error": "No metrics data"}
        
        try:
            with open(self.metrics_file, 'r') as f:
                metrics = json.load(f)
        except Exception:
            return {"error": "Failed to load metrics"}
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent_metrics = [m for m in metrics if m.get("timestamp", "") > cutoff]
        
        if not recent_metrics:
            return {"error": "No recent metrics"}
        
        # 1. 话题热度分析
        topic_scores = defaultdict(list)
        for metric in recent_metrics:
            score = metric.get("overall_score", 0)
            keywords = metric.get("keywords", [])
            hot_topics = metric.get("hot_topics", [])
            
            for topic in keywords + hot_topics:
                if len(topic) >= 2:
                    topic_scores[topic].append(score)
        
        # 计算每个话题的平均分
        topic_avg = {}
        for topic, scores in topic_scores.items():
            if len(scores) >= 2:  # 至少出现2次
                avg = sum(scores) / len(scores)
                topic_avg[topic] = {
                    "avg_score": round(avg, 1),
                    "count": len(scores),
                    "trend": "🔥 热门" if avg >= 8 else "📈 上升" if avg >= 6 else "📊 一般"
                }
        
        # 2. 内容类型偏好
        content_types = {
            "tech_deep": [],  # 技术深度
            "industry": [],   # 行业分析
            "product": [],    # 产品评测
            "trend": []       # 趋势预测
        }
        
        for metric in recent_metrics:
            score = metric.get("overall_score", 0)
            title = metric.get("title", "")
            
            if any(w in title for w in ["芯片", "GPU", "架构", "算法", "模型"]):
                content_types["tech_deep"].append(score)
            elif any(w in title for w in ["市场", "行业", "财报", "并购", "融资"]):
                content_types["industry"].append(score)
            elif any(w in title for w in ["评测", "体验", "测试", "对比"]):
                content_types["product"].append(score)
            else:
                content_types["trend"].append(score)
        
        type_avg = {}
        for ctype, scores in content_types.items():
            if scores:
                type_avg[ctype] = round(sum(scores) / len(scores), 1)
        
        # 3. 高价值和低价值话题
        sorted_topics = sorted(topic_avg.items(), key=lambda x: -x[1]["avg_score"])
        high_value = sorted_topics[:5]
        low_value = sorted_topics[-5:] if len(sorted_topics) >= 10 else []
        
        return {
            "total_articles": len(recent_metrics),
            "avg_score": round(sum(m.get("overall_score", 0) for m in recent_metrics) / len(recent_metrics), 1),
            "topic_preferences": dict(sorted(topic_avg.items(), key=lambda x: -x[1]["avg_score"])[:10]),
            "content_type_preferences": type_avg,
            "high_value_topics": high_value,
            "low_value_topics": low_value
        }
    
    def generate_reader_insight(self) -> str:
        """生成读者洞察（用于Prompt注入）"""
        analysis = self.analyze_topic_preferences()
        
        if "error" in analysis:
            return ""
        
        lines = ["\n### 👤 读者偏好分析\n"]
        
        # 总体概况
        lines.append(f"**近期文章概况**: {analysis['total_articles']}篇，平均评分 {analysis['avg_score']}/10")
        lines.append("")
        
        # 高价值话题
        if analysis.get("high_value_topics"):
            lines.append("**读者最感兴趣的话题**（高评分）:")
            for topic, data in analysis["high_value_topics"][:3]:
                lines.append(f"- {topic}: {data['avg_score']}分 ({data['count']}篇) {data['trend']}")
            lines.append("")
        
        # 内容类型偏好
        if analysis.get("content_type_preferences"):
            type_names = {
                "tech_deep": "🔧 技术深度", "industry": "🏢 行业分析",
                "product": "📱 产品评测", "trend": "📈 趋势预测"
            }
            lines.append("**内容类型偏好**:")
            for ctype, avg in sorted(analysis["content_type_preferences"].items(), key=lambda x: -x[1]):
                lines.append(f"- {type_names.get(ctype, ctype)}: {avg}分")
            lines.append("")
        
        # 建议
        lines.append("**内容策略建议**:")
        if analysis.get("high_value_topics"):
            top_topic = analysis["high_value_topics"][0][0]
            lines.append(f"- 优先深入分析 '{top_topic}' 相关话题")
        lines.append("- 保持技术深度，读者对技术分析反响最好")
        lines.append("- 避免低分话题的重复讨论")
        lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def get_reader_insight(trendradar_path: str = ".") -> str:
    """获取读者偏好洞察"""
    analytics = ReaderAnalytics(trendradar_path)
    return analytics.generate_reader_insight()


if __name__ == "__main__":
    # 测试
    analytics = ReaderAnalytics()
    insight = analytics.generate_reader_insight()
    print(insight)
