# -*- coding: utf-8 -*-
"""
Lv53: 自动配图生成器 - 为文章生成主题相关的 AI 封面图

核心理念：
1. 根据文章标题生成高质量的图片 prompt
2. 使用 Pollinations.ai（免费无限制）生成图片 URL
3. 更新 Astro 博客文章的 image 字段

图片生成服务：
- Pollinations.ai: 完全免费，无需 API Key
- URL: https://image.pollinations.ai/prompt/{prompt}?width=1600&height=900&nologo=true

工作流程：
1. 通过 GitHub API 获取 Astro 仓库中文章的 frontmatter
2. 识别使用默认/随机图片的文章
3. 为每篇文章生成主题相关的图片 prompt
4. 构建 Pollinations.ai URL
5. 通过 GitHub API 更新文章的 image 字段
"""

import base64
import json
import os
import re
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional

import requests


class AutoImageGenerator:
    """自动配图生成器"""

    POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
    DEFAULT_PARAMS = "?width=1600&height=900&nologo=true&seed={seed}"

    # 图片风格模板
    STYLE_TEMPLATES = {
        "tech": "futuristic tech illustration, digital art, clean modern design, blue and purple gradient, high quality, 4k",
        "business": "professional business illustration, modern corporate style, clean lines, warm lighting, high quality",
        "science": "scientific illustration, clean diagram style, educational, bright colors, high detail",
        "news": "modern news editorial illustration, bold colors, graphic design style, professional",
        "default": "modern digital illustration, clean design, professional, high quality, 4k",
    }

    def __init__(self, github_token: str = "", astro_owner: str = "garcci", astro_repo: str = "Astro"):
        self.github_token = github_token
        self.astro_owner = astro_owner
        self.astro_repo = astro_repo
        self.headers = {}
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
        self.headers["Accept"] = "application/vnd.github.v3+json"

    def _github_api(self, path: str, method: str = "GET", data: dict = None) -> dict:
        """调用 GitHub API"""
        url = f"https://api.github.com/repos/{self.astro_owner}/{self.astro_repo}/{path}"
        try:
            if method == "GET":
                resp = requests.get(url, headers=self.headers, timeout=30)
            elif method == "PUT":
                resp = requests.put(url, headers=self.headers, json=data, timeout=30)
            else:
                resp = requests.request(method, url, headers=self.headers, json=data, timeout=30)

            if resp.status_code in (200, 201):
                return resp.json()
            else:
                print(f"[GitHub API] {method} {path} -> {resp.status_code}: {resp.text[:200]}")
                return {}
        except Exception as e:
            print(f"[GitHub API] Error: {e}")
            return {}

    def list_news_articles(self) -> List[Dict]:
        """获取 news 目录下的文章列表"""
        result = self._github_api("contents/src/content/posts/news")
        if not result:
            return []

        articles = []
        for item in result:
            if item.get("type") == "file" and item.get("name", "").endswith(".md"):
                articles.append(
                    {
                        "name": item["name"],
                        "path": item["path"],
                        "sha": item["sha"],
                    }
                )
        return articles

    def get_article_content(self, path: str) -> str:
        """获取文章完整内容"""
        result = self._github_api(f"contents/{path}")
        if not result or "content" not in result:
            return ""

        try:
            content = base64.b64decode(result["content"]).decode("utf-8")
            return content
        except Exception:
            return ""

    def extract_frontmatter(self, content: str) -> Dict:
        """提取 frontmatter"""
        if not content.lstrip().startswith("---"):
            return {}

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}

        fm_text = parts[1].strip()
        fm = {}
        for line in fm_text.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("-"):
                key, value = line.split(":", 1)
                fm[key.strip()] = value.strip().strip('"').strip("'")
            elif line.startswith("tags:"):
                fm["tags"] = []
            elif line.startswith("- ") and "tags" in fm:
                fm["tags"].append(line[2:].strip().strip('"').strip("'"))

        return fm

    def generate_image_prompt(self, title: str, content: str = "", tags: List[str] = None) -> str:
        """根据文章标题生成图片 prompt"""
        tags = tags or []

        # 清理标题
        clean_title = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', title)
        clean_title = clean_title[:80]  # 限制长度

        # 检测风格
        style = "default"
        if any(w in title for w in ["芯片", "GPU", "AI", "算法", "模型", "计算", "数据"]):
            style = "tech"
        elif any(w in title for w in ["财报", "市场", "投资", "并购", "融资", "行业"]):
            style = "business"
        elif any(w in title for w in ["科学", "研究", "发现", "实验", "物理", "化学"]):
            style = "science"
        elif any(w in title for w in ["新闻", "热点", "事件", "突发"]):
            style = "news"

        style_desc = self.STYLE_TEMPLATES.get(style, self.STYLE_TEMPLATES["default"])

        # 构建 prompt
        # 将中文标题翻译成英文概念（简化处理）
        prompt = f"{clean_title}, {style_desc}"
        return prompt[:300]  # 限制长度

    def build_image_url(self, prompt: str, seed: int = None) -> str:
        """构建 Pollinations.ai 图片 URL"""
        seed = seed or hash(prompt) % 10000
        encoded_prompt = urllib.parse.quote(prompt)
        params = self.DEFAULT_PARAMS.format(seed=seed)
        return f"{self.POLLINATIONS_URL.format(prompt=encoded_prompt)}{params}"

    def needs_new_image(self, image_url: str, title: str) -> bool:
        """判断文章是否需要新图片"""
        if not image_url:
            return True
        # 如果是 picsum.photos 的随机图片，需要替换
        if "picsum.photos" in image_url:
            return True
        # 如果已经是 Pollinations.ai 的图片，不需要替换
        if "pollinations.ai" in image_url:
            return False
        return False

    def update_article_image(self, path: str, sha: str, content: str, new_image_url: str) -> bool:
        """通过 GitHub API 更新文章的 image 字段"""
        # 替换 frontmatter 中的 image 字段
        old_fm = self.extract_frontmatter(content)
        old_image = old_fm.get("image", "")

        if not old_image:
            # 在 frontmatter 中插入 image 字段
            lines = content.split("\n")
            new_lines = []
            in_frontmatter = False
            frontmatter_end = 0

            for i, line in enumerate(lines):
                if line.strip() == "---":
                    if not in_frontmatter:
                        in_frontmatter = True
                    else:
                        frontmatter_end = i
                        break

            if frontmatter_end > 0:
                # 在 frontmatter 结束前插入 image 字段
                lines.insert(frontmatter_end, f'image: "{new_image_url}"')
                new_content = "\n".join(lines)
            else:
                return False
        else:
            # 替换现有的 image 字段
            new_content = content.replace(f"image: {old_image}", f'image: "{new_image_url}"')
            if new_content == content:
                new_content = content.replace(f'image: "{old_image}"', f'image: "{new_image_url}"')

        if new_content == content:
            print(f"[Lv53] 无法替换图片: {path}")
            return False

        # 提交到 GitHub
        commit_msg = f"🎨 Lv53: 为文章生成 AI 配图 - {path.split('/')[-1]}"
        result = self._github_api(
            f"contents/{path}",
            "PUT",
            {
                "message": commit_msg,
                "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
                "sha": sha,
            },
        )

        return "commit" in result

    def process_articles(self, max_articles: int = 3) -> List[str]:
        """处理文章，为需要配图的生成新图片"""
        if not self.github_token:
            print("[Lv53] 跳过: 未配置 GitHub Token")
            return []

        articles = self.list_news_articles()
        if not articles:
            print("[Lv53] 未找到文章")
            return []

        updated = []
        processed = 0

        for article in articles:
            if processed >= max_articles:
                break

            content = self.get_article_content(article["path"])
            if not content:
                continue

            fm = self.extract_frontmatter(content)
            title = fm.get("title", "")
            image = fm.get("image", "")
            tags = fm.get("tags", [])

            if not self.needs_new_image(image, title):
                continue

            # 生成新图片
            prompt = self.generate_image_prompt(title, content, tags)
            new_url = self.build_image_url(prompt, seed=hash(title) % 10000)

            print(f"[Lv53] 生成配图: {title[:40]}...")
            print(f"[Lv53]   Prompt: {prompt[:80]}...")
            print(f"[Lv53]   URL: {new_url[:80]}...")

            # 更新文章
            if self.update_article_image(article["path"], article["sha"], content, new_url):
                updated.append(article["name"])
                print(f"[Lv53]   ✓ 已更新")
            else:
                print(f"[Lv53]   ✗ 更新失败")

            processed += 1

        return updated


def run_auto_image_generation(
    github_token: str = "", astro_owner: str = "garcci", astro_repo: str = "Astro", max_articles: int = 3
):
    """运行自动配图生成"""
    print("=" * 60)
    print("🎨 Lv53 自动配图生成器")
    print("=" * 60)

    generator = AutoImageGenerator(github_token, astro_owner, astro_repo)
    updated = generator.process_articles(max_articles)

    print("\n📊 Lv53 生成摘要:")
    print(f"  更新文章数: {len(updated)}")
    for name in updated:
        print(f"  ✓ {name}")

    print("=" * 60)
    return updated


if __name__ == "__main__":
    token = os.environ.get("GH_MEMORY_TOKEN", "")
    run_auto_image_generation(token)
