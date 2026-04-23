# -*- coding: utf-8 -*-
"""
文章结构多样化引擎 - 防止AI生成固化模式

问题：
1. AI倾向于使用相同的文章结构
2. 每篇文章都变成：引言→分析1→分析2→热点精选→趋势→结语
3. 读者会感到单调乏味

解决方案：
1. 随机选择文章结构模板
2. 轮换分析角度
3. 动态调整内容比重
4. 引入意外元素
"""

import random
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ArticleTemplate:
    """文章结构模板"""
    name: str
    description: str
    sections: List[Dict]
    suitable_for: List[str]  # 适合的话题类型
    complexity: int  # 1-5
    tone: str  # 'analytical', 'narrative', 'provocative', etc.


class ArticleDiversityEngine:
    """文章多样化引擎"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.history_file = f"{trendradar_path}/evolution/template_history.json"
        
        # 定义多样化的文章模板
        self.templates = self._init_templates()
    
    def _init_templates(self) -> List[ArticleTemplate]:
        """初始化文章模板库"""
        return [
            ArticleTemplate(
                name="对比分析型",
                description="通过对比不同方案/公司/技术，揭示本质差异",
                sections=[
                    {"type": "hook", "description": "用反差引入话题", "length": "150字"},
                    {"type": "contrast_table", "description": "多维度对比表格", "required": True},
                    {"type": "deep_dive_1", "description": "深度分析方案A", "length": "400字"},
                    {"type": "deep_dive_2", "description": "深度分析方案B", "length": "400字"},
                    {"type": "verdict", "description": "综合判断与建议", "length": "200字"},
                    {"type": "implications", "description": "对行业的影响", "length": "200字"}
                ],
                suitable_for=["技术选型", "产品对比", "公司财报", "芯片"],
                complexity=4,
                tone="analytical"
            ),
            ArticleTemplate(
                name="故事叙事型",
                description="用故事线串联热点，增加可读性",
                sections=[
                    {"type": "story_hook", "description": "从一个具体场景/人物故事切入", "length": "200字"},
                    {"type": "context", "description": "背景铺垫", "length": "200字"},
                    {"type": "turning_point", "description": "关键转折点", "length": "300字"},
                    {"type": "analysis", "description": "深入分析事件意义", "length": "400字"},
                    {"type": "foreshadowing", "description": "未来可能的发展", "length": "200字"}
                ],
                suitable_for=["创业", "人物", "重大事件", "政策变化"],
                complexity=3,
                tone="narrative"
            ),
            ArticleTemplate(
                name="问题解答型",
                description="提出关键问题，逐层深入解答",
                sections=[
                    {"type": "big_question", "description": "提出一个引人深思的问题", "length": "100字"},
                    {"type": "surface_answer", "description": "表面层面的回答", "length": "200字"},
                    {"type": "deeper_question", "description": "追问更深一层", "length": "100字"},
                    {"type": "deep_analysis", "description": "深入分析", "length": "500字"},
                    {"type": "ultimate_answer", "description": "核心洞察", "length": "200字"},
                    {"type": "new_questions", "description": "引出新的思考问题", "length": "100字"}
                ],
                suitable_for=["技术原理", "市场现象", "社会趋势", "AI"],
                complexity=5,
                tone="provocative"
            ),
            ArticleTemplate(
                name="时间线梳理型",
                description="按时间线梳理事件发展，预测未来",
                sections=[
                    {"type": "present", "description": "当前状态快照", "length": "150字"},
                    {"type": "timeline", "description": "关键时间节点表格", "required": True},
                    {"type": "past", "description": "回顾关键历史节点", "length": "300字"},
                    {"type": "present_analysis", "description": "分析当前局势", "length": "300字"},
                    {"type": "future_roadmap", "description": "未来路线图", "length": "300字"}
                ],
                suitable_for=["产品发布", "政策演变", "技术迭代", "竞争态势"],
                complexity=3,
                tone="analytical"
            ),
            ArticleTemplate(
                name="跨界关联型",
                description="发现不同领域间的隐藏关联",
                sections=[
                    {"type": "parallel_stories", "description": "并置两个看似无关的事件", "length": "200字"},
                    {"type": "field_1", "description": "分析领域A", "length": "300字"},
                    {"type": "field_2", "description": "分析领域B", "length": "300字"},
                    {"type": "connection", "description": "揭示隐藏关联", "length": "300字"},
                    {"type": "synthesis", "description": "综合洞察", "length": "200字"}
                ],
                suitable_for=["AI应用", "产业融合", "技术迁移", "创新"],
                complexity=5,
                tone="insightful"
            ),
            ArticleTemplate(
                name="数据驱动型",
                description="以数据为核心，用数字讲故事",
                sections=[
                    {"type": "killer_stat", "description": "一个震撼的数据", "length": "100字"},
                    {"type": "data_table", "description": "数据对比表格", "required": True},
                    {"type": "trend_chart", "description": "趋势分析", "length": "300字"},
                    {"type": "deep_dive", "description": "数据背后的故事", "length": "400字"},
                    {"type": "prediction", "description": "基于数据的预测", "length": "200字"}
                ],
                suitable_for=["财报", "市场数据", "用户增长", "性能指标"],
                complexity=4,
                tone="analytical"
            ),
            ArticleTemplate(
                name="反直觉型",
                description="挑战常识，提供反直觉的洞察",
                sections=[
                    {"type": "counter_intuitive_hook", "description": "一个反直觉的论断", "length": "150字"},
                    {"type": "common_wisdom", "description": "普遍认知", "length": "200字"},
                    {"type": "evidence", "description": "证据与数据", "length": "400字"},
                    {"type": "reframing", "description": "重新框架问题", "length": "300字"},
                    {"type": "implications", "description": "反直觉结论的意义", "length": "200字"}
                ],
                suitable_for=["技术趋势", "市场判断", "社会现象", "AI"],
                complexity=5,
                tone="provocative"
            )
        ]
    
    def select_template(self, topics: List[str], recent_templates: List[str] = None) -> ArticleTemplate:
        """
        智能选择文章模板
        
        策略：
        1. 根据话题匹配适合的模板
        2. 避免最近使用过的模板
        3. 随机引入意外选择（20%概率）
        """
        recent_templates = recent_templates or []
        
        # 根据话题筛选
        matching = []
        for template in self.templates:
            score = sum(1 for topic in topics if any(
                keyword in topic.lower() for keyword in template.suitable_for
            ))
            if score > 0:
                matching.append((template, score))
        
        # 如果没有匹配，使用所有模板
        if not matching:
            matching = [(t, 1) for t in self.templates]
        
        # 排除最近使用过的（降低权重）
        for i, (template, score) in enumerate(matching):
            if template.name in recent_templates:
                matching[i] = (template, score * 0.3)  # 降低权重
        
        # 20%概率完全随机（引入意外）
        if random.random() < 0.2:
            return random.choice(self.templates)
        
        # 按权重选择
        total_weight = sum(score for _, score in matching)
        if total_weight == 0:
            return random.choice(self.templates)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        for template, score in matching:
            cumulative += score
            if r <= cumulative:
                return template
        
        return matching[-1][0]
    
    def generate_template_instructions(self, template: ArticleTemplate) -> str:
        """
        生成模板指导文本（用于注入到Prompt中）
        """
        instructions = f"""
### 🎲 今日文章结构模板: {template.name}
{template.description}

**要求:**
"""
        
        for i, section in enumerate(template.sections, 1):
            required = " [必须]" if section.get('required') else ""
            instructions += f"{i}. {section['type']}{required}: {section['description']}"
            if 'length' in section:
                instructions += f" ({section['length']})"
            instructions += "\n"
        
        instructions += f"\n**语气风格:** {template.tone}\n"
        instructions += "**注意:** 不要生搬硬套，用这个框架组织你的思路，但保持自然流畅。"
        
        return instructions
    
    def record_template_usage(self, template_name: str, article_title: str):
        """记录模板使用历史"""
        try:
            import os
            history = []
            
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            history.append({
                'date': datetime.now().isoformat(),
                'template': template_name,
                'article': article_title
            })
            
            # 只保留最近20条
            history = history[-20:]
            
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[多样化引擎] 记录模板使用失败: {e}")
    
    def get_recent_templates(self, days: int = 7) -> List[str]:
        """获取最近使用的模板"""
        try:
            import os
            if not os.path.exists(self.history_file):
                return []
            
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 过滤最近N天
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            recent = [h for h in history if h['date'] > cutoff]
            
            return [h['template'] for h in recent]
        except Exception:
            return []


# 便捷函数
def get_diversity_instructions(trendradar_path: str, topics: List[str]) -> str:
    """
    获取文章多样化指导
    
    这是文章多样化引擎的入口点
    """
    engine = ArticleDiversityEngine(trendradar_path)
    
    # 获取最近使用的模板
    recent = engine.get_recent_templates(days=7)
    
    # 选择模板
    template = engine.select_template(topics, recent)
    
    # 生成指导
    instructions = engine.generate_template_instructions(template)
    
    # 记录使用
    # 注意：实际文章标题在生成后才知道，这里先记录模板名
    engine.record_template_usage(template.name, "pending")
    
    return instructions


# 角度轮换器
class PerspectiveRotator:
    """分析角度轮换器"""
    
    PERSPECTIVES = [
        {"name": "技术架构师", "focus": "系统设计和架构选择", "questions": ["底层技术原理是什么？", "架构优势在哪里？"]},
        {"name": "产品经理", "focus": "用户体验和商业价值", "questions": ["用户真正需要什么？", "商业模式如何？"]},
        {"name": "投资人", "focus": "市场机会和风险", "questions": ["市场空间有多大？", "竞争壁垒在哪里？"]},
        {"name": "开发者", "focus": "实现细节和工具", "questions": ["如何落地实现？", "开发者体验如何？"]},
        {"name": "行业观察者", "focus": "宏观趋势和影响", "questions": ["对行业格局有何影响？", "长期趋势如何？"]},
        {"name": "反对者", "focus": "潜在问题和风险", "questions": ["有什么问题被忽视了？", "风险在哪里？"]},
        {"name": "历史学家", "focus": "历史类比和周期", "questions": ["历史上是否发生过类似事件？", "周期性规律是什么？"]},
        {"name": "未来学家", "focus": "预测和展望", "questions": ["3年后会是什么样？", "下一个突破点在哪里？"]}
    ]
    
    @classmethod
    def get_rotated_perspectives(cls, count: int = 2) -> str:
        """获取轮换的分析角度"""
        selected = random.sample(cls.PERSPECTIVES, min(count, len(cls.PERSPECTIVES)))
        
        text = "\n### 🔭 分析角度轮换\n"
        text += "今日要求你从以下角度分析（至少选择2个）:\n\n"
        
        for p in selected:
            text += f"**{p['name']}视角** - {p['focus']}\n"
            for q in p['questions']:
                text += f"  • {q}\n"
            text += "\n"
        
        return text
