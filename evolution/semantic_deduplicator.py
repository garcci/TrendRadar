# -*- coding: utf-8 -*-
"""
语义去重引擎 — 基于语义相似度的跨天话题去重

问题：
1. 同一话题可能在连续多天出现（如"OpenAI 发布新模型"）
2. 简单标题匹配无法捕捉语义相似但表述不同的话题
3. 读者对重复话题感到疲劳

解决方案：
1. 获取最近 N 天的文章标题和摘要
2. 提取关键词向量
3. 计算当前话题与历史文章的语义相似度
4. 相似度超过阈值时建议跳过或更换角度
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple


class SemanticDeduplicator:
    """语义去重引擎"""

    # 科技领域关键词库（用于增强语义表示）
    TECH_KEYWORDS = {
        "ai": ["人工智能", "ai", "大模型", "llm", "神经网络", "深度学习", "机器学习",
               "gpt", "claude", "gemini", "llama", "transformer", "agent", "rag"],
        "chip": ["芯片", "半导体", "gpu", "cpu", "npu", "tpu", "制程", "光刻",
                 "晶圆", "代工", "台积电", "英特尔", "英伟达", "amd"],
        "cloud": ["云计算", "云原生", "容器", "kubernetes", "docker", "serverless",
                  "aws", "azure", "gcp", "阿里云", "腾讯云"],
        "security": ["安全", "网络安全", "漏洞", "黑客", "加密", "隐私", "零信任",
                     "渗透测试", "防火墙"],
        "opensource": ["开源", "github", "license", "社区", "贡献者", "fork", "pr",
                       "merge", "版本控制"],
        "data": ["数据", "大数据", "数据库", "数据仓库", "数据湖", "etl", "bi",
                 "analytics", "数据治理"],
        "robot": ["机器人", " robotics", "自动驾驶", "无人机", "具身智能",
                   "机械臂", "传感器", "slam"],
        "quantum": ["量子", "量子计算", "量子通信", "量子纠缠", "超导"],
        "biotech": ["生物", "基因", "crispr", "合成生物学", "脑机接口", "神经科学"],
        "energy": ["新能源", "电池", "储能", "光伏", "风电", "氢能", "核聚变",
                   "固态电池", "充电桩"],
    }

    def __init__(
        self,
        github_owner: str = "garcci",
        github_repo: str = "Astro",
        github_token: Optional[str] = None,
        similarity_threshold: float = 0.65,
        lookback_days: int = 7,
    ):
        self.owner = github_owner
        self.repo = github_repo
        self.token = github_token or os.environ.get("ASTRO_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.threshold = similarity_threshold
        self.lookback_days = lookback_days
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.headers["Accept"] = "application/vnd.github.v3+json"
        self.headers["User-Agent"] = "TrendRadar-SemanticDeduplicator/1.0"

    def check_duplication(self, current_topics: List[str]) -> Dict:
        """
        检查当前话题是否与近期文章重复

        Args:
            current_topics: 当前热点标题列表

        Returns:
            {
                "is_duplicate": bool,
                "similar_articles": List[Dict],
                "max_similarity": float,
                "recommendation": str,
            }
        """
        # 获取最近文章
        recent_articles = self._get_recent_articles()
        if not recent_articles:
            return {
                "is_duplicate": False,
                "similar_articles": [],
                "max_similarity": 0.0,
                "recommendation": "无历史文章，可以生成",
            }

        # 计算相似度
        similar_articles = []
        max_similarity = 0.0

        current_vector = self._extract_semantic_vector(" ".join(current_topics))

        for article in recent_articles:
            article_text = f"{article.get('title', '')} {article.get('excerpt', '')}"
            article_vector = self._extract_semantic_vector(article_text)

            similarity = self._calculate_similarity(current_vector, article_vector)

            if similarity > max_similarity:
                max_similarity = similarity

            if similarity >= self.threshold:
                similar_articles.append({
                    "title": article.get("title", ""),
                    "date": article.get("date", ""),
                    "similarity": round(similarity, 3),
                    "url": article.get("url", ""),
                })

        # 排序
        similar_articles.sort(key=lambda x: x["similarity"], reverse=True)

        # 生成建议
        if max_similarity >= 0.85:
            recommendation = f"高度重复（相似度 {max_similarity:.0%}），建议跳过今日生成"
        elif max_similarity >= self.threshold:
            recommendation = f"中度重复（相似度 {max_similarity:.0%}），建议更换角度或深入分析"
        elif max_similarity >= 0.4:
            recommendation = f"轻度关联（相似度 {max_similarity:.0%}），可以生成但建议寻找新角度"
        else:
            recommendation = f"话题新鲜（相似度 {max_similarity:.0%}），可以生成"

        return {
            "is_duplicate": max_similarity >= self.threshold,
            "similar_articles": similar_articles[:5],  # 只返回前5个
            "max_similarity": round(max_similarity, 3),
            "recommendation": recommendation,
        }

    def _get_recent_articles(self) -> List[Dict]:
        """通过 GitHub API 获取最近的文章列表"""
        try:
            # 获取 news 目录下的文件列表
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/src/content/posts/news"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                files = json.loads(resp.read().decode())

            # 过滤最近 N 天的 .md 文件
            cutoff = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%Y-%m-%d")
            recent_files = []
            for f in files:
                if not isinstance(f, dict):
                    continue
                name = f.get("name", "")
                if not name.endswith(".md"):
                    continue
                # 检查文件名是否以日期开头
                if len(name) >= 10 and name[:10] >= cutoff:
                    recent_files.append(f)

            # 获取文件内容
            articles = []
            for f in recent_files[:10]:  # 最多检查10篇
                try:
                    content = self._get_file_content(f.get("download_url", ""))
                    if content:
                        article = self._parse_article(content, f.get("name", ""))
                        if article:
                            articles.append(article)
                except Exception:
                    continue

            return articles

        except Exception:
            return []

    def _get_file_content(self, download_url: str) -> Optional[str]:
        """获取文件内容"""
        if not download_url:
            return None
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": self.headers["User-Agent"]})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _parse_article(self, content: str, filename: str) -> Optional[Dict]:
        """解析文章 frontmatter 和正文"""
        try:
            # 提取 frontmatter
            if not content.startswith("---"):
                return None

            parts = content.split("---", 2)
            if len(parts) < 3:
                return None

            fm_text = parts[1].strip()
            body = parts[2].strip()[:500]  # 只取前500字符作为摘要

            # 简单解析 frontmatter
            title = ""
            date = filename[:10] if len(filename) >= 10 else ""
            for line in fm_text.split("\n"):
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"').strip("'")

            return {
                "title": title,
                "date": date,
                "excerpt": body,
                "filename": filename,
                "url": f"https://www.gjqqq.com/posts/news/{filename.replace('.md', '')}/",
            }
        except Exception:
            return None

    def _extract_semantic_vector(self, text: str) -> Dict[str, float]:
        """
        提取语义向量（基于关键词频率和领域权重）

        返回: {keyword: weight}
        """
        text_lower = text.lower()

        # 分词（简单空格分词+中文单字）
        tokens = set()
        # 英文词
        tokens.update(re.findall(r'[a-z]+', text_lower))
        # 中文字
        tokens.update(re.findall(r'[\u4e00-\u9fff]', text))
        # 中文词（2-4字）
        tokens.update(re.findall(r'[\u4e00-\u9fff]{2,4}', text_lower))

        vector = {}

        # 直接词频
        for token in tokens:
            if len(token) >= 2 or token in "abcdefghijklmnopqrstuvwxyz":
                vector[token] = vector.get(token, 0) + 1

        # 领域关键词增强
        for domain, keywords in self.TECH_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    # 领域关键词赋予更高权重
                    weight = 2.0 if len(kw) >= 2 else 1.0
                    vector[kw] = vector.get(kw, 0) + weight
                    # 同时给整个领域加分
                    vector[f"__domain_{domain}"] = vector.get(f"__domain_{domain}", 0) + 1

        return vector

    def _calculate_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """计算两个语义向量的余弦相似度"""
        if not vec1 or not vec2:
            return 0.0

        # 取交集
        common = set(vec1.keys()) & set(vec2.keys())
        if not common:
            return 0.0

        # 点积
        dot_product = sum(vec1[k] * vec2[k] for k in common)

        # 模长
        norm1 = sum(v ** 2 for v in vec1.values()) ** 0.5
        norm2 = sum(v ** 2 for v in vec2.values()) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


def check_content_duplication(
    topics: List[str],
    github_owner: str = "garcci",
    github_repo: str = "Astro",
    github_token: Optional[str] = None,
    threshold: float = 0.65,
) -> Dict:
    """
    便捷函数：检查内容是否重复

    Returns:
        {
            "is_duplicate": bool,
            "similar_articles": List[Dict],
            "max_similarity": float,
            "recommendation": str,
        }
    """
    deduplicator = SemanticDeduplicator(
        github_owner=github_owner,
        github_repo=github_repo,
        github_token=github_token,
        similarity_threshold=threshold,
    )
    return deduplicator.check_duplication(topics)


if __name__ == "__main__":
    # 测试
    test_topics = [
        "OpenAI 发布 GPT-5 模型",
        "Anthropic 推出 Claude 4",
        "AI 大模型竞争加剧",
    ]
    result = check_content_duplication(test_topics)
    print(json.dumps(result, ensure_ascii=False, indent=2))
