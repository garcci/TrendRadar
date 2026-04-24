# -*- coding: utf-8 -*-
"""
Lv42: 跨项目学习引擎

从外部数据源（GitHub Trending、HackerNews、Dev.to等）提取技术趋势
和最佳实践，将洞察注入Prompt，提升文章深度和时效性。

数据源：
1. GitHub Trending - 热门项目、技术栈变化
2. HackerNews - 技术讨论热点
3. Dev.to - 开发者社区趋势
4. Stack Overflow - 热门标签

输出：
- 技术趋势洞察（用于Prompt注入）
- 热门技术栈变化
- 新兴框架/工具推荐
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 零API成本 - 使用公开网页抓取
import urllib.request
from urllib.error import HTTPError, URLError


class CrossProjectLearner:
    """跨项目学习引擎"""
    
    # 数据源配置
    SOURCES = {
        "github_trending": {
            "url": "https://github.com/trending",
            "type": "html",
            "weight": 1.0
        },
        "github_trending_python": {
            "url": "https://github.com/trending/python",
            "type": "html",
            "weight": 0.9
        },
        "github_trending_javascript": {
            "url": "https://github.com/trending/javascript",
            "type": "html",
            "weight": 0.9
        },
        "hackernews": {
            "url": "https://news.ycombinator.com/",
            "type": "html",
            "weight": 0.8
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.cache_dir = f"{trendradar_path}/evolution/learning_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _fetch(self, url: str, timeout: int = 15) -> Optional[str]:
        """抓取网页内容"""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "identity"
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
                # 尝试解码
                for encoding in ["utf-8", "gb2312", "gbk", "latin-1"]:
                    try:
                        return data.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                return data.decode("utf-8", errors="ignore")
        except (HTTPError, URLError) as e:
            print(f"  [跨项目学习] 抓取失败 {url}: {e}")
            return None
        except Exception as e:
            print(f"  [跨项目学习] 异常 {url}: {e}")
            return None
    
    def _get_cache(self, source_id: str) -> Optional[str]:
        """获取缓存内容"""
        cache_file = f"{self.cache_dir}/{source_id}.html"
        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < 3600:  # 1小时缓存
                try:
                    with open(cache_file, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                except Exception:
                    pass
        return None
    
    def _set_cache(self, source_id: str, content: str):
        """设置缓存"""
        cache_file = f"{self.cache_dir}/{source_id}.html"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            pass
    
    def extract_github_trending(self, html: str) -> List[Dict]:
        """从GitHub Trending HTML提取热门项目"""
        if not html:
            return []
        
        projects = []
        
        # 提取项目名和描述
        # GitHub Trending的HTML结构
        repo_pattern = re.compile(
            r'h2[^>]*>\s*<a[^>]*href="(/[^/]+/[^"]+)"[^>]*>.*?<span[^>]*>([^<]+)</span>.*?<span[^>]*>([^<]+)</span>.*?<p[^>]*>(.*?)</p>',
            re.DOTALL | re.IGNORECASE
        )
        
        matches = repo_pattern.findall(html)
        for i, match in enumerate(matches[:10]):  # 取前10个
            try:
                href = match[0]
                owner = match[1].strip() if match[1] else ""
                name = match[2].strip() if match[2] else ""
                desc = re.sub(r'<[^>]+>', '', match[3]).strip() if match[3] else ""
                desc = re.sub(r'\s+', ' ', desc)
                
                # 尝试提取语言
                lang_match = re.search(
                    r'itemprop="programmingLanguage">([^<]+)</span>',
                    html[html.find(href):html.find(href)+2000] if html.find(href) >= 0 else ""
                )
                language = lang_match.group(1).strip() if lang_match else "Unknown"
                
                # 尝试提取今日星标
                stars_match = re.search(
                    r'(\d+)\s*stars\s*today',
                    html[html.find(href):html.find(href)+3000] if html.find(href) >= 0 else "",
                    re.IGNORECASE
                )
                today_stars = int(stars_match.group(1)) if stars_match else 0
                
                projects.append({
                    "rank": i + 1,
                    "owner": owner,
                    "name": name,
                    "full_name": f"{owner}/{name}",
                    "description": desc[:200],
                    "language": language,
                    "today_stars": today_stars,
                    "url": f"https://github.com{href}"
                })
            except Exception:
                continue
        
        # 如果上面没匹配到，尝试简化模式
        if not projects:
            # 提取所有仓库链接
            repo_links = re.findall(r'href="(/[^/]+/[^"]+)"[^>]*>\s*<span[^>]*>([^<]+)</span>\s*/\s*<span[^>]*>([^<]+)</span>', html)
            seen = set()
            for href, owner, name in repo_links[:15]:
                key = f"{owner}/{name}"
                if key in seen:
                    continue
                seen.add(key)
                
                projects.append({
                    "rank": len(projects) + 1,
                    "owner": owner.strip(),
                    "name": name.strip(),
                    "full_name": key,
                    "description": "",
                    "language": "Unknown",
                    "today_stars": 0,
                    "url": f"https://github.com{href}"
                })
                if len(projects) >= 10:
                    break
        
        return projects
    
    def extract_hackernews(self, html: str) -> List[Dict]:
        """从HackerNews提取热门话题"""
        if not html:
            return []
        
        topics = []
        
        # HN的HTML结构: titleline
        title_pattern = re.compile(
            r'<span class="titleline">\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>',
            re.IGNORECASE
        )
        
        score_pattern = re.compile(
            r'(\d+)\s*points?',
            re.IGNORECASE
        )
        
        matches = title_pattern.findall(html)
        for i, match in enumerate(matches[:10]):
            try:
                url = match[0]
                title = match[1].strip()
                
                if not title or title.startswith("("):
                    continue
                
                # 提取分数
                score = 0
                score_search = html[max(0, html.find(match[0])-500):html.find(match[0])+1000]
                score_match = score_pattern.search(score_search)
                if score_match:
                    score = int(score_match.group(1))
                
                topics.append({
                    "rank": i + 1,
                    "title": title[:150],
                    "url": url,
                    "score": score,
                    "source": "hackernews"
                })
            except Exception:
                continue
        
        return topics
    
    def analyze_tech_trends(self, github_projects: List[Dict], hackernews_topics: List[Dict]) -> Dict:
        """分析技术趋势"""
        
        # 统计语言分布
        language_count = {}
        for proj in github_projects:
            lang = proj.get("language", "Unknown")
            if lang and lang != "Unknown":
                language_count[lang] = language_count.get(lang, 0) + 1
        
        top_languages = sorted(language_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 从GitHub项目描述提取关键词
        all_text = " ".join([
            p.get("description", "") + " " + p.get("name", "")
            for p in github_projects
        ])
        
        # 技术关键词
        tech_keywords = [
            "AI", "ML", "deep learning", "neural", "LLM", "GPT", "transformer",
            "Rust", "Go", "Python", "TypeScript", "JavaScript", "WebAssembly",
            "Kubernetes", "Docker", "cloud", "serverless", "edge",
            "blockchain", "crypto", "Web3", "DeFi",
            "React", "Vue", "Next.js", "Svelte", "Astro",
            "database", "vector", "embedding", "RAG",
            "API", "microservice", "gateway", "proxy"
        ]
        
        found_keywords = []
        for kw in tech_keywords:
            count = all_text.lower().count(kw.lower())
            if count > 0:
                found_keywords.append({"keyword": kw, "count": count})
        
        found_keywords.sort(key=lambda x: x["count"], reverse=True)
        
        # 生成趋势洞察
        insights = []
        
        if top_languages:
            insights.append(f"GitHub热门语言: {', '.join([l[0] for l in top_languages[:3]])}")
        
        if found_keywords:
            top_kw = [k["keyword"] for k in found_keywords[:5]]
            insights.append(f"热门技术关键词: {', '.join(top_kw)}")
        
        if github_projects:
            top_projects = [p["full_name"] for p in github_projects[:3]]
            insights.append(f"热门项目: {', '.join(top_projects)}")
        
        if hackernews_topics:
            hn_titles = [t["title"] for t in hackernews_topics[:3]]
            insights.append(f"HN讨论热点: {hn_titles[0]}")
        
        return {
            "top_languages": top_languages,
            "keywords": found_keywords[:10],
            "top_github_projects": github_projects[:5],
            "top_hackernews": hackernews_topics[:5],
            "insights": insights,
            "total_projects": len(github_projects),
            "total_hn_topics": len(hackernews_topics)
        }
    
    def generate_prompt_insight(self, trends: Dict) -> str:
        """生成Prompt洞察注入"""
        if not trends or not trends.get("insights"):
            return ""
        
        lines = ["### 🔭 跨项目技术趋势洞察"]
        lines.append("")
        
        for insight in trends["insights"][:4]:
            lines.append(f"- {insight}")
        
        # 添加热门项目详情
        if trends.get("top_github_projects"):
            lines.append("\n**热门开源项目:**")
            for proj in trends["top_github_projects"][:3]:
                desc = proj.get("description", "")[:100]
                lang = proj.get("language", "")
                stars = proj.get("today_stars", 0)
                info = f"  - [{proj['full_name']}]({proj['url']})"
                if lang:
                    info += f" [{lang}]"
                if stars:
                    info += f" +{stars} stars today"
                if desc:
                    info += f" - {desc}"
                lines.append(info)
        
        # 添加HN热点
        if trends.get("top_hackernews"):
            lines.append("\n**HackerNews热门讨论:**")
            for topic in trends["top_hackernews"][:2]:
                lines.append(f"  - {topic['title']} ({topic['score']} points)")
        
        lines.append("")
        return "\n".join(lines)
    
    def learn(self) -> Dict:
        """执行跨项目学习"""
        print("[跨项目学习] 开始从外部数据源学习...")
        
        all_trends = {
            "timestamp": datetime.now().isoformat(),
            "github_projects": [],
            "hackernews_topics": [],
            "analysis": {},
            "prompt_insight": ""
        }
        
        # GitHub Trending
        print("  [跨项目学习] 获取GitHub Trending...")
        cache = self._get_cache("github_trending")
        html = cache if cache else self._fetch(self.SOURCES["github_trending"]["url"])
        if html:
            if not cache:
                self._set_cache("github_trending", html)
            projects = self.extract_github_trending(html)
            all_trends["github_projects"] = projects
            print(f"  [跨项目学习] 发现{len(projects)}个热门项目")
        
        # HackerNews
        print("  [跨项目学习] 获取HackerNews...")
        cache = self._get_cache("hackernews")
        html = cache if cache else self._fetch(self.SOURCES["hackernews"]["url"])
        if html:
            if not cache:
                self._set_cache("hackernews", html)
            topics = self.extract_hackernews(html)
            all_trends["hackernews_topics"] = topics
            print(f"  [跨项目学习] 发现{len(topics)}个HN话题")
        
        # 分析
        analysis = self.analyze_tech_trends(
            all_trends["github_projects"],
            all_trends["hackernews_topics"]
        )
        all_trends["analysis"] = analysis
        
        # 生成Prompt洞察
        prompt_insight = self.generate_prompt_insight(analysis)
        all_trends["prompt_insight"] = prompt_insight
        
        # 保存趋势数据
        trends_file = f"{self.cache_dir}/latest_trends.json"
        try:
            with open(trends_file, 'w', encoding='utf-8') as f:
                json.dump(all_trends, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        
        print(f"[跨项目学习] 完成! 生成了{len(analysis.get('insights', []))}条趋势洞察")
        return all_trends
    
    def get_prompt_insight(self) -> str:
        """获取Prompt洞察（使用缓存）"""
        trends_file = f"{self.cache_dir}/latest_trends.json"
        if os.path.exists(trends_file):
            try:
                mtime = os.path.getmtime(trends_file)
                if time.time() - mtime < 7200:  # 2小时缓存
                    with open(trends_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    insight = data.get("prompt_insight", "")
                    if insight:
                        return insight
            except Exception:
                pass
        
        # 重新学习
        trends = self.learn()
        return trends.get("prompt_insight", "")


# 便捷函数
def learn_cross_project(trendradar_path: str = ".") -> str:
    """执行跨项目学习并返回Prompt洞察"""
    try:
        learner = CrossProjectLearner(trendradar_path)
        return learner.get_prompt_insight()
    except Exception as e:
        print(f"[跨项目学习] 错误: {e}")
        return ""


def get_tech_trends(trendradar_path: str = ".") -> Dict:
    """获取技术趋势分析"""
    try:
        learner = CrossProjectLearner(trendradar_path)
        trends = learner.learn()
        return trends.get("analysis", {})
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    learner = CrossProjectLearner()
    insight = learner.get_prompt_insight()
    print(insight)
