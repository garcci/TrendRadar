# -*- coding: utf-8 -*-
"""
自动优化系统 - 基于D1历史数据驱动进化

功能：
1. 分析历史文章质量趋势
2. 自动识别最优Prompt版本
3. 推荐RSS源替换策略
4. 预测最佳发布时机
5. 生成系统优化建议
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class AutoOptimizer:
    """自动优化引擎"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.d1_store = None
        
        # 尝试连接D1
        try:
            from evolution.storage_d1 import get_evolution_data_store
            self.d1_store = get_evolution_data_store(trendradar_path)
        except Exception:
            pass
    
    # ═══════════════════════════════════════════════════════════
    # 1. 文章质量趋势分析
    # ═══════════════════════════════════════════════════════════
    
    def analyze_quality_trend(self, days: int = 14) -> Dict:
        """分析文章质量趋势"""
        if not self.d1_store:
            return {"error": "D1未配置"}
        
        try:
            metrics = self.d1_store.get_article_metrics(days)
            
            if not metrics:
                return {"status": "no_data", "message": "暂无历史数据"}
            
            # 计算趋势
            scores = [m.get("overall_score", 0) for m in metrics]
            tech_ratios = [m.get("tech_content_ratio", 0) for m in metrics]
            
            # 简单线性趋势
            if len(scores) >= 2:
                trend = scores[0] - scores[-1]  # 最新 - 最早
                tech_trend = tech_ratios[0] - tech_ratios[-1]
            else:
                trend = 0
                tech_trend = 0
            
            return {
                "status": "success",
                "sample_size": len(metrics),
                "avg_score": sum(scores) / len(scores) if scores else 0,
                "score_trend": trend,  # 正数=提升，负数=下降
                "tech_trend": tech_trend,
                "latest_score": scores[0] if scores else 0,
                "recommendation": self._generate_quality_recommendation(trend, scores)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_quality_recommendation(self, trend: float, scores: List[float]) -> str:
        """生成质量改进建议"""
        avg = sum(scores) / len(scores) if scores else 0
        
        if trend < -0.5:
            return "📉 文章质量下降趋势明显，建议：\n1. 检查最近Prompt版本\n2. 增加科技内容比例\n3. 启用高质量模式"
        elif avg < 7.0:
            return "⚠️ 平均质量偏低，建议：\n1. 优化Prompt模板\n2. 增加分析深度要求\n3. 启用A/B测试"
        elif trend > 0.5:
            return "📈 质量持续提升，保持当前策略"
        else:
            return "➡️ 质量稳定，可尝试小幅优化"
    
    # ═══════════════════════════════════════════════════════════
    # 2. RSS源健康度分析
    # ═══════════════════════════════════════════════════════════
    
    def analyze_rss_health(self, days: int = 7) -> Dict:
        """分析RSS源健康度"""
        # 从文件读取（D1降级）
        rss_file = f"{self.trendradar_path}/evolution/rss_health.json"
        
        try:
            if not os.path.exists(rss_file):
                return {"status": "no_data"}
            
            with open(rss_file, 'r') as f:
                records = json.load(f)
            
            # 统计各源成功率
            source_stats = {}
            for record in records:
                sid = record.get("source_id", "unknown")
                if sid not in source_stats:
                    source_stats[sid] = {"total": 0, "success": 0}
                source_stats[sid]["total"] += 1
                if record.get("success"):
                    source_stats[sid]["success"] += 1
            
            # 识别问题源
            problematic = []
            for sid, stats in source_stats.items():
                rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
                if rate < 0.5:
                    problematic.append({
                        "source_id": sid,
                        "success_rate": rate,
                        "recommendation": "建议替换或修复"
                    })
            
            return {
                "status": "success",
                "source_count": len(source_stats),
                "problematic_sources": problematic,
                "recommendation": f"发现 {len(problematic)} 个问题源需要处理" if problematic else "所有源健康度良好"
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ═══════════════════════════════════════════════════════════
    # 3. 成本分析
    # ═══════════════════════════════════════════════════════════
    
    def analyze_cost(self, days: int = 7) -> Dict:
        """分析成本趋势"""
        try:
            from evolution.quota_monitor import QuotaMonitor
            monitor = QuotaMonitor(self.trendradar_path)
            
            # 读取使用记录
            usage_file = f"{self.trendradar_path}/evolution/ai_provider_usage.json"
            if not os.path.exists(usage_file):
                return {"status": "no_data"}
            
            with open(usage_file, 'r') as f:
                records = json.load(f)
            
            # 统计成本
            total_cost = sum(r.get("cost", 0) for r in records)
            deepseek_cost = sum(r.get("cost", 0) for r in records if r.get("provider") == "deepseek")
            free_usage = len([r for r in records if r.get("provider") in ["cloudflare_workers_ai", "google_gemini"]])
            
            return {
                "status": "success",
                "total_cost": total_cost,
                "deepseek_cost": deepseek_cost,
                "free_api_calls": free_usage,
                "savings_rate": free_usage / len(records) * 100 if records else 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ═══════════════════════════════════════════════════════════
    # 4. 综合优化报告
    # ═══════════════════════════════════════════════════════════
    
    def generate_optimization_report(self) -> str:
        """生成综合优化报告"""
        report = []
        report.append("=" * 70)
        report.append("🧬 系统自动优化报告")
        report.append(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        
        # 1. 质量分析
        report.append("\n📊 一、文章质量趋势")
        quality = self.analyze_quality_trend(14)
        if quality.get("status") == "success":
            report.append(f"   样本数: {quality['sample_size']} 篇")
            report.append(f"   平均分: {quality['avg_score']:.1f}/10")
            report.append(f"   趋势: {'📈' if quality['score_trend'] > 0 else '📉'} {quality['score_trend']:+.1f}")
            report.append(f"   建议: {quality['recommendation']}")
        else:
            report.append(f"   {quality.get('message', '暂无数据')}")
        
        # 2. RSS健康
        report.append("\n📡 二、RSS源健康度")
        rss = self.analyze_rss_health(7)
        if rss.get("status") == "success":
            report.append(f"   监控源数: {rss['source_count']}")
            if rss.get("problematic_sources"):
                report.append(f"   ⚠️ 问题源:")
                for src in rss["problematic_sources"]:
                    report.append(f"      - {src['source_id']}: 成功率 {src['success_rate']*100:.0f}%")
            report.append(f"   建议: {rss['recommendation']}")
        
        # 3. 成本分析
        report.append("\n💰 三、成本分析")
        cost = self.analyze_cost(7)
        if cost.get("status") == "success":
            report.append(f"   总成本: ¥{cost['total_cost']:.3f}")
            report.append(f"   DeepSeek成本: ¥{cost['deepseek_cost']:.3f}")
            report.append(f"   免费API调用: {cost['free_api_calls']} 次")
            report.append(f"   节省率: {cost['savings_rate']:.1f}%")
        
        # 4. 综合建议
        report.append("\n🎯 四、优化建议")
        suggestions = self._generate_suggestions(quality, rss, cost)
        for i, suggestion in enumerate(suggestions, 1):
            report.append(f"   {i}. {suggestion}")
        
        report.append("\n" + "=" * 70)
        return "\n".join(report)
    
    def _generate_suggestions(self, quality: Dict, rss: Dict, cost: Dict) -> List[str]:
        """生成具体优化建议"""
        suggestions = []
        
        # 质量建议
        if quality.get("score_trend", 0) < -0.5:
            suggestions.append("文章质量下降，启用高质量生成模式（强制DeepSeek）")
        
        # RSS建议
        if rss.get("problematic_sources"):
            suggestions.append(f"替换 {len(rss['problematic_sources'])} 个失效RSS源")
        
        # 成本建议
        if cost.get("savings_rate", 0) < 30:
            suggestions.append("免费API使用率偏低，检查额度配置")
        
        # 通用建议
        if not suggestions:
            suggestions.append("系统运行良好，保持当前策略")
            suggestions.append("可尝试启用A/B测试进一步优化Prompt")
        
        return suggestions


# 便捷函数
def run_auto_optimization(trendradar_path: str = ".") -> str:
    """运行自动优化"""
    optimizer = AutoOptimizer(trendradar_path)
    return optimizer.generate_optimization_report()


if __name__ == "__main__":
    print(run_auto_optimization())
