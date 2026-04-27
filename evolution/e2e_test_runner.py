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


def run_free_ai_router_tests() -> Dict:
    """运行免费 AI 路由端到端测试"""
    from e2e.test_free_ai_router import TestFreeAIRouter

    tester = TestFreeAIRouter()
    return tester.run_all()


def run_tag_optimizer_tests() -> Dict:
    """运行标签优化端到端测试"""
    from e2e.test_tag_optimizer import TestTagOptimizer

    tester = TestTagOptimizer()
    return tester.run_all()


def run_trend_forecast_tests() -> Dict:
    """运行热点预测端到端测试"""
    from e2e.test_trend_forecast import TestTrendForecast

    tester = TestTrendForecast()
    return tester.run_all()


def run_semantic_deduplicator_tests() -> Dict:
    """运行语义去重端到端测试"""
    from e2e.test_semantic_deduplicator import TestSemanticDeduplicator

    tester = TestSemanticDeduplicator()
    return tester.run_all()


def run_auto_calibration_tests() -> Dict:
    """运行自动校准端到端测试"""
    from e2e.test_auto_calibration import TestAutoCalibration

    tester = TestAutoCalibration()
    return tester.run_all()


def run_self_observer_tests() -> Dict:
    """运行自我观察端到端测试"""
    from e2e.test_self_observer import TestSelfObserver

    tester = TestSelfObserver()
    return tester.run_all()


def run_smart_summary_tests() -> Dict:
    """运行智能摘要端到端测试"""
    from e2e.test_smart_summary import TestSmartSummary

    tester = TestSmartSummary()
    return tester.run_all()


def run_title_optimizer_tests() -> Dict:
    """运行标题优化端到端测试"""
    from e2e.test_title_optimizer import TestTitleOptimizer

    tester = TestTitleOptimizer()
    return tester.run_all()


def run_regression_guard_tests() -> Dict:
    """运行退化检测端到端测试"""
    from e2e.test_regression_guard import TestRegressionGuard

    tester = TestRegressionGuard()
    return tester.run_all()


def run_output_quality_validator_tests() -> Dict:
    """运行输出质量验证端到端测试"""
    from e2e.test_output_quality_validator import TestOutputQualityValidator

    tester = TestOutputQualityValidator()
    return tester.run_all()


def run_frontmatter_validator_tests() -> Dict:
    """运行 frontmatter 预验证端到端测试"""
    from e2e.test_frontmatter_validator import TestFrontmatterValidator

    tester = TestFrontmatterValidator()
    return tester.run_all()


def run_health_check_tests() -> Dict:
    """运行系统健康检查端到端测试"""
    from e2e.test_health_check import TestHealthCheck

    tester = TestHealthCheck()
    return tester.run_all()


def run_article_quality_db_tests() -> Dict:
    """运行文章质量数据库端到端测试"""
    from e2e.test_article_quality_db import TestArticleQualityDB

    tester = TestArticleQualityDB()
    return tester.run_all()


def run_diversity_engine_tests() -> Dict:
    """运行文章多样化引擎端到端测试"""
    from e2e.test_diversity_engine import TestDiversityEngine

    tester = TestDiversityEngine()
    return tester.run_all()


def run_knowledge_graph_tests() -> Dict:
    """运行知识图谱端到端测试"""
    from e2e.test_knowledge_graph import TestKnowledgeGraph

    tester = TestKnowledgeGraph()
    return tester.run_all()


def run_cleanup_manager_tests() -> Dict:
    """运行清理管理器端到端测试"""
    from e2e.test_cleanup_manager import TestCleanupManager

    tester = TestCleanupManager()
    return tester.run_all()


def run_emotion_analyzer_tests() -> Dict:
    """运行情感分析端到端测试"""
    from e2e.test_emotion_analyzer import TestEmotionAnalyzer

    tester = TestEmotionAnalyzer()
    return tester.run_all()


def run_unified_logger_tests() -> Dict:
    """运行统一日志端到端测试"""
    from e2e.test_unified_logger import TestUnifiedLogger

    tester = TestUnifiedLogger()
    return tester.run_all()


def run_module_value_assessor_tests() -> Dict:
    """运行模块价值评估端到端测试"""
    from e2e.test_module_value_assessor import TestModuleValueAssessor

    tester = TestModuleValueAssessor()
    return tester.run_all()


def run_data_archiver_tests() -> Dict:
    """运行数据归档端到端测试"""
    from e2e.test_data_archiver import TestDataArchiver

    tester = TestDataArchiver()
    return tester.run_all()


def run_reader_behavior_analyzer_tests() -> Dict:
    """运行读者行为分析端到端测试"""
    from e2e.test_reader_behavior_analyzer import TestReaderBehaviorAnalyzer

    tester = TestReaderBehaviorAnalyzer()
    return tester.run_all()


def run_ab_testing_tests() -> Dict:
    """运行 A/B 测试端到端测试"""
    from e2e.test_ab_testing import TestABTesting

    tester = TestABTesting()
    return tester.run_all()


def run_prompt_optimizer_tests() -> Dict:
    """运行 Prompt 优化器端到端测试"""
    from e2e.test_prompt_optimizer import TestPromptOptimizer

    tester = TestPromptOptimizer()
    return tester.run_all()


def run_prompt_tracker_tests() -> Dict:
    """运行 Prompt 追踪器端到端测试"""
    from e2e.test_prompt_tracker import TestPromptTracker

    tester = TestPromptTracker()
    return tester.run_all()


def run_smart_scheduler_tests() -> Dict:
    """运行智能调度器端到端测试"""
    from e2e.test_smart_scheduler import TestSmartScheduler

    tester = TestSmartScheduler()
    return tester.run_all()


def run_trend_predictor_tests() -> Dict:
    """运行热点预测端到端测试"""
    from e2e.test_trend_predictor import TestTrendPredictor

    tester = TestTrendPredictor()
    return tester.run_all()


def run_quota_monitor_tests() -> Dict:
    """运行额度监控端到端测试"""
    from e2e.test_quota_monitor import TestQuotaMonitor

    tester = TestQuotaMonitor()
    return tester.run_all()


def run_dynamic_scheduler_tests() -> Dict:
    """运行动态调度器端到端测试"""
    from e2e.test_dynamic_scheduler import TestDynamicScheduler

    tester = TestDynamicScheduler()
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
        ("free_ai_router", run_free_ai_router_tests),
        ("tag_optimizer", run_tag_optimizer_tests),
        ("trend_forecast", run_trend_forecast_tests),
        ("semantic_deduplicator", run_semantic_deduplicator_tests),
        ("auto_calibration", run_auto_calibration_tests),
        ("self_observer", run_self_observer_tests),
        ("smart_summary", run_smart_summary_tests),
        ("title_optimizer", run_title_optimizer_tests),
        ("regression_guard", run_regression_guard_tests),
        ("output_quality_validator", run_output_quality_validator_tests),
        ("frontmatter_validator", run_frontmatter_validator_tests),
        ("health_check", run_health_check_tests),
        ("article_quality_db", run_article_quality_db_tests),
        ("diversity_engine", run_diversity_engine_tests),
        ("knowledge_graph", run_knowledge_graph_tests),
        ("cleanup_manager", run_cleanup_manager_tests),
        ("emotion_analyzer", run_emotion_analyzer_tests),
        ("unified_logger", run_unified_logger_tests),
        ("module_value_assessor", run_module_value_assessor_tests),
        ("data_archiver", run_data_archiver_tests),
        ("reader_behavior_analyzer", run_reader_behavior_analyzer_tests),
        ("ab_testing", run_ab_testing_tests),
        ("prompt_optimizer", run_prompt_optimizer_tests),
        ("prompt_tracker", run_prompt_tracker_tests),
        ("smart_scheduler", run_smart_scheduler_tests),
        ("trend_predictor", run_trend_predictor_tests),
        ("quota_monitor", run_quota_monitor_tests),
        ("dynamic_scheduler", run_dynamic_scheduler_tests),
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
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(run_suite, s): s[0] for s in suites}
        for future in as_completed(futures):
            result = future.result()
            all_results.append(result)
            total_passed += result.get("passed", 0)
            failed_val = result.get("failed", 0)
            if isinstance(failed_val, list):
                total_failed += len(failed_val)
            else:
                total_failed += failed_val
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
            # 兼容两种格式: {"test":..., "passed":..., "message":...} 和 {"name":..., "status": "PASS"|"FAIL", "error":...}
            if "test" in r:
                test_name = r["test"]
                passed = r["passed"]
                message = r.get("message", "")
            else:
                test_name = r.get("name", "unknown")
                passed = r.get("status") == "PASS"
                message = r.get("error", "") if not passed else "通过"
            emoji = "✅" if passed else "❌"
            lines.append(f"- {emoji} **{test_name}**: {message}")
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
