# -*- coding: utf-8 -*-
"""
跨源关联引擎 - 发现不同RSS源的关联话题

核心理念：
1. 同一话题在不同平台会有不同视角
2. 跨平台关联能提供更全面的分析角度
3. 自动发现隐藏的关联和趋势

关联算法：
- 关键词匹配：提取各源关键词，计算重叠度
- 语义相似度：使用简单文本相似度算法
- 时间聚类：同时出现在多个源的话题更可能是大事件

输出：
- 关联话题簇：哪些平台在讨论同一话题
- 跨平台视角：不同平台的不同观点
- 独特话题：只在某个平台出现的新鲜话题
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple


class CrossSourceAnalyzer:
    """跨源关联分析器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
    
    def extract_keywords(self, text: str) -> Set[str]:
        """从文本中提取关键词"""
        # 提取中文关键词（2-8字）
        keywords = set(re.findall(r'[\u4e00-\u9fa5]{2,8}', text))
        
        # 提取英文技术词汇
        tech_words = re.findall(r'[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,2}', text)
        for word in tech_words:
            if len(word) >= 3 and word.lower() not in {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'she', 'use', 'her', 'way', 'many', 'oil', 'sit', 'set', 'run', 'eat', 'far', 'sea', 'eye', 'ask', 'own', 'say', 'too', 'any', 'try', 'end', 'why', 'let', 'put', 'say', 'she', 'try', 'way', 'own', 'too', 'old', 'tell', 'very', 'when', 'much', 'would', 'there', 'their', 'what', 'said', 'each', 'which', 'will', 'about', 'could', 'other', 'after', 'first', 'never', 'these', 'think', 'where', 'being', 'every', 'great', 'might', 'shall', 'still', 'those', 'while', 'this', 'that', 'with', 'have', 'from', 'they', 'know', 'want', 'been', 'good', 'just', 'come', 'time', 'than', 'them', 'well', 'were', 'look', 'more', 'also', 'back', 'only', 'over', 'year', 'work', 'life', 'even', 'here', 'into', 'such', 'make', 'take', 'long', 'most', 'find', 'give', 'does', 'made', 'part', 'keep', 'call', 'came', 'need', 'feel', 'seem', 'turn', 'hand', 'high', 'sure', 'upon', 'head', 'help', 'home', 'side', 'move', 'both', 'five', 'once', 'same', 'must', 'name', 'left', 'each', 'done', 'open', 'case', 'show', 'live', 'play', 'went', 'told', 'seen', 'sent', 'felt', 'land', 'line', 'kind', 'next', 'word', 'came', 'went', 'told', 'seen', 'sent', 'felt', 'land', 'line', 'kind', 'next', 'word'}:
                keywords.add(word)
        
        return keywords
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（简单Jaccard）"""
        keywords1 = self.extract_keywords(text1)
        keywords2 = self.extract_keywords(text2)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        
        return len(intersection) / len(union)
    
    def find_topic_clusters(self, platform_items: Dict[str, List[Dict]]) -> List[Dict]:
        """
        发现跨平台话题簇
        
        Args:
            platform_items: {平台名: [{title, excerpt, url}, ...]}
            
        返回: 话题簇列表
        """
        # 1. 收集所有items并标注来源
        all_items = []
        for platform, items in platform_items.items():
            for item in items:
                all_items.append({
                    **item,
                    "source_platform": platform
                })
        
        # 2. 计算相似度矩阵
        n = len(all_items)
        clusters = []
        visited = set()
        
        for i in range(n):
            if i in visited:
                continue
            
            # 寻找与当前item相似的其他items
            cluster_items = [all_items[i]]
            visited.add(i)
            
            for j in range(i + 1, n):
                if j in visited:
                    continue
                
                similarity = self.calculate_similarity(
                    all_items[i].get("title", "") + all_items[i].get("excerpt", ""),
                    all_items[j].get("title", "") + all_items[j].get("excerpt", "")
                )
                
                # 相似度阈值0.2（较低，因为不同平台表述差异大）
                if similarity >= 0.2:
                    cluster_items.append(all_items[j])
                    visited.add(j)
            
            # 只保留跨平台的话题簇（至少2个平台）
            platforms = set(item["source_platform"] for item in cluster_items)
            if len(platforms) >= 2:
                clusters.append({
                    "size": len(cluster_items),
                    "platforms": list(platforms),
                    "items": cluster_items,
                    "representative_title": cluster_items[0].get("title", "")
                })
        
        # 按簇大小排序
        clusters.sort(key=lambda x: x["size"], reverse=True)
        return clusters
    
    def generate_cross_source_insights(self, clusters: List[Dict]) -> str:
        """
        生成跨源关联洞察文本
        
        返回: 可用于注入到Prompt中的文本
        """
        if not clusters:
            return ""
        
        lines = ["\n### 🔗 跨平台关联分析\n"]
        lines.append("以下话题在多个平台同时出现，具有较高关注度：\n")
        
        for i, cluster in enumerate(clusters[:5], 1):  # 最多5个簇
            lines.append(f"**关联话题{i}**: {cluster['representative_title'][:50]}...")
            lines.append(f"- 涉及平台: {', '.join(cluster['platforms'])}")
            lines.append(f"- 相关报道数: {cluster['size']}条")
            
            # 列出各平台标题（简短）
            for item in cluster["items"][:3]:
                platform = item["source_platform"]
                title = item.get("title", "")[:40]
                lines.append(f"  - {platform}: {title}...")
            
            lines.append("")
        
        lines.append("**建议**：优先选择跨平台关联话题进行深度分析，提供多视角观点。\n")
        
        return "\n".join(lines)
    
    def find_unique_topics(self, platform_items: Dict[str, List[Dict]], 
                          min_platform_size: int = 3) -> Dict[str, List[Dict]]:
        """
        发现各平台的独特话题（只在某个平台出现）
        
        返回: {平台名: [独特话题列表]}
        """
        # 1. 先找到所有跨平台话题的关键词
        cross_platform_keywords = set()
        clusters = self.find_topic_clusters(platform_items)
        for cluster in clusters:
            for item in cluster["items"]:
                cross_platform_keywords.update(
                    self.extract_keywords(item.get("title", ""))
                )
        
        # 2. 找出每个平台的独特话题
        unique_topics = {}
        for platform, items in platform_items.items():
            if len(items) < min_platform_size:
                continue
            
            unique = []
            for item in items:
                keywords = self.extract_keywords(item.get("title", ""))
                # 如果与跨平台关键词重叠度<0.3，认为是独特话题
                overlap = len(keywords & cross_platform_keywords) / max(len(keywords), 1)
                if overlap < 0.3:
                    unique.append(item)
            
            if unique:
                unique_topics[platform] = unique[:5]  # 最多5个
        
        return unique_topics


# 便捷函数
def analyze_cross_source(platform_items: Dict[str, List[Dict]], 
                        trendradar_path: str = ".") -> Tuple[str, List[Dict]]:
    """
    分析跨源关联
    
    返回: (Prompt增强文本, 话题簇列表)
    """
    analyzer = CrossSourceAnalyzer(trendradar_path)
    clusters = analyzer.find_topic_clusters(platform_items)
    insights = analyzer.generate_cross_source_insights(clusters)
    return insights, clusters


if __name__ == "__main__":
    # 测试
    test_data = {
        "Hacker News": [
            {"title": "OpenAI releases GPT-5 with 40% performance boost", "excerpt": "New model"},
            {"title": "Rust 1.75 released with async improvements", "excerpt": "New features"}
        ],
        "TechCrunch": [
            {"title": "OpenAI's GPT-5: A 40% leap in AI capabilities", "excerpt": "Analysis"},
            {"title": "Startup funding drops 30% in Q4", "excerpt": "Report"}
        ],
        "36氪": [
            {"title": "OpenAI发布GPT-5，性能提升40%", "excerpt": "评测"},
            {"title": "国内大模型厂商纷纷跟进", "excerpt": "动态"}
        ]
    }
    
    analyzer = CrossSourceAnalyzer()
    clusters = analyzer.find_topic_clusters(test_data)
    print(f"发现 {len(clusters)} 个跨平台话题簇")
    for c in clusters:
        print(f"- {c['representative_title'][:50]}... ({c['size']}条, 平台: {c['platforms']})")
