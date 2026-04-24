# -*- coding: utf-8 -*-
"""
Lv43: 智能内容分发

为每篇文章自动生成多种格式的分发内容：
1. Twitter/X 推文（280字符限制）
2. 文章摘要卡片（用于社交媒体分享）
3. SEO 描述和关键词
4. 微信分享文案
5. Reddit/HN 帖子标题

零API成本 - 纯本地文本处理
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional


class ContentDistributor:
    """智能内容分发器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.cache_dir = f"{trendradar_path}/evolution/distribute_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def generate_twitter_post(self, title: str, summary: str, tags: List[str]) -> str:
        """生成Twitter/X推文"""
        # 提取核心观点
        sentences = re.split(r'[。！？\n]', summary)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        if sentences:
            key_point = sentences[0][:100]
        else:
            key_point = summary[:100] if summary else title[:100]
        
        # 选择最相关的标签
        hashtags = []
        for tag in tags[:3]:
            # 转换为英文风格hashtag
            hashtag = re.sub(r'[^\w]', '', tag)
            if len(hashtag) >= 2:
                hashtags.append(f"#{hashtag}")
        
        # 如果没有标签，使用通用标签
        if not hashtags:
            hashtags = ["#TechTrends", "#AI"]
        
        # 构建推文
        lines = []
        lines.append(f"🚀 {title[:80]}")
        lines.append("")
        lines.append(key_point)
        if len(key_point) < 80 and len(sentences) > 1:
            lines.append(sentences[1][:80])
        lines.append("")
        lines.append(" ".join(hashtags))
        
        tweet = "\n".join(lines)
        
        # 确保不超过280字符
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        
        return tweet
    
    def generate_seo_meta(self, title: str, summary: str, tags: List[str]) -> Dict:
        """生成SEO元数据"""
        # 描述：从摘要中提取，150-160字符
        desc = summary[:160] if summary else title
        if len(desc) < 50:
            desc = f"{title} - {desc}"
        desc = desc[:160]
        
        # 关键词
        keywords = ", ".join(tags[:8]) if tags else "科技, AI, 技术趋势"
        
        # 生成slug
        slug = re.sub(r'[^\w\s-]', '', title)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.lower()[:60]
        
        return {
            "title": title[:60],
            "description": desc,
            "keywords": keywords,
            "slug": slug,
            "og_title": title,
            "og_description": desc,
            "og_type": "article"
        }
    
    def generate_wechat_share(self, title: str, summary: str, tags: List[str]) -> str:
        """生成微信分享文案"""
        lines = []
        lines.append(f"📢 {title}")
        lines.append("")
        
        # 核心内容
        sentences = re.split(r'[。！？\n]', summary)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        for sentence in sentences[:3]:
            if len(sentence) > 15:
                lines.append(f"▸ {sentence}")
        
        # 标签
        if tags:
            lines.append("")
            tag_str = " ".join([f"#{tag}" for tag in tags[:5]])
            lines.append(f"🏷 {tag_str}")
        
        lines.append("")
        lines.append("👉 阅读全文了解更多")
        
        return "\n".join(lines)
    
    def generate_reddit_title(self, title: str, summary: str) -> str:
        """生成Reddit/HN风格标题"""
        # 尝试提取最有吸引力的角度
        sentences = re.split(r'[。！？\n]', summary)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        patterns = [
            (r'(\w+)\s*(?:发布|推出|开源|上线)\s*(了)?\s*(.+)', "{0} launches {2}"),
            (r'(.+)\s*(?:获得|拿到|融资)\s*(.+)', "{0} raises {1}"),
            (r'(.+)\s*(?:超越|超过|击败)\s*(.+)', "{0} surpasses {1}"),
            (r'(.+)\s*(?:更新|升级|改版)\s*(.+)', "{0} updates {1}"),
        ]
        
        for sentence in sentences[:2]:
            for pattern, template in patterns:
                match = re.search(pattern, sentence)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        try:
                            return template.format(*groups)
                        except Exception:
                            pass
        
        # 默认转换
        clean_title = re.sub(r'[【】\[\]「」]', '', title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # 添加前缀增强吸引力
        prefixes = ["Show HN: ", "Ask HN: ", ""]
        for prefix in prefixes:
            candidate = prefix + clean_title
            if len(candidate) <= 100:
                return candidate
        
        return clean_title[:100]
    
    def generate_distribution_package(self, title: str, summary: str, tags: List[str], 
                                     article_url: str = "") -> Dict:
        """生成分发内容包"""
        
        package = {
            "article_title": title,
            "generated_at": datetime.now().isoformat(),
            "platforms": {}
        }
        
        # Twitter/X
        package["platforms"]["twitter"] = {
            "content": self.generate_twitter_post(title, summary, tags),
            "max_chars": 280,
            "has_media": False
        }
        
        # SEO
        package["platforms"]["seo"] = self.generate_seo_meta(title, summary, tags)
        
        # 微信
        package["platforms"]["wechat"] = {
            "content": self.generate_wechat_share(title, summary, tags),
            "format": "text"
        }
        
        # Reddit/HN
        package["platforms"]["reddit"] = {
            "title": self.generate_reddit_title(title, summary),
            "subreddit_suggestions": ["technology", "MachineLearning", "webdev", "programming"]
        }
        
        # 通用分享文案
        package["platforms"]["generic"] = {
            "short_desc": summary[:200] if summary else title,
            "call_to_action": f"阅读完整分析: {article_url}" if article_url else "阅读完整分析"
        }
        
        return package
    
    def save_distribution(self, article_id: str, package: Dict):
        """保存分发内容"""
        filepath = f"{self.cache_dir}/{article_id}_distribute.json"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(package, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def load_distribution(self, article_id: str) -> Optional[Dict]:
        """加载分发内容"""
        filepath = f"{self.cache_dir}/{article_id}_distribute.json"
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None


# 便捷函数
def generate_share_package(title: str, summary: str, tags: List[str],
                           article_url: str = "", trendradar_path: str = ".") -> Dict:
    """生成文章分发内容包"""
    try:
        distributor = ContentDistributor(trendradar_path)
        return distributor.generate_distribution_package(title, summary, tags, article_url)
    except Exception as e:
        print(f"[内容分发] 错误: {e}")
        return {}


def format_for_platform(platform: str, title: str, summary: str, tags: List[str]) -> str:
    """为指定平台格式化内容"""
    try:
        distributor = ContentDistributor()
        
        if platform == "twitter":
            return distributor.generate_twitter_post(title, summary, tags)
        elif platform == "wechat":
            return distributor.generate_wechat_share(title, summary, tags)
        elif platform == "reddit":
            return distributor.generate_reddit_title(title, summary)
        else:
            return summary[:200]
    except Exception:
        return summary[:200]


if __name__ == "__main__":
    # 测试
    title = "OpenAI发布GPT-5：多模态推理能力大幅提升"
    summary = "OpenAI最新发布的GPT-5模型在数学推理、代码生成和多模态理解方面实现了突破性进展。新模型在多项基准测试中超越了人类专家水平。"
    tags = ["AI", "OpenAI", "GPT", "大模型"]
    
    package = generate_share_package(title, summary, tags)
    print(json.dumps(package, ensure_ascii=False, indent=2))
