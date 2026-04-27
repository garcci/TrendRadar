# -*- coding: utf-8 -*-
"""
标题优化系统 - 自动生成和选择最佳标题

核心理念：
1. 标题是文章的门面，决定点击率
2. 基于历史数据学习哪些标题特征更有效
3. 自动生成多个候选标题，选择最优

评估维度：
- 标题长度：20-30字最佳
- 悬念感：是否引发好奇心
- 信息密度：是否包含关键信息
- 情感倾向：适度情感化提升点击
- 数字使用：带数字的标题更吸引人
- 疑问句式：疑问句引发思考

优化策略：
- 生成3个候选标题
- 基于评分模型选择最佳标题
- 将最佳标题注入到Frontmatter
"""

import json
import os
import random
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class TitleOptimizer:
    """标题优化器"""
    
    # 高点击率标题模板
    TITLE_TEMPLATES = {
        "insight": [
            "{topic}背后：{insight}",
            "为什么{topic}？深度解析",
            "{topic}的真相：{detail}",
            "从{topic}看{perspective}"
        ],
        "data_driven": [
            "{number}个数据揭示{topic}",
            "{topic}：{percentage}%的人不知道",
            "{topic}，{metric}提升{percentage}%",
            "{number}分钟了解{topic}"
        ],
        "question": [
            "{topic}会改变什么？",
            "为什么{topic}引发热议？",
            "{topic}：机会还是陷阱？",
            "{topic}，你看懂了吗？"
        ],
        "trend": [
            "{topic}：{trend}正在发生",
            "{topic}的{year}年：{change}",
            "从{topic}看{trend}",
            "{topic}新趋势：{detail}"
        ],
        "contrast": [
            "{topic}：{group1} vs {group2}",
            "{topic}的两面：{aspect1}与{aspect2}",
            "{topic}：{old}到{new}",
            "{topic}：理想与现实"
        ]
    }
    
    # 标题评分权重
    SCORE_WEIGHTS = {
        "length": 0.15,      # 长度适中
        "has_number": 0.15,  # 包含数字
        "has_question": 0.15, # 疑问句式
        "has_contrast": 0.15, # 对比结构
        "has_insight": 0.15,  # 有洞察词
        "emotional_balance": 0.15,  # 情感平衡
        "uniqueness": 0.10   # 独特性
    }

    # 垃圾标题模式：这些模式表示标题质量极低
    GARBAGE_PATTERNS = [
        # "AI，4背后的秘密" — 主话题+无意义短数字+固定模板
        r'^.+，\d{1,3}(?!%|倍|万|亿|折|折起|个点|分钟?)背后的秘密$',
        # "AI，V4背后的秘密" — 版本号+固定模板
        r'^.+，V?\d+(?:\.\d+)?背后的秘密$',
        # 纯数字开头或结尾的无意义标题
        r'^\d+[^\u4e00-\u9fa5]{0,2}$',
    ]

    # 有意义的数字单位：数字必须搭配这些单位才有业务含义
    MEANINGFUL_NUMBER_UNITS = ['%', '倍', '万', '亿', '折', '折起', '个点', '分钟', '小时', '天', '年', '款', '项', '家', '人']
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
    
    def extract_topics_from_content(self, content: str) -> List[str]:
        """从内容中提取关键话题"""
        topics = []
        
        # 移除frontmatter
        if content.lstrip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]
        
        # 1. 优先从科技关键词库匹配（长的、具体的词优先）
        tech_keywords = [
            # 具体产品/公司（优先，更具体）
            "DeepSeek", "OpenAI", "ChatGPT", "GPT-4", "GPT-4o", "Claude",
            "NVIDIA", "英伟达", "AMD", "Intel", "华为", "特斯拉", "苹果",
            "小米", "三星", "台积电", "Google", "微软", "字节跳动", "阿里",
            # 技术领域
            "大模型", "人工智能", "AI", "芯片", "GPU", "半导体", "开源",
            "云计算", "量子计算", "自动驾驶", "机器人", "脑机接口", "物联网",
            "5G", "6G", "新能源", "电动车", "元宇宙", "VR", "AR", "区块链",
            # 热点概念
            "降价", "价格战", "算力", "推理", "训练", "API", "Token",
        ]
        # 按长度降序排列，优先匹配更具体的词
        tech_keywords.sort(key=len, reverse=True)
        for kw in tech_keywords:
            if kw in content and kw not in topics:
                topics.append(kw)
        
        # 2. 从加粗文本提取（过滤掉常见非话题词）
        bold_texts = re.findall(r'\*\*([^*]{2,20})\*\*', content)
        skip_words = {'今日', '热点', '分析', '深度', '平台', '趋势', '文章', '内容',
                     '新闻', '报告', '总结', '概述', '引言', '结语', '建议',
                     '注意', '重要', '必须', '不要', '可以', '需要'}
        for text in bold_texts:
            if text not in skip_words and len(text) >= 2 and text not in topics:
                topics.append(text)
        
        # 3. 从标题提取
        headings = re.findall(r'^#{2,3}\s+(.+)$', content, re.MULTILINE)
        for h in headings:
            # 清理markdown标记
            clean = re.sub(r'[#*`]', '', h).strip()
            if clean and clean not in skip_words and clean not in topics:
                topics.append(clean)
        
        # 4. 从tags提取
        tags_match = re.search(r'tags:\s*\[([^\]]+)\]', content)
        if tags_match:
            tags = [t.strip().strip('"').strip("'") for t in tags_match.group(1).split(",")]
            for tag in tags:
                if tag not in topics and tag not in skip_words:
                    topics.append(tag)
        
        # 过滤和排序
        filtered = [t for t in topics if len(t) >= 2 and len(t) <= 20]
        return filtered[:10]
    
    def _has_meaningful_number(self, text: str) -> bool:
        """检查文本中的数字是否有有意义的业务单位"""
        # 提取数字+单位的组合
        number_units = re.findall(r'\d+(?:\.\d+)?(%|倍|万|亿|折|折起|个点|分钟|小时|天|年|款|项|家|人)', text)
        return len(number_units) > 0

    def is_title_garbage(self, title: str) -> bool:
        """检测标题是否为垃圾标题"""
        if not title or len(title) < 5:
            return True
        for pattern in self.GARBAGE_PATTERNS:
            if re.match(pattern, title):
                return True
        return False

    def generate_candidate_titles(self, content: str, date_str: str = "") -> List[str]:
        """
        生成候选标题
        
        返回: 3个候选标题
        """
        topics = self.extract_topics_from_content(content)
        main_topic = topics[0] if topics else "今日热点"
        
        candidates = []
        
        # 候选1: 洞察型（安全，不依赖数字提取）
        insight_words = ['深度解析', '真相', '趋势', '观察']
        candidates.append(f"{main_topic}：{random.choice(insight_words)}")
        
        # 候选2: 数据型（严格过滤：只使用带明确业务单位的数字）
        numbers = re.findall(r'\d+(?:\.\d+)?(?:%|倍|万|亿|折|折起|个点|分钟|小时|天|年|款|项|家|人)', content)
        # 排除版本号/年份，且要求数字+单位整体至少3个字符
        meaningful_numbers = [
            n for n in numbers
            if len(n) >= 3 and not re.match(r'^(202\d|V?\d{1,2})$', re.sub(r'(?:%|倍|万|亿|折|折起|个点|分钟|小时|天|年|款|项|家|人)$', '', n), re.I)
        ]
        if meaningful_numbers:
            num = meaningful_numbers[0]
            # 如果数字太短（如"4%"），不使用"背后的秘密"模板，改用更安全的表达
            if len(num) >= 4:
                candidates.append(f"{main_topic}，{num}背后的秘密")
            else:
                candidates.append(f"{main_topic}：{num}意味着什么？")
        else:
            # 无有意义数字时，使用安全模板
            candidates.append(f"{main_topic}：3个关键变化")
        
        # 候选3: 疑问型
        question_suffixes = ['会改变什么？', '你看懂了吗？', '为什么重要？', '意味着什么？']
        candidates.append(f"{main_topic}{random.choice(question_suffixes)}")
        
        # 候选4: 趋势型（备用）
        if len(topics) >= 2:
            candidates.append(f"从{topics[0]}到{topics[1]}：技术趋势观察")
        
        # 过滤垃圾标题
        candidates = [c for c in candidates if not self.is_title_garbage(c)]
        
        # 去重并返回前3个
        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        
        return unique[:3] if unique else [f"{main_topic}：技术趋势观察"]
    
    def score_title(self, title: str, content: str = "") -> float:
        """
        评分标题质量
        
        返回: 0-100的分数
        """
        score = 0
        
        # 1. 长度评分 (0-15)
        length = len(title)
        if 15 <= length <= 30:
            score += 15
        elif 10 <= length < 15 or 30 < length <= 40:
            score += 10
        else:
            score += 5
        
        # 2. 是否包含有意义的数字 (0-15)
        # 不是只要有数字就加分，数字必须搭配有意义的单位
        if self._has_meaningful_number(title):
            score += 15
        elif re.search(r'\d{3,}', title):
            # 至少3位数字（如日期、大金额）给部分分
            score += 8
        elif re.search(r'\d', title):
            # 纯短数字（如"4"、"V4"）不给分或给最低分
            score += 2
        
        # 3. 是否疑问句式 (0-15)
        if '？' in title or '吗' in title or '什么' in title or '为什么' in title:
            score += 15
        
        # 4. 是否有对比结构 (0-15)
        contrast_words = ['vs', '对比', ' versus', '两面', '从', '到']
        if any(w in title for w in contrast_words):
            score += 15
        
        # 5. 是否有洞察词 (0-15)
        insight_words = ['深度', '真相', '背后', '秘密', '解析', '趋势', '观察', '思考']
        if any(w in title for w in insight_words):
            score += 15
        
        # 6. 情感平衡 (0-15)
        # 不过度正面也不过度负面
        positive_words = ['突破', '成功', '利好', '优秀', '强大']
        negative_words = ['危机', '风险', '问题', '失败', '下跌']
        pos_count = sum(1 for w in positive_words if w in title)
        neg_count = sum(1 for w in negative_words if w in title)
        
        if pos_count == 0 and neg_count == 0:
            score += 10  # 中性偏客观
        elif pos_count > 0 and neg_count > 0:
            score += 15  # 平衡，有张力
        else:
            score += 8   # 单一情感
        
        # 7. 独特性 (0-10)
        # 避免常见套话
        cliches = ['重磅', '突发', '震惊', '注意了', '必看', '紧急']
        if not any(c in title for c in cliches):
            score += 10
        
        return score
    
    def select_best_title(self, candidates: List[str], content: str = "") -> Tuple[str, float]:
        """
        选择最佳标题
        
        返回: (最佳标题, 分数)
        """
        # 过滤垃圾标题
        valid_candidates = [t for t in candidates if not self.is_title_garbage(t)]
        if not valid_candidates:
            # 所有候选都是垃圾，使用第一个非空候选或安全回退
            safe = candidates[0] if candidates else "技术趋势观察"
            return safe, 30.0
        
        scored = [(title, self.score_title(title, content)) for title in valid_candidates]
        scored.sort(key=lambda x: -x[1])
        
        return scored[0]
    
    def optimize_title(self, content: str, current_title: str = "", date_str: str = "") -> str:
        """
        优化标题
        
        返回: 优化后的标题
        """
        # 生成候选标题
        candidates = self.generate_candidate_titles(content, date_str)
        
        # 如果当前标题不是默认的日期标题，也加入候选
        if current_title and "TrendRadar Report" not in current_title:
            if not self.is_title_garbage(current_title):
                candidates.append(current_title)
        
        # 选择最佳标题
        best_title, score = self.select_best_title(candidates, content)
        
        # 最终校验：如果最佳标题仍是垃圾，使用安全回退
        if self.is_title_garbage(best_title):
            topics = self.extract_topics_from_content(content)
            main_topic = topics[0] if topics else "科技"
            best_title = f"{main_topic}：深度趋势观察"
            score = 50.0
        
        print(f"\n{'='*50}")
        print(f"📝 标题优化")
        print(f"{'='*50}")
        print(f"候选标题:")
        for i, title in enumerate(candidates, 1):
            s = self.score_title(title, content)
            garbage_mark = " [垃圾]" if self.is_title_garbage(title) else ""
            marker = " ✅" if title == best_title else ""
            print(f"  {i}. {title} (评分: {s}){marker}{garbage_mark}")
        print(f"\n最佳标题: {best_title} (评分: {score})")
        print(f"{'='*50}\n")
        
        return best_title
    
    def replace_title_in_content(self, content: str, new_title: str) -> str:
        """在文章内容中替换标题（安全处理引号，防止 YAML 解析失败）"""
        if 'title:' not in content:
            return content
        
        # 安全包裹新标题：如果包含双引号且无单引号，改用单引号包裹
        if '"' in new_title and "'" not in new_title:
            replacement = f"title: '{new_title}'"
        else:
            # 转义内部双引号
            safe_title = new_title.replace('"', '\\"')
            replacement = f'title: "{safe_title}"'
        
        # 匹配各种 title 格式：双引号、单引号
        content = re.sub(
            r'^title:\s*(?:"[^"]*"|\'[^\']*\')$',
            replacement,
            content,
            flags=re.MULTILINE
        )
        
        return content


# 便捷函数
def optimize_article_title(content: str, current_title: str = "", trendradar_path: str = ".") -> str:
    """优化文章标题"""
    optimizer = TitleOptimizer(trendradar_path)
    return optimizer.optimize_title(content, current_title)


def replace_article_title(content: str, new_title: str) -> str:
    """替换文章中的标题"""
    optimizer = TitleOptimizer()
    return optimizer.replace_title_in_content(content, new_title)


if __name__ == "__main__":
    # 测试
    test_content = """---
title: "TrendRadar Report - 2024-01-15"
tags: [科技, AI芯片, 半导体]
---

今天AI芯片市场发生了重大变化。

## 市场格局

**AMD的MI300X**正在快速抢占市场，性能在某些场景下已经超越H100。

**Intel Gaudi 3**开始获得云厂商订单。

## 数据亮点

1. 英伟达市场份额从95%下降到85%
2. AMD MI300X推理性能提升40%
3. 中国厂商加速追赶
"""
    
    optimizer = TitleOptimizer()
    best = optimizer.optimize_title(test_content)
    print(f"\n最终标题: {best}")
