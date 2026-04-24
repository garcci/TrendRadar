# -*- coding: utf-8 -*-
"""
自主功能设计 - AI根据观察结果自主设计新功能

核心理念：
1. 读取自我观察报告，识别能力缺口
2. 基于缺口类型，匹配预设的设计模板
3. 生成新功能的详细设计文档
4. 设计文档包含：功能名称、目标、核心逻辑、输入输出、文件名

设计模板库：
- 内容质量不足 → 设计新的内容增强模块（数据提取、深度分析等）
- 系统稳定性差 → 设计新的容错/监控模块（健康检查、自动恢复等）
- 数据质量低 → 设计新的数据处理模块（去重、清洗、增强等）
- 功能覆盖少 → 设计新的进化模块（分析、预测、优化等）

输出：
- 功能设计文档（JSON格式）
- 设计文档保存到 evolution/designs/ 目录
- 供 Lv28 自主代码生成使用
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional


class SelfDesigner:
    """自主功能设计师"""
    
    # 功能设计模板库
    DESIGN_TEMPLATES = {
        "content_quality": {
            "category": "内容增强",
            "templates": [
                {
                    "problem_pattern": "深度不足",
                    "feature_name": "深度分析增强器",
                    "description": "自动识别文章中的浅层描述，建议补充技术细节",
                    "core_logic": "扫描文章内容，识别缺少数据支撑的观点，生成补充建议",
                    "input": "文章内容",
                    "output": "深度改进建议列表",
                    "file_name": "depth_enhancer.py"
                },
                {
                    "problem_pattern": "结构单一",
                    "feature_name": "文章结构多样化器",
                    "description": "分析历史文章结构，推荐不同的文章组织方式",
                    "core_logic": "统计历史文章结构模式，生成结构多样化建议",
                    "input": "历史文章列表",
                    "output": "推荐的文章结构模板",
                    "file_name": "structure_diversifier.py"
                },
                {
                    "problem_pattern": "数据不足",
                    "feature_name": "外部数据补充器",
                    "description": "自动从维基百科、GitHub等外部源获取补充数据",
                    "core_logic": "识别文章中的关键实体，从外部API获取相关数据",
                    "input": "文章内容",
                    "output": "补充数据点列表",
                    "file_name": "external_data_fetcher.py"
                }
            ]
        },
        "system_stability": {
            "category": "系统稳定",
            "templates": [
                {
                    "problem_pattern": "API降级",
                    "feature_name": "智能API路由优化器",
                    "description": "根据API历史表现动态调整路由策略",
                    "core_logic": "记录各API成功率、延迟、成本，动态优化路由",
                    "input": "API调用日志",
                    "output": "优化后的路由配置",
                    "file_name": "api_router_optimizer.py"
                },
                {
                    "problem_pattern": "错误率高",
                    "feature_name": "错误自愈系统",
                    "description": "自动检测常见错误模式并应用修复",
                    "core_logic": "分类错误日志，匹配已知修复方案，自动应用",
                    "input": "错误日志",
                    "output": "修复操作记录",
                    "file_name": "auto_healer.py"
                }
            ]
        },
        "data_quality": {
            "category": "数据处理",
            "templates": [
                {
                    "problem_pattern": "重复内容",
                    "feature_name": "内容去重优化器",
                    "description": "更智能的内容去重，避免相似文章重复发布",
                    "core_logic": "使用语义相似度计算，识别内容相似度高的文章",
                    "input": "文章列表",
                    "output": "去重后的文章列表",
                    "file_name": "semantic_dedup.py"
                },
                {
                    "problem_pattern": "数据量不足",
                    "feature_name": "RSS源智能推荐器",
                    "description": "根据内容偏好自动推荐新的RSS源",
                    "core_logic": "分析现有内容主题，推荐匹配的高质量RSS源",
                    "input": "现有文章主题分析",
                    "output": "推荐RSS源列表",
                    "file_name": "rss_recommender.py"
                }
            ]
        },
        "feature_coverage": {
            "category": "功能扩展",
            "templates": [
                {
                    "problem_pattern": "缺少分析维度",
                    "feature_name": "多维度分析引擎",
                    "description": "从更多维度分析热点内容",
                    "core_logic": "添加新的分析维度（如地理位置、时间线、影响力等）",
                    "input": "热点数据",
                    "output": "多维度分析报告",
                    "file_name": "multi_dimension_analyzer.py"
                },
                {
                    "problem_pattern": "进化等级低",
                    "feature_name": "进化效果评估器",
                    "description": "评估每个进化模块的实际效果",
                    "core_logic": "对比启用/禁用各模块时的文章评分差异",
                    "input": "文章评分数据",
                    "output": "各模块效果评估报告",
                    "file_name": "evolution_effect_evaluator.py"
                }
            ]
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.designs_dir = f"{trendradar_path}/evolution/designs"
        os.makedirs(self.designs_dir, exist_ok=True)
    
    def load_diagnosis(self) -> Optional[Dict]:
        """加载最新的自我诊断报告"""
        report_file = f"{self.trendradar_path}/evolution/self_diagnosis.json"
        if not os.path.exists(report_file):
            return None
        
        try:
            with open(report_file, 'r') as f:
                reports = json.load(f)
            return reports[-1] if reports else None
        except Exception:
            return None
    
    def analyze_gaps(self, diagnosis: Dict) -> List[Dict]:
        """分析能力缺口，生成设计需求"""
        gaps = []
        
        dimensions = diagnosis.get("dimensions", {})
        
        for dim_name, dim_data in dimensions.items():
            status = dim_data.get("status", "unknown")
            
            if status in ["poor", "acceptable"]:
                # 有改进空间，需要设计新功能
                issues = dim_data.get("issues", [])
                suggestions = dim_data.get("suggestions", [])
                
                # 根据问题内容匹配设计模板
                templates = self.DESIGN_TEMPLATES.get(dim_name, {}).get("templates", [])
                
                for issue in issues:
                    matched = False
                    for template in templates:
                        if self._match_pattern(issue, template["problem_pattern"]):
                            gaps.append({
                                "dimension": dim_name,
                                "issue": issue,
                                "priority": "high" if status == "poor" else "medium",
                                "proposed_feature": template
                            })
                            matched = True
                            break
                    
                    if not matched and templates:
                        # 没有精确匹配，使用第一个模板作为基础
                        gaps.append({
                            "dimension": dim_name,
                            "issue": issue,
                            "priority": "medium",
                            "proposed_feature": templates[0]
                        })
        
        # 按优先级排序
        gaps.sort(key=lambda x: 0 if x["priority"] == "high" else 1)
        
        return gaps
    
    def _match_pattern(self, issue: str, pattern: str) -> bool:
        """匹配问题描述和设计模板"""
        issue_lower = issue.lower()
        pattern_lower = pattern.lower()
        
        # 直接包含
        if pattern_lower in issue_lower:
            return True
        
        # 关键词匹配
        keywords = pattern_lower.split()
        match_count = sum(1 for kw in keywords if kw in issue_lower)
        return match_count >= len(keywords) * 0.5
    
    def generate_design_document(self, gap: Dict, design_id: str) -> Dict:
        """生成详细的功能设计文档"""
        feature = gap["proposed_feature"]
        
        design = {
            "design_id": design_id,
            "timestamp": datetime.now().isoformat(),
            "status": "designed",  # designed → implemented → tested → deployed
            
            # 需求来源
            "origin": {
                "dimension": gap["dimension"],
                "issue": gap["issue"],
                "priority": gap["priority"]
            },
            
            # 功能定义
            "feature": {
                "name": feature["feature_name"],
                "description": feature["description"],
                "category": self.DESIGN_TEMPLATES.get(gap["dimension"], {}).get("category", "通用"),
                "core_logic": feature["core_logic"],
                "input_spec": feature["input"],
                "output_spec": feature["output"],
                "file_name": feature["file_name"]
            },
            
            # 技术规范
            "technical_spec": {
                "language": "Python",
                "dependencies": [],
                "estimated_lines": "50-150",
                "complexity": "medium",
                "api_cost": "free"  # 尽量零API成本
            },
            
            # 实现指南（供Lv28使用）
            "implementation_guide": {
                "class_name": self._generate_class_name(feature["file_name"]),
                "main_method": "process",
                "utility_function": f"get_{feature['file_name'].replace('.py', '')}_insight",
                "error_handling": "try/except with graceful degradation",
                "integration_point": "github.py prompt injection or post-generation pipeline"
            },
            
            # 验收标准
            "acceptance_criteria": [
                "代码能通过Python语法检查",
                "模块能独立运行（有__main__测试）",
                "集成到主流程后不影响现有功能",
                "提供清晰的日志输出"
            ]
        }
        
        return design
    
    def _generate_class_name(self, file_name: str) -> str:
        """根据文件名生成类名"""
        base = file_name.replace('.py', '')
        parts = base.split('_')
        return ''.join(part.capitalize() for part in parts)
    
    def design_new_features(self) -> List[Dict]:
        """主入口：基于诊断报告设计新功能"""
        diagnosis = self.load_diagnosis()
        
        if not diagnosis:
            print("[自主设计] 无法加载诊断报告，跳过功能设计")
            return []
        
        print("[自主设计] 分析能力缺口...")
        gaps = self.analyze_gaps(diagnosis)
        
        if not gaps:
            print("[自主设计] 未发现需要设计的新功能，系统状态良好")
            return []
        
        print(f"[自主设计] 发现 {len(gaps)} 个能力缺口，开始设计新功能...")
        
        designs = []
        for i, gap in enumerate(gaps[:3]):  # 每次最多设计3个
            design_id = f"auto_design_{datetime.now().strftime('%Y%m%d')}_{i+1}"
            design = self.generate_design_document(gap, design_id)
            designs.append(design)
            
            print(f"[自主设计] 设计新功能: {design['feature']['name']}")
            print(f"  - 目标: {design['feature']['description']}")
            print(f"  - 文件: {design['feature']['file_name']}")
            print(f"  - 优先级: {gap['priority']}")
            
            # 保存设计文档
            self._save_design(design)
        
        return designs
    
    def _save_design(self, design: Dict):
        """保存设计文档"""
        file_path = f"{self.designs_dir}/{design['design_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(design, f, ensure_ascii=False, indent=2)
    
    def load_pending_designs(self) -> List[Dict]:
        """加载待实现的设计文档"""
        designs = []
        
        if not os.path.exists(self.designs_dir):
            return designs
        
        for file_name in sorted(os.listdir(self.designs_dir)):
            if not file_name.endswith('.json'):
                continue
            
            file_path = f"{self.designs_dir}/{file_name}"
            try:
                with open(file_path, 'r') as f:
                    design = json.load(f)
                
                if design.get("status") == "designed":
                    designs.append(design)
            except Exception:
                continue
        
        return designs
    
    def generate_design_insight(self) -> str:
        """生成设计洞察（用于Prompt注入）"""
        designs = self.load_pending_designs()
        
        if not designs:
            return ""
        
        lines = ["\n### 🎨 自主功能设计\n"]
        lines.append("**系统正在规划以下新功能**:")
        
        for design in designs:
            feature = design["feature"]
            lines.append(f"- **{feature['name']}**: {feature['description']}")
            lines.append(f"  - 目标: 解决 {design['origin']['issue']}")
            lines.append(f"  - 核心逻辑: {feature['core_logic']}")
        
        lines.append("")
        lines.append("**建议**: 在现有能力基础上，尝试融入以上新维度。\n")
        
        return "\n".join(lines)


# 便捷函数
def run_self_design(trendradar_path: str = ".") -> List[Dict]:
    """运行自主功能设计"""
    designer = SelfDesigner(trendradar_path)
    return designer.design_new_features()


def get_design_insight(trendradar_path: str = ".") -> str:
    """获取设计洞察"""
    designer = SelfDesigner(trendradar_path)
    return designer.generate_design_insight()


if __name__ == "__main__":
    designs = run_self_design()
    if designs:
        print(f"\n已设计 {len(designs)} 个新功能")
        for d in designs:
            print(f"- {d['feature']['name']}")
    else:
        print("\n暂无需要设计的新功能")
