# -*- coding: utf-8 -*-
"""
Prompt动态优化系统 - 根据文章评分自动调整Prompt强度

核心逻辑：
- 评分 < 6.0: 强化模式 - 增加技术深度要求、数据支撑要求
- 评分 6.0-7.5: 标准模式 - 保持当前要求
- 评分 > 7.5: 创新模式 - 鼓励更多创新角度

进化机制：
1. 读取最近3篇文章的评分
2. 计算平均分和趋势
3. 根据分数选择对应的Prompt增强策略
4. 将增强指令注入到system_prompt中
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class PromptOptimizer:
    """Prompt动态优化器"""
    
    # 不同评分区间对应的增强策略
    ENHANCEMENT_STRATEGIES = {
        "critical": {  # 评分 < 6.0
            "level": "强化模式",
            "instructions": """
## ⚠️ 质量强化指令（系统检测到近期文章评分偏低，请严格执行）

### 技术深度强制要求
- **每个技术话题必须包含**：
  - 核心技术原理的详细解释（至少150字）
  - 具体的技术架构图或流程描述
  - 性能数据对比（如延迟、吞吐量、准确率等）
  - 与竞品/替代方案的详细对比表格

### 数据支撑强制要求  
- **每篇文章至少包含5个具体数据点**：
  - 市场份额、增长率、用户数量等
  - 性能指标（如训练成本、推理速度）
  - 财务数据（营收、估值、融资额）
  - 时间线数据（发布日期、里程碑）

### 分析深度强制要求
- **禁止表面描述**，必须回答：
  - 这项技术/事件为什么重要？（行业影响）
  - 背后的驱动因素是什么？（深层原因）
  - 对谁有利？对谁不利？（利益分析）
  - 3-6个月后会怎样？（趋势预测）

### 结构强制要求
- 深度分析板块不少于3个
- 每个板块必须包含：技术细节 + 数据表格 + 预测分析
- 总字数不少于1500字
""",
            "temperature_adjustment": -0.1,  # 降低随机性，提高确定性
            "max_tokens_adjustment": 1.3    # 增加输出长度
        },
        "standard": {  # 评分 6.0-7.5
            "level": "标准模式",
            "instructions": "",  # 不添加额外指令
            "temperature_adjustment": 0,
            "max_tokens_adjustment": 1.0
        },
        "creative": {  # 评分 > 7.5
            "level": "创新模式",
            "instructions": """
## 🚀 创新鼓励指令（系统检测到近期文章质量优秀，鼓励创新）

### 创新角度建议
- 尝试跨界关联：将科技热点与其他领域（哲学、社会学、心理学）联系
- 使用故事化叙事：用具体案例或人物故事引出技术话题
- 提出反直觉观点：挑战主流认知，提供独特视角
- 历史对比：将当前事件与科技史上的类似事件对比

### 风格多样化
- 可以尝试：访谈体、日记体、书信体等创新形式
- 适当增加幽默感，让技术文章更生动
- 使用类比和隐喻解释复杂概念

### 保持质量的同时追求特色
- 在保持深度分析的基础上，追求独特的表达风格
- 每篇文章尝试1-2个新的写作技巧
""",
            "temperature_adjustment": 0.1,   # 增加随机性，鼓励创新
            "max_tokens_adjustment": 1.1
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = f"{trendradar_path}/evolution/article_metrics.json"
    
    def get_recent_scores(self, days: int = 7) -> List[Dict]:
        """获取最近的文章评分"""
        if not os.path.exists(self.metrics_file):
            return []
        
        with open(self.metrics_file, 'r') as f:
            metrics = json.load(f)
        
        # 按时间排序，取最近的
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [m for m in metrics if m.get("timestamp", "") > cutoff]
        
        return recent
    
    def analyze_score_trend(self, scores: List[Dict]) -> Tuple[str, float, str]:
        """
        分析评分趋势
        
        返回: (策略名称, 平均分, 趋势描述)
        """
        if not scores:
            return "standard", 0.0, "无历史数据"
        
        # 计算平均分
        avg_score = sum(s.get("overall_score", 0) for s in scores) / len(scores)
        
        # 计算趋势
        if len(scores) >= 2:
            first_half = sum(s.get("overall_score", 0) for s in scores[:len(scores)//2]) / max(len(scores)//2, 1)
            second_half = sum(s.get("overall_score", 0) for s in scores[len(scores)//2:]) / max(len(scores) - len(scores)//2, 1)
            
            if second_half > first_half + 0.5:
                trend = "上升"
            elif second_half < first_half - 0.5:
                trend = "下降"
            else:
                trend = "平稳"
        else:
            trend = "未知"
        
        # 选择策略
        if avg_score < 6.0:
            strategy = "critical"
        elif avg_score > 7.5:
            strategy = "creative"
        else:
            strategy = "standard"
        
        return strategy, avg_score, trend
    
    def get_prompt_enhancement(self) -> Dict:
        """
        获取Prompt增强配置
        
        返回: {
            "instructions": "增强指令文本",
            "temperature_delta": 温度调整值,
            "max_tokens_multiplier": 长度调整倍数,
            "level": "当前模式名称",
            "avg_score": 平均评分,
            "trend": 趋势描述
        }
        """
        scores = self.get_recent_scores(days=7)
        strategy_name, avg_score, trend = self.analyze_score_trend(scores)
        
        strategy = self.ENHANCEMENT_STRATEGIES[strategy_name]
        
        return {
            "instructions": strategy["instructions"],
            "temperature_delta": strategy["temperature_adjustment"],
            "max_tokens_multiplier": strategy["max_tokens_adjustment"],
            "level": strategy["level"],
            "avg_score": avg_score,
            "trend": trend,
            "sample_count": len(scores)
        }
    
    def inject_enhancement(self, system_prompt: str, base_temperature: float = 0.7, 
                          base_max_tokens: int = 4000) -> Tuple[str, float, int]:
        """
        将增强指令注入到system_prompt中
        
        返回: (增强后的prompt, 调整后的temperature, 调整后的max_tokens)
        """
        enhancement = self.get_prompt_enhancement()
        
        # 如果没有增强指令，返回原始值
        if not enhancement["instructions"]:
            return system_prompt, base_temperature, base_max_tokens
        
        # 在prompt末尾注入增强指令（在"记住："之前）
        injection_point = "记住：读者时间宝贵"
        if injection_point in system_prompt:
            enhanced_prompt = system_prompt.replace(
                injection_point,
                enhancement["instructions"] + "\n\n" + injection_point
            )
        else:
            enhanced_prompt = system_prompt + "\n\n" + enhancement["instructions"]
        
        # 计算调整后的参数
        new_temperature = max(0.1, min(1.0, base_temperature + enhancement["temperature_delta"]))
        new_max_tokens = int(base_max_tokens * enhancement["max_tokens_multiplier"])
        
        print(f"[Prompt优化] 当前模式: {enhancement['level']}")
        print(f"[Prompt优化] 近期平均分: {enhancement['avg_score']:.1f}/10 ({enhancement['trend']}趋势)")
        print(f"[Prompt优化] 样本数: {enhancement['sample_count']}篇")
        print(f"[Prompt优化] 温度调整: {base_temperature} → {new_temperature}")
        print(f"[Prompt优化] 长度调整: {base_max_tokens} → {new_max_tokens}")
        
        return enhanced_prompt, new_temperature, new_max_tokens


# 便捷函数
def get_optimized_prompt_params(system_prompt: str, base_temp: float = 0.7, 
                                base_tokens: int = 4000, trendradar_path: str = ".") -> Tuple[str, float, int]:
    """获取优化后的Prompt参数"""
    optimizer = PromptOptimizer(trendradar_path)
    return optimizer.inject_enhancement(system_prompt, base_temp, base_tokens)


if __name__ == "__main__":
    # 测试
    optimizer = PromptOptimizer()
    enhancement = optimizer.get_prompt_enhancement()
    print(f"\n当前模式: {enhancement['level']}")
    print(f"平均分: {enhancement['avg_score']:.1f}")
    print(f"趋势: {enhancement['trend']}")
    print(f"样本数: {enhancement['sample_count']}")
    if enhancement['instructions']:
        print(f"\n增强指令:\n{enhancement['instructions'][:200]}...")
