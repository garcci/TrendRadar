# -*- coding: utf-8 -*-
"""
智能摘要系统 - 自动生成文章TL;DR和核心摘要

核心理念：
1. 读者时间宝贵，需要快速了解文章核心
2. 摘要应该自动提取，不依赖AI API（零成本）
3. 摘要应该放在文章顶部，方便快速浏览

提取策略：
- 从文章结构中提取关键信息
- 识别Admonition引用块（这些通常是核心观点）
- 提取表格标题和数据
- 识别加粗的关键句
- 提取趋势列表

输出格式：
- TL;DR: 一句话概括
- 核心观点: 3-5个要点
- 关键词: 5-8个关键词
- 阅读时间: 预估
"""

import re
from typing import Dict, List, Optional, Tuple


class SmartSummary:
    """智能摘要生成器"""
    
    def __init__(self):
        pass
    
    def extract_tldr(self, content: str) -> str:
        """提取TL;DR（一句话概括）"""
        # 优先从description字段提取
        desc_match = re.search(r'description:\s*"([^"]+)"', content)
        if desc_match:
            return desc_match.group(1)
        
        # 从开篇引言提取第一句话（通常是总结）
        # 移除frontmatter
        if content.lstrip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]
        
        # 找开篇段落（非标题、非空行）
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            # 跳过markdown标记、标题、空行
            if line and not line.startswith("#") and not line.startswith("-") and not line.startswith("*") and not line.startswith("|"):
                # 取前100字作为TL;DR
                if len(line) > 20:
                    return line[:100] + ("..." if len(line) > 100 else "")
        
        return "今日热点速览"
    
    def extract_key_insights(self, content: str) -> List[str]:
        """提取核心观点（从Admonition和加粗文本）"""
        insights = []
        
        # 1. 提取Admonition内容（:::note, :::tip等）
        admonition_pattern = r':::(?:note|tip|warning)\[[^\]]*\]\s*\n([^:]+?)(?=\n:::)'
        admonitions = re.findall(admonition_pattern, content, re.DOTALL)
        for ad in admonitions[:3]:
            text = ad.strip().replace("\n", " ")
            if len(text) > 10:
                insights.append(text[:150])
        
        # 2. 提取加粗的关键句（通常是核心观点）
        bold_pattern = r'\*\*([^*]{10,80})\*\*'
        bold_items = re.findall(bold_pattern, content)
        for item in bold_items[:5]:
            # 过滤掉常见的非观点加粗
            if not any(skip in item for skip in ['平台', '日期', '标题', '作者', '来源']):
                insights.append(item[:150])
        
        # 3. 提取趋势列表项（以数字开头的要点）
        trend_pattern = r'^\d+\.\s+(.{20,100})$'
        lines = content.split("\n")
        for line in lines:
            match = re.match(trend_pattern, line.strip())
            if match:
                insights.append(match.group(1)[:150])
        
        # 去重并限制数量
        unique = []
        seen = set()
        for insight in insights:
            key = insight[:30]
            if key not in seen and len(insight) > 15:
                seen.add(key)
                unique.append(insight)
                if len(unique) >= 5:
                    break
        
        return unique
    
    def extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 从tags提取
        tags_match = re.search(r'tags:\s*\[([^\]]+)\]', content)
        if tags_match:
            tags_str = tags_match.group(1)
            tags = [t.strip().strip('"').strip("'") for t in tags_str.split(",")]
            return tags[:8]
        
        # 从内容提取高频技术词
        tech_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', content)
        word_freq = {}
        for word in tech_words:
            if len(word) >= 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 过滤常见词，取高频词
        stop_words = {'今日', '热点', '分析', '深度', '平台', '趋势', '文章', '内容', '新闻', '报告'}
        keywords = [w for w, c in sorted(word_freq.items(), key=lambda x: -x[1]) 
                   if w not in stop_words][:8]
        
        return keywords
    
    def estimate_reading_time(self, content: str) -> int:
        """估算阅读时间（分钟）"""
        # 移除frontmatter和markdown标记
        clean = re.sub(r'---.*?---', '', content, flags=re.DOTALL)
        clean = re.sub(r'!\[.*?\]\(.*?\)', '', clean)
        clean = re.sub(r'\[.*?\]\(.*?\)', '', clean)
        clean = re.sub(r'[#*`>|:-]', '', clean)
        
        # 中文字数 ≈ 阅读分钟数 / 300 * 60 ≈ 字数 / 300
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', clean))
        return max(1, round(chinese_chars / 300))
    
    def generate_summary_block(self, content: str) -> str:
        """
        生成完整的摘要块
        
        返回: Markdown格式的摘要块，可插入文章开头
        """
        tldr = self.extract_tldr(content)
        insights = self.extract_key_insights(content)
        keywords = self.extract_keywords(content)
        reading_time = self.estimate_reading_time(content)
        
        lines = [
            "",
            ":::tip[📋 快速阅读]",
            f"**一句话总结**: {tldr}",
            "",
            f"**阅读时间**: ⏱️ {reading_time} 分钟",
            "",
        ]
        
        if insights:
            lines.append("**核心观点**:")
            for i, insight in enumerate(insights[:5], 1):
                lines.append(f"{i}. {insight}")
            lines.append("")
        
        if keywords:
            lines.append(f"**关键词**: {', '.join(keywords)}")
            lines.append("")
        
        lines.append(":::")
        lines.append("")
        
        return "\n".join(lines)
    
    def inject_summary(self, content: str) -> str:
        """
        将摘要注入到文章开头（Frontmatter之后）
        
        返回: 注入摘要后的完整文章内容
        """
        summary_block = self.generate_summary_block(content)
        
        # 找到frontmatter结束位置
        if content.lstrip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = "---" + parts[1] + "---"
                body = parts[2]
                return frontmatter + "\n" + summary_block + body
        
        # 如果没有frontmatter，直接插入开头
        return summary_block + "\n" + content


# 便捷函数
def add_smart_summary(content: str) -> str:
    """为文章添加智能摘要"""
    summarizer = SmartSummary()
    return summarizer.inject_summary(content)


def get_article_summary(content: str) -> Dict:
    """获取文章摘要信息"""
    summarizer = SmartSummary()
    return {
        "tldr": summarizer.extract_tldr(content),
        "insights": summarizer.extract_key_insights(content),
        "keywords": summarizer.extract_keywords(content),
        "reading_time": summarizer.estimate_reading_time(content)
    }


if __name__ == "__main__":
    # 测试
    test_content = """---
title: "AI芯片革命：英伟达的挑战者们"
published: 2024-01-15T08:00:00+08:00
tags: [科技, AI芯片, 半导体, 英伟达]
description: "英伟达面临来自AMD、Intel和众多初创公司的激烈竞争"
---

今天，AI芯片市场发生了重大变化。

:::note[💡 关键洞察]
英伟达的市场份额从95%下降到85%，这是一个历史性的转折点。
:::

**AMD的MI300X正在快速抢占市场**，其性能在某些场景下已经超越H100。

## 市场格局变化

1. AMD MI300X在推理场景下性能领先
2. Intel Gaudi 3开始获得云厂商订单
3. 中国厂商寒武纪、海光信息加速追赶

**未来趋势**: 预计未来6个月，AI芯片市场将呈现三足鼎立的格局。
"""
    
    summarizer = SmartSummary()
    summary = get_article_summary(test_content)
    print(f"TL;DR: {summary['tldr']}")
    print(f"阅读时间: {summary['reading_time']}分钟")
    print(f"核心观点: {len(summary['insights'])}条")
    for i, insight in enumerate(summary['insights'], 1):
        print(f"  {i}. {insight[:50]}...")
    print(f"关键词: {', '.join(summary['keywords'])}")
