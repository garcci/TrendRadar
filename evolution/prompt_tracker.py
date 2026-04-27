# -*- coding: utf-8 -*-
"""
Prompt效果追踪 - Lv39

核心理念：
1. 为每个Prompt注入片段分配唯一ID
2. 记录每次生成时哪些Prompt片段被使用
3. 关联文章评分，计算每个片段的"效果分"
4. 识别哪些Prompt片段真正提升了文章质量

追踪维度：
- 片段ID: 每个Prompt模块的唯一标识
- 使用频率: 该片段被使用的次数
- 平均评分: 使用该片段时的文章平均分
- 对比评分: 不使用该片段时的文章平均分
- 效果增量: 使用该片段带来的评分提升

Prompt片段定义：
- quality_feedback: 历史文章质量反馈
- data_enhancement: 数据增强洞察
- cross_source: 跨源关联洞察
- trend_forecast: 趋势预测洞察
- emotion_analysis: 情感分析洞察
- knowledge_graph: 知识图谱洞察
- reader_profile: 读者画像洞察
- realtime_tracking: 实时热点洞察
- self_design: 自主功能设计洞察
- evolution_effect: 进化效果评估洞察
- rss_recommend: RSS源推荐洞察
- exception_prediction: 异常预测洞察
- exception_monitor: 异常监控洞察
- exception_heal: 异常修复洞察
- repo_size: 仓库体积监控洞察
- structure_diversity: 结构多样化模板

输出：
- Prompt片段效果报告
- 各片段评分关联分析
"""

import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class PromptTracker:
    """Prompt效果追踪器"""
    
    # Prompt片段定义
    PROMPT_FRAGMENTS = {
        "quality_feedback": {"name": "历史质量反馈", "category": "质量"},
        "data_enhancement": {"name": "数据增强", "category": "内容"},
        "cross_source": {"name": "跨源关联", "category": "内容"},
        "trend_forecast": {"name": "趋势预测", "category": "内容"},
        "emotion_analysis": {"name": "情感分析", "category": "风格"},
        "knowledge_graph": {"name": "知识图谱", "category": "深度"},
        "reader_profile": {"name": "读者画像", "category": "受众"},
        "realtime_tracking": {"name": "实时热点", "category": "时效"},
        "self_design": {"name": "自主功能设计", "category": "系统"},
        "evolution_effect": {"name": "进化效果评估", "category": "系统"},
        "rss_recommend": {"name": "RSS源推荐", "category": "系统"},
        "exception_prediction": {"name": "异常预测", "category": "系统"},
        "exception_monitor": {"name": "异常监控", "category": "系统"},
        "exception_heal": {"name": "异常修复", "category": "系统"},
        "repo_size": {"name": "仓库体积监控", "category": "系统"},
        "structure_diversity": {"name": "结构多样化", "category": "风格"}
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.track_file = f"{trendradar_path}/evolution/prompt_track.json"
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
    
    def _load_tracks(self) -> List[Dict]:
        """加载追踪记录"""
        if os.path.exists(self.track_file):
            try:
                with open(self.track_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _save_tracks(self, tracks: List[Dict]):
        """保存追踪记录"""
        os.makedirs(os.path.dirname(self.track_file), exist_ok=True)
        with open(self.track_file, 'w') as f:
            json.dump(tracks, f, ensure_ascii=False, indent=2)
    
    def _load_metrics(self) -> List[Dict]:
        """加载文章评分数据"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def record_prompt_usage(self, article_id: str, fragments_used: List[str]):
        """记录一次Prompt使用情况"""
        tracks = self._load_tracks()
        
        track_record = {
            "timestamp": datetime.now().isoformat(),
            "article_id": article_id,
            "fragments": fragments_used,
            "fragment_count": len(fragments_used)
        }
        
        tracks.append(track_record)
        tracks = tracks[-200:]  # 保留最近200条
        
        self._save_tracks(tracks)
    
    def analyze_fragment_effectiveness(self) -> Dict[str, Dict]:
        """分析各Prompt片段的效果"""
        tracks = self._load_tracks()
        metrics = self._load_metrics()
        
        if not tracks or not metrics:
            return {}
        
        # 建立文章ID到评分的映射
        article_scores = {}
        for m in metrics:
            aid = m.get("article_id", "")
            if aid:
                article_scores[aid] = m.get("overall_score", 0)
        
        # 统计每个片段的使用情况
        fragment_stats = defaultdict(lambda: {
            "uses": 0,
            "scores": [],
            "articles": []
        })
        
        for track in tracks:
            article_id = track.get("article_id", "")
            score = article_scores.get(article_id, 0)
            
            if score > 0:
                for fragment in track.get("fragments", []):
                    fragment_stats[fragment]["uses"] += 1
                    fragment_stats[fragment]["scores"].append(score)
                    fragment_stats[fragment]["articles"].append(article_id)
        
        # 计算效果
        results = {}
        for fragment_id, stats in fragment_stats.items():
            scores = stats["scores"]
            if len(scores) < 2:
                continue
            
            avg_score = sum(scores) / len(scores)
            
            # 计算不使用该片段时的平均评分
            other_scores = []
            for track in tracks:
                if fragment_id not in track.get("fragments", []):
                    aid = track.get("article_id", "")
                    s = article_scores.get(aid, 0)
                    if s > 0:
                        other_scores.append(s)
            
            other_avg = sum(other_scores) / len(other_scores) if other_scores else 0
            
            # 效果增量
            effect_delta = avg_score - other_avg
            
            # 信息
            info = self.PROMPT_FRAGMENTS.get(fragment_id, {})
            
            results[fragment_id] = {
                "name": info.get("name", fragment_id),
                "category": info.get("category", "其他"),
                "uses": stats["uses"],
                "avg_score": round(avg_score, 2),
                "other_avg_score": round(other_avg, 2),
                "effect_delta": round(effect_delta, 2),
                "effect_pct": round(effect_delta / other_avg * 100, 1) if other_avg > 0 else 0,
                "assessment": self._assess_effect(effect_delta)
            }
        
        return results
    
    def _assess_effect(self, delta: float) -> str:
        """评估效果"""
        if delta >= 0.5:
            return "显著提升"
        elif delta >= 0.2:
            return "中等提升"
        elif delta > 0:
            return "轻微提升"
        elif delta == 0:
            return "无影响"
        elif delta > -0.5:
            return "轻微下降"
        else:
            return "显著下降"
    
    def get_top_fragments(self, min_uses: int = 3) -> List[Dict]:
        """获取最有效的Prompt片段"""
        results = self.analyze_fragment_effectiveness()
        
        filtered = []
        for fid, data in results.items():
            if data["uses"] >= min_uses:
                filtered.append({"id": fid, **data})
        
        # 按效果增量排序
        filtered.sort(key=lambda x: -x["effect_delta"])
        return filtered
    
    def get_weak_fragments(self, min_uses: int = 3) -> List[Dict]:
        """获取效果较差的Prompt片段"""
        results = self.analyze_fragment_effectiveness()
        
        filtered = []
        for fid, data in results.items():
            if data["uses"] >= min_uses and data["effect_delta"] < 0:
                filtered.append({"id": fid, **data})
        
        # 按效果下降幅度排序
        filtered.sort(key=lambda x: x["effect_delta"])
        return filtered
    
    def generate_effectiveness_report(self) -> str:
        """生成效果分析报告"""
        top = self.get_top_fragments(min_uses=2)
        weak = self.get_weak_fragments(min_uses=2)
        
        lines = ["\n### 🎯 Prompt效果追踪报告\n"]
        
        if not top:
            lines.append("**数据不足**，需要更多文章来评估Prompt效果。\n")
            return "\n".join(lines)
        
        lines.append(f"**分析样本**: {len(self._load_tracks())} 次生成记录")
        lines.append("")
        
        # 最有效的片段
        lines.append("**🏆 最有效Prompt片段**:")
        for f in top[:5]:
            emoji = "🚀" if f["effect_delta"] >= 0.5 else "📈" if f["effect_delta"] > 0 else "➡️"
            lines.append(
                f"- {emoji} **{f['name']}** ({f['category']})\n"
                f"  使用{f['uses']}次 | 均分{f['avg_score']} | 提升{f['effect_delta']:+.2f} ({f['assessment']})"
            )
        lines.append("")
        
        # 需要改进的片段
        if weak:
            lines.append("**⚠️ 需改进Prompt片段**:")
            for f in weak[:3]:
                lines.append(
                    f"- 📉 **{f['name']}**: 下降{f['effect_delta']:.2f}分，建议优化或移除"
                )
            lines.append("")
        
        # 建议
        lines.append("**💡 Prompt优化建议**:")
        if top:
            best = top[0]
            lines.append(f"- 强化「{best['name']}」的使用，它与高评分强相关")
        if weak:
            worst = weak[0]
            lines.append(f"- 考虑优化或移除「{worst['name']}」，它可能干扰文章质量")
        lines.append("")
        
        return "\n".join(lines)


# 便捷函数
_prompt_tracker_instance = None

def get_prompt_tracker(trendradar_path: str = ".") -> PromptTracker:
    """获取Prompt追踪器实例（单例）"""
    global _prompt_tracker_instance
    if _prompt_tracker_instance is None:
        _prompt_tracker_instance = PromptTracker(trendradar_path)
    return _prompt_tracker_instance


def get_prompt_effectiveness_report(trendradar_path: str = ".") -> str:
    """获取Prompt效果报告"""
    tracker = get_prompt_tracker(trendradar_path)
    return tracker.generate_effectiveness_report()


def record_prompt_fragments(article_id: str, fragments: List[str], trendradar_path: str = "."):
    """记录Prompt片段使用情况"""
    tracker = get_prompt_tracker(trendradar_path)
    tracker.record_prompt_usage(article_id, fragments)


if __name__ == "__main__":
    tracker = PromptTracker()
    print(tracker.generate_effectiveness_report())
