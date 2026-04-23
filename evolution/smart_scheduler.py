# -*- coding: utf-8 -*-
"""
智能调度系统 - 根据质量动态调整生成策略

问题：
1. 每天固定生成文章，但有时没有好内容
2. Token预算固定，无法根据质量调整
3. 文章质量波动时缺乏自适应机制

解决方案：
1. 质量预测 - 根据热点数据预测文章质量
2. 动态预算 - 质量预期高时增加投入，低时减少
3. 智能跳过 - 没有好内容时不硬写
4. 补偿机制 - 跳过后在有好内容时加倍投入
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ScheduleDecision:
    """调度决策"""
    should_generate: bool
    reason: str
    token_budget: int
    temperature: float
    max_tokens: int
    expected_quality: float
    confidence: float


class SmartScheduler:
    """智能调度器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/metrics_history.json"
        
        # 默认配置
        self.default_token_budget = 200000  # 每日默认预算
        self.min_token_budget = 50000  # 最低预算
        self.max_token_budget = 500000  # 最高预算
        self.quality_threshold = 6.0  # 质量阈值，低于此建议跳过
        self.skip_cooldown_days = 2  # 跳过后的冷却期
    
    def make_decision(self, hot_topics: List[str], rss_count: int) -> ScheduleDecision:
        """
        做出生成决策
        
        考虑因素：
        1. 最近文章质量趋势
        2. 今日热点数量和质量
        3. RSS数据丰富度
        4. 历史跳过记录
        """
        # 加载历史指标
        metrics = self._load_recent_metrics(14)
        
        if not metrics:
            # 没有历史数据，使用默认配置
            return ScheduleDecision(
                should_generate=True,
                reason="无历史数据，使用默认配置生成",
                token_budget=self.default_token_budget,
                temperature=0.7,
                max_tokens=4000,
                expected_quality=7.0,
                confidence=0.5
            )
        
        # 计算质量趋势
        recent_scores = [m.get('overall_score', 0) for m in metrics[-7:]]
        avg_quality = sum(recent_scores) / len(recent_scores) if recent_scores else 7.0
        
        # 检测下降趋势
        declining = False
        if len(recent_scores) >= 3:
            declining = all(recent_scores[i] >= recent_scores[i+1] for i in range(len(recent_scores)-1))
        
        # 计算今日内容质量预期
        content_score = self._evaluate_content_quality(hot_topics, rss_count)
        
        # 检查最近是否跳过过
        recent_skips = self._count_recent_skips(metrics)
        
        # 决策逻辑
        if content_score < 3.0 and avg_quality < 6.5:
            # 内容少且质量差，建议跳过
            return ScheduleDecision(
                should_generate=False,
                reason=f"今日内容质量预期低({content_score:.1f})，且近期平均质量({avg_quality:.1f})不高，建议跳过",
                token_budget=0,
                temperature=0.7,
                max_tokens=0,
                expected_quality=content_score,
                confidence=0.7
            )
        
        if declining and avg_quality < 6.0:
            # 质量持续下降，保守策略
            return ScheduleDecision(
                should_generate=True,
                reason=f"质量持续下降，降低预算保守生成",
                token_budget=int(self.default_token_budget * 0.6),
                temperature=0.8,  # 增加随机性
                max_tokens=3500,
                expected_quality=avg_quality * 0.9,
                confidence=0.6
            )
        
        if content_score > 7.0 and avg_quality > 7.5:
            # 内容好且历史质量高，增加投入
            return ScheduleDecision(
                should_generate=True,
                reason=f"内容质量预期高({content_score:.1f})，增加预算深度生成",
                token_budget=int(self.default_token_budget * 1.5),
                temperature=0.6,  # 更稳定
                max_tokens=5000,
                expected_quality=min(9.0, avg_quality * 1.1),
                confidence=0.8
            )
        
        if recent_skips >= 2:
            # 最近跳过多，补偿性生成
            return ScheduleDecision(
                should_generate=True,
                reason=f"已连续跳过{recent_skips}天，补偿性生成",
                token_budget=int(self.default_token_budget * 1.3),
                temperature=0.7,
                max_tokens=4500,
                expected_quality=avg_quality,
                confidence=0.6
            )
        
        # 默认决策
        return ScheduleDecision(
            should_generate=True,
            reason=f"标准生成 (内容质量: {content_score:.1f}, 近期平均: {avg_quality:.1f})",
            token_budget=self.default_token_budget,
            temperature=0.7,
            max_tokens=4000,
            expected_quality=avg_quality,
            confidence=0.6
        )
    
    def get_budget_adjustment(self, actual_quality: float, expected_quality: float) -> str:
        """
        根据实际质量调整未来预算
        
        Returns:
            调整建议
        """
        ratio = actual_quality / expected_quality if expected_quality > 0 else 1.0
        
        if ratio > 1.2:
            return "实际质量超预期，下次可适当增加预算"
        elif ratio < 0.8:
            return "实际质量低于预期，建议优化Prompt或减少输入噪声"
        else:
            return "质量符合预期，保持当前策略"
    
    def _evaluate_content_quality(self, hot_topics: List[str], rss_count: int) -> float:
        """
        评估今日内容质量预期
        
        基于：
        1. 热点数量
        2. RSS数据量
        3. 科技内容关键词密度
        """
        score = 5.0  # 基础分
        
        # 热点加分
        score += min(len(hot_topics) * 0.3, 2.0)
        
        # RSS加分
        score += min(rss_count * 0.1, 2.0)
        
        # 科技关键词检测
        tech_keywords = ['AI', '人工智能', '芯片', '开源', '算法', '模型', 'GPT', '科技']
        tech_count = sum(1 for topic in hot_topics for kw in tech_keywords if kw in topic)
        score += min(tech_count * 0.3, 2.0)
        
        return min(score, 10.0)
    
    def _load_recent_metrics(self, days: int) -> List[Dict]:
        """加载最近指标"""
        try:
            import os
            if not os.path.exists(self.metrics_file):
                return []
            
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            return [d for d in data if d.get('date', '') >= cutoff]
        except Exception:
            return []
    
    def _count_recent_skips(self, metrics: List[Dict]) -> int:
        """计算最近跳过的天数"""
        # 如果metrics中没有记录，说明那天可能跳过了
        # 简化处理：检查最近7天中有多少天有记录
        recent_dates = set(m['date'] for m in metrics[-7:])
        
        # 检查最近7天
        skipped = 0
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            if date not in recent_dates:
                skipped += 1
        
        return skipped


# 便捷函数
def get_smart_schedule_config(trendradar_path: str, hot_topics: List[str], 
                              rss_count: int) -> Dict:
    """
    获取智能调度配置
    
    这是智能调度系统的入口点
    """
    scheduler = SmartScheduler(trendradar_path)
    decision = scheduler.make_decision(hot_topics, rss_count)
    
    return {
        'should_generate': decision.should_generate,
        'reason': decision.reason,
        'token_budget': decision.token_budget,
        'temperature': decision.temperature,
        'max_tokens': decision.max_tokens,
        'expected_quality': decision.expected_quality,
        'confidence': decision.confidence
    }
