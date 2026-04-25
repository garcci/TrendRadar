# -*- coding: utf-8 -*-
"""
Lv55: 跨源观点聚合器 - 多源信息融合生成深度报道

核心理念：
1. 识别同一话题下的多篇文章
2. 提取每篇文章的核心观点和数据
3. 整合不同来源的信息，生成360度视角
4. 输出深度分析文章或报告

数据来源：
- 自身文章数据: evolution/article_metrics.json
- 外部趋势: evolution/github_trends.json
- RSS 源数据: evolution/rss_health.json

输出：
- 深度聚合报告: evolution/synthesis_reports/
- 话题聚类索引: evolution/topic_clusters.json
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional


class CrossSourceSynthesizer:
    """跨源观点聚合器"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.trends_file = f"{trendradar_path}/evolution/github_trends.json"
        self.report_dir = f"{trendradar_path}/evolution/synthesis_reports"
        self.clusters_file = f"{trendradar_path}/evolution/topic_clusters.json"

        os.makedirs(self.report_dir, exist_ok=True)

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
        """加载文章数据"""
        data = self._load_json(self.metrics_file)
        return data if isinstance(data, list) else []

    def _load_trends(self) -> List[Dict]:
        """加载外部趋势"""
        data = self._load_json(self.trends_file)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("trends", [])
        return []

    def _extract_topic(self, title: str) -> Optional[str]:
        """从标题提取核心话题"""
        tech_keywords = [
            "AI", "人工智能", "大模型", "GPT", "LLM", "ChatGPT",
            "芯片", "GPU", "半导体", "英伟达", "台积电",
            "新能源", "电动车", "特斯拉", "比亚迪", "电池",
            "苹果", "iPhone", "华为", "小米",
            "云计算", "AWS", "Azure", "阿里云",
            "自动驾驶", "机器人",
            "SpaceX", "星舰", "航天",
            "量子", "量子计算",
            "OpenAI", "Anthropic", "Google", "Meta",
            "投资", "融资", "IPO",
            "Rust", "Python", "Go",
        ]
        for kw in tech_keywords:
            if kw.lower() in title.lower():
                return kw
        return None

    def cluster_articles(self, metrics: List[Dict]) -> Dict[str, List[Dict]]:
        """按话题聚类文章"""
        clusters = defaultdict(list)
        uncategorized = []

        for metric in metrics:
            title = metric.get("title", "")
            topic = self._extract_topic(title)
            if topic:
                clusters[topic].append(metric)
            else:
                uncategorized.append(metric)

        # 只保留有2篇以上的话题
        result = {k: v for k, v in clusters.items() if len(v) >= 2}
        if uncategorized:
            result["其他"] = uncategorized
        return result

    def generate_synthesis(self, topic: str, articles: List[Dict]) -> str:
        """为话题生成聚合分析报告"""
        if len(articles) < 2:
            return ""

        lines = [f"# 🔬 {topic} 深度聚合分析\n"]
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        lines.append(f"*基于 {len(articles)} 篇文章聚合*\n")

        # 文章概览
        lines.append("## 📰 来源文章\n")
        for i, article in enumerate(articles, 1):
            title = article.get("title", "")
            score = article.get("overall_score", 0)
            depth = article.get("analysis_depth", 0)
            lines.append(f"{i}. **{title}** (评分 {score}/10, 深度 {depth}/10)")
        lines.append("")

        # 数据聚合
        scores = [a.get("overall_score", 0) for a in articles]
        tech_ratios = [a.get("tech_content_ratio", 0) for a in articles]
        depths = [a.get("analysis_depth", 0) for a in articles]

        avg_score = sum(scores) / len(scores) if scores else 0
        avg_tech = sum(tech_ratios) / len(tech_ratios) if tech_ratios else 0
        avg_depth = sum(depths) / len(depths) if depths else 0

        lines.append("## 📊 数据聚合\n")
        lines.append(f"- 平均评分: **{avg_score:.1f}/10**")
        lines.append(f"- 平均技术占比: **{avg_tech:.1f}/10**")
        lines.append(f"- 平均分析深度: **{avg_depth:.1f}/10**")
        lines.append(f"- 文章数量: **{len(articles)}** 篇")
        lines.append("")

        # 多角度对比
        lines.append("## 🔍 多角度对比\n")
        best = max(articles, key=lambda x: x.get("overall_score", 0))
        deepest = max(articles, key=lambda x: x.get("analysis_depth", 0))
        most_tech = max(articles, key=lambda x: x.get("tech_content_ratio", 0))

        lines.append(f"- 🏆 **最高评分**: {best.get('title', '')}")
        lines.append(f"- 🧠 **最深分析**: {deepest.get('title', '')}")
        lines.append(f"- 🔬 **最高技术占比**: {most_tech.get('title', '')}")
        lines.append("")

        # 内容缺口分析
        if avg_depth < 7:
            lines.append("## ⚠️ 分析缺口\n")
            lines.append(f"- 该话题平均分析深度仅 {avg_depth:.1f}/10，建议增加深度解读")
            lines.append("")

        # 综合观点
        lines.append("## 💡 综合观点\n")
        lines.append(f"基于 {len(articles)} 篇文章的交叉验证，'{topic}' 是一个")
        if avg_score >= 8:
            lines.append("**高价值话题**，文章质量 consistently 优秀。")
        elif avg_score >= 6:
            lines.append("**中等价值话题**，有提升空间。")
        else:
            lines.append("**需关注话题**，文章质量有待改善。")

        if len(articles) >= 3:
            lines.append(f"多源报道显示该话题持续受关注，建议跟进最新动态。")
        lines.append("")

        # 行动建议
        lines.append("## 🎯 行动建议\n")
        if avg_depth < 7:
            lines.append("1. **增加深度分析**: 当前分析偏浅，建议挖掘技术细节")
        if avg_tech < 7:
            lines.append("2. **提升技术含量**: 增加数据、代码、架构等硬核内容")
        if len(articles) >= 3 and avg_score >= 7:
            lines.append("3. **专题策划**: 话题热度高，可考虑制作系列专题")
        lines.append("")

        return "\n".join(lines)

    def generate_all_syntheses(self) -> Dict[str, str]:
        """为所有聚类话题生成聚合报告"""
        metrics = self._load_metrics()
        if not metrics:
            return {}

        clusters = self.cluster_articles(metrics)
        reports = {}

        for topic, articles in clusters.items():
            if len(articles) >= 2 and topic != "其他":
                report = self.generate_synthesis(topic, articles)
                reports[topic] = report

                # 保存到文件
                safe_topic = re.sub(r'[^\w\u4e00-\u9fff]', '_', topic)
                filepath = f"{self.report_dir}/{safe_topic}_synthesis.md"
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"[Lv55] 已生成: {filepath}")

        return reports

    def generate_cluster_index(self) -> Dict:
        """生成话题聚类索引"""
        metrics = self._load_metrics()
        clusters = self.cluster_articles(metrics)

        index = {
            "generated_at": datetime.now().isoformat(),
            "total_articles": len(metrics),
            "topic_count": len([k for k in clusters.keys() if k != "其他"]),
            "clusters": {},
        }

        for topic, articles in clusters.items():
            if topic == "其他":
                continue
            scores = [a.get("overall_score", 0) for a in articles]
            index["clusters"][topic] = {
                "article_count": len(articles),
                "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
                "article_titles": [a.get("title", "") for a in articles],
                "has_synthesis": len(articles) >= 2,
            }

        # 保存索引
        with open(self.clusters_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        return index

    def save_outputs(self):
        """保存所有输出"""
        reports = self.generate_all_syntheses()
        index = self.generate_cluster_index()

        print(f"[Lv55] 生成聚合报告: {len(reports)} 个话题")
        print(f"[Lv55] 话题聚类索引: {index['topic_count']} 个话题")


def run_cross_source_synthesis(trendradar_path: str = "."):
    """运行跨源观点聚合"""
    print("=" * 60)
    print("🔬 Lv55 跨源观点聚合器")
    print("=" * 60)

    synthesizer = CrossSourceSynthesizer(trendradar_path)
    synthesizer.save_outputs()

    # 打印摘要
    metrics = synthesizer._load_metrics()
    clusters = synthesizer.cluster_articles(metrics)
    multi_article_topics = [k for k, v in clusters.items() if len(v) >= 2 and k != "其他"]

    print(f"\n📊 Lv55 聚合摘要:")
    print(f"  总文章数: {len(metrics)}")
    print(f"  话题数: {len(clusters)}")
    print(f"  多源话题: {len(multi_article_topics)}")
    if multi_article_topics:
        print(f"  优先聚合: {', '.join(multi_article_topics[:3])}")

    print("=" * 60)


if __name__ == "__main__":
    run_cross_source_synthesis()
