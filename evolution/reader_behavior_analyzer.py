# -*- coding: utf-8 -*-
"""
Lv52: 读者行为分析器 - 深度洞察内容消费模式

核心理念：
1. 分析已发布文章的标签分布、主题热度
2. 关联文章质量评分与读者潜在偏好
3. 识别内容缺口（高价值但覆盖不足的话题）
4. 输出可执行的 Content Strategy 建议

数据来源：
- Astro 博客已发布的文章 frontmatter
- TrendRadar article_metrics.json 质量评分
- RSS 源健康数据 rss_health.json

输出：
- 读者偏好报告 (evolution/reader_insight_report.md)
- 内容策略建议 JSON (evolution/content_strategy.json)
"""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ReaderBehaviorAnalyzer:
    """读者行为深度分析器"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.rss_health_file = f"{trendradar_path}/evolution/rss_health.json"
        self.report_file = f"{trendradar_path}/evolution/reader_insight_report.md"
        self.strategy_file = f"{trendradar_path}/evolution/content_strategy.json"

    def _load_metrics(self) -> List[Dict]:
        """加载文章质量数据"""
        if not os.path.exists(self.metrics_file):
            return []
        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _load_rss_health(self) -> Dict:
        """加载 RSS 源健康数据"""
        if not os.path.exists(self.rss_health_file):
            return {}
        try:
            with open(self.rss_health_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def analyze_tag_popularity(self, metrics: List[Dict]) -> Dict:
        """分析标签热度与质量关联"""
        tag_scores = defaultdict(list)
        tag_counts = Counter()

        for metric in metrics:
            score = metric.get("overall_score", 0)
            title = metric.get("title", "")
            # 从标题提取关键词作为标签代理
            keywords = self._extract_keywords(title)
            for kw in keywords:
                tag_scores[kw].append(score)
                tag_counts[kw] += 1

        # 计算每个标签的平均分、出现次数
        tag_analysis = {}
        for tag, scores in tag_scores.items():
            if len(scores) >= 1:
                avg = sum(scores) / len(scores)
                tag_analysis[tag] = {
                    "avg_score": round(avg, 1),
                    "count": len(scores),
                    "total_score": round(sum(scores), 1),
                    "heat_level": "🔥 热门" if avg >= 8.5 else "📈 良好" if avg >= 7 else "📊 一般",
                }

        # 按综合价值排序（平均分 * log(次数+1)）
        sorted_tags = sorted(
            tag_analysis.items(),
            key=lambda x: x[1]["avg_score"] * (1 + x[1]["count"] * 0.1),
            reverse=True,
        )
        return dict(sorted_tags[:15])

    def analyze_quality_trends(self, metrics: List[Dict]) -> Dict:
        """分析质量评分趋势"""
        if not metrics:
            return {}

        scores = [m.get("overall_score", 0) for m in metrics]
        tech_ratios = [m.get("tech_content_ratio", 0) for m in metrics]
        depths = [m.get("analysis_depth", 0) for m in metrics]

        # 按时间分组（如果有时间数据）
        recent = scores[-5:] if len(scores) >= 5 else scores
        older = scores[:5] if len(scores) >= 10 else scores[: len(scores) // 2]

        trend = "stable"
        if recent and older:
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            if recent_avg > older_avg + 0.5:
                trend = "improving"
            elif recent_avg < older_avg - 0.5:
                trend = "declining"

        return {
            "total_articles": len(metrics),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "avg_tech_ratio": round(sum(tech_ratios) / len(tech_ratios), 1) if tech_ratios else 0,
            "avg_depth": round(sum(depths) / len(depths), 1) if depths else 0,
            "highest_score": max(scores) if scores else 0,
            "lowest_score": min(scores) if scores else 0,
            "trend": trend,
            "recent_avg": round(sum(recent) / len(recent), 1) if recent else 0,
        }

    def analyze_source_quality(self) -> Dict:
        """分析 RSS 源质量贡献"""
        rss_health = self._load_rss_health()
        if not rss_health:
            return {}

        sources = rss_health.get("sources", [])
        source_analysis = {}

        for src in sources:
            name = src.get("name", "unknown")
            success_rate = src.get("success_rate", 0)
            avg_quality = src.get("avg_quality", 0)
            article_count = src.get("article_count", 0)

            # 综合价值 = 成功率 * 平均质量 * log(文章数+1)
            value = success_rate * avg_quality * (1 + article_count * 0.05)
            source_analysis[name] = {
                "success_rate": success_rate,
                "avg_quality": avg_quality,
                "article_count": article_count,
                "value_score": round(value, 1),
                "recommendation": (
                    "✅ 核心源" if value >= 7 else "🟡 辅助源" if value >= 4 else "🔴 待优化"
                ),
            }

        return dict(sorted(source_analysis.items(), key=lambda x: -x[1]["value_score"]))

    def identify_content_gaps(self, tag_analysis: Dict, metrics: List[Dict]) -> List[Dict]:
        """识别内容缺口 - 高潜力但覆盖不足的话题"""
        # 高评分但出现次数少的标签 = 潜力话题
        gaps = []
        for tag, data in tag_analysis.items():
            if data["avg_score"] >= 8.0 and data["count"] <= 2:
                gaps.append(
                    {
                        "topic": tag,
                        "avg_score": data["avg_score"],
                        "current_coverage": data["count"],
                        "potential": "🔥 高潜力缺口",
                        "suggestion": f"增加 '{tag}' 相关内容产出",
                    }
                )

        # 按潜力排序
        return sorted(gaps, key=lambda x: -x["avg_score"])[:8]

    def generate_content_strategy(self) -> Dict:
        """生成完整的内容策略建议"""
        metrics = self._load_metrics()
        if not metrics:
            return {"error": "No metrics data available"}

        tag_analysis = self.analyze_tag_popularity(metrics)
        quality_trends = self.analyze_quality_trends(metrics)
        source_quality = self.analyze_source_quality()
        content_gaps = self.identify_content_gaps(tag_analysis, metrics)

        # 生成策略建议
        strategies = []

        # 1. 标签策略
        if tag_analysis:
            top_tags = list(tag_analysis.keys())[:3]
            strategies.append(
                {
                    "type": "tag_focus",
                    "priority": "high",
                    "action": f"重点覆盖标签: {', '.join(top_tags)}",
                    "reason": "这些标签的文章评分最高，读者反响最好",
                }
            )

        # 2. 缺口填补
        if content_gaps:
            gap_topics = [g["topic"] for g in content_gaps[:3]]
            strategies.append(
                {
                    "type": "gap_fill",
                    "priority": "high",
                    "action": f"增加话题覆盖: {', '.join(gap_topics)}",
                    "reason": "高评分但内容覆盖不足，存在增长空间",
                }
            )

        # 3. 质量维持
        if quality_trends.get("trend") == "declining":
            strategies.append(
                {
                    "type": "quality_boost",
                    "priority": "urgent",
                    "action": "加强文章深度分析，提升技术内容占比",
                    "reason": "近期文章评分呈下降趋势",
                }
            )
        else:
            strategies.append(
                {
                    "type": "quality_maintain",
                    "priority": "medium",
                    "action": "保持当前质量标准，持续优化 Prompt",
                    "reason": "质量趋势稳定或上升",
                }
            )

        # 4. 源优化
        if source_quality:
            core_sources = [k for k, v in source_quality.items() if v["recommendation"] == "✅ 核心源"]
            weak_sources = [k for k, v in source_quality.items() if v["recommendation"] == "🔴 待优化"]
            if weak_sources:
                strategies.append(
                    {
                        "type": "source_optimize",
                        "priority": "medium",
                        "action": f"优化或替换低效 RSS 源: {', '.join(weak_sources[:2])}",
                        "reason": "这些源的成功率低或产出质量不足",
                    }
                )

        return {
            "generated_at": datetime.now().isoformat(),
            "quality_trends": quality_trends,
            "top_tags": tag_analysis,
            "source_quality": source_quality,
            "content_gaps": content_gaps,
            "strategies": strategies,
        }

    def generate_report(self) -> str:
        """生成 Markdown 格式的读者洞察报告"""
        strategy = self.generate_content_strategy()

        if "error" in strategy:
            return f"# 👤 读者行为分析报告\n\n> {strategy['error']}\n"

        lines = ["# 👤 Lv52 读者行为深度分析报告\n"]
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

        # 质量趋势
        trends = strategy.get("quality_trends", {})
        lines.append("## 📈 质量趋势概况\n")
        lines.append(f"- 分析文章数: **{trends.get('total_articles', 0)}** 篇")
        lines.append(f"- 平均评分: **{trends.get('avg_score', 0)}/10**")
        lines.append(f"- 技术内容占比: **{trends.get('avg_tech_ratio', 0)}/10**")
        lines.append(f"- 分析深度: **{trends.get('avg_depth', 0)}/10**")
        trend_emoji = {"improving": "📈 上升", "declining": "📉 下降", "stable": "➡️ 稳定"}
        lines.append(f"- 质量趋势: **{trend_emoji.get(trends.get('trend', 'stable'), '➡️ 稳定')}**")
        lines.append("")

        # 热门标签
        tags = strategy.get("top_tags", {})
        if tags:
            lines.append("## 🔥 热门话题排行\n")
            lines.append("| 话题 | 平均分 | 文章数 | 热度 |")
            lines.append("|------|--------|--------|------|")
            for tag, data in list(tags.items())[:10]:
                lines.append(f"| {tag} | {data['avg_score']} | {data['count']} | {data['heat_level']} |")
            lines.append("")

        # 内容缺口
        gaps = strategy.get("content_gaps", [])
        if gaps:
            lines.append("## 🎯 高潜力内容缺口\n")
            lines.append("| 话题 | 当前覆盖 | 平均分 | 建议 |")
            lines.append("|------|----------|--------|------|")
            for gap in gaps[:5]:
                lines.append(f"| {gap['topic']} | {gap['current_coverage']} 篇 | {gap['avg_score']} | {gap['suggestion']} |")
            lines.append("")

        # RSS 源质量
        sources = strategy.get("source_quality", {})
        if sources:
            lines.append("## 📡 RSS 源质量评估\n")
            lines.append("| 源名称 | 成功率 | 平均质量 | 文章数 | 评级 |")
            lines.append("|--------|--------|----------|--------|------|")
            for name, data in list(sources.items())[:8]:
                lines.append(
                    f"| {name} | {data['success_rate']}% | {data['avg_quality']} | {data['article_count']} | {data['recommendation']} |"
                )
            lines.append("")

        # 策略建议
        strategies = strategy.get("strategies", [])
        if strategies:
            lines.append("## 🎯 内容策略建议\n")
            priority_emoji = {"urgent": "🚨", "high": "🔴", "medium": "🟡", "low": "🟢"}
            for s in strategies:
                emoji = priority_emoji.get(s.get("priority", ""), "⚪")
                lines.append(f"{emoji} **[{s.get('priority', '').upper()}]** {s.get('action', '')}")
                lines.append(f"   > 💡 {s.get('reason', '')}")
                lines.append("")

        return "\n".join(lines)

    def save_outputs(self):
        """保存报告和策略 JSON"""
        # 保存 Markdown 报告
        report = self.generate_report()
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(report)

        # 保存策略 JSON
        strategy = self.generate_content_strategy()
        with open(self.strategy_file, "w", encoding="utf-8") as f:
            json.dump(strategy, f, ensure_ascii=False, indent=2)

        print(f"[Lv52] 报告已保存: {self.report_file}")
        print(f"[Lv52] 策略已保存: {self.strategy_file}")

    @staticmethod
    def _extract_keywords(title: str) -> List[str]:
        """从标题提取关键词"""
        # 常见科技关键词词典
        tech_keywords = [
            "AI", "人工智能", "大模型", "GPT", "LLM", "ChatGPT", "Claude",
            "芯片", "GPU", "TPU", "NPU", "半导体", "台积电", "英伟达",
            "新能源", "电动车", "特斯拉", "比亚迪", "电池", "储能",
            "苹果", "iPhone", "华为", "小米", "手机", "数码",
            "云计算", "AWS", "Azure", "阿里云", "腾讯云",
            "区块链", "比特币", "加密货币", "Web3",
            "自动驾驶", "机器人", "人形机器人",
            "SpaceX", "星舰", "航天", "卫星",
            "量子", "量子计算", "生物科技", "基因",
            "5G", "6G", "通信", "光刻机", "光刻",
            "算力", "数据中心", "液冷", "冷却",
            "OpenAI", "Anthropic", "Google", "Meta", "微软",
            "投资", "融资", "IPO", "股市", "财报",
            "地缘政治", "中美", "贸易战", "芯片战",
        ]

        found = []
        for kw in tech_keywords:
            if kw.lower() in title.lower():
                found.append(kw)
        return found[:5]  # 最多5个关键词


def run_reader_analysis(trendradar_path: str = "."):
    """运行读者行为分析"""
    analyzer = ReaderBehaviorAnalyzer(trendradar_path)
    analyzer.save_outputs()

    # 打印摘要
    strategy = analyzer.generate_content_strategy()
    if "error" not in strategy:
        trends = strategy.get("quality_trends", {})
        print(f"\n📊 Lv52 分析摘要:")
        print(f"  文章总数: {trends.get('total_articles', 0)}")
        print(f"  平均评分: {trends.get('avg_score', 0)}/10")
        print(f"  热门标签: {', '.join(list(strategy.get('top_tags', {}).keys())[:3])}")
        print(f"  策略建议: {len(strategy.get('strategies', []))} 条")


if __name__ == "__main__":
    run_reader_analysis()
