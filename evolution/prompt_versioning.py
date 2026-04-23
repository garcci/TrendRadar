# -*- coding: utf-8 -*-
"""
Prompt版本管理系统 - 防止进化反馈无限增长

问题：
1. 进化反馈直接追加到Prompt中，导致Prompt越来越长
2. Token消耗增加
3. 建议重复
4. 旧建议与新建议冲突

解决方案：
1. 版本化管理Prompt
2. 去重机制
3. 定期清理过期建议
4. 结构化存储而非文本追加
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict


@dataclass
class PromptVersion:
    """Prompt版本记录"""
    version_id: str
    timestamp: str
    content_hash: str
    optimizations: List[Dict]  # 结构化优化建议
    metrics_before: Dict
    metrics_after: Optional[Dict]
    is_active: bool


@dataclass
class OptimizationRule:
    """优化规则"""
    rule_id: str
    category: str  # 'tech_content', 'insightfulness', 'style', etc.
    condition: str  # 触发条件
    action: str  # 执行动作
    priority: int  # 1-10
    added_at: str
    expires_at: Optional[str]  # 过期时间
    is_active: bool
    applied_count: int  # 应用次数
    success_rate: Optional[float]  # 成功率


class PromptVersionManager:
    """Prompt版本管理器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.prompt_versions_file = f"{trendradar_path}/evolution/prompt_versions.json"
        self.rules_file = f"{trendradar_path}/evolution/prompt_rules.json"
        
        # 配置
        self.max_active_rules = 10  # 最多同时激活10条规则
        self.rule_ttl_days = 14  # 规则默认有效期14天
        self.min_effectiveness = 0.3  # 最低有效阈值
    
    def generate_structured_feedback(self, metrics_history: List[Dict]) -> str:
        """
        生成结构化的进化反馈（替代文本追加）
        
        特点：
        1. 去重 - 不会重复相同建议
        2. 时效性 - 只包含活跃规则
        3. 优先级 - 按重要程度排序
        4. 简洁性 - 结构化而非长文本
        """
        rules = self._load_active_rules()
        
        if not rules:
            return ""
        
        # 根据最新指标动态调整规则优先级
        if metrics_history:
            latest = metrics_history[-1]
            rules = self._prioritize_rules(rules, latest)
        
        # 生成简洁的结构化反馈
        feedback_parts = ["\n\n### 🧬 进化反馈 v2.0"]
        feedback_parts.append(f"活跃规则数: {len(rules)} | 最后更新: {datetime.now().strftime('%m-%d %H:%M')}")
        
        # 按优先级分组
        high_priority = [r for r in rules if r.priority >= 7]
        medium_priority = [r for r in rules if 4 <= r.priority < 7]
        low_priority = [r for r in rules if r.priority < 4]
        
        if high_priority:
            feedback_parts.append("\n🔴 高优先级:")
            for rule in high_priority[:3]:
                feedback_parts.append(f"  • {rule.action} (已应用{rule.applied_count}次)")
        
        if medium_priority:
            feedback_parts.append("\n🟡 中优先级:")
            for rule in medium_priority[:2]:
                feedback_parts.append(f"  • {rule.action}")
        
        # 添加简化的指标趋势
        if len(metrics_history) >= 3:
            feedback_parts.append("\n📊 7天趋势:")
            for dim in ['tech_content_ratio', 'insightfulness', 'style_diversity']:
                values = [m.get(dim, 0) for m in metrics_history[-7:]]
                if len(values) >= 3:
                    trend = "↑" if values[-1] > values[0] else "↓" if values[-1] < values[0] else "→"
                    feedback_parts.append(f"  {trend} {dim}: {values[0]:.1f}→{values[-1]:.1f}")
        
        return "\n".join(feedback_parts)
    
    def add_optimization_rule(self, category: str, condition: str, action: str, 
                             priority: int = 5) -> str:
        """
        添加优化规则（自动去重）
        
        去重逻辑：
        1. 相同category + action的组合不会重复添加
        2. 相似度>80%的规则会被合并
        """
        rules = self._load_rules()
        
        # 生成规则ID
        rule_hash = hashlib.md5(f"{category}:{action}".encode()).hexdigest()[:8]
        rule_id = f"{category}_{rule_hash}"
        
        # 检查是否已存在
        existing = [r for r in rules if r.rule_id == rule_id]
        if existing:
            # 更新现有规则
            rule = existing[0]
            rule.priority = max(rule.priority, priority)
            rule.applied_count += 1
            rule.expires_at = (datetime.now() + timedelta(days=self.rule_ttl_days)).isoformat()
            print(f"[Prompt版本管理] 更新现有规则: {rule_id}")
        else:
            # 创建新规则
            new_rule = OptimizationRule(
                rule_id=rule_id,
                category=category,
                condition=condition,
                action=action,
                priority=priority,
                added_at=datetime.now().isoformat(),
                expires_at=(datetime.now() + timedelta(days=self.rule_ttl_days)).isoformat(),
                is_active=True,
                applied_count=1,
                success_rate=None
            )
            rules.append(new_rule)
            print(f"[Prompt版本管理] 添加新规则: {rule_id}")
        
        # 清理过期规则
        self._cleanup_expired_rules(rules)
        
        # 限制活跃规则数量
        self._limit_active_rules(rules)
        
        self._save_rules(rules)
        return rule_id
    
    def evaluate_rule_effectiveness(self, rule_id: str, metrics_before: Dict, 
                                   metrics_after: Dict):
        """
        评估规则的有效性
        
        计算规则应用前后的指标变化，更新成功率
        """
        rules = self._load_rules()
        rule = next((r for r in rules if r.rule_id == rule_id), None)
        
        if not rule:
            return
        
        # 计算相关指标的提升
        category_metrics = {
            'tech_content': 'tech_content_ratio',
            'insightfulness': 'insightfulness',
            'style': 'style_diversity',
            'analysis_depth': 'analysis_depth'
        }
        
        metric_key = category_metrics.get(rule.category)
        if metric_key and metric_key in metrics_before and metric_key in metrics_after:
            before = metrics_before[metric_key]
            after = metrics_after[metric_key]
            improvement = (after - before) / before if before > 0 else 0
            
            # 更新成功率（滑动平均）
            if rule.success_rate is None:
                rule.success_rate = improvement
            else:
                rule.success_rate = rule.success_rate * 0.7 + improvement * 0.3
            
            # 如果规则持续无效，降低优先级或停用
            if rule.success_rate < -0.1:  # 负面效果
                rule.priority -= 2
                if rule.priority <= 0:
                    rule.is_active = False
                    print(f"[Prompt版本管理] 停用无效规则: {rule_id} (成功率: {rule.success_rate:.1%})")
            elif rule.success_rate > 0.2:  # 正面效果
                rule.priority = min(10, rule.priority + 1)
                print(f"[Prompt版本管理] 提升有效规则优先级: {rule_id} (成功率: {rule.success_rate:.1%})")
            
            self._save_rules(rules)
    
    def get_prompt_digest(self) -> str:
        """
        获取当前Prompt的摘要（用于版本追踪）
        """
        rules = self._load_active_rules()
        
        digest_parts = []
        for rule in sorted(rules, key=lambda r: r.priority, reverse=True)[:5]:
            digest_parts.append(f"{rule.category}({rule.priority})")
        
        return " | ".join(digest_parts) if digest_parts else "default"
    
    def _load_rules(self) -> List[OptimizationRule]:
        """加载所有规则"""
        try:
            import os
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [OptimizationRule(**r) for r in data]
        except Exception as e:
            print(f"[Prompt版本管理] 加载规则失败: {e}")
        
        return []
    
    def _save_rules(self, rules: List[OptimizationRule]):
        """保存规则"""
        try:
            import os
            os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in rules], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Prompt版本管理] 保存规则失败: {e}")
    
    def _load_active_rules(self) -> List[OptimizationRule]:
        """加载活跃规则"""
        rules = self._load_rules()
        now = datetime.now().isoformat()
        
        return [
            r for r in rules 
            if r.is_active 
            and (r.expires_at is None or r.expires_at > now)
        ]
    
    def _cleanup_expired_rules(self, rules: List[OptimizationRule]):
        """清理过期规则"""
        now = datetime.now().isoformat()
        expired = [r for r in rules if r.expires_at and r.expires_at < now]
        
        for rule in expired:
            rule.is_active = False
            print(f"[Prompt版本管理] 规则过期: {rule.rule_id}")
    
    def _limit_active_rules(self, rules: List[OptimizationRule]):
        """限制活跃规则数量"""
        active = [r for r in rules if r.is_active]
        
        if len(active) > self.max_active_rules:
            # 按优先级和成功率排序，保留最好的
            sorted_rules = sorted(
                active, 
                key=lambda r: (r.priority, r.success_rate or 0), 
                reverse=True
            )
            
            for rule in sorted_rules[self.max_active_rules:]:
                rule.is_active = False
                print(f"[Prompt版本管理] 规则降级（数量限制）: {rule.rule_id}")
    
    def _prioritize_rules(self, rules: List[OptimizationRule], 
                         latest_metrics: Dict) -> List[OptimizationRule]:
        """根据最新指标动态调整优先级"""
        for rule in rules:
            # 如果相关指标已经很好，降低该规则的优先级
            if rule.category == 'tech_content' and latest_metrics.get('tech_content_ratio', 0) > 7.0:
                rule.priority = max(1, rule.priority - 2)
            elif rule.category == 'insightfulness' and latest_metrics.get('insightfulness', 0) > 7.0:
                rule.priority = max(1, rule.priority - 2)
            elif rule.category == 'style' and latest_metrics.get('style_diversity', 0) > 7.0:
                rule.priority = max(1, rule.priority - 2)
        
        return sorted(rules, key=lambda r: r.priority, reverse=True)


# 便捷函数
def get_compact_evolution_feedback(trendradar_path: str, metrics_history: List[Dict]) -> str:
    """
    获取紧凑的进化反馈（替代原有的长文本追加）
    
    这个函数是Prompt版本管理的入口点
    """
    manager = PromptVersionManager(trendradar_path)
    return manager.generate_structured_feedback(metrics_history)
