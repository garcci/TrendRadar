# -*- coding: utf-8 -*-
"""
实时热点追踪 - 缩短响应时间，提升时效性

核心理念：
1. 重大热点事件需要快速响应
2. 识别突发性和紧急性话题
3. 根据热点紧急程度调整发布策略

识别信号：
- 突发性关键词：突发、紧急、刚刚、最新消息
- 多平台同步爆发：同一话题在多个平台同时出现
- 情感强度突变：情感强度突然增强
- 高影响力实体：涉及大公司/大人物的话题

响应策略：
- 紧急: 立即生成并发布（涉及重大事件）
- 重要: 正常生成并发布（有价值的热点）
- 一般: 按常规流程处理
"""

import re
from typing import Dict, List, Tuple


class RealTimeTracker:
    """实时热点追踪器"""
    
    # 突发性关键词
    URGENT_KEYWORDS = [
        "突发", "紧急", "刚刚", "最新消息", "重磅", "爆炸性", "独家",
        "快讯", "速报", "Breaking", "Urgent", "突发新闻"
    ]
    
    # 高影响力实体（涉及这些实体的消息更紧急）
    HIGH_IMPACT_ENTITIES = [
        "英伟达", "NVIDIA", "OpenAI", "Google", "谷歌", "微软", "Microsoft",
        "苹果", "Apple", "特斯拉", "Tesla", "马斯克", "Elon Musk",
        "美联储", "央行", "证监会", "国务院", "白宫", "五角大楼"
    ]
    
    # 紧急事件类型
    URGENT_EVENTS = [
        "发布", "发布会", "财报", "收购", "并购", "上市", "退市",
        "裁员", "罢工", " outage", "宕机", "泄露", "攻击", "制裁"
    ]
    
    def __init__(self):
        pass
    
    def analyze_urgency(self, titles: List[str]) -> Dict:
        """
        分析热点紧急程度
        
        返回: {
            "level": "urgent|important|normal",
            "score": 紧急分数 (0-10),
            "reason": 原因,
            "urgent_topics": [紧急话题列表]
        }
        """
        if not titles:
            return {"level": "normal", "score": 0, "reason": "无热点数据", "urgent_topics": []}
        
        urgent_count = 0
        important_count = 0
        urgent_topics = []
        
        for title in titles:
            score = 0
            reasons = []
            
            # 1. 检测突发性关键词
            for keyword in self.URGENT_KEYWORDS:
                if keyword in title:
                    score += 3
                    reasons.append(f"突发关键词: {keyword}")
                    break
            
            # 2. 检测高影响力实体
            for entity in self.HIGH_IMPACT_ENTITIES:
                if entity in title:
                    score += 2
                    reasons.append(f"高影响力实体: {entity}")
                    break
            
            # 3. 检测紧急事件类型
            for event in self.URGENT_EVENTS:
                if event in title:
                    score += 1
                    reasons.append(f"事件类型: {event}")
                    break
            
            # 4. 检测负面/危机信号
            crisis_words = ["危机", "风险", "故障", "泄露", "攻击", "下跌", "暴跌"]
            for word in crisis_words:
                if word in title:
                    score += 1
                    reasons.append(f"危机信号: {word}")
                    break
            
            if score >= 4:
                urgent_count += 1
                urgent_topics.append({
                    "title": title[:50],
                    "score": score,
                    "reasons": reasons
                })
            elif score >= 2:
                important_count += 1
        
        # 计算整体紧急程度
        total = len(titles)
        urgent_ratio = urgent_count / total if total > 0 else 0
        important_ratio = important_count / total if total > 0 else 0
        
        if urgent_ratio >= 0.1 or urgent_count >= 3:
            level = "urgent"
            overall_score = min(10, 5 + urgent_count * 2)
            reason = f"检测到 {urgent_count} 个紧急话题，建议立即发布"
        elif important_ratio >= 0.2 or important_count >= 5:
            level = "important"
            overall_score = min(7, 3 + important_count)
            reason = f"检测到 {important_count} 个重要话题，建议正常发布"
        else:
            level = "normal"
            overall_score = 3
            reason = "无特别紧急的热点，按常规流程处理"
        
        return {
            "level": level,
            "score": overall_score,
            "reason": reason,
            "urgent_topics": sorted(urgent_topics, key=lambda x: -x["score"])[:5],
            "urgent_count": urgent_count,
            "important_count": important_count
        }
    
    def generate_urgency_insight(self, titles: List[str]) -> str:
        """生成紧急度洞察（用于Prompt注入）"""
        analysis = self.analyze_urgency(titles)
        
        if analysis["level"] == "normal":
            return ""
        
        lines = ["\n### ⚡ 实时热点追踪\n"]
        
        level_emoji = {"urgent": "🚨", "important": "⚠️", "normal": "✅"}
        lines.append(f"**紧急等级**: {level_emoji.get(analysis['level'], '')} {analysis['level'].upper()} (评分: {analysis['score']}/10)")
        lines.append(f"**原因**: {analysis['reason']}")
        lines.append("")
        
        if analysis["urgent_topics"]:
            lines.append("**紧急话题**:")
            for topic in analysis["urgent_topics"]:
                lines.append(f"- [{topic['score']}分] {topic['title']}...")
                if topic['reasons']:
                    lines.append(f"  原因: {'; '.join(topic['reasons'][:2])}")
            lines.append("")
        
        lines.append("**写作建议**: 优先处理紧急话题，提供快速、准确的分析，注意事实核查。\n")
        
        return "\n".join(lines)


# 便捷函数
def get_urgency_insight(titles: List[str]) -> str:
    """获取紧急度洞察"""
    tracker = RealTimeTracker()
    return tracker.generate_urgency_insight(titles)


if __name__ == "__main__":
    # 测试
    test_titles = [
        "突发：英伟达发布新一代AI芯片",
        "紧急：OpenAI服务中断，影响数百万用户",
        "最新消息：美联储宣布降息",
        "特斯拉财报超预期，股价大涨",
        "某科技公司发布新产品",
        "行业分析：云计算市场趋势"
    ]
    
    tracker = RealTimeTracker()
    result = tracker.analyze_urgency(test_titles)
    print(f"紧急等级: {result['level']}")
    print(f"评分: {result['score']}/10")
    print(f"紧急话题: {len(result['urgent_topics'])}个")
    print("\n洞察:")
    print(tracker.generate_urgency_insight(test_titles))
