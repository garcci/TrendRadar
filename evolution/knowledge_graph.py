# -*- coding: utf-8 -*-
"""
话题知识图谱 - 构建实体关系网络，提升文章深度

核心理念：
1. 识别文章中的关键实体（公司、技术、人物、产品）
2. 发现实体之间的关系（竞争、合作、依赖、替代）
3. 基于知识图谱提供更深度的分析角度
4. 将图谱洞察注入Prompt，帮助AI写出更有深度的文章

实体类型：
- 公司: 英伟达、AMD、Intel、OpenAI、Google
- 技术: AI、大模型、GPU、芯片、云计算
- 产品: GPT-5、MI300X、H100、iPhone
- 人物: 马斯克、奥特曼、黄仁勋
- 领域: 半导体、自动驾驶、量子计算

关系类型：
- 竞争: A vs B
- 合作: A + B
- 依赖: A 依赖 B
- 替代: A 替代 B
- 包含: A 包含 B
"""

import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple


class KnowledgeGraph:
    """话题知识图谱"""
    
    # 预定义实体库
    ENTITIES = {
        "company": [
            "英伟达", "NVIDIA", "AMD", "Intel", "英特尔", "高通", "Qualcomm", "苹果", "Apple",
            "谷歌", "Google", "微软", "Microsoft", "亚马逊", "Amazon", "Meta", "脸书",
            "OpenAI", "Anthropic", "DeepSeek", "百度", "阿里", "腾讯", "华为", "小米",
            "字节跳动", "特斯拉", "Tesla", "三星", "Samsung", "台积电", "TSMC"
        ],
        "technology": [
            "人工智能", "AI", "大模型", "LLM", "GPT", "机器学习", "深度学习", "神经网络",
            "芯片", "GPU", "CPU", "TPU", "NPU", "半导体", "制程", "光刻",
            "云计算", "云原生", "容器", "Kubernetes", "Docker", "微服务",
            "区块链", "量子计算", "5G", "6G", "物联网", "IoT", "边缘计算"
        ],
        "product": [
            "ChatGPT", "GPT-4", "GPT-5", "Claude", "Llama", "Gemini", "Copilot",
            "iPhone", "iPad", "MacBook", "Android", "Windows", "iOS",
            "MI300X", "H100", "H200", "A100", "RTX", "CUDA",
            "TensorFlow", "PyTorch", "Kubernetes", "React", "Vue"
        ],
        "person": [
            "马斯克", "Elon Musk", "山姆·奥特曼", "Sam Altman", "黄仁勋", "Jensen Huang",
            "扎克伯格", "Zuckerberg", "贝佐斯", "Bezos", "李彦宏", "马云", "马化腾",
            "雷军", "余承东", "任正非", "张一鸣"
        ],
        "field": [
            "自动驾驶", "智能驾驶", "机器人", "人形机器人", "无人机",
            "新能源", "电动车", "光伏", "储能", "核聚变",
            "生物医药", "基因编辑", "脑机接口", "航天", "卫星",
            "金融科技", "数字货币", "Web3", "元宇宙", "VR", "AR"
        ]
    }
    
    # 关系关键词
    RELATION_PATTERNS = {
        "compete": ["vs", "对抗", "竞争", " rival", "对手", "比拼", "较量", "争夺"],
        "cooperate": ["合作", "联手", "联盟", "结盟", "伙伴", "联合", "共同"],
        "depend": ["依赖", "依靠", "基于", "基于", "依托", "离不开"],
        "replace": ["替代", "取代", "颠覆", "淘汰", "代替", "革新"],
        "include": ["包含", "包括", "涵盖", "集成", "内置", "搭载"]
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.graph_file = f"{trendradar_path}/evolution/knowledge_graph.json"
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """从文本中提取实体"""
        entities = defaultdict(list)
        
        for entity_type, entity_list in self.ENTITIES.items():
            for entity in entity_list:
                if entity in text:
                    if entity not in entities[entity_type]:
                        entities[entity_type].append(entity)
        
        return dict(entities)
    
    def find_relations(self, text: str, entities: Dict[str, List[str]]) -> List[Dict]:
        """发现实体之间的关系"""
        relations = []
        
        # 收集所有实体
        all_entities = []
        for entity_list in entities.values():
            all_entities.extend(entity_list)
        
        # 寻找实体对和关系
        for i, entity1 in enumerate(all_entities):
            for entity2 in all_entities[i+1:]:
                # 找到包含两个实体的句子
                sentences = re.split(r'[。！？\n]', text)
                for sentence in sentences:
                    if entity1 in sentence and entity2 in sentence:
                        # 检测关系类型
                        for rel_type, keywords in self.RELATION_PATTERNS.items():
                            for keyword in keywords:
                                if keyword in sentence:
                                    relations.append({
                                        "entity1": entity1,
                                        "entity2": entity2,
                                        "relation": rel_type,
                                        "context": sentence[:100]
                                    })
                                    break
        
        return relations
    
    def build_graph_from_content(self, content: str) -> Dict:
        """从文章内容构建知识图谱"""
        entities = self.extract_entities(content)
        relations = self.find_relations(content, entities)
        
        return {
            "entities": entities,
            "relations": relations,
            "entity_count": sum(len(v) for v in entities.values()),
            "relation_count": len(relations)
        }
    
    def generate_graph_insight(self, graph: Dict) -> str:
        """生成知识图谱洞察（用于Prompt注入）"""
        if graph["entity_count"] == 0:
            return ""
        
        lines = ["\n### 🕸️ 话题知识图谱\n"]
        
        # 实体概览
        lines.append("**识别到的关键实体**:")
        for entity_type, entity_list in graph["entities"].items():
            if entity_list:
                type_names = {
                    "company": "🏢 公司", "technology": "🔧 技术", 
                    "product": "📱 产品", "person": "👤 人物", "field": "🌐 领域"
                }
                lines.append(f"- {type_names.get(entity_type, entity_type)}: {', '.join(entity_list[:5])}")
        lines.append("")
        
        # 关系洞察
        if graph["relations"]:
            lines.append("**实体关系**:")
            rel_names = {
                "compete": "⚔️ 竞争", "cooperate": "🤝 合作",
                "depend": "🔗 依赖", "replace": "🔄 替代", "include": "📦 包含"
            }
            for rel in graph["relations"][:5]:
                rel_emoji = rel_names.get(rel["relation"], rel["relation"])
                lines.append(f"- {rel_emoji}: {rel['entity1']} ↔ {rel['entity2']}")
            lines.append("")
        
        lines.append("**建议**: 基于以上知识图谱，尝试从实体关系角度分析，提供更深入的洞察。\n")
        
        return "\n".join(lines)
    
    def save_graph(self, date: str, graph: Dict):
        """保存知识图谱到文件"""
        graphs = {}
        if os.path.exists(self.graph_file):
            with open(self.graph_file, 'r') as f:
                graphs = json.load(f)
        
        graphs[date] = graph
        
        with open(self.graph_file, 'w') as f:
            json.dump(graphs, f, ensure_ascii=False, indent=2)
    
    def get_entity_history(self, entity: str) -> List[Dict]:
        """获取实体的历史出现记录"""
        if not os.path.exists(self.graph_file):
            return []
        
        with open(self.graph_file, 'r') as f:
            graphs = json.load(f)
        
        history = []
        for date, graph in graphs.items():
            for entity_type, entity_list in graph.get("entities", {}).items():
                if entity in entity_list:
                    history.append({
                        "date": date,
                        "type": entity_type,
                        "relations": [r for r in graph.get("relations", []) 
                                     if r["entity1"] == entity or r["entity2"] == entity]
                    })
        
        return history[-10:]  # 最近10次


# 便捷函数
def get_knowledge_graph_insight(content: str, trendradar_path: str = ".") -> str:
    """获取知识图谱洞察（用于Prompt注入）"""
    kg = KnowledgeGraph(trendradar_path)
    graph = kg.build_graph_from_content(content)
    return kg.generate_graph_insight(graph)


if __name__ == "__main__":
    # 测试
    test_content = """
    英伟达和AMD在AI芯片市场展开激烈竞争。
    英伟达的H100面临AMD MI300X的挑战。
    OpenAI依赖英伟达的GPU训练大模型。
    谷歌则选择自研TPU来替代英伟达的方案。
    特斯拉也在开发自己的AI芯片用于自动驾驶。
    """
    
    kg = KnowledgeGraph()
    graph = kg.build_graph_from_content(test_content)
    print(f"实体数: {graph['entity_count']}")
    print(f"关系数: {graph['relation_count']}")
    print("\n洞察:")
    print(kg.generate_graph_insight(graph))
