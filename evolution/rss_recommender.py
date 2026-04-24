# -*- coding: utf-8 -*-
"""
智能RSS源推荐 - Lv32

核心理念：
1. 分析现有文章主题，识别内容覆盖缺口
2. 从RSS源库中匹配缺失话题的高质量源
3. 推荐新的RSS源以丰富内容多样性
4. 持续优化RSS源组合

RSS源库分类：
- AI/大模型: OpenAI Blog, Google AI Blog, Anthropic
- 芯片/硬件: AnandTech, Tom's Hardware
- 编程/开发: GitHub Blog, Dev.to, Hashnode
- 中文科技: 36氪, 钛媒体, 量子位, 机器之心
- 国际科技: TechCrunch, The Verge, Wired
- 学术: arXiv CS, Papers With Code
- 财经/市场: 华尔街见闻, 雅虎财经

输出：
- 内容覆盖分析报告
- 缺失话题识别
- 推荐RSS源列表
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class RSSRecommender:
    """智能RSS源推荐器"""
    
    # RSS源库（预设高质量源）
    RSS_SOURCE_LIBRARY = {
        "ai_llm": {
            "category": "AI/大模型",
            "sources": [
                {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "keywords": ["AI", "GPT", "OpenAI", "大模型"]},
                {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "keywords": ["AI", "Google", "Gemini", "机器学习"]},
                {"name": "Anthropic", "url": "https://www.anthropic.com/rss.xml", "keywords": ["AI", "Claude", "安全", "对齐"]},
                {"name": "DeepLearning.AI", "url": "https://www.deeplearning.ai/blog/rss.xml", "keywords": ["AI", "深度学习", "课程"]},
            ]
        },
        "chip_hardware": {
            "category": "芯片/硬件",
            "sources": [
                {"name": "AnandTech", "url": "https://www.anandtech.com/rss/", "keywords": ["芯片", "CPU", "GPU", "硬件"]},
                {"name": "Tom's Hardware", "url": "https://www.tomshardware.com/rss.xml", "keywords": ["硬件", "评测", "GPU"]},
                {"name": "Semiconductor Engineering", "url": "https://semiengineering.com/feed/", "keywords": ["半导体", "芯片", "制程"]},
            ]
        },
        "programming": {
            "category": "编程/开发",
            "sources": [
                {"name": "GitHub Blog", "url": "https://github.blog/feed/", "keywords": ["开源", "GitHub", "开发"]},
                {"name": "Dev.to", "url": "https://dev.to/feed", "keywords": ["编程", "开发", "教程"]},
                {"name": "CSS-Tricks", "url": "https://css-tricks.com/feed/", "keywords": ["前端", "CSS", "Web"]},
            ]
        },
        "cn_tech": {
            "category": "中文科技",
            "sources": [
                {"name": "量子位", "url": "https://www.qbitai.com/feed", "keywords": ["AI", "科技", "中国"]},
                {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "keywords": ["AI", "机器学习", "中国"]},
                {"name": "雷峰网", "url": "https://www.leiphone.com/feed", "keywords": ["科技", "创业", "中国"]},
            ]
        },
        "intl_tech": {
            "category": "国际科技",
            "sources": [
                {"name": "Wired", "url": "https://www.wired.com/feed/rss", "keywords": ["科技", "未来", "创新"]},
                {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/", "keywords": ["科技", "MIT", "研究"]},
                {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "keywords": ["科技", "产品", "消费电子"]},
            ]
        },
        "academic": {
            "category": "学术研究",
            "sources": [
                {"name": "Papers With Code", "url": "https://paperswithcode.com/rss", "keywords": ["论文", "代码", "SOTA"]},
                {"name": " distill.pub", "url": "https://distill.pub/rss.xml", "keywords": ["可视化", "深度学习", "解释"]},
            ]
        },
        "finance_market": {
            "category": "财经/市场",
            "sources": [
                {"name": "Bloomberg Technology", "url": "https://feeds.bloomberg.com/bloomberg/markets.rss", "keywords": ["财经", "市场", "科技股市"]},
                {"name": "CNBC Technology", "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html", "keywords": ["财经", "科技股", "市场"]},
            ]
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
        self.config_file = f"{trendradar_path}/config/config.yaml"
    
    def _load_metrics(self, days: int = 30) -> List[Dict]:
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
    
    def _extract_existing_sources(self) -> List[str]:
        """提取当前配置中的RSS源"""
        existing = []
        
        if not os.path.exists(self.config_file):
            return existing
        
        try:
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # 简单提取所有name字段（已启用的源）
            import re
            # 匹配 name: "xxx" 的行
            name_matches = re.findall(r'^\s*name:\s*"([^"]+)"', content, re.MULTILINE)
            
            # 过滤掉平台名称，只保留RSS源
            # 简单判断：包含"网"、"报"、"志"、"Blog"、"RSS"的通常是RSS源
            rss_keywords = ['网', '报', '志', 'Blog', 'RSS', 'Feed', 'News', 'Times', 'Post']
            for name in name_matches:
                if any(kw in name for kw in rss_keywords):
                    existing.append(name)
        except Exception:
            pass
        
        return existing
    
    def analyze_topic_coverage(self, metrics: List[Dict]) -> Dict:
        """分析现有内容的话题覆盖情况"""
        if not metrics:
            return {"error": "No metrics data"}
        
        # 统计所有话题
        topic_counter = Counter()
        for metric in metrics:
            keywords = metric.get("keywords", [])
            hot_topics = metric.get("hot_topics", [])
            for topic in keywords + hot_topics:
                if len(topic) >= 2:
                    topic_counter[topic] += 1
        
        # 计算各类别的覆盖度
        category_coverage = {}
        for cat_id, cat_info in self.RSS_SOURCE_LIBRARY.items():
            cat_keywords = []
            for source in cat_info["sources"]:
                cat_keywords.extend(source["keywords"])
            
            # 计算该类别关键词在文章中的出现频率
            matched_topics = []
            matched_count = 0
            for keyword in set(cat_keywords):
                if keyword in topic_counter:
                    matched_topics.append({"topic": keyword, "count": topic_counter[keyword]})
                    matched_count += topic_counter[keyword]
            
            # 覆盖度评分 (0-10)
            coverage_score = min(10, matched_count / len(metrics) * 2)
            
            category_coverage[cat_id] = {
                "category": cat_info["category"],
                "coverage_score": round(coverage_score, 1),
                "matched_topics": sorted(matched_topics, key=lambda x: -x["count"])[:5],
                "status": "good" if coverage_score >= 7 else "moderate" if coverage_score >= 4 else "poor"
            }
        
        return category_coverage
    
    def identify_gaps(self, coverage: Dict) -> List[Dict]:
        """识别内容覆盖缺口"""
        gaps = []
        
        for cat_id, cat_data in coverage.items():
            if cat_data["status"] in ["poor", "moderate"]:
                cat_info = self.RSS_SOURCE_LIBRARY.get(cat_id, {})
                
                gaps.append({
                    "category": cat_data["category"],
                    "coverage_score": cat_data["coverage_score"],
                    "status": cat_data["status"],
                    "missing_keywords": self._get_missing_keywords(cat_id, cat_data.get("matched_topics", [])),
                    "recommended_sources": cat_info.get("sources", [])[:2]  # 推荐前2个源
                })
        
        # 按缺口严重程度排序
        gaps.sort(key=lambda x: x["coverage_score"])
        
        return gaps
    
    def _get_missing_keywords(self, cat_id: str, matched_topics: List[Dict]) -> List[str]:
        """获取缺失的关键词"""
        cat_info = self.RSS_SOURCE_LIBRARY.get(cat_id, {})
        all_keywords = set()
        for source in cat_info.get("sources", []):
            all_keywords.update(source["keywords"])
        
        matched = {t["topic"] for t in matched_topics}
        missing = all_keywords - matched
        
        return list(missing)[:5]
    
    def generate_recommendations(self, gaps: List[Dict]) -> List[Dict]:
        """生成RSS源推荐"""
        recommendations = []
        
        for gap in gaps[:3]:  # 最多推荐3个类别
            for source in gap.get("recommended_sources", []):
                recommendations.append({
                    "category": gap["category"],
                    "gap_status": gap["status"],
                    "source_name": source["name"],
                    "source_url": source["url"],
                    "relevance_keywords": source["keywords"][:3],
                    "reason": f"{gap['category']}覆盖度较低({gap['coverage_score']}/10)，建议添加"
                })
        
        return recommendations
    
    def generate_recommendation_report(self) -> Dict:
        """生成推荐报告"""
        metrics = self._load_metrics(days=30)
        existing_sources = self._extract_existing_sources()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "analysis_period_days": 30,
            "existing_sources_count": len(existing_sources),
            "existing_sources": existing_sources[:10]  # 只显示前10个
        }
        
        # 话题覆盖分析
        coverage = self.analyze_topic_coverage(metrics)
        report["topic_coverage"] = coverage
        
        # 缺口识别
        gaps = self.identify_gaps(coverage)
        report["gaps"] = gaps
        
        # 推荐源
        recommendations = self.generate_recommendations(gaps)
        report["recommendations"] = recommendations
        
        # 总体评估
        if coverage:
            avg_coverage = sum(c["coverage_score"] for c in coverage.values()) / len(coverage)
            report["overall_coverage"] = round(avg_coverage, 1)
            report["coverage_assessment"] = "良好" if avg_coverage >= 7 else "一般" if avg_coverage >= 5 else "需改进"
        
        return report
    
    def generate_recommendation_insight(self) -> str:
        """生成推荐洞察（用于Prompt注入）"""
        report = self.generate_recommendation_report()
        
        lines = ["\n### 📡 RSS源智能推荐\n"]
        
        # 总体覆盖
        overall = report.get("overall_coverage", 0)
        assessment = report.get("coverage_assessment", "未知")
        lines.append(f"**内容覆盖度**: {overall}/10 ({assessment})")
        lines.append("")
        
        # 缺口
        gaps = report.get("gaps", [])
        if gaps:
            lines.append("**内容缺口**:")
            for gap in gaps[:3]:
                emoji = "🔴" if gap["status"] == "poor" else "🟡"
                lines.append(f"- {emoji} {gap['category']}: 覆盖度 {gap['coverage_score']}/10")
            lines.append("")
        
        # 推荐
        recommendations = report.get("recommendations", [])
        if recommendations:
            lines.append("**推荐RSS源**:")
            for rec in recommendations[:3]:
                lines.append(f"- 📡 {rec['source_name']} ({rec['category']})")
                lines.append(f"  原因: {rec['reason']}")
            lines.append("")
        
        lines.append("**建议**: 关注缺失话题领域，丰富内容多样性。\n")
        
        return "\n".join(lines)


# 便捷函数
def get_rss_recommendation_insight(trendradar_path: str = ".") -> str:
    """获取RSS推荐洞察"""
    recommender = RSSRecommender(trendradar_path)
    return recommender.generate_recommendation_insight()


def get_rss_recommendation_report(trendradar_path: str = ".") -> Dict:
    """获取RSS推荐报告"""
    recommender = RSSRecommender(trendradar_path)
    return recommender.generate_recommendation_report()


if __name__ == "__main__":
    recommender = RSSRecommender()
    report = recommender.generate_recommendation_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
