# -*- coding: utf-8 -*-
"""
Prompt自动优化 - Lv40

核心理念：
1. 基于Lv39的追踪数据自动计算各Prompt片段的权重
2. 识别低效片段并生成改进建议
3. 动态调整Prompt注入顺序（高效片段优先）
4. 生成优化后的Prompt模板建议

优化策略：
- 提升高效片段: 增加使用频率，放在Prompt前面
- 降低低效片段: 减少使用频率，放在Prompt后面或移除
- 新增片段测试: 为低覆盖领域生成新片段建议
- 片段融合: 将多个低效片段合并为一个高效片段

权重计算：
- 基础权重 = 效果增量 × 使用频率
- 稳定权重 = 基础权重 × 置信度（使用次数越多越可信）
- 最终权重 = 稳定权重 + 领域覆盖 bonus

输出：
- 优化后的Prompt片段权重
- 片段调整建议
- 新片段生成建议
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional


class PromptOptimizer:
    """Prompt自动优化器"""
    
    # 权重阈值
    WEIGHT_THRESHOLDS = {
        "high": 2.0,      # 高效片段
        "medium": 0.5,    # 中等片段
        "low": -0.5,      # 低效片段
        "remove": -1.0    # 建议移除
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.track_file = f"{trendradar_path}/evolution/prompt_track.json"
        self.optimize_file = f"{trendradar_path}/evolution/prompt_optimization.json"
    
    def _load_tracks(self) -> List[Dict]:
        """加载追踪记录"""
        if os.path.exists(self.track_file):
            try:
                with open(self.track_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _load_optimization_history(self) -> List[Dict]:
        """加载优化历史"""
        if os.path.exists(self.optimize_file):
            try:
                with open(self.optimize_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _save_optimization(self, optimization: Dict):
        """保存优化结果"""
        history = self._load_optimization_history()
        history.append(optimization)
        history = history[-20:]  # 保留最近20次
        
        with open(self.optimize_file, 'w') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def calculate_fragment_weights(self, fragment_data: Dict) -> Dict[str, float]:
        """计算片段权重"""
        weights = {}
        
        for fid, data in fragment_data.items():
            effect_delta = data.get("effect_delta", 0)
            uses = data.get("uses", 0)
            
            # 基础权重 = 效果增量
            base_weight = effect_delta
            
            # 置信度因子（使用次数越多越可信）
            confidence = min(1.0, uses / 10)  # 10次以上达到最大置信度
            
            # 稳定权重
            stable_weight = base_weight * confidence
            
            # 使用频率加成（常用片段更有价值）
            frequency_bonus = min(0.5, uses / 20)
            
            weights[fid] = stable_weight + frequency_bonus
        
        return weights
    
    def generate_optimization_plan(self, fragment_data: Dict) -> Dict:
        """生成优化计划"""
        weights = self.calculate_fragment_weights(fragment_data)
        
        plan = {
            "timestamp": datetime.now().isoformat(),
            "boost": [],      # 需要提升的片段
            "reduce": [],     # 需要降低的片段
            "remove": [],     # 建议移除的片段
            "new_suggestions": [],  # 新片段建议
            "reorder": []     # 重新排序建议
        }
        
        # 分类处理
        for fid, weight in weights.items():
            data = fragment_data.get(fid, {})
            name = data.get("name", fid)
            
            item = {
                "id": fid,
                "name": name,
                "weight": round(weight, 2),
                "current_uses": data.get("uses", 0),
                "avg_score": data.get("avg_score", 0)
            }
            
            if weight >= self.WEIGHT_THRESHOLDS["high"]:
                plan["boost"].append(item)
            elif weight <= self.WEIGHT_THRESHOLDS["remove"]:
                plan["remove"].append(item)
            elif weight <= self.WEIGHT_THRESHOLDS["low"]:
                plan["reduce"].append(item)
        
        # 按权重排序
        plan["boost"].sort(key=lambda x: -x["weight"])
        plan["reduce"].sort(key=lambda x: x["weight"])
        plan["remove"].sort(key=lambda x: x["weight"])
        
        # 生成重新排序建议（高效片段放前面）
        all_fragments = []
        for fid, data in fragment_data.items():
            all_fragments.append({
                "id": fid,
                "name": data.get("name", fid),
                "weight": round(weights.get(fid, 0), 2)
            })
        
        all_fragments.sort(key=lambda x: -x["weight"])
        plan["reorder"] = all_fragments[:10]
        
        # 新片段建议（基于低覆盖领域）
        covered_categories = set()
        for fid, data in fragment_data.items():
            covered_categories.add(data.get("category", "其他"))
        
        all_categories = {"质量", "内容", "风格", "深度", "受众", "时效", "系统"}
        missing = all_categories - covered_categories
        
        if missing:
            category_suggestions = {
                "质量": "文章质量自检清单",
                "内容": "数据来源可信度分析",
                "风格": "语气一致性检查",
                "深度": "专家观点引用建议",
                "受众": "读者阅读时间预估",
                "时效": "新闻时效性分级",
                "系统": "系统资源使用提示"
            }
            
            for cat in missing:
                plan["new_suggestions"].append({
                    "category": cat,
                    "suggested_name": category_suggestions.get(cat, f"{cat}增强"),
                    "reason": f"{cat}类Prompt片段缺失，建议补充"
                })
        
        return plan
    
    def generate_optimization_report(self) -> str:
        """生成优化报告"""
        # 从tracker获取数据
        from evolution.prompt_tracker import PromptTracker
        tracker = PromptTracker(self.trendradar_path)
        fragment_data = tracker.analyze_fragment_effectiveness()
        
        if not fragment_data:
            return "\n### 🎯 Prompt优化建议\n\n**数据不足**，需要更多文章来生成优化建议。\n"
        
        plan = self.generate_optimization_plan(fragment_data)
        
        # 保存优化计划
        self._save_optimization(plan)
        
        lines = ["\n### 🎯 Prompt自动优化建议\n"]
        
        # 提升建议
        if plan["boost"]:
            lines.append("**📈 建议强化以下片段**（高效，放前面）:")
            for item in plan["boost"][:5]:
                lines.append(f"- ⬆️ **{item['name']}** (权重: {item['weight']}, 使用{item['current_uses']}次)")
            lines.append("")
        
        # 降低建议
        if plan["reduce"]:
            lines.append("**📉 建议弱化以下片段**（低效，放后面）:")
            for item in plan["reduce"][:3]:
                lines.append(f"- ⬇️ **{item['name']}** (权重: {item['weight']}, 均分{item['avg_score']})")
            lines.append("")
        
        # 移除建议
        if plan["remove"]:
            lines.append("**🗑️ 建议移除以下片段**（负效果）:")
            for item in plan["remove"]:
                lines.append(f"- ❌ **{item['name']}** (权重: {item['weight']})")
            lines.append("")
        
        # 新片段建议
        if plan["new_suggestions"]:
            lines.append("**✨ 建议新增以下片段**:")
            for sugg in plan["new_suggestions"]:
                lines.append(f"- 🆕 {sugg['suggested_name']} ({sugg['category']})")
            lines.append("")
        
        # 排序建议
        if plan["reorder"]:
            lines.append("**📋 建议Prompt注入顺序**:")
            for i, item in enumerate(plan["reorder"][:8], 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                lines.append(f"{emoji} {item['name']} (权重: {item['weight']})")
            lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def get_prompt_optimization_report(trendradar_path: str = ".") -> str:
    """获取Prompt优化报告"""
    optimizer = PromptOptimizer(trendradar_path)
    return optimizer.generate_optimization_report()


if __name__ == "__main__":
    optimizer = PromptOptimizer()
    print(optimizer.generate_optimization_report())
