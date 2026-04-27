# -*- coding: utf-8 -*-
"""
科技内容守护者 - 确保文章科技占比≥70%

核心功能：
1. 检测文章中科技相关内容的比例
2. 如果比例不足，返回具体改进建议
3. 可以要求AI重写特定部分

检测维度：
- 科技关键词密度
- 技术概念提及次数
- 技术深度（原理/架构/数据）
- 非科技内容占比
"""

import re
from typing import Dict, List, Tuple


class TechContentGuard:
    """科技内容检测器"""
    
    # 科技关键词库
    TECH_KEYWORDS = {
        "ai": ["人工智能", "AI", "机器学习", "深度学习", "神经网络", "大模型", "LLM", "GPT", "Claude", 
               "训练", "推理", "参数", "token", " Transformer", "生成式AI", "AGI", "多模态"],
        "chip": ["芯片", "半导体", "GPU", "TPU", "NPU", "制程", "纳米", "光刻", "EDA", "晶圆", 
                 "封装", "架构", "算力", "HBM", "存储", "内存墙"],
        "cloud": ["云计算", "云原生", "Kubernetes", "Docker", "容器", "微服务", "Serverless",
                  "AWS", "Azure", "阿里云", "腾讯云", "混合云", "私有云"],
        "code": ["开源", "GitHub", "代码", "编程", "Python", "JavaScript", "Rust", "Go", "TypeScript",
                 "框架", "库", "API", "SDK", "开发者", "程序员", "工程师"],
        "product": ["产品", "发布", "更新", "版本", "功能", "特性", "用户体验", "界面", "设计",
                    "评测", "对比", "性能"],
        "data": ["数据", "大数据", "数据库", "SQL", "NoSQL", "数据科学", "数据分析", "可视化",
                 "隐私", "安全", "加密", "区块链"],
        "frontier": ["量子计算", "脑机接口", "航天", "卫星", "火星", "生物科技", "基因", "合成生物学",
                     "新材料", "新能源", "核聚变"]
    }
    
    # 非科技关键词（用于排除）
    NON_TECH_KEYWORDS = [
        "娱乐", "明星", "八卦", "绯闻", "恋情", "离婚", "结婚", "综艺", "电视剧", "电影",
        "美食", "旅游", "时尚", "化妆", "穿搭", "减肥", "健身", "宠物", "星座", "运势"
    ]
    
    def __init__(self, min_tech_ratio: float = 0.7):
        self.min_tech_ratio = min_tech_ratio
        self.all_tech_keywords = []
        for category, keywords in self.TECH_KEYWORDS.items():
            self.all_tech_keywords.extend(keywords)
    
    def analyze(self, content: str) -> Dict:
        """
        分析文章的科技内容占比
        
        返回: {
            "tech_ratio": 科技内容比例 (0-1),
            "tech_score": 科技深度评分 (0-10),
            "non_tech_ratio": 非科技内容比例,
            "tech_categories": 检测到的科技类别,
            "issues": 发现的问题,
            "suggestions": 改进建议
        }
        """
        # 清理内容
        clean_content = self._clean_content(content)
        total_chars = len(clean_content)
        
        if total_chars == 0:
            return {
                "tech_ratio": 0,
                "tech_score": 0,
                "non_tech_ratio": 1,
                "tech_categories": [],
                "issues": ["内容为空"],
                "suggestions": ["请生成文章内容"]
            }
        
        # 1. 计算科技关键词覆盖率
        tech_mentions = 0
        tech_categories = set()
        
        for category, keywords in self.TECH_KEYWORDS.items():
            category_mentions = 0
            for keyword in keywords:
                count = clean_content.count(keyword)
                category_mentions += count
                tech_mentions += count
            
            if category_mentions > 0:
                tech_categories.add(category)
        
        # 2. 计算非科技关键词覆盖率
        non_tech_mentions = 0
        for keyword in self.NON_TECH_KEYWORDS:
            non_tech_mentions += clean_content.count(keyword)
        
        # 3. 检测技术深度指标
        depth_score = self._check_technical_depth(clean_content)
        
        # 4. 计算科技比例（综合算法）
        # 科技词出现次数 / 总字数 * 调整因子 + 深度分
        tech_density = min(tech_mentions * 10 / total_chars, 0.5)  # 密度上限50%
        depth_bonus = depth_score / 20  # 深度加分，上限0.5
        
        tech_ratio = min(tech_density + depth_bonus, 1.0)
        non_tech_ratio = min(non_tech_mentions * 15 / total_chars, 1.0)
        
        # 5. 科技深度评分
        tech_score = min(10, tech_mentions * 2 + depth_score)
        
        # 6. 生成问题和建议
        issues = []
        suggestions = []
        
        if tech_ratio < self.min_tech_ratio:
            issues.append(f"科技内容占比仅 {tech_ratio*100:.0f}%，低于要求 {self.min_tech_ratio*100:.0f}%")
            suggestions.append("增加技术原理分析、架构解析、性能数据等技术细节")
        
        if depth_score < 5:
            issues.append(f"技术深度不足 (评分: {depth_score}/10)")
            suggestions.append("深入解释技术原理，不要停留在概念层面")
        
        if len(tech_categories) < 2:
            issues.append("科技话题单一")
            suggestions.append("尝试跨领域关联，引入更多技术视角")
        
        if non_tech_ratio > 0.3:
            issues.append(f"非科技内容占比过高 ({non_tech_ratio*100:.0f}%)")
            suggestions.append("减少社会新闻、娱乐八卦等非科技内容")
        
        return {
            "tech_ratio": tech_ratio,
            "tech_score": tech_score,
            "non_tech_ratio": non_tech_ratio,
            "tech_categories": list(tech_categories),
            "depth_score": depth_score,
            "issues": issues,
            "suggestions": suggestions,
            "is_pass": tech_ratio >= self.min_tech_ratio and depth_score >= 5
        }
    
    def _clean_content(self, content: str) -> str:
        """清理内容，移除markdown标记和frontmatter"""
        # 移除frontmatter
        if content.lstrip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]
        
        # 移除markdown标记
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)  # 图片
        content = re.sub(r'\[.*?\]\(.*?\)', '', content)   # 链接
        content = re.sub(r'[#*`>:|]', '', content)          # 标记符号
        content = re.sub(r'\s+', '', content)               # 空白
        
        return content
    
    def _check_technical_depth(self, content: str) -> int:
        """
        检查技术深度
        
        返回: 深度评分 (0-10)
        """
        score = 0
        
        # 检测技术原理描述
        if re.search(r'(原理|机制|架构|设计|实现)', content):
            score += 2
        
        # 检测具体数据
        if re.search(r'\d+[%倍个万亿]+', content):
            score += 2
        
        # 检测对比分析
        if re.search(r'(对比|比较|vs|versus)', content, re.IGNORECASE):
            score += 1
        
        # 检测代码或技术术语
        if re.search(r'(代码|函数|算法|模型|协议|接口)', content):
            score += 2
        
        # 检测预测和判断
        if re.search(r'(预测|预计|将|可能|趋势|未来)', content):
            score += 1
        
        # 检测表格（通常包含数据对比）
        if '|' in content and '---' in content:
            score += 2
        
        return min(score, 10)
    
    def get_enforcement_prompt(self, analysis: Dict) -> str:
        """
        生成强制执行Prompt
        
        当科技内容不足时，返回要求重写的Prompt片段
        """
        if analysis["is_pass"]:
            return ""
        
        prompt = """
## ⚠️ 科技内容强化要求（系统检测到科技占比不足）

当前文章存在以下问题：
"""
        for issue in analysis["issues"]:
            prompt += f"- {issue}\n"
        
        prompt += "\n必须改进的方面：\n"
        for suggestion in analysis["suggestions"]:
            prompt += f"- {suggestion}\n"
        
        prompt += f"""
具体要求：
1. 科技相关词汇密度需达到 {self.min_tech_ratio*100:.0f}% 以上
2. 至少涉及2个不同技术领域（如AI+芯片、开源+云计算等）
3. 每个技术话题必须解释原理，不能只说概念
4. 使用具体数据支撑观点（性能指标、市场份额等）
5. 添加技术对比表格

请重写文章，确保科技内容达标！
"""
        return prompt


# 便捷函数
def check_tech_content(content: str, min_ratio: float = 0.7) -> Tuple[bool, str]:
    """
    检查科技内容是否达标
    
    返回: (是否通过, 改进建议)
    """
    guard = TechContentGuard(min_ratio)
    result = guard.analyze(content)
    
    if result["is_pass"]:
        return True, f"科技内容达标: {result['tech_ratio']*100:.0f}%"
    else:
        enforcement = guard.get_enforcement_prompt(result)
        return False, enforcement


if __name__ == "__main__":
    # 测试
    test_content = """
今天的热点包括：
1. OpenAI发布了GPT-5，性能提升30%
2. 某明星离婚事件引发热议
3. 华为发布新款芯片，采用3nm工艺
4. 某地发生地震
"""
    
    guard = TechContentGuard()
    result = guard.analyze(test_content)
    print(f"科技占比: {result['tech_ratio']*100:.0f}%")
    print(f"深度评分: {result['tech_score']}/10")
    print(f"是否通过: {result['is_pass']}")
    print(f"问题: {result['issues']}")
