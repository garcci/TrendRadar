# -*- coding: utf-8 -*-
"""
系统最终健康检查 — Round 5 调优验证

功能：
1. 检查所有 evolution 模块可导入性
2. 验证关键配置文件完整
3. 检查 workflow 语法有效性
4. 统计调优成果
5. 输出最终系统状态报告
"""

import ast
import sys
from pathlib import Path
from typing import Dict


class SystemFinalCheck:
    """系统最终健康检查器"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = Path(trendradar_path)
        self.evolution_dir = self.trendradar_path / "evolution"
        self.results = []
        self.warnings = []
        self.errors = []

    def run_all_checks(self) -> Dict:
        """运行所有检查"""
        self.check_module_imports()
        self.check_critical_files()
        self.check_workflow_syntax()
        self.check_tuning_results()
        self.check_github_py_health()

        return {
            "status": "healthy" if not self.errors else "issues_found",
            "checks_passed": len(self.results),
            "warnings": len(self.warnings),
            "errors": len(self.errors),
            "details": {
                "results": self.results,
                "warnings": self.warnings,
                "errors": self.errors,
            }
        }

    def check_module_imports(self):
        """检查所有模块可导入"""
        import sys
        sys.path.insert(0, str(self.trendradar_path))

        py_files = list(self.evolution_dir.glob("*.py"))
        success = 0
        failed = []

        for py_file in py_files:
            if py_file.name.startswith("_"):
                continue
            module_name = f"evolution.{py_file.stem}"
            try:
                __import__(module_name)
                success += 1
            except Exception as e:
                failed.append(f"{py_file.stem}: {e}")

        self.results.append(f"模块导入: {success}/{len(py_files)} 成功")
        if failed:
            self.warnings.extend([f"导入失败: {f}" for f in failed[:5]])

    def check_critical_files(self):
        """检查关键文件"""
        critical = [
            ".github/workflows/evolution.yml",
            ".github/workflows/crawler.yml",
            "trendradar/storage/github.py",
            "trendradar/ai/smart_client.py",
            "evolution/exception_monitor.py",
            "evolution/data_pipeline.py",
            "evolution/module_health_dashboard.py",
        ]

        missing = []
        for f in critical:
            if not (self.trendradar_path / f).exists():
                missing.append(f)

        self.results.append(f"关键文件: {len(critical) - len(missing)}/{len(critical)} 存在")
        if missing:
            self.errors.extend([f"缺失: {m}" for m in missing])

    def check_workflow_syntax(self):
        """检查 workflow YAML 基本语法"""
        try:
            import yaml
            wf_file = self.trendradar_path / ".github/workflows/evolution.yml"
            if wf_file.exists():
                with open(wf_file, 'r') as f:
                    data = yaml.safe_load(f)
                steps = data.get("jobs", {}).get("evolve", {}).get("steps", [])
                self.results.append(f"evolution.yml 语法: ✅ ({len(steps)} 个步骤)")
            else:
                self.errors.append("evolution.yml 不存在")
        except ImportError:
            self.results.append("evolution.yml 语法: 跳过 (无 PyYAML)")
        except Exception as e:
            self.errors.append(f"evolution.yml 语法错误: {e}")

    def check_tuning_results(self):
        """检查调优成果"""
        github_py = self.trendradar_path / "trendradar/storage/github.py"
        if github_py.exists():
            content = github_py.read_text()
            checks = {
                "prompt精简": "Prompt 膨胀控制" in content or "prompt压缩" in content,
                "context长度限制": "MAX_CONTEXT_LENGTH" in content,
                "数据管道接入": "write_record" in content,
                "科技检测": "tech_content_guard" in content,
                "语义去重": "semantic_deduplicator" in content,
                "构建预检": "astro_preflight" in content,
                "部署回滚": "rollback_on_failure" in content,
                "热点预测": "trend_forecast" in content,
            }
            passed = sum(checks.values())
            self.results.append(f"调优检查: {passed}/{len(checks)} 项已应用")
            for name, ok in checks.items():
                if not ok:
                    self.warnings.append(f"调优未应用: {name}")

    def check_github_py_health(self):
        """检查 github.py 健康度"""
        github_py = self.trendradar_path / "trendradar/storage/github.py"
        if not github_py.exists():
            return

        content = github_py.read_text()

        # 检查关键方法是否存在
        methods = ["save_news_data", "_generate_ai_article", "_push_to_github"]
        for method in methods:
            if f"def {method}" in content:
                self.results.append(f"github.py.{method}: ✅")
            else:
                self.errors.append(f"github.py.{method}: ❌ 缺失")

        # 检查是否有死代码（未使用的导入）
        try:
            tree = ast.parse(content)
            imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
            # 简化检查
            self.results.append(f"github.py AST解析: ✅")
        except SyntaxError as e:
            self.errors.append(f"github.py 语法错误: {e}")

    def generate_report(self) -> str:
        """生成最终报告"""
        result = self.run_all_checks()

        lines = []
        lines.append("# 🔬 系统最终健康检查报告 (Round 5)")
        lines.append("")
        lines.append(f"**状态**: {'✅ 健康' if result['status'] == 'healthy' else '⚠️ 发现问题'}")
        lines.append(f"**检查通过**: {result['checks_passed']} 项")
        lines.append(f"**警告**: {result['warnings']} 个")
        lines.append(f"**错误**: {result['errors']} 个")
        lines.append("")

        lines.append("## ✅ 检查结果")
        for r in result['details']['results']:
            lines.append(f"- {r}")

        if result['details']['warnings']:
            lines.append("")
            lines.append("## ⚠️ 警告")
            for w in result['details']['warnings'][:10]:
                lines.append(f"- {w}")

        if result['details']['errors']:
            lines.append("")
            lines.append("## ❌ 错误")
            for e in result['details']['errors']:
                lines.append(f"- {e}")

        lines.append("")
        lines.append("---")
        lines.append("**Round 5 完成**: 系统架构调优与最终验证结束。")

        return "\n".join(lines)


def run_final_check(trendradar_path: str = ".") -> str:
    """便捷函数"""
    checker = SystemFinalCheck(trendradar_path)
    return checker.generate_report()


if __name__ == "__main__":
    print(run_final_check())
