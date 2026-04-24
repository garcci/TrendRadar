# -*- coding: utf-8 -*-
"""
进化效果量化评估 - Lv31

核心理念：
1. 量化每个进化阶段对文章质量的真实影响
2. 识别哪些进化模块真正提升了评分
3. 发现无效进化，避免资源浪费
4. 为后续进化方向提供数据支撑

评估维度：
- 阶段对比: 不同进化等级的平均评分差异
- 模块归因: 哪些模块与评分提升最相关
- 趋势分析: 评分随时间的变化趋势
- ROI评估: 进化投入（代码量/复杂度）vs 评分提升

进化阶段划分：
- 阶段0 (Lv1-Lv5):  基础质量评估 + Prompt优化
- 阶段1 (Lv6-Lv10): 智能路由 + 热点预测 + 免费API
- 阶段2 (Lv11-Lv15): D1存储 + 自主进化 + 预测维护 + 智能回滚
- 阶段3 (Lv16-Lv20): 质量突破 + 智能调度 + 跨源关联 + 智能摘要 + 趋势预测
- 阶段4 (Lv21-Lv25): 情感分析 + 标题优化 + 知识图谱 + 读者画像 + 实时追踪
- 阶段5 (Lv26-Lv30): 自主观察 + 自主设计 + 自主编码 + 自主测试 + 自主部署

输出：
- 进化效果量化报告
- 模块效果排名
- 进化ROI分析
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class EvolutionEffectEvaluator:
    """进化效果评估器"""
    
    # 进化阶段定义（根据commit时间或文章时间推断）
    # 使用大致的时间范围来划分阶段
    EVOLUTION_PHASES = {
        "phase_0_baseline": {
            "name": "基础阶段",
            "levels": "Lv1-Lv5",
            "modules": ["文章评分", "Prompt优化", "RSS监控"],
            "start_date": "2025-01-01",  # 基准线
        },
        "phase_1_routing": {
            "name": "智能路由",
            "levels": "Lv6-Lv10",
            "modules": ["多模型路由", "热点预测", "免费API"],
            "start_date": "2025-02-01",
        },
        "phase_2_system": {
            "name": "系统进化",
            "levels": "Lv11-Lv15",
            "modules": ["D1存储", "自主诊断", "预测维护", "智能回滚"],
            "start_date": "2025-03-01",
        },
        "phase_3_quality": {
            "name": "质量突破",
            "levels": "Lv16-Lv20",
            "modules": ["Prompt优化", "科技检测", "数据增强", "智能调度", "跨源关联", "智能摘要", "趋势预测"],
            "start_date": "2025-04-01",
        },
        "phase_4_enhancement": {
            "name": "多维增强",
            "levels": "Lv21-Lv25",
            "modules": ["情感分析", "标题优化", "知识图谱", "读者画像", "实时追踪"],
            "start_date": "2025-04-15",
        },
        "phase_5_autonomous": {
            "name": "自主进化",
            "levels": "Lv26-Lv30",
            "modules": ["自我观察", "自主设计", "自主编码", "自主测试", "自主部署"],
            "start_date": "2025-04-20",
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.report_file = f"{trendradar_path}/evolution/evolution_effect_report.json"
    
    def _load_metrics(self, days: int = 60) -> List[Dict]:
        """加载历史指标数据"""
        if not os.path.exists(self.metrics_file):
            return []
        
        try:
            with open(self.metrics_file, 'r') as f:
                metrics = json.load(f)
        except Exception:
            return []
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [m for m in metrics if m.get("timestamp", "") > cutoff]
    
    def _classify_phase(self, timestamp: str) -> str:
        """根据时间戳判断文章属于哪个进化阶段"""
        try:
            article_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00').replace('+00:00', ''))
        except Exception:
            return "unknown"
        
        # 从最新到最旧匹配
        for phase_id, phase_info in sorted(
            self.EVOLUTION_PHASES.items(),
            key=lambda x: x[1]["start_date"],
            reverse=True
        ):
            phase_date = datetime.strptime(phase_info["start_date"], "%Y-%m-%d")
            if article_date >= phase_date:
                return phase_id
        
        return "phase_0_baseline"
    
    def calculate_phase_scores(self, metrics: List[Dict]) -> Dict[str, Dict]:
        """计算各进化阶段的平均评分"""
        phase_scores = defaultdict(list)
        
        for metric in metrics:
            timestamp = metric.get("timestamp", "")
            phase = self._classify_phase(timestamp)
            score = metric.get("overall_score", 0)
            
            if score > 0:
                phase_scores[phase].append(score)
        
        results = {}
        for phase_id, scores in phase_scores.items():
            if not scores:
                continue
            
            phase_info = self.EVOLUTION_PHASES.get(phase_id, {})
            
            results[phase_id] = {
                "name": phase_info.get("name", phase_id),
                "levels": phase_info.get("levels", ""),
                "modules": phase_info.get("modules", []),
                "article_count": len(scores),
                "avg_score": round(sum(scores) / len(scores), 1),
                "max_score": round(max(scores), 1),
                "min_score": round(min(scores), 1),
                "median_score": round(sorted(scores)[len(scores)//2], 1),
                "scores": scores
            }
        
        return results
    
    def calculate_improvement(self, phase_results: Dict) -> List[Dict]:
        """计算各阶段相比前一阶段的提升"""
        improvements = []
        
        phase_order = [
            "phase_0_baseline",
            "phase_1_routing",
            "phase_2_system",
            "phase_3_quality",
            "phase_4_enhancement",
            "phase_5_autonomous"
        ]
        
        prev_score = None
        prev_name = None
        
        for phase_id in phase_order:
            if phase_id not in phase_results:
                continue
            
            phase = phase_results[phase_id]
            current_score = phase["avg_score"]
            
            if prev_score is not None:
                improvement = current_score - prev_score
                improvement_pct = (improvement / prev_score * 100) if prev_score > 0 else 0
                
                improvements.append({
                    "from_phase": prev_name,
                    "to_phase": phase["name"],
                    "from_score": prev_score,
                    "to_score": current_score,
                    "improvement": round(improvement, 1),
                    "improvement_pct": round(improvement_pct, 1),
                    "modules_added": phase["modules"],
                    "assessment": self._assess_improvement(improvement)
                })
            
            prev_score = current_score
            prev_name = phase["name"]
        
        return improvements
    
    def _assess_improvement(self, improvement: float) -> str:
        """评估提升幅度"""
        if improvement >= 1.0:
            return "显著提升"
        elif improvement >= 0.5:
            return "中等提升"
        elif improvement > 0:
            return "轻微提升"
        elif improvement == 0:
            return "无变化"
        else:
            return "下降（需要审查）"
    
    def identify_top_performers(self, metrics: List[Dict]) -> Dict:
        """识别表现最好的文章特征"""
        if not metrics:
            return {}
        
        # 找出高评分文章的共同特征
        high_scores = [m for m in metrics if m.get("overall_score", 0) >= 8.0]
        low_scores = [m for m in metrics if m.get("overall_score", 0) <= 5.0]
        
        # 统计高评分文章的关键词
        high_keywords = []
        for m in high_scores:
            high_keywords.extend(m.get("keywords", []))
            high_keywords.extend(m.get("hot_topics", []))
        
        # 统计低评分文章的关键词
        low_keywords = []
        for m in low_scores:
            low_keywords.extend(m.get("keywords", []))
            low_keywords.extend(m.get("hot_topics", []))
        
        # 找出高评分文章独有、低评分文章没有的关键词
        high_counter = defaultdict(int)
        for kw in high_keywords:
            high_counter[kw] += 1
        
        low_set = set(low_keywords)
        
        unique_high = []
        for kw, count in high_counter.items():
            if kw not in low_set and count >= 2:
                unique_high.append({"keyword": kw, "count": count})
        
        unique_high.sort(key=lambda x: -x["count"])
        
        return {
            "high_score_count": len(high_scores),
            "low_score_count": len(low_scores),
            "high_score_ratio": round(len(high_scores) / len(metrics), 2),
            "success_keywords": unique_high[:10],
            "avg_high_score": round(sum(m.get("overall_score", 0) for m in high_scores) / len(high_scores), 1) if high_scores else 0,
            "avg_low_score": round(sum(m.get("overall_score", 0) for m in low_scores) / len(low_scores), 1) if low_scores else 0
        }
    
    def generate_evolution_report(self) -> Dict:
        """生成进化效果报告"""
        metrics = self._load_metrics(days=60)
        
        if not metrics:
            return {"error": "No metrics data available", "timestamp": datetime.now().isoformat()}
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_articles_analyzed": len(metrics),
            "analysis_period_days": 60
        }
        
        # 1. 各阶段评分
        phase_results = self.calculate_phase_scores(metrics)
        report["phase_scores"] = phase_results
        
        # 2. 阶段间提升
        improvements = self.calculate_improvement(phase_results)
        report["improvements"] = improvements
        
        # 3. 高评分文章特征
        top_performers = self.identify_top_performers(metrics)
        report["top_performers"] = top_performers
        
        # 4. 总体评估
        if phase_results:
            latest_phase = max(phase_results.items(), key=lambda x: x[1].get("avg_score", 0))
            baseline_phase = phase_results.get("phase_0_baseline", {})
            
            if baseline_phase:
                total_improvement = latest_phase[1]["avg_score"] - baseline_phase["avg_score"]
                report["overall_assessment"] = {
                    "latest_phase": latest_phase[1]["name"],
                    "latest_score": latest_phase[1]["avg_score"],
                    "baseline_score": baseline_phase["avg_score"],
                    "total_improvement": round(total_improvement, 1),
                    "assessment": self._assess_improvement(total_improvement)
                }
        
        # 5. 建议
        report["recommendations"] = self._generate_recommendations(report)
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """生成进化建议"""
        recommendations = []
        
        improvements = report.get("improvements", [])
        
        if not improvements:
            recommendations.append("数据不足，无法评估进化效果")
            return recommendations
        
        # 找出最有效的阶段
        positive_improvements = [i for i in improvements if i["improvement"] > 0]
        if positive_improvements:
            best = max(positive_improvements, key=lambda x: x["improvement"])
            recommendations.append(
                f"最有效的进化阶段是'{best['to_phase']}'(提升{best['improvement']}分)，"
                f"建议继续强化相关模块: {', '.join(best['modules_added'][:3])}"
            )
        
        # 找出效果不佳的阶段
        negative_improvements = [i for i in improvements if i["improvement"] < 0]
        if negative_improvements:
            worst = min(negative_improvements, key=lambda x: x["improvement"])
            recommendations.append(
                f"'{worst['to_phase']}'阶段评分下降{abs(worst['improvement'])}分，"
                f"建议审查该阶段添加的模块效果"
            )
        
        # 高评分文章特征
        top = report.get("top_performers", {})
        if top.get("success_keywords"):
            keywords = [k["keyword"] for k in top["success_keywords"][:3]]
            recommendations.append(
                f"高评分文章常涉及话题: {', '.join(keywords)}，建议增加相关内容"
            )
        
        # 整体趋势
        overall = report.get("overall_assessment", {})
        if overall.get("total_improvement", 0) > 2:
            recommendations.append("进化系统整体效果显著，继续保持当前方向")
        elif overall.get("total_improvement", 0) < 0:
            recommendations.append("警告：进化系统整体效果为负，需要全面审查")
        else:
            recommendations.append("进化效果不明显，建议尝试新的进化方向")
        
        return recommendations
    
    def _save_report(self, report: Dict):
        """保存报告"""
        reports = []
        if os.path.exists(self.report_file):
            try:
                with open(self.report_file, 'r') as f:
                    reports = json.load(f)
            except Exception:
                pass
        
        reports.append(report)
        reports = reports[-10:]  # 保留最近10份
        
        with open(self.report_file, 'w') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
    
    def generate_effect_insight(self) -> str:
        """生成效果洞察（用于Prompt注入）"""
        report = self.generate_evolution_report()
        
        if "error" in report:
            return ""
        
        lines = ["\n### 📊 进化效果评估\n"]
        
        # 总体评估
        overall = report.get("overall_assessment", {})
        if overall:
            lines.append(f"**当前进化阶段**: {overall['latest_phase']} (评分: {overall['latest_score']})")
            lines.append(f"**相比基准线**: {overall['assessment']} ({overall['total_improvement']:+.1f}分)")
            lines.append("")
        
        # 阶段对比
        improvements = report.get("improvements", [])
        if improvements:
            lines.append("**各阶段提升情况**:")
            for imp in improvements:
                emoji = "🚀" if imp["improvement"] >= 1 else "📈" if imp["improvement"] > 0 else "📉"
                lines.append(
                    f"- {emoji} {imp['from_phase']} → {imp['to_phase']}: "
                    f"{imp['from_score']} → {imp['to_score']} ({imp['improvement']:+.1f}, {imp['assessment']})"
                )
            lines.append("")
        
        # 建议
        recommendations = report.get("recommendations", [])
        if recommendations:
            lines.append("**进化建议**:")
            for rec in recommendations:
                lines.append(f"- 💡 {rec}")
            lines.append("")
        
        lines.append("**写作指导**: 参考高评分文章的成功因素，提升内容质量。\n")
        
        return "\n".join(lines)


# 便捷函数
def get_evolution_effect_insight(trendradar_path: str = ".") -> str:
    """获取进化效果洞察"""
    evaluator = EvolutionEffectEvaluator(trendradar_path)
    return evaluator.generate_effect_insight()


def get_evolution_report(trendradar_path: str = ".") -> Dict:
    """获取进化效果报告"""
    evaluator = EvolutionEffectEvaluator(trendradar_path)
    return evaluator.generate_evolution_report()


if __name__ == "__main__":
    evaluator = EvolutionEffectEvaluator()
    report = evaluator.generate_evolution_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
