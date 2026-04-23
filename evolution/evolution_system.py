# -*- coding: utf-8 -*-
"""
AI 自我进化系统 - 让 DeepSeek 持续自我改进

功能：
1. 文章质量评估 - 分析生成文章的质量并打分
2. 学习总结 - 提取改进经验和最佳实践
3. Prompt 优化 - 基于反馈自动调整生成策略
4. 进化日志 - 记录系统的成长轨迹
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional


class AIEvolutionSystem:
    """AI 自我进化系统"""
    
    def __init__(self, repo_owner: str, repo_name: str, token: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.evolution_log_path = "evolution/evolution_log.md"
        self.reviews_dir = "evolution/article_reviews"
        
    def evaluate_article(self, article_content: str, article_title: str) -> Dict:
        """
        评估文章质量，返回评估结果
        
        评估维度：
        - 科技/AI 内容占比
        - 分析深度
        - 写作风格多样性
        - 洞察力
        - 可读性
        """
        evaluation = {
            "title": article_title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dimensions": {},
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "improvement_suggestions": []
        }
        
        # 1. 科技/AI 内容占比评估
        tech_keywords = [
            "AI", "人工智能", "机器学习", "深度学习", "神经网络",
            "开源", "GitHub", "代码", "算法", "模型", "LLM", "GPT",
            "芯片", "算力", "GPU", "TPU", "云计算", "大数据",
            "区块链", "Web3", "量子计算", "机器人", "自动驾驶",
            "编程", "Python", "Rust", "JavaScript", "框架",
            "API", "开发者", "技术架构", "系统", "数据库"
        ]
        
        tech_mentions = sum(1 for keyword in tech_keywords if keyword in article_content)
        total_chars = len(article_content)
        tech_ratio = min(tech_mentions / 20, 1.0)  # 归一化到 0-1
        evaluation["dimensions"]["tech_content_ratio"] = {
            "score": round(tech_ratio * 10, 1),
            "max": 10,
            "description": f"科技/AI 关键词出现 {tech_mentions} 次"
        }
        
        # 2. 分析深度评估
        depth_indicators = [
            "原理", "架构", "底层", "机制", "算法", "优化", "性能",
            "对比", "差异", "优势", "劣势", "挑战", "解决方案",
            "影响", "趋势", "预测", "展望", "变革", "革命"
        ]
        depth_mentions = sum(1 for indicator in depth_indicators if indicator in article_content)
        depth_score = min(depth_mentions / 10, 1.0)
        evaluation["dimensions"]["analysis_depth"] = {
            "score": round(depth_score * 10, 1),
            "max": 10,
            "description": f"深度分析指标出现 {depth_mentions} 次"
        }
        
        # 3. 写作风格多样性评估
        style_elements = {
            "admonition": ":::" in article_content,
            "quote": "> " in article_content,
            "table": "|" in article_content and "---" in article_content,
            "code": "```" in article_content,
            "list": "- " in article_content,
            "bold": "**" in article_content
        }
        style_score = sum(style_elements.values()) / len(style_elements)
        evaluation["dimensions"]["style_diversity"] = {
            "score": round(style_score * 10, 1),
            "max": 10,
            "description": f"使用 {sum(style_elements.values())}/{len(style_elements)} 种 Markdown 元素"
        }
        
        # 4. 洞察力评估
        insight_patterns = [
            r"这意味着",
            r"背后的逻辑",
            r"本质上是",
            r"更深层次",
            r"揭示了",
            r"表明",
            r"预示着",
            r"关键洞察",
            r"核心命题"
        ]
        insight_count = sum(len(re.findall(pattern, article_content)) for pattern in insight_patterns)
        insight_score = min(insight_count / 5, 1.0)
        evaluation["dimensions"]["insightfulness"] = {
            "score": round(insight_score * 10, 1),
            "max": 10,
            "description": f"洞察性表达出现 {insight_count} 次"
        }
        
        # 5. 可读性评估（文章长度适中）
        word_count = len(article_content)
        if 3000 <= word_count <= 8000:
            readability_score = 1.0
        elif 2000 <= word_count < 3000:
            readability_score = 0.8
        elif 8000 < word_count <= 12000:
            readability_score = 0.7
        else:
            readability_score = 0.5
        evaluation["dimensions"]["readability"] = {
            "score": round(readability_score * 10, 1),
            "max": 10,
            "description": f"文章长度 {word_count} 字"
        }
        
        # 计算总分
        total_score = sum(d["score"] for d in evaluation["dimensions"].values())
        evaluation["overall_score"] = round(total_score / len(evaluation["dimensions"]), 1)
        
        # 识别优点
        if tech_ratio > 0.7:
            evaluation["strengths"].append("科技/AI 内容占比高")
        if depth_score > 0.7:
            evaluation["strengths"].append("分析深入，不流于表面")
        if style_score > 0.7:
            evaluation["strengths"].append("写作风格多样，善用 Markdown 特性")
        if insight_score > 0.7:
            evaluation["strengths"].append("洞察力强，有独到观点")
        
        # 识别弱点
        if tech_ratio < 0.5:
            evaluation["weaknesses"].append("科技/AI 内容占比不足")
        if depth_score < 0.5:
            evaluation["weaknesses"].append("分析深度不够，需要更多技术细节")
        if insight_score < 0.5:
            evaluation["weaknesses"].append("洞察力不足，缺乏独到见解")
        
        # 生成改进建议
        if tech_ratio < 0.7:
            evaluation["improvement_suggestions"].append("增加更多技术细节和专业术语")
        if depth_score < 0.7:
            evaluation["improvement_suggestions"].append("深入分析技术原理，而非表面描述")
        if insight_score < 0.7:
            evaluation["improvement_suggestions"].append("增加更多原创性观点和预测")
        if not style_elements["table"]:
            evaluation["improvement_suggestions"].append("使用表格进行对比分析")
        if not style_elements["admonition"]:
            evaluation["improvement_suggestions"].append("使用 Admonition 引用块突出关键洞察")
        
        return evaluation
    
    def generate_improvement_prompt(self, evaluation: Dict) -> str:
        """
        基于评估结果生成优化建议 Prompt
        """
        suggestions = evaluation.get("improvement_suggestions", [])
        weaknesses = evaluation.get("weaknesses", [])
        
        if not suggestions and not weaknesses:
            return ""
        
        prompt_parts = ["\n\n### 进化反馈（基于之前文章的自动评估）"]
        prompt_parts.append("根据之前生成文章的质量评估，以下方面需要改进：\n")
        
        for i, weakness in enumerate(weaknesses, 1):
            prompt_parts.append(f"{i}. ❌ {weakness}")
        
        for i, suggestion in enumerate(suggestions, len(weaknesses) + 1):
            prompt_parts.append(f"{i}. 💡 {suggestion}")
        
        prompt_parts.append("\n请在本次创作中针对性改进以上问题。")
        
        return "\n".join(prompt_parts)
    
    def save_evaluation(self, evaluation: Dict) -> bool:
        """
        保存评估结果到进化日志
        """
        try:
            import requests
            
            # 格式化评估结果为 Markdown
            content = self._format_evaluation_markdown(evaluation)
            
            # 创建或更新进化日志
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{self.reviews_dir}/{date_str}-review.md"
            
            # 检查文件是否已存在
            check_url = f"{self.base_url}/contents/{filename}"
            response = requests.get(check_url, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })
            
            if response.status_code == 200:
                # 文件存在，追加内容
                existing = response.json()
                sha = existing["sha"]
                existing_content = requests.get(existing["download_url"]).text
                new_content = existing_content + "\n\n---\n\n" + content
                
                update_data = {
                    "message": f"feat: 追加文章评估 - {evaluation['title']}",
                    "content": self._encode_content(new_content),
                    "sha": sha
                }
            else:
                # 创建新文件
                new_content = f"# 文章质量评估日志\n\n{content}"
                update_data = {
                    "message": f"feat: 添加文章评估 - {evaluation['title']}",
                    "content": self._encode_content(new_content)
                }
            
            response = requests.put(
                f"{self.base_url}/contents/{filename}",
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=update_data
            )
            
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"[进化系统] 保存评估失败: {e}")
            return False
    
    def _format_evaluation_markdown(self, evaluation: Dict) -> str:
        """格式化评估结果为 Markdown"""
        lines = [
            f"## 评估: {evaluation['title']}",
            f"**时间**: {evaluation['date']}",
            f"**综合评分**: {evaluation['overall_score']}/10",
            "",
            "### 维度评分",
        ]
        
        for dim_name, dim_data in evaluation["dimensions"].items():
            lines.append(f"- **{dim_name}**: {dim_data['score']}/{dim_data['max']} - {dim_data['description']}")
        
        if evaluation["strengths"]:
            lines.extend(["", "### ✅ 优点"])
            for strength in evaluation["strengths"]:
                lines.append(f"- {strength}")
        
        if evaluation["weaknesses"]:
            lines.extend(["", "### ❌ 待改进"])
            for weakness in evaluation["weaknesses"]:
                lines.append(f"- {weakness}")
        
        if evaluation["improvement_suggestions"]:
            lines.extend(["", "### 💡 改进建议"])
            for suggestion in evaluation["improvement_suggestions"]:
                lines.append(f"- {suggestion}")
        
        return "\n".join(lines)
    
    def _encode_content(self, content: str) -> str:
        """编码内容为 base64"""
        import base64
        return base64.b64encode(content.encode("utf-8")).decode("utf-8")
    
    def get_evolution_context(self) -> str:
        """
        获取进化上下文，用于注入到下次的 Prompt 中
        """
        try:
            import requests
            
            # 获取最近的评估记录
            reviews_url = f"{self.base_url}/contents/{self.reviews_dir}"
            response = requests.get(reviews_url, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })
            
            if response.status_code != 200:
                return ""
            
            files = response.json()
            if not files:
                return ""
            
            # 获取最新的评估文件
            latest_file = sorted(files, key=lambda x: x["name"], reverse=True)[0]
            content_url = latest_file["download_url"]
            content_response = requests.get(content_url)
            
            if content_response.status_code == 200:
                # 提取改进建议部分
                content = content_response.text
                # 只取最近 3 条评估的改进建议
                sections = content.split("---")
                recent_sections = sections[-3:] if len(sections) > 3 else sections
                
                context_parts = ["\n\n### 进化反馈（基于历史文章评估）"]
                context_parts.append("根据之前文章的质量评估，请注意以下改进方向：\n")
                
                for section in recent_sections:
                    if "💡 改进建议" in section:
                        suggestions = re.findall(r"- (.*?)(?=\n|$)", section.split("💡 改进建议")[1])
                        for suggestion in suggestions[:3]:
                            context_parts.append(f"- {suggestion.strip()}")
                
                return "\n".join(context_parts)
            
            return ""
        except Exception as e:
            print(f"[进化系统] 获取进化上下文失败: {e}")
            return ""


# 便捷函数
def evaluate_and_evolve(article_content: str, article_title: str, 
                       repo_owner: str, repo_name: str, token: str) -> str:
    """
    评估文章并返回进化反馈 Prompt
    """
    system = AIEvolutionSystem(repo_owner, repo_name, token)
    
    # 评估文章
    evaluation = system.evaluate_article(article_content, article_title)
    
    # 保存评估结果
    system.save_evaluation(evaluation)
    
    # 生成改进 Prompt
    improvement_prompt = system.generate_improvement_prompt(evaluation)
    
    print(f"[进化系统] 文章 '{article_title}' 评估完成，综合评分: {evaluation['overall_score']}/10")
    
    return improvement_prompt
