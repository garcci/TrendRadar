# -*- coding: utf-8 -*-
"""
热点预测引擎 - 提前发现未来热点

问题：
1. 系统只能被动响应已有热点
2. 错过新兴趋势的最早阶段
3. 没有利用历史数据的周期性规律

解决方案：
1. 分析历史热点的周期性模式
2. 检测新兴话题的加速增长
3. 跨平台关联分析
4. 生成预测性内容建议

预测维度：
- 周期性事件（发布会、财报季、节假日）
- 技术周期（新产品周期、版本发布）
- 社会周期（政策周期、行业大会）
- 突发事件的持续影响
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TrendPrediction:
    """趋势预测"""
    topic: str
    confidence: float  # 0-1
    predicted_date: str
    category: str  # 'tech', 'finance', 'policy', 'social'
    reasoning: str
    source_signals: List[str]
    suggested_action: str


@dataclass
class HistoricalPattern:
    """历史模式"""
    pattern_name: str
    cycle_days: int  # 周期天数
    keywords: List[str]
    typical_months: List[int]  # 典型月份
    last_occurrence: str
    next_predicted: str
    confidence: float


class TrendForecastEngine:
    """热点预测引擎"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.predictions_file = f"{trendradar_path}/evolution/trend_predictions.json"
        self.patterns_file = f"{trendradar_path}/evolution/historical_patterns.json"
        
        # 初始化已知周期性模式
        self.known_patterns = self._init_known_patterns()
    
    def _init_known_patterns(self) -> List[HistoricalPattern]:
        """初始化已知的周期性模式"""
        return [
            HistoricalPattern(
                pattern_name="Apple发布会周期",
                cycle_days=365,
                keywords=["Apple", "iPhone", "WWDC", "发布会"],
                typical_months=[3, 6, 9, 10],
                last_occurrence="2025-09",
                next_predicted="2026-06",
                confidence=0.9
            ),
            HistoricalPattern(
                pattern_name="Google I/O",
                cycle_days=365,
                keywords=["Google", "Android", "AI", "I/O"],
                typical_months=[5],
                last_occurrence="2025-05",
                next_predicted="2026-05",
                confidence=0.9
            ),
            HistoricalPattern(
                pattern_name="CES消费电子展",
                cycle_days=365,
                keywords=["CES", "消费电子", "新品", "拉斯维加斯"],
                typical_months=[1],
                last_occurrence="2026-01",
                next_predicted="2027-01",
                confidence=0.95
            ),
            HistoricalPattern(
                pattern_name="双11电商节",
                cycle_days=365,
                keywords=["双11", "电商", "购物节", "促销"],
                typical_months=[11],
                last_occurrence="2025-11",
                next_predicted="2026-11",
                confidence=0.95
            ),
            HistoricalPattern(
                pattern_name="财报季",
                cycle_days=90,
                keywords=["财报", "季度", "营收", "利润", "Q1", "Q2", "Q3", "Q4"],
                typical_months=[2, 5, 8, 11],
                last_occurrence="2026-02",
                next_predicted="2026-05",
                confidence=0.85
            ),
            HistoricalPattern(
                pattern_name="AI模型发布潮",
                cycle_days=60,
                keywords=["GPT", "大模型", "发布", "Claude", "Gemini", "Llama"],
                typical_months=[],
                last_occurrence="2026-04",
                next_predicted="2026-06",
                confidence=0.6
            ),
            HistoricalPattern(
                pattern_name="开源峰会",
                cycle_days=180,
                keywords=["开源", "GitHub", "Linux", "基金会", "峰会"],
                typical_months=[3, 9],
                last_occurrence="2025-09",
                next_predicted="2026-03",
                confidence=0.7
            )
        ]
    
    def analyze_upcoming_events(self, days_ahead: int = 14) -> List[TrendPrediction]:
        """
        分析即将到来的热点事件
        
        Args:
            days_ahead: 预测未来多少天
        
        Returns:
            预测列表
        """
        predictions = []
        now = datetime.now()
        target_date = now + timedelta(days=days_ahead)
        
        for pattern in self.known_patterns:
            # 检查是否在预测窗口内
            try:
                next_date = datetime.strptime(pattern.next_predicted, "%Y-%m")
            except:
                continue
            
            if now <= next_date <= target_date:
                confidence = pattern.confidence
                
                # 如果接近目标日期，提高置信度
                days_until = (next_date - now).days
                if days_until < 7:
                    confidence = min(1.0, confidence + 0.1)
                
                prediction = TrendPrediction(
                    topic=f"{pattern.pattern_name} ({pattern.next_predicted})",
                    confidence=confidence,
                    predicted_date=pattern.next_predicted,
                    category="tech",
                    reasoning=f"基于历史周期性分析，{pattern.pattern_name}预计将在{pattern.next_predicted}到来",
                    source_signals=[
                        f"历史周期: {pattern.cycle_days}天",
                        f"上次发生: {pattern.last_occurrence}",
                        f"关键词: {', '.join(pattern.keywords[:3])}"
                    ],
                    suggested_action=f"提前准备{pattern.keywords[0]}相关内容"
                )
                predictions.append(prediction)
        
        # 添加基于当前时间的季节性预测
        current_month = now.month
        seasonal = self._get_seasonal_predictions(current_month, days_ahead)
        predictions.extend(seasonal)
        
        # 按置信度排序
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        return predictions
    
    def _get_seasonal_predictions(self, current_month: int, days_ahead: int) -> List[TrendPrediction]:
        """获取季节性预测"""
        predictions = []
        
        # 年中总结
        if current_month == 6:
            predictions.append(TrendPrediction(
                topic="年中技术总结与展望",
                confidence=0.8,
                predicted_date=(datetime.now() + timedelta(days=15)).strftime("%Y-%m"),
                category="tech",
                reasoning="每年6月各大科技公司发布年中总结",
                source_signals=["周期性", "行业惯例"],
                suggested_action="准备上半年技术趋势回顾"
            ))
        
        # 年底盘点
        if current_month == 12:
            predictions.append(TrendPrediction(
                topic="年度技术盘点",
                confidence=0.9,
                predicted_date=(datetime.now() + timedelta(days=15)).strftime("%Y-%m"),
                category="tech",
                reasoning="年底各大媒体和公司发布年度总结",
                source_signals=["周期性", "媒体惯例"],
                suggested_action="准备年度技术回顾文章"
            ))
        
        # 开学季
        if current_month == 9:
            predictions.append(TrendPrediction(
                topic="开学季教育科技",
                confidence=0.7,
                predicted_date=(datetime.now() + timedelta(days=10)).strftime("%Y-%m"),
                category="tech",
                reasoning="9月开学季，教育科技话题升温",
                source_signals=["季节性", "教育周期"],
                suggested_action="关注AI教育应用"
            ))
        
        return predictions
    
    def detect_emerging_trends(self, recent_topics: List[str], 
                               historical_topics: List[str]) -> List[TrendPrediction]:
        """
        检测新兴趋势
        
        通过比较近期话题与历史话题，发现新出现的热点
        """
        predictions = []
        
        # 简单的新话题检测（实际应该用更复杂的算法）
        recent_set = set(recent_topics)
        historical_set = set(historical_topics)
        
        new_topics = recent_set - historical_set
        
        for topic in list(new_topics)[:5]:  # 最多5个
            predictions.append(TrendPrediction(
                topic=topic,
                confidence=0.6,
                predicted_date=datetime.now().strftime("%Y-%m-%d"),
                category="emerging",
                reasoning="该话题近期首次出现，可能是新兴趋势",
                source_signals=["新话题检测", "对比历史数据"],
                suggested_action=f"跟踪{topic}的发展"
            ))
        
        return predictions
    
    def generate_content_suggestions(self, predictions: List[TrendPrediction]) -> List[Dict]:
        """
        基于预测生成内容建议
        
        为每个预测生成具体的内容创作建议
        """
        suggestions = []
        
        for pred in predictions:
            if pred.confidence < 0.5:
                continue
            
            suggestion = {
                "topic": pred.topic,
                "priority": "high" if pred.confidence > 0.8 else "medium",
                "timing": f"建议在 {pred.predicted_date} 前准备",
                "content_type": self._suggest_content_type(pred),
                "angles": self._suggest_angles(pred),
                "estimated_quality": min(10.0, 6.0 + pred.confidence * 4)
            }
            suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_content_type(self, prediction: TrendPrediction) -> str:
        """建议内容类型"""
        if "发布会" in prediction.topic or "CES" in prediction.topic:
            return "前瞻分析 + 实时跟踪"
        elif "财报" in prediction.topic:
            return "数据解读 + 对比分析"
        elif "总结" in prediction.topic or "盘点" in prediction.topic:
            return "年度/季度回顾"
        else:
            return "深度分析"
    
    def _suggest_angles(self, prediction: TrendPrediction) -> List[str]:
        """建议分析角度"""
        angles = ["技术影响", "市场反应"]
        
        if "AI" in prediction.topic or "模型" in prediction.topic:
            angles.extend(["性能对比", "应用场景", "开源影响"])
        elif "财报" in prediction.topic:
            angles.extend(["同比分析", "业务拆分", "未来指引"])
        elif "发布" in prediction.topic:
            angles.extend(["竞品对比", "用户反馈", "供应链分析"])
        
        return angles
    
    def get_prediction_summary(self) -> str:
        """获取预测摘要（用于注入Prompt）"""
        predictions = self.analyze_upcoming_events(14)
        
        if not predictions:
            return ""
        
        summary = "\n\n### 🔮 热点预测（未来14天）\n"
        
        for pred in predictions[:3]:  # 最多3个
            icon = "🔴" if pred.confidence > 0.8 else "🟡" if pred.confidence > 0.6 else "🟢"
            summary += f"{icon} {pred.topic} (置信度: {pred.confidence:.0%})\n"
            summary += f"   建议: {pred.suggested_action}\n"
        
        return summary
    
    def save_predictions(self, predictions: List[TrendPrediction]):
        """保存预测到历史记录"""
        try:
            records = []
            if os.path.exists(self.predictions_file):
                with open(self.predictions_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            
            for pred in predictions:
                records.append({
                    "topic": pred.topic,
                    "confidence": pred.confidence,
                    "predicted_date": pred.predicted_date,
                    "category": pred.category,
                    "reasoning": pred.reasoning,
                    "created_at": datetime.now().isoformat()
                })
            
            # 只保留最近90天的预测
            cutoff = (datetime.now() - timedelta(days=90)).isoformat()
            records = [r for r in records if r.get("created_at", "") > cutoff]
            
            os.makedirs(os.path.dirname(self.predictions_file), exist_ok=True)
            with open(self.predictions_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[热点预测] 保存预测失败: {e}")


# 便捷函数
def get_trend_predictions(trendradar_path: str = ".") -> str:
    """
    获取热点预测（用于注入Prompt）
    
    这是热点预测引擎的入口点
    """
    engine = TrendForecastEngine(trendradar_path)
    return engine.get_prediction_summary()


def get_content_suggestions(trendradar_path: str = ".") -> List[Dict]:
    """获取内容建议"""
    engine = TrendForecastEngine(trendradar_path)
    predictions = engine.analyze_upcoming_events(14)
    return engine.generate_content_suggestions(predictions)
