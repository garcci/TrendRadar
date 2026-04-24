# -*- coding: utf-8 -*-
"""
数据增强器 - 从RSS内容中提取数据点，增强文章说服力

核心功能：
1. 从RSS标题和摘要中提取数字、百分比、金额等数据
2. 将提取的数据整理成结构化格式
3. 在生成文章时注入到Prompt中，提醒AI使用这些数据

提取维度：
- 数字：用户数、营收、估值、市场份额等
- 百分比：增长率、提升幅度、占比等  
- 金额：融资额、营收、市值等
- 时间：发布日期、里程碑时间等
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional


class DataEnhancer:
    """数据增强器"""
    
    # 数据提取正则模式
    PATTERNS = {
        "percentage": r'(\d+(?:\.\d+)?)\s*%',
        "large_number": r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(万|亿|万亿|百万|千万|k|K|M|B|T)?',
        "money": r'([\$￥€£]\s*\d+(?:,\d{3})*(?:\.\d+)?\s*(?:万|亿|百万|千万)?)',
        "time": r'(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}[日]?|\d{1,2}[月/-]\d{1,2}[日]?)',
        "performance": r'(提升|提高|增长|下降|降低|减少)\s*(\d+(?:\.\d+)?)\s*%?',
        "comparison": r'(超过|大于|小于|等于|相当于)\s*(\d+)',
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
    
    def extract_data_points(self, text: str) -> List[Dict]:
        """
        从文本中提取数据点
        
        返回: [{"type": "percentage", "value": "30%", "context": "..."}, ...]
        """
        data_points = []
        
        for data_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                # 获取上下文（前后20个字符）
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context = text[start:end]
                
                data_points.append({
                    "type": data_type,
                    "value": match.group(0),
                    "context": context.strip(),
                    "position": match.start()
                })
        
        # 去重并排序
        seen = set()
        unique_points = []
        for point in data_points:
            key = point["value"] + point["context"]
            if key not in seen:
                seen.add(key)
                unique_points.append(point)
        
        unique_points.sort(key=lambda x: x["position"])
        return unique_points
    
    def enhance_prompt_with_data(self, news_text: str) -> str:
        """
        从新闻文本中提取数据，生成Prompt增强片段
        
        返回: 数据增强Prompt文本
        """
        data_points = self.extract_data_points(news_text)
        
        if not data_points:
            return ""
        
        # 按类型分组
        grouped = {}
        for point in data_points:
            pt = point["type"]
            if pt not in grouped:
                grouped[pt] = []
            grouped[pt].append(point)
        
        # 生成Prompt片段
        lines = ["\n### 📊 可用数据点（请在文章中引用）\n"]
        
        type_names = {
            "percentage": "百分比数据",
            "large_number": "数量数据", 
            "money": "金额数据",
            "time": "时间数据",
            "performance": "性能变化",
            "comparison": "对比数据"
        }
        
        for data_type, points in grouped.items():
            if len(points) > 5:
                points = points[:5]  # 每类最多5个
            
            lines.append(f"**{type_names.get(data_type, data_type)}：**")
            for point in points:
                lines.append(f"- {point['value']}（上下文: ...{point['context']}...）")
            lines.append("")
        
        lines.append("**注意**：请在深度分析中引用以上数据，用具体数字支撑你的观点！")
        
        return "\n".join(lines)
    
    def save_data_points(self, date: str, points: List[Dict]):
        """保存数据点到文件"""
        data_file = f"{self.trendradar_path}/evolution/daily_data_points.json"
        
        data = {}
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
        
        data[date] = points
        
        with open(data_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_historical_data(self, keyword: str, days: int = 30) -> List[Dict]:
        """获取历史数据点（用于趋势分析）"""
        data_file = f"{self.trendradar_path}/evolution/daily_data_points.json"
        
        if not os.path.exists(data_file):
            return []
        
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        results = []
        for date, points in data.items():
            for point in points:
                if keyword in point.get("context", ""):
                    results.append({
                        "date": date,
                        **point
                    })
        
        return results[-20:]  # 最多返回20条


# 便捷函数
def get_data_enhancement(news_text: str, trendradar_path: str = ".") -> str:
    """获取数据增强Prompt片段"""
    enhancer = DataEnhancer(trendradar_path)
    return enhancer.enhance_prompt_with_data(news_text)


if __name__ == "__main__":
    # 测试
    test_text = """
    OpenAI发布GPT-4 Turbo，性能提升40%，价格降低50%。
    公司估值达到800亿美元，年收入超过20亿美元。
    用户数量增长至1.8亿，月活跃用户1亿。
    发布时间：2024年3月15日
    """
    
    enhancer = DataEnhancer()
    points = enhancer.extract_data_points(test_text)
    print(f"提取到 {len(points)} 个数据点")
    for p in points[:5]:
        print(f"- {p['type']}: {p['value']}")
