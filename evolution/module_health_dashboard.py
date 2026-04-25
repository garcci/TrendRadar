# -*- coding: utf-8 -*-
"""
模块健康度仪表盘 — 自动扫描进化系统模块状态

功能：
1. 扫描 evolution/ 目录下所有 Python 模块
2. 检查哪些模块被 evolution.yml 调用
3. 检查哪些模块被 github.py（核心流程）调用
4. 标记闲置模块和集成盲区
5. 生成可视化健康报告
"""

import ast
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class ModuleStatus:
    """模块状态"""
    name: str
    filepath: str
    has_main: bool
    has_entry_function: bool
    evolution_yml_called: bool = False
    github_py_called: bool = False
    crawler_yml_called: bool = False
    status: str = "unknown"  # active, idle, orphaned, broken
    lines_of_code: int = 0
    last_modified: str = ""


class ModuleHealthDashboard:
    """模块健康度仪表盘"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = Path(trendradar_path)
        self.evolution_dir = self.trendradar_path / "evolution"
        self.modules: List[ModuleStatus] = []

    def scan_all_modules(self) -> List[ModuleStatus]:
        """扫描所有进化模块"""
        if not self.evolution_dir.exists():
            return []

        # 1. 扫描 evolution/ 下的 .py 文件
        py_files = sorted(self.evolution_dir.glob("*.py"))

        for py_file in py_files:
            if py_file.name.startswith("_"):
                continue

            status = self._analyze_module(py_file)
            self.modules.append(status)

        # 2. 检查 workflow 调用情况
        self._check_workflow_integration()

        # 3. 检查核心流程调用情况
        self._check_core_integration()

        # 4. 标记状态
        for m in self.modules:
            if m.github_py_called or m.evolution_yml_called or m.crawler_yml_called:
                m.status = "active"
            elif m.has_main or m.has_entry_function:
                m.status = "idle"  # 有入口但未被调用
            else:
                m.status = "orphaned"  # 无入口且无调用

        return self.modules

    def _analyze_module(self, py_file: Path) -> ModuleStatus:
        """分析单个模块"""
        content = py_file.read_text(encoding="utf-8")

        # 检查是否有 if __name__ == "__main__"
        has_main = 'if __name__ == "__main__"' in content or "if __name__ == '__main__'" in content

        # 检查是否有便捷函数（模块级入口函数）
        has_entry = bool(re.search(r'^def (get_|run_|check_|verify_|generate_|show_)', content, re.MULTILINE))

        # 代码行数
        lines = len(content.splitlines())

        # 最后修改时间
        try:
            mtime = datetime.fromtimestamp(py_file.stat().st_mtime).strftime("%Y-%m-%d")
        except Exception:
            mtime = ""

        return ModuleStatus(
            name=py_file.stem,
            filepath=str(py_file.relative_to(self.trendradar_path)),
            has_main=has_main,
            has_entry_function=has_entry,
            lines_of_code=lines,
            last_modified=mtime,
        )

    def _check_workflow_integration(self):
        """检查 evolution.yml 和 crawler.yml 中的调用"""
        workflow_files = [
            self.trendradar_path / ".github" / "workflows" / "evolution.yml",
            self.trendradar_path / ".github" / "workflows" / "crawler.yml",
        ]

        for wf_file in workflow_files:
            if not wf_file.exists():
                continue

            content = wf_file.read_text(encoding="utf-8")
            is_crawler = "crawler" in wf_file.name

            for m in self.modules:
                # 匹配 from evolution.xxx import 或 import evolution.xxx
                patterns = [
                    rf'from evolution\.({m.name})\b',
                    rf'import evolution\.({m.name})\b',
                    rf'from evolution import .*\b{m.name}\b',
                ]
                for pattern in patterns:
                    if re.search(pattern, content):
                        if is_crawler:
                            m.crawler_yml_called = True
                        else:
                            m.evolution_yml_called = True
                        break

    def _check_core_integration(self):
        """检查 github.py 等核心文件中的调用"""
        core_files = [
            self.trendradar_path / "trendradar" / "storage" / "github.py",
            self.trendradar_path / "trendradar" / "__main__.py",
            self.trendradar_path / "trendradar" / "ai" / "smart_client.py",
        ]

        for core_file in core_files:
            if not core_file.exists():
                continue

            content = core_file.read_text(encoding="utf-8")

            for m in self.modules:
                patterns = [
                    rf'from evolution\.({m.name})\b',
                    rf'import evolution\.({m.name})\b',
                    rf'from evolution import .*\b{m.name}\b',
                ]
                for pattern in patterns:
                    if re.search(pattern, content):
                        m.github_py_called = True
                        break

    def generate_report(self) -> str:
        """生成健康度报告"""
        if not self.modules:
            self.scan_all_modules()

        active = [m for m in self.modules if m.status == "active"]
        idle = [m for m in self.modules if m.status == "idle"]
        orphaned = [m for m in self.modules if m.status == "orphaned"]

        lines = []
        lines.append("# 📊 TrendRadar 进化系统模块健康度仪表盘")
        lines.append(f"\n**扫描时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**模块总数**: {len(self.modules)}")
        lines.append(f"**✅ 活跃模块**: {len(active)} | **⏸️ 闲置模块**: {len(idle)} | **🚫 孤儿模块**: {len(orphaned)}")
        lines.append("")

        # 活跃模块
        if active:
            lines.append("## ✅ 活跃模块（已被集成）")
            for m in sorted(active, key=lambda x: x.name):
                integrations = []
                if m.github_py_called:
                    integrations.append("核心流程")
                if m.evolution_yml_called:
                    integrations.append("evolution.yml")
                if m.crawler_yml_called:
                    integrations.append("crawler.yml")
                lines.append(f"- **{m.name}** ({m.lines_of_code}行) — 集成到: {', '.join(integrations)}")
            lines.append("")

        # 闲置模块
        if idle:
            lines.append("## ⏸️ 闲置模块（有功能但未被调用）")
            lines.append("> 建议：评估是否集成到 workflow 或核心流程中")
            for m in sorted(idle, key=lambda x: x.name):
                entry = "🚀 有入口函数" if m.has_entry_function else "📦 仅main块"
                lines.append(f"- **{m.name}** ({m.lines_of_code}行) — {entry}")
            lines.append("")

        # 孤儿模块
        if orphaned:
            lines.append("## 🚫 孤儿模块（无入口且无调用）")
            lines.append("> 建议：检查是否为内部依赖模块，或考虑归档")
            for m in sorted(orphaned, key=lambda x: x.name):
                lines.append(f"- **{m.name}** ({m.lines_of_code}行)")
            lines.append("")

        # 集成建议
        lines.append("## 🎯 自动优化建议")
        if idle:
            idle_names = [m.name for m in idle]
            lines.append(f"1. 将闲置模块集成到 evolution.yml: {', '.join(idle_names[:5])}")
        if len(active) < 10:
            lines.append("2. 活跃模块数量较少，建议增加自动化集成覆盖")
        lines.append(f"3. 系统代码总量: {sum(m.lines_of_code for m in self.modules)} 行")
        lines.append("")

        return "\n".join(lines)

    def export_json(self) -> Dict:
        """导出 JSON 格式数据"""
        if not self.modules:
            self.scan_all_modules()

        return {
            "timestamp": datetime.now().isoformat(),
            "total_modules": len(self.modules),
            "active": [m.__dict__ for m in self.modules if m.status == "active"],
            "idle": [m.__dict__ for m in self.modules if m.status == "idle"],
            "orphaned": [m.__dict__ for m in self.modules if m.status == "orphaned"],
        }


def generate_health_dashboard(trendradar_path: str = ".") -> str:
    """便捷函数：生成健康度仪表盘报告"""
    dashboard = ModuleHealthDashboard(trendradar_path)
    return dashboard.generate_report()


def export_dashboard_json(trendradar_path: str = ".") -> Dict:
    """便捷函数：导出 JSON 数据"""
    dashboard = ModuleHealthDashboard(trendradar_path)
    return dashboard.export_json()


if __name__ == "__main__":
    print(generate_health_dashboard())
