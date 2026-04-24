# -*- coding: utf-8 -*-
"""
情感分析系统 - 分析热点情感倾向，提升文章客观性

核心理念：
1. 了解热点的情感倾向有助于提供更全面的分析
2. 争议性话题需要特别标注，提醒保持客观
3. 情感极端的话题可能不适合深入讨论

分析维度：
- 整体情感倾向：正面/负面/中性
- 情感强度：弱/中/强
- 争议度：情感两极分化的程度
- 情绪关键词：引发情感的关键词

实现方式：
- 基于情感词典的本地分析（零API成本）
- 中文正面/负面情感词库
- 简单的加权计算

输出：
- 情感分析报告
- 争议话题列表
- Prompt增强建议
"""

import re
from collections import Counter
from typing import Dict, List, Tuple


class EmotionAnalyzer:
    """情感分析器"""
    
    # 正面情感词库
    POSITIVE_WORDS = {
        '突破', '创新', '领先', '成功', '增长', '提升', '优化', '改进', '胜利', '成就',
        '赞', '好', '优秀', '强大', '繁荣', '利好', '上升', '进步', '高效', '稳定',
        '赞赏', '支持', '欢迎', '期待', '兴奋', '惊喜', '满意', '认可', '肯定', '优势',
        '冠军', '第一', '最佳', '卓越', '杰出', '完美', '理想', '希望', '机会', '潜力',
        '火爆', '热门', '追捧', '青睐', '看好', '推荐', '爆款', '网红', '现象级',
        '开源', '免费', '福利', '优惠', '降价', '补贴', '奖励', '赠品', '升级'
    }
    
    # 负面情感词库
    NEGATIVE_WORDS = {
        '危机', '风险', '问题', '故障', '漏洞', '攻击', '泄露', '丑闻', '腐败', '欺诈',
        '失败', '下降', '亏损', '裁员', '倒闭', '破产', '下滑', '衰退', '萎缩', '停滞',
        '差', '糟糕', '恶劣', '严重', '危险', '可怕', '恐怖', '灾难', '悲剧', '痛心',
        '愤怒', '不满', '抱怨', '质疑', '批评', '谴责', '抵制', '抗议', '反对', '担忧',
        '焦虑', '恐慌', '紧张', '压力', '困境', '麻烦', '障碍', '阻力', '挑战', '威胁',
        '封禁', '下架', '删除', '屏蔽', '限制', '禁止', '违规', '违法', '犯罪', '起诉',
        '暴跌', '崩盘', '腰斩', '跳水', '重挫', '大跌', '抛售', '逃离', '撤离'
    }
    
    # 争议性话题标志词（容易引发两极分化）
    CONTROVERSIAL_MARKERS = {
        '争议', '争论', '辩论', '对立', '分歧', '冲突', '矛盾', '抵制', '抗议',
        '举报', '投诉', '维权', '曝光', '爆料', '揭秘', '内幕', '黑幕',
        '撕逼', '互怼', '口水战', '论战', '骂战', '宣战', '反击', '回应',
        '反转', '打脸', '实锤', '辟谣', '澄清', '道歉', '追责', '问责'
    }
    
    # 情感强度修饰词
    INTENSIFIERS = {
        '非常', '极其', '特别', '十分', '相当', '很', '太', '最', '绝对', '完全',
        '彻底', '根本', '简直', '实在', '确实', '明显', '显著', '大幅', '剧烈'
    }
    
    def __init__(self):
        pass
    
    def analyze_text(self, text: str) -> Dict:
        """
        分析单条文本的情感
        
        返回: {
            "sentiment": "positive|negative|neutral",
            "score": 情感分数 (-1到1),
            "intensity": "weak|medium|strong",
            "positive_words": [正面词列表],
            "negative_words": [负面词列表],
            "is_controversial": 是否争议性
        }
        """
        if not text:
            return {"sentiment": "neutral", "score": 0, "intensity": "weak", 
                   "positive_words": [], "negative_words": [], "is_controversial": False}
        
        pos_count = 0
        neg_count = 0
        pos_words = []
        neg_words = []
        
        # 检测正面词
        for word in self.POSITIVE_WORDS:
            if word in text:
                count = text.count(word)
                pos_count += count
                pos_words.extend([word] * count)
        
        # 检测负面词
        for word in self.NEGATIVE_WORDS:
            if word in text:
                count = text.count(word)
                neg_count += count
                neg_words.extend([word] * count)
        
        # 计算情感分数
        total = pos_count + neg_count
        if total == 0:
            sentiment = "neutral"
            score = 0
        else:
            score = (pos_count - neg_count) / total
            if score > 0.2:
                sentiment = "positive"
            elif score < -0.2:
                sentiment = "negative"
            else:
                sentiment = "neutral"
        
        # 计算强度
        intensity = self._calculate_intensity(text, total)
        
        # 检测争议性
        is_controversial = self._check_controversial(text)
        
        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "intensity": intensity,
            "positive_words": list(set(pos_words)),
            "negative_words": list(set(neg_words)),
            "is_controversial": is_controversial
        }
    
    def _calculate_intensity(self, text: str, emotion_count: int) -> str:
        """计算情感强度"""
        # 基础强度
        if emotion_count >= 5:
            base_intensity = 3
        elif emotion_count >= 2:
            base_intensity = 2
        else:
            base_intensity = 1
        
        # 修饰词加成
        intensifier_count = sum(1 for word in self.INTENSIFIERS if word in text)
        
        total = base_intensity + min(intensifier_count, 2)
        
        if total >= 4:
            return "strong"
        elif total >= 2:
            return "medium"
        else:
            return "weak"
    
    def _check_controversial(self, text: str) -> bool:
        """检测是否争议性话题"""
        marker_count = sum(1 for word in self.CONTROVERSIAL_MARKERS if word in text)
        return marker_count >= 2
    
    def analyze_batch(self, texts: List[str]) -> Dict:
        """
        批量分析多条文本
        
        返回: {
            "overall_sentiment": 整体情感,
            "positive_ratio": 正面比例,
            "negative_ratio": 负面比例,
            "neutral_ratio": 中性比例,
            "controversial_topics": [争议话题],
            "hot_positive": [最热正面话题],
            "hot_negative": [最热负面话题]
        }
        """
        results = [self.analyze_text(text) for text in texts if text]
        
        if not results:
            return {"overall_sentiment": "neutral", "positive_ratio": 0, 
                   "negative_ratio": 0, "neutral_ratio": 1, 
                   "controversial_topics": [], "hot_positive": [], "hot_negative": []}
        
        total = len(results)
        positive = sum(1 for r in results if r["sentiment"] == "positive")
        negative = sum(1 for r in results if r["sentiment"] == "negative")
        neutral = sum(1 for r in results if r["sentiment"] == "neutral")
        
        # 整体情感
        if positive > negative and positive > neutral:
            overall = "positive"
        elif negative > positive and negative > neutral:
            overall = "negative"
        else:
            overall = "neutral"
        
        # 争议话题
        controversial = [texts[i] for i, r in enumerate(results) if r["is_controversial"]]
        
        # 最热正面话题（按正面词数量排序）
        positive_items = [(texts[i], len(r["positive_words"])) 
                         for i, r in enumerate(results) if r["sentiment"] == "positive"]
        positive_items.sort(key=lambda x: -x[1])
        
        # 最热负面话题
        negative_items = [(texts[i], len(r["negative_words"])) 
                         for i, r in enumerate(results) if r["sentiment"] == "negative"]
        negative_items.sort(key=lambda x: -x[1])
        
        return {
            "overall_sentiment": overall,
            "positive_ratio": round(positive / total, 2),
            "negative_ratio": round(negative / total, 2),
            "neutral_ratio": round(neutral / total, 2),
            "controversial_topics": controversial[:5],
            "hot_positive": [item[0][:50] for item in positive_items[:3]],
            "hot_negative": [item[0][:50] for item in negative_items[:3]],
            "strong_emotion_count": sum(1 for r in results if r["intensity"] == "strong")
        }
    
    def generate_emotion_insight(self, texts: List[str]) -> str:
        """
        生成情感分析洞察（用于Prompt注入）
        
        返回: 可注入到Prompt中的文本
        """
        analysis = self.analyze_batch(texts)
        
        if analysis["neutral_ratio"] == 1:
            return ""
        
        lines = ["\n### 😊😠 情感分析洞察\n"]
        
        # 整体情感
        sentiment_emoji = {"positive": "😊 整体偏正面", "negative": "😠 整体偏负面", "neutral": "😐 整体中性"}
        lines.append(f"**{sentiment_emoji.get(analysis['overall_sentiment'], '')}**")
        lines.append(f"- 正面: {analysis['positive_ratio']*100:.0f}% | 负面: {analysis['negative_ratio']*100:.0f}% | 中性: {analysis['neutral_ratio']*100:.0f}%")
        lines.append("")
        
        # 争议话题提醒
        if analysis["controversial_topics"]:
            lines.append("⚠️ **争议性话题**（注意保持客观中立）:")
            for topic in analysis["controversial_topics"][:3]:
                lines.append(f"- {topic[:60]}...")
            lines.append("")
        
        # 情感极端提醒
        if analysis["strong_emotion_count"] > 0:
            lines.append(f"📢 **强情感话题数**: {analysis['strong_emotion_count']}条")
            lines.append("建议：对强情感话题提供理性分析，避免情绪化表达")
            lines.append("")
        
        # 热门正面/负面
        if analysis["hot_positive"]:
            lines.append(f"😊 **热门正面**: {', '.join(analysis['hot_positive'][:2])}")
        if analysis["hot_negative"]:
            lines.append(f"😠 **热门负面**: {', '.join(analysis['hot_negative'][:2])}")
        lines.append("")
        
        lines.append("**写作建议**: 基于以上情感分析，请在文章中保持客观中立，对争议性话题提供多方观点。\n")
        
        return "\n".join(lines)


# 便捷函数
def get_emotion_insight(titles: List[str]) -> str:
    """获取情感分析洞察（用于Prompt注入）"""
    analyzer = EmotionAnalyzer()
    return analyzer.generate_emotion_insight(titles)


def analyze_emotion(text: str) -> Dict:
    """分析单条文本情感"""
    analyzer = EmotionAnalyzer()
    return analyzer.analyze_text(text)


if __name__ == "__main__":
    # 测试
    test_titles = [
        "OpenAI发布GPT-5，性能大幅提升，开发者欢呼",
        "某科技公司大规模裁员，员工愤怒抗议",
        "新产品发布引发争议，用户褒贬不一",
        "技术突破！国产芯片取得重大进展",
        "数据泄露事件曝光，用户隐私受到威胁",
        "行业报告：AI市场持续增长，前景广阔"
    ]
    
    analyzer = EmotionAnalyzer()
    insight = analyzer.generate_emotion_insight(test_titles)
    print(insight)
    
    print("\n=== 单条分析 ===")
    for title in test_titles:
        result = analyzer.analyze_text(title)
        print(f"{result['sentiment']:10s} | {result['intensity']:6s} | {title[:40]}...")
