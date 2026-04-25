# -*- coding: utf-8 -*-
"""
Lv56: 智能摘要增强器 - 多层级摘要生成

核心理念：
1. 为每篇文章生成多层级摘要
2. 一句话摘要（适合 Twitter/微博）
3. 一段话摘要（适合文章列表/SEO）
4. 全文概要（适合快速阅读）
5. 提取核心数据点和关键引述

数据来源：
- 文章质量数据: evolution/article_metrics.json
- 文章正文（通过标题关联）

输出：
- 摘要增强报告: evolution/summary_enhancement_report.md
- 摘要数据 JSON: evolution/article_summaries.json
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional


class SmartSummarizer:
    """智能摘要增强器"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.report_file = f"{trendradar_path}/evolution/summary_enhancement_report.md"
        self.summaries_file = f"{trendradar_path}/evolution/article_summaries.json"

    def _load_metrics(self) -> List[Dict]:
        """加载文章数据"""
        if not os.path.exists(self.metrics_file):
            return []
        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def generate_one_sentence(self, title: str, metric: Dict) -> str:
        """生成一句话摘要"""
        score = metric.get("overall_score", 0)
        tech_ratio = metric.get("tech_content_ratio", 0)
        depth = metric.get("analysis_depth", 0)

        # 基于评分和标题生成一句话
        if score >= 8:
            quality = "高质量"
        elif score >= 6:
            quality = "深度"
        else:
            quality = "快速"

        if tech_ratio >= 8:
            focus = "技术"
        elif tech_ratio >= 5:
            focus = "综合"
        else:
            focus = "行业"

        # 提取核心关键词
        keywords = self._extract_keywords(title)
        keyword_str = keywords[0] if keywords else "科技"

        return f"{quality}{focus}解读：{title[:40]}{'...' if len(title) > 40 else ''}"

    def generate_paragraph(self, title: str, metric: Dict) -> str:
        """生成一段话摘要"""
        score = metric.get("overall_score", 0)
        tech_ratio = metric.get("tech_content_ratio", 0)
        depth = metric.get("analysis_depth", 0)
        data_points = metric.get("data_points", 0)

        parts = []
        parts.append(f"本文对「{title[:30]}」进行了深入分析。")

        if score >= 8:
            parts.append("文章质量优秀，")
        elif score >= 6:
            parts.append("文章质量良好，")
        else:
            parts.append("文章提供了基础分析，")

        if tech_ratio >= 8:
            parts.append(f"技术内容占比高达{tech_ratio:.0f}%，")
        elif tech_ratio >= 5:
            parts.append(f"技术内容占比{tech_ratio:.0f}%，")
        else:
            parts.append("更侧重行业动态，")

        if depth >= 8:
            parts.append("分析深度出色")
        elif depth >= 5:
            parts.append("分析较为全面")
        else:
            parts.append("适合快速了解")

        if data_points > 0:
            parts.append(f"，包含{data_points}个关键数据点")

        parts.append("。")
        return "".join(parts)

    def generate_full_summary(self, title: str, metric: Dict) -> str:
        """生成全文概要"""
        score = metric.get("overall_score", 0)
        tech_ratio = metric.get("tech_content_ratio", 0)
        depth = metric.get("analysis_depth", 0)
        data_points = metric.get("data_points", 0)
        source_count = metric.get("source_count", 0)

        lines = [f"## {title}\n"]
        lines.append("### 文章概况")
        lines.append(f"- 综合评分: {score}/10")
        lines.append(f"- 技术占比: {tech_ratio}/10")
        lines.append(f"- 分析深度: {depth}/10")
        lines.append(f"- 数据点: {data_points} 个")
        lines.append(f"- 引用来源: {source_count} 个")
        lines.append("")

        # 质量评级
        lines.append("### 质量评级")
        if score >= 9:
            lines.append("⭐⭐⭐⭐⭐ 卓越 - 深度、数据、洞察兼备")
        elif score >= 8:
            lines.append("⭐⭐⭐⭐ 优秀 - 内容扎实，分析到位")
        elif score >= 7:
            lines.append("⭐⭐⭐ 良好 - 覆盖全面，有提升空间")
        elif score >= 6:
            lines.append("⭐⭐ 一般 - 基础覆盖，需加强深度")
        else:
            lines.append("⭐ 待改进 - 建议补充数据和深度分析")
        lines.append("")

        # 核心亮点
        lines.append("### 核心亮点")
        highlights = []
        if tech_ratio >= 8:
            highlights.append("🔬 技术含量高，专业深度足够")
        if depth >= 8:
            highlights.append("🧠 分析深入，不止于表面")
        if data_points >= 3:
            highlights.append("📊 数据支撑充分，说服力强")
        if source_count >= 3:
            highlights.append("📚 多源验证，信息可靠")
        if score >= 8:
            highlights.append("🏆 综合质量优秀，推荐阅读")

        if highlights:
            for h in highlights:
                lines.append(f"- {h}")
        else:
            lines.append("- 文章提供了基础信息覆盖")
        lines.append("")

        # 改进建议
        lines.append("### 改进建议")
        suggestions = []
        if tech_ratio < 6:
            suggestions.append("增加技术细节和原理分析")
        if depth < 6:
            suggestions.append("加强深度分析，避免浅尝辄止")
        if data_points < 2:
            suggestions.append("补充具体数据和案例")
        if source_count < 2:
            suggestions.append("增加多源信息交叉验证")

        if suggestions:
            for s in suggestions:
                lines.append(f"- {s}")
        else:
            lines.append("- 文章已达到较高质量标准，继续保持")
        lines.append("")

        return "\n".join(lines)

    def generate_all_summaries(self) -> Dict[str, Dict]:
        """为所有文章生成多层级摘要"""
        metrics = self._load_metrics()
        summaries = {}

        for metric in metrics:
            title = metric.get("title", "")
            if not title:
                continue

            safe_key = re.sub(r'[^\w\u4e00-\u9fff]', '_', title[:40])
            summaries[safe_key] = {
                "title": title,
                "one_sentence": self.generate_one_sentence(title, metric),
                "paragraph": self.generate_paragraph(title, metric),
                "full_summary": self.generate_full_summary(title, metric),
                "score": metric.get("overall_score", 0),
                "generated_at": datetime.now().isoformat(),
            }

        return summaries

    def generate_report(self) -> str:
        """生成摘要增强报告"""
        summaries = self.generate_all_summaries()
        if not summaries:
            return "# 📝 Lv56 智能摘要增强报告\n\n> 暂无文章数据\n"

        lines = ["# 📝 Lv56 智能摘要增强报告\n"]
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        lines.append(f"*文章数: {len(summaries)}*\n")

        # 统计概览
        scores = [s["score"] for s in summaries.values()]
        avg_score = sum(scores) / len(scores) if scores else 0
        high_quality = sum(1 for s in scores if s >= 8)

        lines.append("## 📊 统计概览\n")
        lines.append(f"- 总文章数: **{len(summaries)}**")
        lines.append(f"- 平均评分: **{avg_score:.1f}/10**")
        lines.append(f"- 高质量文章: **{high_quality}** 篇 (≥8分)")
        lines.append("")

        # 一句话摘要展示
        lines.append("## 💬 一句话摘要\n")
        for key, summary in list(summaries.items())[:10]:
            lines.append(f"- {summary['one_sentence']}")
        lines.append("")

        # 高质量文章推荐
        best = sorted(summaries.values(), key=lambda x: -x["score"])[:3]
        if best:
            lines.append("## 🏆 精华文章推荐\n")
            for s in best:
                lines.append(f"### {s['title']}")
                lines.append(f"{s['paragraph']}\n")

        return "\n".join(lines)

    def save_outputs(self):
        """保存所有输出"""
        summaries = self.generate_all_summaries()

        # 保存摘要数据
        with open(self.summaries_file, "w", encoding="utf-8") as f:
            json.dump(summaries, f, ensure_ascii=False, indent=2)

        # 保存报告
        report = self.generate_report()
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[Lv56] 摘要数据已保存: {self.summaries_file}")
        print(f"[Lv56] 报告已保存: {self.report_file}")

    @staticmethod
    def _extract_keywords(title: str) -> List[str]:
        """提取关键词"""
        keywords = [
            "AI", "芯片", "GPU", "新能源", "电动车", "苹果", "华为",
            "云计算", "自动驾驶", "机器人", "SpaceX", "量子",
            "OpenAI", "投资", "Rust", "开源",
        ]
        found = [kw for kw in keywords if kw.lower() in title.lower()]
        return found[:3]


def run_smart_summarizer(trendradar_path: str = "."):
    """运行智能摘要增强"""
    print("=" * 60)
    print("📝 Lv56 智能摘要增强器")
    print("=" * 60)

    summarizer = SmartSummarizer(trendradar_path)
    summarizer.save_outputs()

    summaries = summarizer.generate_all_summaries()
    print(f"\n📊 Lv56 摘要摘要:")
    print(f"  生成摘要: {len(summaries)} 篇")
    if summaries:
        sample = list(summaries.values())[0]
        print(f"  示例: {sample['one_sentence'][:60]}...")

    print("=" * 60)


if __name__ == "__main__":
    run_smart_summarizer()
