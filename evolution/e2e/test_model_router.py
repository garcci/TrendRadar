# -*- coding: utf-8 -*-
"""
模型路由端到端测试

测试场景：
1. 不同任务类型路由到正确模型
2. 降级链配置正确
3. 成本估算准确
4. 使用记录可写入和读取

历史教训：
- 曾出现所有任务都用同一个模型，浪费成本
- 曾出现降级链为空时无法容错
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.model_router import ModelRouter, TaskType


class TestModelRouter:
    """模型路由端到端测试"""

    def __init__(self):
        self.test_results = []
        self.router = ModelRouter(trendradar_path="/tmp/test_model_router")

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_article_generation_route(self):
        """测试1: 文章生成 → 选择最高质量模型"""
        decision = self.router.route(
            TaskType.ARTICLE_GENERATION,
            estimated_input_tokens=3000,
            estimated_output_tokens=2000
        )
        if "reasoner" in decision.selected_model:
            self._log("文章生成路由", True, f"选择推理模型: {decision.selected_model}")
        else:
            self._log("文章生成路由", False, f"应选推理模型，实际: {decision.selected_model}")

    def test_rss_analysis_route(self):
        """测试2: RSS分析 → 选择轻量模型"""
        decision = self.router.route(
            TaskType.RSS_ANALYSIS,
            estimated_input_tokens=500,
            estimated_output_tokens=200
        )
        if "chat" in decision.selected_model and "reasoner" not in decision.selected_model:
            self._log("RSS分析路由", True, f"选择轻量模型: {decision.selected_model}")
        else:
            self._log("RSS分析路由", False, f"应选轻量模型，实际: {decision.selected_model}")

    def test_fallback_chain(self):
        """测试3: 降级链不为空"""
        decision = self.router.route(TaskType.ARTICLE_GENERATION)
        if len(decision.fallback_models) > 0:
            self._log("降级链配置", True, f"降级模型: {decision.fallback_models}")
        else:
            self._log("降级链配置", False, "文章生成降级链为空")

    def test_cost_estimation(self):
        """测试4: 成本估算合理"""
        decision = self.router.route(
            TaskType.ARTICLE_GENERATION,
            estimated_input_tokens=1_000_000,
            estimated_output_tokens=500_000
        )
        # reasoner: 输入¥4, 输出¥16 → 1M输入=4元, 0.5M输出=8元 → 总计约12元
        if decision.estimated_cost > 0:
            self._log("成本估算", True, f"预估成本: ¥{decision.estimated_cost:.2f}")
        else:
            self._log("成本估算", False, "成本估算为0")

    def test_translation_lightweight(self):
        """测试5: 翻译任务用轻量模型"""
        decision = self.router.route(TaskType.TRANSLATION)
        config = self.router.models.get(decision.selected_model)
        if config and config.input_price <= 2.0:
            self._log("翻译任务成本", True, f"选择低价模型: {decision.selected_model} (¥{config.input_price}/M)")
        else:
            self._log("翻译任务成本", False, f"翻译任务模型过贵: {decision.selected_model}")

    def test_record_and_report(self):
        """测试6: 记录使用并生成报告"""
        self.router.record_usage(
            task_type=TaskType.RSS_ANALYSIS,
            model="deepseek/deepseek-chat",
            input_tokens=1000,
            output_tokens=500,
            latency=1.5,
            success=True
        )
        report = self.router.get_cost_report(days=1)
        if report and "total_cost" in report:
            self._log("使用记录报告", True, f"成本报告生成成功，总成本: ¥{report.get('total_cost', 0):.4f}")
        else:
            self._log("使用记录报告", False, "成本报告生成失败")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("模型路由端到端测试")
        print("=" * 60)

        self.test_article_generation_route()
        self.test_rss_analysis_route()
        self.test_fallback_chain()
        self.test_cost_estimation()
        self.test_translation_lightweight()
        self.test_record_and_report()

        passed = sum(1 for r in self.test_results if r["passed"])
        failed = sum(1 for r in self.test_results if not r["passed"])

        print()
        for r in self.test_results:
            emoji = "✅" if r["passed"] else "❌"
            print(f"{emoji} {r['test']}: {r['message']}")

        print()
        print(f"总计: {passed}/{len(self.test_results)} 通过, {failed} 失败")
        print("=" * 60)

        return {
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": self.test_results
        }


if __name__ == "__main__":
    tester = TestModelRouter()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
