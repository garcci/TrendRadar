# -*- coding: utf-8 -*-
"""
Lv54: 竞品内容监控器 - 发现内容缺口与竞争机会

核心理念：
1. 分析外部科技趋势（GitHub Trending, HN, RSS）
2. 对比自身内容覆盖
3. 识别高热度但未被覆盖的话题
4. 输出竞争情报报告与内容机会清单

数据来源：
- 自身文章数据: evolution/article_metrics.json
- 外部趋势: evolution/github_trends.json (cross_project_learner 产出)
- RSS 源数据: evolution/rss_health.json

输出：
- 竞品监控报告: evolution/competitor_report.md
- 内容机会清单: evolution/content_opportunities.json
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class CompetitorMonitor:
    """竞品内容监控器"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.trends_file = f"{trendradar_path}/evolution/github_trends.json"
        self.rss_health_file = f"{trendradar_path}/evolution/rss_health.json"
        self.report_file = f"{trendradar_path}/evolution/competitor_report.md"
        self.opportunities_file = f"{trendradar_path}/evolution/content_opportunities.json"

    def _load_json(self, filepath: str) -> any:
        """安全加载 JSON"""
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _load_metrics(self) -> List[Dict]:
        """加载文章质量数据"""
        data = self._load_json(self.metrics_file)
        return data if isinstance(data, list) else []

    def _load_trends(self) -> List[Dict]:
        """加载外部趋势数据"""
        data = self._load_json(self.trends_file)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("trends", [])
        return []

    def _load_rss_topics(self) -> List[str]:
        """从 RSS 健康数据中提取话题"""
        data = self._load_json(self.rss_health_file)
        topics = []
        if isinstance(data, list):
            for item in data:
                if item.get("success"):
                    name = item.get("source_name", "")
                    if name:
                        topics.append(name)
        elif isinstance(data, dict):
            for src in data.get("sources", []):
                if src.get("success_rate", 0) > 50:
                    topics.append(src.get("name", ""))
        return [t for t in topics if t]

    def extract_self_topics(self, metrics: List[Dict]) -> Dict[str, int]:
        """提取自身内容的话题覆盖"""
        topic_counter = Counter()
        for metric in metrics:
            title = metric.get("title", "")
            keywords = self._extract_keywords(title)
            for kw in keywords:
                topic_counter[kw] += 1
        return dict(topic_counter)

    def extract_external_topics(self, trends: List[Dict]) -> Dict[str, float]:
        """提取外部趋势的热门话题及热度分"""
        topic_heat = defaultdict(float)
        for trend in trends:
            # GitHub trending 项目
            name = trend.get("name", "")
            desc = trend.get("description", "")
            stars = trend.get("stars", 0)
            
            # 提取关键词
            text = f"{name} {desc}"
            keywords = self._extract_keywords(text)
            
            # 热度分 = stars 的 log
            heat = max(1.0, min(10.0, float(stars or 0) / 1000))
            for kw in keywords:
                topic_heat[kw] += heat
        return dict(topic_heat)

    def find_content_gaps(
        self, self_topics: Dict[str, int], external_topics: Dict[str, float]
    ) -> List[Dict]:
        """发现内容缺口 - 外部热门但自身未覆盖的话题"""
        gaps = []
        for topic, heat in external_topics.items():
            self_count = self_topics.get(topic, 0)
            # 缺口定义：外部热度高但自身覆盖少
            if heat >= 5.0 and self_count <= 1:
                gaps.append(
                    {
                        "topic": topic,
                        "external_heat": round(heat, 1),
                        "self_coverage": self_count,
                        "gap_score": round(heat / max(self_count, 0.5), 1),
                        "priority": "🔥 高" if heat >= 10 else "⚡ 中" if heat >= 5 else "📌 低",
                        "suggestion": f"外部热度 {heat:.0f}，建议增加 '{topic}' 相关内容",
                    }
                )
        # 按缺口分排序
        return sorted(gaps, key=lambda x: -x["gap_score"])[:15]

    def find_over_covered(self, self_topics: Dict[str, int]) -> List[Dict]:
        """发现过度覆盖的话题"""
        over = []
        for topic, count in self_topics.items():
            if count >= 5:
                over.append(
                    {
                        "topic": topic,
                        "article_count": count,
                        "suggestion": f"已覆盖 {count} 篇，建议减少重复，寻找细分角度",
                    }
                )
        return sorted(over, key=lambda x: -x["article_count"])[:8]

    def generate_competitor_report(self) -> str:
        """生成竞品监控报告"""
        metrics = self._load_metrics()
        trends = self._load_trends()
        rss_topics = self._load_rss_topics()

        self_topics = self.extract_self_topics(metrics)
        external_topics = self.extract_external_topics(trends)
        gaps = self.find_content_gaps(self_topics, external_topics)
        over_covered = self.find_over_covered(self_topics)

        lines = ["# 🔍 Lv54 竞品内容监控报告\n"]
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

        # 概况
        lines.append("## 📊 内容覆盖概况\n")
        lines.append(f"- 自身文章数: **{len(metrics)}** 篇")
        lines.append(f"- 外部趋势源: **{len(trends)}** 条")
        lines.append(f"- 活跃 RSS 源: **{len(rss_topics)}** 个")
        lines.append(f"- 自身话题覆盖: **{len(self_topics)}** 个")
        lines.append(f"- 外部热门话题: **{len(external_topics)}** 个")
        lines.append("")

        # 内容缺口
        if gaps:
            lines.append("## 🔥 高价值内容缺口（外部热 + 自身少）\n")
            lines.append("| 话题 | 外部热度 | 自身覆盖 | 缺口分 | 优先级 |")
            lines.append("|------|----------|----------|--------|--------|")
            for gap in gaps[:10]:
                lines.append(
                    f"| {gap['topic']} | {gap['external_heat']} | {gap['self_coverage']} 篇 | {gap['gap_score']} | {gap['priority']} |"
                )
            lines.append("")

        # 过度覆盖
        if over_covered:
            lines.append("## ⚠️ 过度覆盖话题\n")
            lines.append("| 话题 | 文章数 | 建议 |")
            lines.append("|------|--------|------|")
            for oc in over_covered[:5]:
                lines.append(f"| {oc['topic']} | {oc['article_count']} | {oc['suggestion']} |")
            lines.append("")

        # 热门话题对比
        if external_topics:
            lines.append("## 🌡️ 外部热门话题 TOP10\n")
            sorted_ext = sorted(external_topics.items(), key=lambda x: -x[1])[:10]
            for i, (topic, heat) in enumerate(sorted_ext, 1):
                self_count = self_topics.get(topic, 0)
                status = "✅ 已覆盖" if self_count > 0 else "❌ 未覆盖"
                lines.append(f"{i}. **{topic}** (热度 {heat:.1f}) - {status}")
            lines.append("")

        # 策略建议
        lines.append("## 🎯 竞争策略建议\n")
        if gaps:
            top_gap = gaps[0]["topic"]
            lines.append(f"1. **优先覆盖**: '{top_gap}' 外部热度高但自身缺失")
        if over_covered:
            top_over = over_covered[0]["topic"]
            lines.append(f"2. **避免重复**: '{top_over}' 已过度覆盖，寻找细分角度")
        if len(gaps) > 5:
            lines.append(f"3. **机会众多**: 发现 {len(gaps)} 个内容缺口，建议制定专题计划")
        lines.append("")

        return "\n".join(lines)

    def generate_opportunities(self) -> Dict:
        """生成内容机会清单 JSON"""
        metrics = self._load_metrics()
        trends = self._load_trends()
        self_topics = self.extract_self_topics(metrics)
        external_topics = self.extract_external_topics(trends)
        gaps = self.find_content_gaps(self_topics, external_topics)

        return {
            "generated_at": datetime.now().isoformat(),
            "total_articles": len(metrics),
            "total_external_trends": len(trends),
            "self_topic_count": len(self_topics),
            "external_topic_count": len(external_topics),
            "gap_count": len(gaps),
            "top_opportunities": gaps[:5],
            "all_gaps": gaps,
        }

    def save_outputs(self):
        """保存报告和机会清单"""
        # 保存报告
        report = self.generate_competitor_report()
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(report)

        # 保存机会清单
        opportunities = self.generate_opportunities()
        with open(self.opportunities_file, "w", encoding="utf-8") as f:
            json.dump(opportunities, f, ensure_ascii=False, indent=2)

        print(f"[Lv54] 报告已保存: {self.report_file}")
        print(f"[Lv54] 机会清单已保存: {self.opportunities_file}")

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """从文本提取科技关键词"""
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
            "Rust", "Python", "Go", "TypeScript", "JavaScript",
            "开源", "GitHub", "开发者", "编程",
        ]
        found = []
        for kw in tech_keywords:
            if kw.lower() in text.lower():
                found.append(kw)
        return found[:5]


def run_competitor_monitor(trendradar_path: str = "."):
    """运行竞品内容监控"""
    print("=" * 60)
    print("🔍 Lv54 竞品内容监控器")
    print("=" * 60)

    monitor = CompetitorMonitor(trendradar_path)
    monitor.save_outputs()

    # 打印摘要
    opportunities = monitor.generate_opportunities()
    print(f"\n📊 Lv54 监控摘要:")
    print(f"  自身文章: {opportunities['total_articles']} 篇")
    print(f"  外部趋势: {opportunities['total_external_trends']} 条")
    print(f"  内容缺口: {opportunities['gap_count']} 个")
    if opportunities["top_opportunities"]:
        print(f"  优先机会: {opportunities['top_opportunities'][0]['topic']}")

    print("=" * 60)


if __name__ == "__main__":
    run_competitor_monitor()
