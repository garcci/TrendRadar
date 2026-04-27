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

# 性能优化：阻止 litellm 远程请求模型价格映射（节省 ~4s 导入时间）
import os
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    """运行所有端到端测试（并行执行优化耗时）"""
    e2e_dir = Path(trendradar_path) / "evolution" / "e2e"
    if not e2e_dir.exists():
        return {"all_passed": False, "error": "e2e 目录不存在"}

    suites = [
        ("memory_backend", run_memory_tests),
        ("frontmatter_pipeline", run_frontmatter_tests),
        ("data_pipeline", run_data_pipeline_tests),
        ("github_pipeline", run_github_pipeline_tests),
        ("exception_monitor", run_exception_monitor_tests),
        ("model_router", run_model_router_tests),
        ("tech_content_guard", run_tech_content_guard_tests),
    ]

    all_results = []
    total_passed = 0
    total_failed = 0

    def run_suite(name_func):
        name, func = name_func
        start = time.time()
        try:
            result = func()
            elapsed = time.time() - start
            return {"suite": name, **result, "elapsed": round(elapsed, 2)}
        except Exception as e:
            elapsed = time.time() - start
            return {"suite": name, "all_passed": False, "error": str(e), "elapsed": round(elapsed, 2)}

    # 并行运行（I/O 密集型，线程有效）
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_suite, s): s[0] for s in suites}
        for future in as_completed(futures):
            result = future.result()
            all_results.append(result)
            total_passed += result.get("passed", 0)
            total_failed += result.get("failed", 0)
            if "error" in result and "passed" not in result:
                total_failed += 1

    # 按原始顺序排序
    suite_order = {s[0]: i for i, s in enumerate(suites)}
    all_results.sort(key=lambda x: suite_order.get(x["suite"], 99))

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
        elapsed = suite.get('elapsed', '?')
        lines.append(f"## {suite['suite']} ({elapsed}s)")
        if "error" in suite and "results" not in suite:
            lines.append(f"- ❌ **执行错误**: {suite['error']}")
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
