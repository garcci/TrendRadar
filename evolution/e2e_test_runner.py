# -*- coding: utf-8 -*-
"""
端到端测试运行器 (E2E Test Runner)

Lv29+ 增强：自主测试验证的端到端维度
- 运行所有 e2e/ 目录下的测试
- 生成测试报告
- 集成到 system_final_check 和 evolution Workflow

与 self_tester.py 的区别：
- self_tester: 代码结构检查（语法、导入、方法存在性）
- e2e_test_runner: 功能正确性验证（数据读写一致性、逻辑参数正确性）
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def run_memory_tests() -> Dict:
    """运行记忆系统端到端测试"""
    from e2e.test_memory_backend import TestMemoryBackendConsistency

    tester = TestMemoryBackendConsistency()
    return tester.run_all()


def run_frontmatter_tests() -> Dict:
    """运行 frontmatter 端到端测试"""
    from e2e.test_frontmatter_pipeline import TestFrontmatterPipeline

    tester = TestFrontmatterPipeline()
    return tester.run_all()


def run_data_pipeline_tests() -> Dict:
    """运行数据管道端到端测试"""
    from e2e.test_data_pipeline import TestDataPipelineConsistency

    tester = TestDataPipelineConsistency()
    return tester.run_all()


def run_github_pipeline_tests() -> Dict:
    """运行 github.py 端到端测试"""
    from e2e.test_github_pipeline import TestGitHubPipeline

    tester = TestGitHubPipeline()
    return tester.run_all()


def run_exception_monitor_tests() -> Dict:
    """运行异常监控端到端测试"""
    from e2e.test_exception_monitor import TestExceptionMonitorConsistency

    tester = TestExceptionMonitorConsistency()
    return tester.run_all()


def run_model_router_tests() -> Dict:
    """运行模型路由端到端测试"""
    from e2e.test_model_router import TestModelRouter

    tester = TestModelRouter()
    return tester.run_all()


def run_tech_content_guard_tests() -> Dict:
    """运行科技内容检测端到端测试"""
    from e2e.test_tech_content_guard import TestTechContentGuard

    tester = TestTechContentGuard()
    return tester.run_all()


def run_all_e2e_tests(trendradar_path: str = ".") -> Dict:
    """运行所有端到端测试"""
    e2e_dir = Path(trendradar_path) / "evolution" / "e2e"
    if not e2e_dir.exists():
        return {"all_passed": False, "error": "e2e 目录不存在"}

    all_results = []
    total_passed = 0
    total_failed = 0

    suites = [
        ("memory_backend", run_memory_tests),
        ("frontmatter_pipeline", run_frontmatter_tests),
        ("data_pipeline", run_data_pipeline_tests),
        ("github_pipeline", run_github_pipeline_tests),
        ("exception_monitor", run_exception_monitor_tests),
        ("model_router", run_model_router_tests),
        ("tech_content_guard", run_tech_content_guard_tests),
    ]

    for suite_name, suite_func in suites:
        try:
            result = suite_func()
            all_results.append({"suite": suite_name, **result})
            total_passed += result["passed"]
            total_failed += result["failed"]
        except Exception as e:
            all_results.append({"suite": suite_name, "all_passed": False, "error": str(e)})
            total_failed += 1

    return {
        "all_passed": total_failed == 0,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "suites": all_results,
        "timestamp": datetime.now().isoformat()
    }


def generate_report(results: Dict) -> str:
    """生成测试报告"""
    lines = []
    lines.append("# 🔬 端到端测试报告")
    lines.append("")

    if results.get("all_passed"):
        lines.append("**状态**: ✅ 全部通过")
    else:
        lines.append("**状态**: ❌ 存在失败")

    lines.append(f"**通过**: {results.get('total_passed', 0)} 项")
    lines.append(f"**失败**: {results.get('total_failed', 0)} 项")
    lines.append("")

    for suite in results.get("suites", []):
        lines.append(f"## {suite['suite']}")
        for r in suite.get("results", []):
            emoji = "✅" if r["passed"] else "❌"
            lines.append(f"- {emoji} **{r['test']}**: {r['message']}")
        lines.append("")

    return "\n".join(lines)


def main():
    """主入口"""
    trendradar_path = sys.argv[1] if len(sys.argv) > 1 else "."
    results = run_all_e2e_tests(trendradar_path)

    report = generate_report(results)
    print(report)

    # 保存报告
    report_path = Path(trendradar_path) / "evolution" / "e2e_report.md"
    report_path.write_text(report)
    print(f"\n报告已保存: {report_path}")

    sys.exit(0 if results["all_passed"] else 1)


if __name__ == "__main__":
    main()
