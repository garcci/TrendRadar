# -*- coding: utf-8 -*-
"""
闲置模块价值评估器 — 分析未集成模块的优先级

功能：
1. 读取 module_health_dashboard 的闲置模块列表
2. 基于代码复杂度、功能独特性、集成难度打分
3. 给出集成优先级排序和具体建议
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List


class ModuleValueAssessor:
    """模块价值评估器"""

    # 功能价值权重表
    VALUE_FACTORS = {
        "quality": {
            "keywords": ["quality", "score", "评估", "评分", "metrics"],
            "weight": 1.5,
            "description": "内容质量评估",
        },
        "cost": {
            "keywords": ["cost", "quota", "额度", "成本", "budget", "free"],
            "weight": 1.4,
            "description": "成本与额度优化",
        },
        "seo": {
            "keywords": ["seo", "search", "rank", "标题", "tag", "关键词"],
            "weight": 1.3,
            "description": "SEO与可见性优化",
        },
        "security": {
            "keywords": ["security", "vuln", "漏洞", "安全", "隐私"],
            "weight": 1.2,
            "description": "安全与隐私",
        },
        "automation": {
            "keywords": ["auto", "自动", "schedule", "调度", "predict"],
            "weight": 1.1,
            "description": "自动化与预测",
        },
    }

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = Path(trendradar_path)
        self.evolution_dir = self.trendradar_path / "evolution"

    def assess_idle_modules(self) -> List[Dict]:
        """评估所有闲置模块的价值"""
        import sys
        sys.path.insert(0, str(self.trendradar_path))
        from evolution.module_health_dashboard import ModuleHealthDashboard

        dashboard = ModuleHealthDashboard(str(self.trendradar_path))
        dashboard.scan_all_modules()
        idle_modules = [m for m in dashboard.modules if m.status == "idle"]

        results = []
        for module in idle_modules:
            score, details = self._assess_module(module)
            results.append({
                "name": module.name,
                "lines": module.lines_of_code,
                "value_score": score,
                "details": details,
                "recommendation": self._get_recommendation(module.name, score),
            })

        # 按价值分排序
        results.sort(key=lambda x: x["value_score"], reverse=True)
        return results

    def _assess_module(self, module) -> tuple:
        """评估单个模块"""
        py_file = self.evolution_dir / f"{module.name}.py"
        if not py_file.exists():
            return 0, {}

        content = py_file.read_text(encoding="utf-8")
        details = {}

        # 1. 代码复杂度分（0-20）
        complexity = self._calculate_complexity(content)
        details["complexity_score"] = complexity

        # 2. 功能独特价值分（0-40）
        functional_value = self._calculate_functional_value(content)
        details["functional_score"] = functional_value

        # 3. 集成难度分（0-20）
        integration_difficulty = self._calculate_integration_difficulty(content)
        details["integration_score"] = 20 - integration_difficulty  # 难度越低分越高

        # 4. 维护成熟度分（0-20）
        maturity = self._calculate_maturity(content, module)
        details["maturity_score"] = maturity

        total = complexity + functional_value + (20 - integration_difficulty) + maturity
        return total, details

    def _calculate_complexity(self, content: str) -> int:
        """计算代码复杂度分（0-20）"""
        score = 0
        lines = content.splitlines()

        # 代码行数适中（100-500行最佳）
        if 100 <= len(lines) <= 500:
            score += 8
        elif len(lines) > 500:
            score += 5
        else:
            score += 3

        # 类数量
        class_count = len(re.findall(r'^class ', content, re.MULTILINE))
        if 1 <= class_count <= 3:
            score += 6
        elif class_count > 3:
            score += 4
        else:
            score += 2

        # 函数数量
        func_count = len(re.findall(r'^def ', content, re.MULTILINE))
        if 3 <= func_count <= 15:
            score += 6
        elif func_count > 15:
            score += 4
        else:
            score += 2

        return min(score, 20)

    def _calculate_functional_value(self, content: str) -> int:
        """计算功能独特价值分（0-40）"""
        score = 0
        content_lower = content.lower()

        for factor_name, factor in self.VALUE_FACTORS.items():
            matched = sum(1 for kw in factor["keywords"] if kw.lower() in content_lower)
            if matched > 0:
                score += int(8 * factor["weight"])

        # 检查是否有实际可运行的代码（而非纯框架）
        if 'return' in content_lower and len(content) > 1000:
            score += 5

        # 检查是否有异常处理
        if 'try:' in content_lower and 'except' in content_lower:
            score += 3

        return min(score, 40)

    def _calculate_integration_difficulty(self, content: str) -> int:
        """计算集成难度分（0-20，越高越难）"""
        difficulty = 0

        # 依赖外部API
        if re.search(r'(requests|urllib|httpx)', content):
            difficulty += 3

        # 依赖文件系统操作
        if re.search(r'(open\(|os\.path|shutil)', content):
            difficulty += 2

        # 依赖数据库
        if re.search(r'(sqlite|d1|kv|database)', content, re.IGNORECASE):
            difficulty += 4

        # 需要复杂配置
        if 'config' in content.lower() or 'env' in content.lower():
            difficulty += 2

        # 是否有清晰的入口函数
        if re.search(r'^def (run_|get_|check_|generate_)', content, re.MULTILINE):
            difficulty -= 3

        # 是否有 __main__ 块
        if '__main__' in content:
            difficulty -= 2

        return max(0, min(difficulty, 20))

    def _calculate_maturity(self, content: str, module) -> int:
        """计算维护成熟度分（0-20）"""
        score = 0

        # 文档字符串覆盖率
        docstrings = len(re.findall(r'""".*?"""', content, re.DOTALL))
        if docstrings >= 2:
            score += 6
        elif docstrings >= 1:
            score += 3

        # 类型注解
        if ':' in content and '->' in content:
            score += 4

        # 异常处理
        if 'try:' in content and 'except' in content:
            score += 4

        # 代码注释
        comment_lines = len([l for l in content.splitlines() if l.strip().startswith('#')])
        if comment_lines >= 5:
            score += 3
        elif comment_lines >= 1:
            score += 1

        # 最近是否修改过
        if module.last_modified:
            score += 3

        return min(score, 20)

    def _get_recommendation(self, name: str, score: int) -> str:
        """根据分数给出集成建议"""
        if score >= 70:
            return "🔥 高价值模块，建议立即集成到核心流程"
        elif score >= 55:
            return "⭐ 中高价值，建议优先集成到 evolution.yml"
        elif score >= 40:
            return "📌 中等价值，可评估后选择性集成"
        else:
            return "💤 价值有限，建议观察或归档"

    def generate_report(self) -> str:
        """生成评估报告"""
        results = self.assess_idle_modules()

        lines = []
        lines.append("# 📊 闲置模块价值评估报告")
        lines.append(f"\n评估模块数: {len(results)}")
        lines.append("")

        for i, r in enumerate(results, 1):
            lines.append(f"## {i}. {r['name']} (总分: {r['value_score']}/100)")
            lines.append(f"- 代码行数: {r['lines']} 行")
            lines.append(f"- 复杂度: {r['details'].get('complexity_score', 0)}/20")
            lines.append(f"- 功能价值: {r['details'].get('functional_score', 0)}/40")
            lines.append(f"- 集成友好度: {r['details'].get('integration_score', 0)}/20")
            lines.append(f"- 成熟度: {r['details'].get('maturity_score', 0)}/20")
            lines.append(f"- **建议**: {r['recommendation']}")
            lines.append("")

        # 汇总
        high_value = [r for r in results if r["value_score"] >= 70]
        lines.append("## 汇总")
        lines.append(f"🔥 高价值模块（≥70分）: {len(high_value)} 个")
        if high_value:
            lines.append(f"  优先集成: {', '.join(r['name'] for r in high_value)}")

        return "\n".join(lines)


def assess_idle_modules(trendradar_path: str = ".") -> str:
    """便捷函数"""
    assessor = ModuleValueAssessor(trendradar_path)
    return assessor.generate_report()


if __name__ == "__main__":
    print(assess_idle_modules())
