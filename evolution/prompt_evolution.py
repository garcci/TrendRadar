# -*- coding: utf-8 -*-
"""
Prompt进化引擎 - Lv41

核心理念：
1. 维护Prompt变体库（基于不同片段组合）
2. 追踪各变体的累积效果
3. 基于效果数据自动"进化"出更好的Prompt组合
4. 淘汰低效变体，保留高效变体

变体策略：
- 变体A: 全量注入（所有片段）
- 变体B: 精简注入（仅高效片段）
- 变体C: 深度注入（内容类片段优先）
- 变体D: 系统注入（系统类片段优先）
- 变体E: 动态注入（根据当天热点选择片段）

进化规则：
- 每生成5篇文章后评估一次变体效果
- 效果最好的变体成为"主变体"
- 基于主变体生成新的子变体
- 低效变体被淘汰

输出：
- 变体效果对比
- 最佳变体推荐
- 新变体生成建议
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional


class PromptEvolution:
    """Prompt进化引擎"""
    
    # 预定义变体配置
    VARIANT_CONFIGS = {
        "full": {
            "name": "全量注入",
            "description": "使用所有可用的Prompt片段",
            "fragments": [
                "quality_feedback", "data_enhancement", "cross_source",
                "trend_forecast", "emotion_analysis", "knowledge_graph",
                "reader_profile", "realtime_tracking", "self_design",
                "evolution_effect", "rss_recommend", "exception_prediction",
                "exception_monitor", "exception_heal", "repo_size"
            ]
        },
        "minimal": {
            "name": "精简注入",
            "description": "仅使用高效果的内容类片段",
            "fragments": [
                "quality_feedback", "data_enhancement",
                "trend_forecast", "knowledge_graph", "realtime_tracking"
            ]
        },
        "content_focus": {
            "name": "内容深度",
            "description": "优先内容深度类片段",
            "fragments": [
                "data_enhancement", "cross_source", "trend_forecast",
                "knowledge_graph", "emotion_analysis", "realtime_tracking"
            ]
        },
        "system_focus": {
            "name": "系统智能",
            "description": "优先系统反馈类片段",
            "fragments": [
                "quality_feedback", "self_design", "evolution_effect",
                "rss_recommend", "exception_prediction", "repo_size"
            ]
        },
        "adaptive": {
            "name": "自适应",
            "description": "根据历史效果动态选择Top片段",
            "fragments": []  # 动态生成
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.variant_file = f"{trendradar_path}/evolution/prompt_variants.json"
        self.track_file = f"{trendradar_path}/evolution/prompt_track.json"
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
    
    def _load_variant_data(self) -> Dict:
        """加载变体数据"""
        if os.path.exists(self.variant_file):
            try:
                with open(self.variant_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "current_variant": "full",
            "variant_history": [],
            "variant_scores": {name: {"uses": 0, "scores": []} for name in self.VARIANT_CONFIGS}
        }
    
    def _save_variant_data(self, data: Dict):
        """保存变体数据"""
        with open(self.variant_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_metrics(self) -> List[Dict]:
        """加载文章评分"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def select_variant(self) -> str:
        """选择本次使用的Prompt变体"""
        data = self._load_variant_data()
        
        # 如果数据不足，使用全量变体
        total_uses = sum(v["uses"] for v in data.get("variant_scores", {}).values())
        
        if total_uses < 10:
            # 探索阶段：随机选择
            return random.choice(list(self.VARIANT_CONFIGS.keys()))
        
        # 利用阶段：选择效果最好的变体（80%概率），20%概率探索新变体
        if random.random() < 0.8:
            scores = data.get("variant_scores", {})
            best = max(scores.items(), key=lambda x: sum(x[1].get("scores", [])) / max(1, len(x[1].get("scores", []))))
            return best[0]
        else:
            # 探索
            return random.choice(list(self.VARIANT_CONFIGS.keys()))
    
    def get_variant_fragments(self, variant_name: str) -> List[str]:
        """获取变体的片段列表"""
        if variant_name == "adaptive":
            # 自适应变体：动态选择Top片段
            return self._get_adaptive_fragments()
        
        config = self.VARIANT_CONFIGS.get(variant_name, self.VARIANT_CONFIGS["full"])
        return config.get("fragments", [])
    
    def _get_adaptive_fragments(self) -> List[str]:
        """获取自适应变体的片段（基于历史效果）"""
        try:
            from evolution.prompt_tracker import PromptTracker
            tracker = PromptTracker(self.trendradar_path)
            top = tracker.get_top_fragments(min_uses=2)
            
            # 选择Top 8片段
            return [f["id"] for f in top[:8]]
        except Exception:
            return self.VARIANT_CONFIGS["full"]["fragments"][:5]
    
    def record_variant_result(self, variant_name: str, article_id: str, score: float):
        """记录变体效果"""
        data = self._load_variant_data()
        
        if variant_name not in data["variant_scores"]:
            data["variant_scores"][variant_name] = {"uses": 0, "scores": []}
        
        data["variant_scores"][variant_name]["uses"] += 1
        data["variant_scores"][variant_name]["scores"].append(score)
        
        # 只保留最近20个评分
        data["variant_scores"][variant_name]["scores"] = data["variant_scores"][variant_name]["scores"][-20:]
        
        data["variant_history"].append({
            "timestamp": datetime.now().isoformat(),
            "variant": variant_name,
            "article_id": article_id,
            "score": score
        })
        data["variant_history"] = data["variant_history"][-50:]
        
        self._save_variant_data(data)
    
    def analyze_variants(self) -> Dict:
        """分析各变体效果"""
        data = self._load_variant_data()
        scores = data.get("variant_scores", {})
        
        results = {}
        for name, stats in scores.items():
            uses = stats.get("uses", 0)
            score_list = stats.get("scores", [])
            
            if uses < 2:
                continue
            
            avg = sum(score_list) / len(score_list)
            recent_avg = sum(score_list[-5:]) / min(5, len(score_list))
            
            config = self.VARIANT_CONFIGS.get(name, {})
            
            results[name] = {
                "name": config.get("name", name),
                "description": config.get("description", ""),
                "uses": uses,
                "avg_score": round(avg, 2),
                "recent_score": round(recent_avg, 2),
                "trend": "up" if recent_avg > avg else "down" if recent_avg < avg else "stable"
            }
        
        return results
    
    def generate_evolution_report(self) -> str:
        """生成进化报告"""
        analysis = self.analyze_variants()
        data = self._load_variant_data()
        
        lines = ["\n### 🧬 Prompt进化引擎报告\n"]
        
        if not analysis:
            lines.append("**数据不足**，需要更多文章来评估Prompt变体效果。\n")
            return "\n".join(lines)
        
        # 变体效果对比
        lines.append("**📊 Prompt变体效果对比**:")
        sorted_variants = sorted(analysis.items(), key=lambda x: -x[1]["avg_score"])
        
        for i, (name, stats) in enumerate(sorted_variants, 1):
            trend_emoji = "📈" if stats["trend"] == "up" else "📉" if stats["trend"] == "down" else "➡️"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            lines.append(
                f"{medal} **{stats['name']}** ({name})\n"
                f"   均分: {stats['avg_score']} | 近期: {stats['recent_score']} {trend_emoji} | 使用{stats['uses']}次"
            )
        lines.append("")
        
        # 最佳变体
        best = sorted_variants[0]
        lines.append(f"**🏆 当前最佳变体**: {best[1]['name']} (均分 {best[1]['avg_score']})")
        lines.append("")
        
        # 进化建议
        lines.append("**💡 进化建议**:")
        if best[0] != "full":
            lines.append(f"- 建议切换到「{best[1]['name']}」变体，它比全量注入效果更好")
        
        # 检查是否有上升趋势的变体
        trending_up = [v for v in analysis.values() if v["trend"] == "up" and v["uses"] >= 3]
        if trending_up:
            up = max(trending_up, key=lambda x: x["recent_score"])
            lines.append(f"- 「{up['name']}」近期表现上升趋势，值得关注")
        
        lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def get_prompt_evolution_report(trendradar_path: str = ".") -> str:
    """获取Prompt进化报告"""
    engine = PromptEvolution(trendradar_path)
    return engine.generate_evolution_report()


def select_prompt_variant(trendradar_path: str = ".") -> tuple:
    """选择Prompt变体，返回(变体名, 片段列表)"""
    engine = PromptEvolution(trendradar_path)
    variant = engine.select_variant()
    fragments = engine.get_variant_fragments(variant)
    return variant, fragments


if __name__ == "__main__":
    engine = PromptEvolution()
    print(engine.generate_evolution_report())
