# -*- coding: utf-8 -*-
"""
自我观察引擎 - 系统自我监控，识别能力缺口

核心理念：
1. 系统应该像生物一样有"自我感知"能力
2. 自动收集运行数据，分析自身表现
3. 识别能力缺口和优化机会
4. 生成结构化的"自我诊断报告"

观察维度：
- 内容质量: 文章评分趋势、常见问题
- 系统稳定性: RSS成功率、API可用性、错误率
- 成本效率: API调用次数、配额使用、降级频率
- 功能覆盖: 哪些进化模块工作正常、哪些需要改进
- 数据质量: RSS数据量、新鲜度、多样性

输出：
- 自我诊断报告（结构化JSON）
- 能力缺口列表
- 优化建议（用于Lv27自主功能设计）
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class SelfObserver:
    """自我观察引擎"""
    
    # 能力维度定义
    CAPABILITY_DIMENSIONS = {
        "content_quality": {
            "name": "内容质量",
            "metrics": ["avg_score", "score_trend", "tech_ratio", "structure_diversity"],
            "threshold": {"good": 7.5, "acceptable": 6.0, "poor": 4.0}
        },
        "system_stability": {
            "name": "系统稳定性",
            "metrics": ["rss_success_rate", "api_availability", "error_rate", "workflow_success_rate"],
            "threshold": {"good": 0.95, "acceptable": 0.85, "poor": 0.70}
        },
        "cost_efficiency": {
            "name": "成本效率",
            "metrics": ["api_calls_per_run", "fallback_rate", "quota_usage"],
            "threshold": {"good": 0.3, "acceptable": 0.6, "poor": 0.9}
        },
        "data_quality": {
            "name": "数据质量",
            "metrics": ["rss_item_count", "freshness_ratio", "source_diversity", "topic_coverage"],
            "threshold": {"good": 0.9, "acceptable": 0.7, "poor": 0.5}
        },
        "feature_coverage": {
            "name": "功能覆盖",
            "metrics": ["active_modules", "module_success_rates", "evolution_level"],
            "threshold": {"good": 20, "acceptable": 15, "poor": 10}
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.report_file = f"{trendradar_path}/evolution/self_diagnosis.json"
    
    def _load_metrics(self, days: int = 7) -> List[Dict]:
        """加载近期指标数据"""
        if not os.path.exists(self.metrics_file):
            return []
        
        try:
            with open(self.metrics_file, 'r') as f:
                metrics = json.load(f)
        except Exception:
            return []
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [m for m in metrics if m.get("timestamp", "") > cutoff]
    
    def _analyze_content_quality(self, metrics: List[Dict]) -> Dict:
        """分析内容质量"""
        if not metrics:
            return {"status": "unknown", "score": 0, "issues": [], "trend": "stable"}
        
        scores = [m.get("overall_score", 0) for m in metrics]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # 趋势分析
        if len(scores) >= 3:
            recent_avg = sum(scores[-3:]) / 3
            older_avg = sum(scores[:3]) / 3
            trend = "improving" if recent_avg > older_avg + 0.5 else "declining" if recent_avg < older_avg - 0.5 else "stable"
        else:
            trend = "stable"
        
        # 识别问题
        issues = []
        if avg_score < 6.0:
            issues.append("文章平均评分低于6分，内容深度可能不足")
        if trend == "declining":
            issues.append("文章评分呈下降趋势，需要优化Prompt或数据源")
        
        # 低分文章分析
        low_scores = [m for m in metrics if m.get("overall_score", 0) < 5.0]
        if low_scores:
            issues.append(f"最近有{len(low_scores)}篇文章评分低于5分")
        
        status = "good" if avg_score >= 7.5 else "acceptable" if avg_score >= 6.0 else "poor"
        
        return {
            "status": status,
            "score": round(avg_score, 1),
            "count": len(metrics),
            "trend": trend,
            "issues": issues,
            "suggestions": self._generate_quality_suggestions(avg_score, trend, issues)
        }
    
    def _analyze_system_stability(self, metrics: List[Dict]) -> Dict:
        """分析系统稳定性"""
        issues = []
        
        # 从metrics中提取错误信息
        error_count = sum(1 for m in metrics if m.get("has_errors", False))
        error_rate = error_count / len(metrics) if metrics else 0
        
        if error_rate > 0.2:
            issues.append(f"错误率过高({error_rate:.0%})，系统稳定性需提升")
        
        # API降级频率
        fallback_indicators = []
        for m in metrics:
            if "deepseek" in str(m.get("model_used", "")).lower():
                fallback_indicators.append(m)
        
        fallback_rate = len(fallback_indicators) / len(metrics) if metrics else 0
        if fallback_rate > 0.5:
            issues.append(f"API降级频率过高({fallback_rate:.0%})，建议增加备用API或优化配额管理")
        
        status = "good" if error_rate < 0.05 else "acceptable" if error_rate < 0.15 else "poor"
        
        return {
            "status": status,
            "error_rate": round(error_rate, 2),
            "fallback_rate": round(fallback_rate, 2),
            "issues": issues,
            "suggestions": self._generate_stability_suggestions(error_rate, fallback_rate)
        }
    
    def _analyze_cost_efficiency(self, metrics: List[Dict]) -> Dict:
        """分析成本效率"""
        issues = []
        
        # 估算每次运行的API调用成本
        # 简单模型：每次文章生成约2-3次API调用
        estimated_calls = len(metrics) * 2.5
        
        # 降级频率作为成本指标（降级到DeepSeek通常更便宜）
        fallback_count = sum(1 for m in metrics if "deepseek" in str(m.get("model_used", "")).lower())
        
        if fallback_count > len(metrics) * 0.7:
            issues.append("过度依赖备用API，主API利用率低，可能存在配额浪费")
        
        status = "good" if fallback_count < len(metrics) * 0.3 else "acceptable" if fallback_count < len(metrics) * 0.6 else "poor"
        
        return {
            "status": status,
            "estimated_api_calls": round(estimated_calls, 0),
            "fallback_count": fallback_count,
            "issues": issues,
            "suggestions": []
        }
    
    def _analyze_feature_coverage(self) -> Dict:
        """分析功能覆盖情况"""
        evolution_dir = f"{self.trendradar_path}/evolution"
        
        if not os.path.exists(evolution_dir):
            return {"status": "unknown", "active_modules": 0, "issues": []}
        
        # 扫描evolution目录中的模块
        modules = [f for f in os.listdir(evolution_dir) if f.endswith('.py') and not f.startswith('_')]
        
        # 识别关键模块
        key_modules = {
            "prompt_optimizer": "Prompt动态优化",
            "tech_content_guard": "科技内容检测",
            "data_enhancer": "数据增强",
            "smart_scheduler": "智能调度",
            "cross_source_analyzer": "跨源关联",
            "smart_summary": "智能摘要",
            "trend_predictor": "趋势预测",
            "emotion_analyzer": "情感分析",
            "title_optimizer": "标题优化",
            "knowledge_graph": "知识图谱",
            "reader_analytics": "读者画像",
            "retime_tracker": "实时追踪"
        }
        
        active_modules = []
        missing_modules = []
        
        for module_id, module_name in key_modules.items():
            module_file = f"{module_id}.py"
            if module_file in modules:
                active_modules.append({"id": module_id, "name": module_name, "status": "active"})
            else:
                missing_modules.append({"id": module_id, "name": module_name, "status": "missing"})
        
        issues = []
        if missing_modules:
            issues.append(f"有{len(missing_modules)}个进化模块未激活")
        
        evolution_level = len(active_modules)
        status = "good" if evolution_level >= 20 else "acceptable" if evolution_level >= 15 else "poor"
        
        return {
            "status": status,
            "evolution_level": evolution_level,
            "active_modules": active_modules,
            "missing_modules": missing_modules,
            "issues": issues,
            "suggestions": self._generate_coverage_suggestions(missing_modules)
        }
    
    def _generate_quality_suggestions(self, score: float, trend: str, issues: List[str]) -> List[str]:
        """生成质量优化建议"""
        suggestions = []
        if score < 6.0:
            suggestions.append("建议增强Prompt的深度要求，强制每个话题包含技术细节")
            suggestions.append("建议增加数据来源多样性，引入更多技术博客和论文")
        if trend == "declining":
            suggestions.append("建议审查最近的Prompt变化，回退到低评分的变更")
        if not any("数据" in issue for issue in issues):
            suggestions.append("可以考虑增加自动数据验证，确保文章包含具体数字")
        return suggestions
    
    def _generate_stability_suggestions(self, error_rate: float, fallback_rate: float) -> List[str]:
        """生成稳定性优化建议"""
        suggestions = []
        if error_rate > 0.1:
            suggestions.append("建议增加错误重试机制和备用方案")
        if fallback_rate > 0.5:
            suggestions.append("建议增加更多免费API源作为备选")
        return suggestions
    
    def _generate_coverage_suggestions(self, missing_modules: List[Dict]) -> List[str]:
        """生成功能覆盖建议"""
        suggestions = []
        if missing_modules:
            suggestions.append(f"建议实现以下缺失模块: {', '.join(m['name'] for m in missing_modules[:3])}")
        suggestions.append("建议定期审查模块效果，停用低效模块")
        return suggestions
    
    def generate_diagnosis_report(self) -> Dict:
        """生成自我诊断报告"""
        metrics = self._load_metrics(days=7)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "observation_period_days": 7,
            "overall_health": "unknown",
            "dimensions": {}
        }
        
        # 分析各维度
        content_analysis = self._analyze_content_quality(metrics)
        stability_analysis = self._analyze_system_stability(metrics)
        cost_analysis = self._analyze_cost_efficiency(metrics)
        feature_analysis = self._analyze_feature_coverage()
        
        report["dimensions"] = {
            "content_quality": content_analysis,
            "system_stability": stability_analysis,
            "cost_efficiency": cost_analysis,
            "feature_coverage": feature_analysis
        }
        
        # 计算总体健康度
        statuses = [d["status"] for d in report["dimensions"].values() if "status" in d]
        if all(s == "good" for s in statuses):
            report["overall_health"] = "healthy"
        elif any(s == "poor" for s in statuses):
            report["overall_health"] = "critical"
        else:
            report["overall_health"] = "needs_improvement"
        
        # 汇总所有问题
        all_issues = []
        for dim_name, dim_data in report["dimensions"].items():
            for issue in dim_data.get("issues", []):
                all_issues.append({
                    "dimension": dim_name,
                    "issue": issue,
                    "severity": "high" if dim_data.get("status") == "poor" else "medium"
                })
        
        report["identified_issues"] = all_issues
        
        # 汇总所有建议
        all_suggestions = []
        for dim_name, dim_data in report["dimensions"].items():
            for suggestion in dim_data.get("suggestions", []):
                all_suggestions.append({
                    "dimension": dim_name,
                    "suggestion": suggestion
                })
        
        report["optimization_suggestions"] = all_suggestions
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _save_report(self, report: Dict):
        """保存诊断报告"""
        reports = []
        if os.path.exists(self.report_file):
            try:
                with open(self.report_file, 'r') as f:
                    reports = json.load(f)
            except Exception:
                pass
        
        reports.append(report)
        # 只保留最近10份报告
        reports = reports[-10:]
        
        with open(self.report_file, 'w') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
    
    def generate_capability_gap_report(self) -> str:
        """生成能力缺口报告（用于Lv27功能设计）"""
        report = self.generate_diagnosis_report()
        
        lines = ["\n### 🔍 自我观察报告\n"]
        lines.append(f"**观察时间**: {report['timestamp'][:19]}")
        lines.append(f"**总体健康度**: {report['overall_health']}")
        lines.append(f"**进化等级**: {report['dimensions']['feature_coverage']['evolution_level']}")
        lines.append("")
        
        # 问题汇总
        if report["identified_issues"]:
            lines.append("**发现的问题**:")
            for issue in report["identified_issues"]:
                emoji = "🔴" if issue["severity"] == "high" else "🟡"
                lines.append(f"- {emoji} [{issue['dimension']}] {issue['issue']}")
            lines.append("")
        
        # 优化建议
        if report["optimization_suggestions"]:
            lines.append("**优化建议**:")
            for sug in report["optimization_suggestions"]:
                lines.append(f"- [{sug['dimension']}] {sug['suggestion']}")
            lines.append("")
        
        # 能力缺口（用于Lv27）
        lines.append("**能力缺口分析**:")
        for dim_name, dim_data in report["dimensions"].items():
            status = dim_data.get("status", "unknown")
            emoji = "🟢" if status == "good" else "🟡" if status == "acceptable" else "🔴"
            lines.append(f"- {emoji} {dim_name}: {status}")
        lines.append("")
        
        lines.append("**自主进化建议**: 基于以上观察，系统需要增强以下能力...\n")
        
        return "\n".join(lines)


# 便捷函数
def get_self_diagnosis(trendradar_path: str = ".") -> str:
    """获取自我诊断报告"""
    observer = SelfObserver(trendradar_path)
    return observer.generate_capability_gap_report()


def get_diagnosis_json(trendradar_path: str = ".") -> Dict:
    """获取结构化诊断数据"""
    observer = SelfObserver(trendradar_path)
    return observer.generate_diagnosis_report()


if __name__ == "__main__":
    observer = SelfObserver()
    report = observer.generate_diagnosis_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
