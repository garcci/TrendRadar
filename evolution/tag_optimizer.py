# -*- coding: utf-8 -*-
"""
Lv57: 自动标签优化器 - 提升文章标签相关性

核心理念：
1. 分析文章标题和内容特征
2. 基于科技关键词库匹配最优标签
3. 识别标签冗余和缺失
4. 输出标签优化建议

数据来源：
- 文章数据: evolution/article_metrics.json

输出：
- 标签优化报告: evolution/tag_optimization_report.md
- 标签优化建议 JSON: evolution/tag_recommendations.json
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional


class TagOptimizer:
    """自动标签优化器"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.report_file = f"{trendradar_path}/evolution/tag_optimization_report.md"
        self.recommendations_file = f"{trendradar_path}/evolution/tag_recommendations.json"

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

    def get_tech_keywords(self) -> Dict[str, List[str]]:
        """获取分层科技关键词库"""
        return {
            "AI": ["AI", "人工智能", "大模型", "GPT", "LLM", "ChatGPT", "Claude", "OpenAI", "Anthropic", "机器学习", "深度学习", "神经网络"],
            "芯片": ["芯片", "GPU", "TPU", "NPU", "半导体", "台积电", "英伟达", "NVIDIA", "AMD", "Intel", "光刻机", "光刻", "制程", "晶圆"],
            "新能源": ["新能源", "电动车", "特斯拉", "比亚迪", "电池", "储能", "锂电", "固态电池", "充电桩", "光伏", "风电", "氢能"],
            "手机数码": ["苹果", "iPhone", "华为", "小米", "OPPO", "vivo", "手机", "数码", "平板", "手表", "耳机"],
            "云计算": ["云计算", "AWS", "Azure", "阿里云", "腾讯云", "GCP", "华为云", "SaaS", "PaaS", "IaaS", "Serverless"],
            "自动驾驶": ["自动驾驶", "无人驾驶", "激光雷达", "特斯拉 FSD", "Apollo", "Waymo", "智能座舱", "车联网"],
            "机器人": ["机器人", "人形机器人", "机械臂", "波士顿动力", "宇树", "优必选", "具身智能"],
            "航天": ["SpaceX", "星舰", "航天", "卫星", "火箭", "马斯克", "Starlink", "北斗", "空间站", "登月"],
            "量子计算": ["量子", "量子计算", "量子通信", "超导", "量子霸权"],
            "生物科技": ["生物科技", "基因", "CRISPR", "mRNA", "疫苗", "合成生物学", "脑机接口"],
            "编程": ["Rust", "Python", "Go", "TypeScript", "JavaScript", "Java", "C++", "开源", "GitHub", "开发者", "编程"],
            "投资": ["投资", "融资", "IPO", "股市", "财报", "并购", "独角兽", "估值", "VC", "PE"],
            "通信": ["5G", "6G", "通信", "基站", "光纤", "毫米波", "WiFi 7", "卫星通信"],
            "区块链": ["区块链", "比特币", "加密货币", "Web3", "DeFi", "NFT", "以太坊", "智能合约"],
            "数据": ["大数据", "数据挖掘", "数据分析", "数据安全", "隐私计算", "联邦学习"],
        }

    def extract_tags(self, title: str) -> List[str]:
        """从标题提取标签"""
        keywords = self.get_tech_keywords()
        matched = []
        for category, terms in keywords.items():
            for term in terms:
                if term.lower() in title.lower():
                    matched.append(category)
                    break
        return matched if matched else ["科技"]

    def analyze_tag_distribution(self, metrics: List[Dict]) -> Dict[str, any]:
        """分析标签分布"""
        tag_counter = Counter()
        tag_scores = defaultdict(list)
        article_tags = []

        for metric in metrics:
            title = metric.get("title", "")
            score = metric.get("overall_score", 0)
            tags = self.extract_tags(title)
            article_tags.append({"title": title, "tags": tags, "score": score})
            for tag in tags:
                tag_counter[tag] += 1
                tag_scores[tag].append(score)

        # 计算每个标签的平均分
        tag_quality = {}
        for tag, scores in tag_scores.items():
            avg = sum(scores) / len(scores) if scores else 0
            tag_quality[tag] = {
                "count": len(scores),
                "avg_score": round(avg, 1),
                "total_score": round(sum(scores), 1),
            }

        return {
            "tag_distribution": dict(tag_counter),
            "tag_quality": tag_quality,
            "article_tags": article_tags,
        }

    def find_tag_issues(self, analysis: Dict) -> List[Dict]:
        """发现标签问题"""
        issues = []
        tag_dist = analysis.get("tag_distribution", {})
        tag_quality = analysis.get("tag_quality", {})
        article_tags = analysis.get("article_tags", [])

        # 1. 过度使用的标签
        for tag, count in tag_dist.items():
            if count >= 5:
                issues.append(
                    {
                        "type": "overused",
                        "tag": tag,
                        "count": count,
                        "severity": "medium",
                        "suggestion": f"'{tag}' 使用 {count} 次，建议细分具体方向",
                    }
                )

        # 2. 缺失标签的文章
        for article in article_tags:
            if len(article["tags"]) == 1 and article["tags"][0] == "科技":
                issues.append(
                    {
                        "type": "missing",
                        "title": article["title"],
                        "severity": "high",
                        "suggestion": "标题未匹配到具体科技标签，建议检查标题关键词",
                    }
                )

        # 3. 低质量标签
        for tag, data in tag_quality.items():
            if data["avg_score"] < 6 and data["count"] >= 2:
                issues.append(
                    {
                        "type": "low_quality",
                        "tag": tag,
                        "avg_score": data["avg_score"],
                        "count": data["count"],
                        "severity": "medium",
                        "suggestion": f"'{tag}' 标签下文章平均分仅 {data['avg_score']}，建议提升内容质量",
                    }
                )

        return issues

    def generate_recommendations(self) -> Dict:
        """生成标签优化建议"""
        metrics = self._load_metrics()
        if not metrics:
            return {"error": "No metrics data"}

        analysis = self.analyze_tag_distribution(metrics)
        issues = self.find_tag_issues(analysis)
        tag_dist = analysis.get("tag_distribution", {})
        tag_quality = analysis.get("tag_quality", {})

        # 生成改进建议
        recommendations = []

        # 1. 推荐增加的低频高质量标签
        low_freq_high_quality = [
            {"tag": tag, "avg_score": data["avg_score"], "count": data["count"]}
            for tag, data in tag_quality.items()
            if data["count"] <= 2 and data["avg_score"] >= 8
        ]
        if low_freq_high_quality:
            rec_tags = [d["tag"] for d in low_freq_high_quality[:3]]
            recommendations.append(
                {
                    "type": "expand",
                    "action": f"增加 '{', '.join(rec_tags)}' 相关内容",
                    "reason": "这些标签文章质量高但数量少，有增长空间",
                }
            )

        # 2. 推荐减少的过度使用标签
        overused = [i for i in issues if i["type"] == "overused"]
        if overused:
            rec_tags = [i["tag"] for i in overused[:2]]
            recommendations.append(
                {
                    "type": "refine",
                    "action": f"细分 '{', '.join(rec_tags)}' 标签，增加子分类",
                    "reason": "这些标签使用过于频繁，需要更细粒度分类",
                }
            )

        # 3. 整体标签健康度
        total_tags = len(tag_dist)
        if total_tags < 5:
            recommendations.append(
                {
                    "type": "diversify",
                    "action": "扩大内容覆盖范围，增加更多科技子领域",
                    "reason": f"当前仅 {total_tags} 个标签，话题覆盖较窄",
                }
            )

        return {
            "generated_at": datetime.now().isoformat(),
            "total_articles": len(metrics),
            "tag_count": len(tag_dist),
            "tag_distribution": tag_dist,
            "tag_quality": tag_quality,
            "issues": issues,
            "recommendations": recommendations,
        }

    def generate_report(self) -> str:
        """生成标签优化报告"""
        rec = self.generate_recommendations()
        if "error" in rec:
            return f"# 🏷️ Lv57 标签优化报告\n\n> {rec['error']}\n"

        lines = ["# 🏷️ Lv57 标签优化报告\n"]
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

        # 标签分布
        tag_dist = rec.get("tag_distribution", {})
        if tag_dist:
            lines.append("## 📊 标签分布\n")
            lines.append("| 标签 | 文章数 | 平均分 | 评级 |")
            lines.append("|------|--------|--------|------|")
            tag_quality = rec.get("tag_quality", {})
            for tag, count in sorted(tag_dist.items(), key=lambda x: -x[1]):
                quality = tag_quality.get(tag, {})
                avg = quality.get("avg_score", 0)
                rating = "⭐⭐⭐" if avg >= 8 else "⭐⭐" if avg >= 6 else "⭐"
                lines.append(f"| {tag} | {count} | {avg} | {rating} |")
            lines.append("")

        # 问题列表
        issues = rec.get("issues", [])
        if issues:
            lines.append("## ⚠️ 发现的问题\n")
            for issue in issues[:10]:
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                emoji = severity_emoji.get(issue.get("severity", ""), "⚪")
                lines.append(f"{emoji} **{issue['type'].upper()}**: {issue.get('tag', issue.get('title', ''))}")
                lines.append(f"   > {issue['suggestion']}")
                lines.append("")

        # 建议
        recommendations = rec.get("recommendations", [])
        if recommendations:
            lines.append("## 🎯 优化建议\n")
            for i, r in enumerate(recommendations, 1):
                lines.append(f"{i}. **{r['action']}**")
                lines.append(f"   > {r['reason']}")
                lines.append("")

        return "\n".join(lines)

    def save_outputs(self):
        """保存输出"""
        rec = self.generate_recommendations()
        with open(self.recommendations_file, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)

        report = self.generate_report()
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[Lv57] 建议已保存: {self.recommendations_file}")
        print(f"[Lv57] 报告已保存: {self.report_file}")


def run_tag_optimizer(trendradar_path: str = "."):
    """运行标签优化"""
    print("=" * 60)
    print("🏷️ Lv57 自动标签优化器")
    print("=" * 60)

    optimizer = TagOptimizer(trendradar_path)
    optimizer.save_outputs()

    rec = optimizer.generate_recommendations()
    print(f"\n📊 Lv57 优化摘要:")
    print(f"  文章数: {rec.get('total_articles', 0)}")
    print(f"  标签数: {rec.get('tag_count', 0)}")
    print(f"  问题数: {len(rec.get('issues', []))}")
    print(f"  建议数: {len(rec.get('recommendations', []))}")

    print("=" * 60)


if __name__ == "__main__":
    run_tag_optimizer()
