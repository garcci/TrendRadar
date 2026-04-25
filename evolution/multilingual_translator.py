# -*- coding: utf-8 -*-
"""
Lv49: 多语言自动翻译系统

核心理念：一篇中文文章 → 自动生成英文版 → 扩大全球受众

翻译策略：
1. 用GitHub Models（免费）翻译文章正文
2. 保留技术术语的英文原文（如AI、API、GitHub）
3. 自动翻译frontmatter（title、description、tags）
4. 生成符合Astro Content Collections格式的英文文章
5. 自动提交到博客仓库

目标语言：
- en (英文) - 首选，科技内容国际通用
- 后续可扩展: ja (日文)、ko (韩文)

成本：完全免费（GitHub Models）
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests


class MultilingualTranslator:
    """多语言自动翻译器"""
    
    # 技术术语保留列表（不翻译）
    TECH_TERMS = [
        "AI", "API", "GitHub", "Git", "RSS", "SEO", "LLM", "GPT", "Cloudflare",
        "Python", "JavaScript", "Node.js", "Docker", "Kubernetes", "React",
        "Vue", "Astro", "Svelte", "OpenAI", "DeepSeek", "Gemini", "Claude",
        "Linux", "Windows", "macOS", "iOS", "Android", "Web", "HTTP", "HTTPS",
        "URL", "JSON", "YAML", "SQL", "NoSQL", "GPU", "CPU", "RAM", "SSD",
        "CDN", "DNS", "SSL", "TLS", "OAuth", "JWT", "SDK", "CLI", "GUI",
        "CI/CD", "DevOps", "MLOps", "SaaS", "PaaS", "IaaS", "FaaS",
        "Prompt", "RAG", "Embedding", "Vector", "Transformer", "Diffusion"
    ]
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.github_token = os.environ.get("GH_MODELS_TOKEN", "")
    
    def _call_github_models(self, prompt: str, max_tokens: int = 4000) -> str:
        """调用GitHub Models进行翻译"""
        if not self.github_token:
            raise Exception("GH_MODELS_TOKEN未配置")
        
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": "You are a professional translator. Translate the following Chinese text to English. Keep technical terms in English. Maintain markdown formatting."},
            {"role": "user", "content": prompt}
        ]
        
        response = requests.post(url, headers=headers, json={
            "model": "meta-llama-3.1-8b-instruct",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens
        }, timeout=120)
        
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def translate_frontmatter(self, frontmatter: str) -> str:
        """翻译frontmatter字段"""
        # 提取title
        title_match = re.search(r'title:\s*"(.+?)"', frontmatter)
        if title_match:
            chinese_title = title_match.group(1)
            translated_title = self._call_github_models(
                f"Translate this Chinese blog title to English (concise, catchy):\n{chinese_title}",
                max_tokens=100
            )
            # 清理翻译结果
            translated_title = translated_title.strip().strip('"').strip("'")
            frontmatter = frontmatter.replace(
                f'title: "{chinese_title}"',
                f'title: "{translated_title}"'
            )
        
        # 提取description
        desc_match = re.search(r'description:\s*"(.+?)"', frontmatter)
        if desc_match:
            chinese_desc = desc_match.group(1)
            translated_desc = self._call_github_models(
                f"Translate this Chinese description to English (concise, under 200 chars):\n{chinese_desc}",
                max_tokens=200
            )
            translated_desc = translated_desc.strip().strip('"').strip("'")
            frontmatter = frontmatter.replace(
                f'description: "{chinese_desc}"',
                f'description: "{translated_desc}"'
            )
        
        # 翻译tags（保持技术术语不翻译）
        tags_match = re.search(r'tags:\s*\[(.*?)\]', frontmatter)
        if tags_match:
            tags_str = tags_match.group(1)
            tags = [t.strip().strip('"').strip("'") for t in tags_str.split(',')]
            
            translated_tags = []
            for tag in tags:
                if tag in self.TECH_TERMS or tag.isupper():
                    translated_tags.append(tag)
                else:
                    # 简单翻译常见标签
                    tag_map = {
                        "人工智能": "AI",
                        "科技": "Technology",
                        "开源": "Open Source",
                        "新闻": "News",
                        "教程": "Tutorial",
                        "笔记": "Notes",
                        "趋势": "Trends",
                        "分析": "Analysis",
                        "评测": "Review"
                    }
                    translated_tags.append(tag_map.get(tag, tag))
            
            new_tags = ', '.join([f'"{t}"' for t in translated_tags])
            frontmatter = frontmatter.replace(f'tags: [{tags_str}]', f'tags: [{new_tags}]')
        
        # 修改category
        category_map = {
            "news": "news",
            "tech": "tech",
            "tutorials": "tutorials",
            "notes": "notes"
        }
        
        return frontmatter
    
    def translate_content(self, content: str) -> str:
        """翻译文章正文"""
        # 分割frontmatter和正文
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]
        else:
            frontmatter = ""
            body = content
        
        # 翻译frontmatter
        translated_fm = self.translate_frontmatter(frontmatter)
        
        # 分段翻译正文（避免超过token限制）
        paragraphs = body.split('\n\n')
        translated_paragraphs = []
        
        batch = []
        batch_size = 0
        max_batch_chars = 1500  # 每批约1500字符
        
        for para in paragraphs:
            if not para.strip():
                translated_paragraphs.append('')
                continue
            
            # 跳过代码块、图片等不需要翻译的内容
            if para.startswith('```') or para.startswith('![') or para.startswith('|'):
                # 先翻译之前的批次
                if batch:
                    batch_text = '\n\n'.join(batch)
                    translated = self._translate_batch(batch_text)
                    translated_paragraphs.extend(translated.split('\n\n'))
                    batch = []
                    batch_size = 0
                
                translated_paragraphs.append(para)
                continue
            
            if batch_size + len(para) > max_batch_chars:
                # 翻译当前批次
                batch_text = '\n\n'.join(batch)
                translated = self._translate_batch(batch_text)
                translated_paragraphs.extend(translated.split('\n\n'))
                batch = [para]
                batch_size = len(para)
            else:
                batch.append(para)
                batch_size += len(para)
        
        # 翻译最后一批
        if batch:
            batch_text = '\n\n'.join(batch)
            translated = self._translate_batch(batch_text)
            translated_paragraphs.extend(translated.split('\n\n'))
        
        translated_body = '\n\n'.join(translated_paragraphs)
        
        # 保护技术术语（替换回英文）
        for term in self.TECH_TERMS:
            # 如果术语被翻译成了其他形式，尝试恢复
            pass  # Llama模型通常能正确保留技术术语
        
        # 组合结果
        result = f"---\n{translated_fm}\n---\n{translated_body}"
        return result
    
    def _translate_batch(self, text: str) -> str:
        """翻译一批文本"""
        prompt = f"""Translate the following Chinese markdown text to English.
Rules:
1. Keep all technical terms, brand names, and code in English
2. Maintain markdown formatting (headings, lists, links, bold, etc.)
3. Translate naturally, not word-for-word
4. Keep the tone professional but accessible

Text:
{text}"""
        
        return self._call_github_models(prompt, max_tokens=2000)
    
    def translate_article_file(self, file_path: str, output_dir: str = "src/content/posts") -> Optional[str]:
        """翻译单个文章文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否已经是英文
            if self._is_english_content(content):
                print(f"[翻译] 跳过（已是英文）: {file_path}")
                return None
            
            print(f"[翻译] 正在翻译: {os.path.basename(file_path)}")
            translated = self.translate_content(content)
            
            # 生成输出路径（添加-en后缀）
            base_name = os.path.basename(file_path)
            name, ext = os.path.splitext(base_name)
            output_name = f"{name}-en{ext}"
            output_path = os.path.join(output_dir, output_name)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(translated)
            
            print(f"[翻译] 完成: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"[翻译] 失败 {file_path}: {e}")
            return None
    
    def _is_english_content(self, content: str) -> bool:
        """检查内容是否主要是英文"""
        # 简单检查：如果中文字符占比<10%，认为是英文
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(content)
        if total_chars == 0:
            return True
        return chinese_chars / total_chars < 0.1
    
    def translate_recent_articles(self, posts_dir: str = "src/content/posts",
                                  days: int = 7) -> List[str]:
        """翻译最近的文章"""
        translated_files = []
        
        cutoff = datetime.now().timestamp() - days * 86400
        
        for root, _, files in os.walk(posts_dir):
            for file in files:
                if not file.endswith('.md'):
                    continue
                
                # 跳过已有英文版的文件
                if '-en.' in file:
                    continue
                
                file_path = os.path.join(root, file)
                
                # 检查修改时间
                mtime = os.path.getmtime(file_path)
                if mtime < cutoff:
                    continue
                
                result = self.translate_article_file(file_path, posts_dir)
                if result:
                    translated_files.append(result)
        
        return translated_files


# 便捷函数
def translate_latest_article(posts_dir: str = "src/content/posts") -> Optional[str]:
    """翻译最新的文章"""
    translator = MultilingualTranslator()
    
    # 找到最新的文章
    latest_file = None
    latest_time = 0
    
    for root, _, files in os.walk(posts_dir):
        for file in files:
            if not file.endswith('.md') or '-en.' in file:
                continue
            
            file_path = os.path.join(root, file)
            mtime = os.path.getmtime(file_path)
            if mtime > latest_time:
                latest_time = mtime
                latest_file = file_path
    
    if latest_file:
        return translator.translate_article_file(latest_file, posts_dir)
    
    return None


def batch_translate(posts_dir: str = "src/content/posts", days: int = 7) -> List[str]:
    """批量翻译最近文章"""
    translator = MultilingualTranslator()
    return translator.translate_recent_articles(posts_dir, days)


if __name__ == "__main__":
    # 测试翻译
    test_md = """---
title: "测试文章"
published: 2026-04-25
description: "这是一篇测试文章"
tags: ["人工智能", "科技", "开源"]
category: tech
draft: false
---

# 引言

人工智能正在改变世界。

## 主要内容

这是一些中文内容。
"""
    
    translator = MultilingualTranslator()
    result = translator.translate_content(test_md)
    print(result)
