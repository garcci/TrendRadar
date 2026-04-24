# -*- coding: utf-8 -*-
"""
异常预测预防 - Lv35

核心理念：
1. 分析历史异常的时间模式和规律
2. 识别可预测的异常（如固定时间429、特定源定期失败）
3. 在异常发生前采取预防措施
4. 降低系统故障率

预测维度：
- 时间模式: 某些异常是否在固定时间发生（如每小时的第0分钟429）
- 频率模式: 异常频率是否在增加
- 关联模式: 某些异常是否总是成对出现
- 源模式: 哪些RSS源/API有周期性故障

预防措施：
- 预热: 在异常高发时段前预热备用API
- 规避: 暂时避开已知有问题的源
- 缓存: 在异常高发时段使用缓存数据
- 限流: 主动降低请求频率

输出：
- 异常预测报告
- 预防建议
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ExceptionPredictor:
    """异常预测器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.knowledge_base_file = f"{trendradar_path}/evolution/exception_knowledge.json"
    
    def _load_knowledge_base(self) -> Dict:
        """加载异常知识库"""
        if os.path.exists(self.knowledge_base_file):
            try:
                with open(self.knowledge_base_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"exceptions": [], "patterns": {}}
    
    def _parse_hour(self, timestamp: str) -> int:
        """从时间戳提取小时"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00').replace('+00:00', ''))
            return dt.hour
        except Exception:
            return -1
    
    def _parse_weekday(self, timestamp: str) -> int:
        """从时间戳提取星期几"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00').replace('+00:00', ''))
            return dt.weekday()
        except Exception:
            return -1
    
    def analyze_time_patterns(self, exceptions: List[Dict]) -> Dict:
        """分析异常的时间模式"""
        if not exceptions:
            return {}
        
        # 按小时统计
        hour_distribution = Counter()
        for exc in exceptions:
            hour = self._parse_hour(exc.get("timestamp", ""))
            if hour >= 0:
                hour_distribution[hour] += 1
        
        # 找出异常高发时段
        high_risk_hours = []
        avg = len(exceptions) / 24
        for hour, count in hour_distribution.items():
            if count > avg * 2:  # 超过平均值2倍
                high_risk_hours.append({
                    "hour": hour,
                    "count": count,
                    "risk_level": "high" if count > avg * 3 else "medium"
                })
        
        # 按星期几统计
        weekday_distribution = Counter()
        for exc in exceptions:
            wd = self._parse_weekday(exc.get("timestamp", ""))
            if wd >= 0:
                weekday_distribution[wd] += 1
        
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        high_risk_days = []
        for wd, count in weekday_distribution.items():
            if count > len(exceptions) / 7 * 1.5:
                high_risk_days.append({
                    "day": weekday_names[wd],
                    "count": count,
                    "risk_level": "medium"
                })
        
        return {
            "high_risk_hours": sorted(high_risk_hours, key=lambda x: -x["count"]),
            "high_risk_days": sorted(high_risk_days, key=lambda x: -x["count"]),
            "hour_distribution": dict(sorted(hour_distribution.items()))
        }
    
    def analyze_frequency_trend(self, exceptions: List[Dict]) -> Dict:
        """分析异常频率趋势"""
        if not exceptions:
            return {}
        
        # 按天分组统计
        daily_counts = defaultdict(int)
        for exc in exceptions:
            try:
                dt = datetime.fromisoformat(exc.get("timestamp", "").replace('Z', '+00:00').replace('+00:00', ''))
                day_key = dt.strftime("%Y-%m-%d")
                daily_counts[day_key] += 1
            except Exception:
                continue
        
        if len(daily_counts) < 3:
            return {"message": "数据不足，无法分析趋势"}
        
        sorted_days = sorted(daily_counts.items())
        
        # 计算最近3天的平均值
        recent_avg = sum(count for _, count in sorted_days[-3:]) / 3
        older_avg = sum(count for _, count in sorted_days[:3]) / 3 if len(sorted_days) >= 6 else recent_avg
        
        trend = "increasing" if recent_avg > older_avg * 1.3 else "decreasing" if recent_avg < older_avg * 0.7 else "stable"
        
        return {
            "trend": trend,
            "recent_avg": round(recent_avg, 1),
            "older_avg": round(older_avg, 1) if older_avg > 0 else 0,
            "total_days": len(daily_counts),
            "peak_day": max(daily_counts.items(), key=lambda x: x[1])[0] if daily_counts else "",
            "peak_count": max(daily_counts.values()) if daily_counts else 0
        }
    
    def analyze_source_patterns(self, exceptions: List[Dict]) -> List[Dict]:
        """分析异常源模式"""
        # 从异常信息中提取源名称
        source_patterns = defaultdict(lambda: {"count": 0, "categories": Counter()})
        
        for exc in exceptions:
            msg = exc.get("message", "")
            category = exc.get("category", "")
            
            # 尝试提取URL中的域名
            import re
            urls = re.findall(r'https?://([^/\s\'"]+)', msg)
            
            for url in urls:
                source_patterns[url]["count"] += 1
                source_patterns[url]["categories"][category] += 1
        
        # 转换为列表并排序
        results = []
        for source, data in sorted(source_patterns.items(), key=lambda x: -x[1]["count"]):
            if data["count"] >= 2:  # 至少出现2次
                results.append({
                    "source": source,
                    "count": data["count"],
                    "main_category": data["categories"].most_common(1)[0][0] if data["categories"] else "unknown",
                    "risk_level": "high" if data["count"] >= 5 else "medium"
                })
        
        return results[:5]  # 只返回前5个
    
    def generate_predictions(self) -> Dict:
        """生成异常预测"""
        kb = self._load_knowledge_base()
        exceptions = kb.get("exceptions", [])
        
        # 只分析最近7天的异常
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        recent_exceptions = [e for e in exceptions if e.get("timestamp", "") > cutoff]
        
        if not recent_exceptions:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "healthy",
                "message": "过去7天无异常记录，系统运行良好"
            }
        
        predictions = {
            "timestamp": datetime.now().isoformat(),
            "analysis_period": "7天",
            "total_exceptions": len(recent_exceptions),
            "time_patterns": self.analyze_time_patterns(recent_exceptions),
            "frequency_trend": self.analyze_frequency_trend(recent_exceptions),
            "source_patterns": self.analyze_source_patterns(recent_exceptions),
            "prevention_suggestions": []
        }
        
        # 生成预防建议
        suggestions = []
        
        # 基于时间模式的建议
        high_risk_hours = predictions["time_patterns"].get("high_risk_hours", [])
        if high_risk_hours:
            hours = ", ".join(str(h["hour"]) for h in high_risk_hours[:3])
            suggestions.append(f"⚠️ 异常高发时段: {hours}时，建议降低请求频率或预热备用API")
        
        # 基于频率趋势的建议
        trend = predictions["frequency_trend"].get("trend", "")
        if trend == "increasing":
            suggestions.append("🚨 异常频率呈上升趋势，建议全面审查系统稳定性")
        
        # 基于源模式的建议
        sources = predictions["source_patterns"]
        if sources:
            for src in sources[:2]:
                if src["risk_level"] == "high":
                    suggestions.append(f"🔴 源 {src['source']} 频繁异常({src['count']}次)，建议禁用或寻找替代")
                else:
                    suggestions.append(f"🟡 源 {src['source']} 有异常记录，建议监控")
        
        # 基于类别的建议
        category_counts = Counter(e.get("category", "") for e in recent_exceptions)
        top_category = category_counts.most_common(1)
        if top_category:
            cat, count = top_category[0]
            if count >= 5:
                suggestions.append(f"📊 {cat}类异常最多({count}次)，建议针对性优化")
        
        predictions["prevention_suggestions"] = suggestions
        
        # 总体状态
        if len(suggestions) >= 3:
            predictions["status"] = "warning"
        elif len(suggestions) >= 1:
            predictions["status"] = "caution"
        else:
            predictions["status"] = "healthy"
        
        return predictions
    
    def generate_prediction_insight(self) -> str:
        """生成预测洞察（用于Prompt注入）"""
        predictions = self.generate_predictions()
        
        lines = ["\n### 🔮 异常预测与预防\n"]
        
        status = predictions.get("status", "")
        if status == "healthy":
            lines.append("**系统状态**: 🟢 健康（过去7天异常频率低）\n")
            return "\n".join(lines)
        
        emoji = "🔴" if status == "warning" else "🟡"
        lines.append(f"**系统状态**: {emoji} {status.upper()}")
        lines.append(f"**分析周期**: {predictions.get('analysis_period', '7天')}")
        lines.append(f"**异常总数**: {predictions.get('total_exceptions', 0)}")
        lines.append("")
        
        # 频率趋势
        trend = predictions.get("frequency_trend", {})
        if "trend" in trend:
            trend_emoji = "📈" if trend["trend"] == "increasing" else "📉" if trend["trend"] == "decreasing" else "➡️"
            lines.append(f"**频率趋势**: {trend_emoji} {trend['trend']} (近期平均: {trend.get('recent_avg', 0)}/天)")
            lines.append("")
        
        # 预防建议
        suggestions = predictions.get("prevention_suggestions", [])
        if suggestions:
            lines.append("**预防建议**:")
            for sug in suggestions:
                lines.append(f"- {sug}")
            lines.append("")
        
        lines.append("**建议**: 关注异常趋势，提前采取预防措施。\n")
        
        return "\n".join(lines)


# 便捷函数
def get_exception_prediction(trendradar_path: str = ".") -> str:
    """获取异常预测"""
    predictor = ExceptionPredictor(trendradar_path)
    return predictor.generate_prediction_insight()


if __name__ == "__main__":
    predictor = ExceptionPredictor()
    predictions = predictor.generate_predictions()
    print(json.dumps(predictions, ensure_ascii=False, indent=2))
