# -*- coding: utf-8 -*-
"""
免费 AI 路由端到端测试

测试场景：
1. 轻量任务 → 选择免费 Provider
2. 高质量要求 → 选择 DeepSeek
3. 免费额度耗尽 → 降级到 DeepSeek
4. 额度状态查询正确
5. 使用记录与成本报告

历史教训：
- 曾出现免费额度耗尽后仍尝试使用免费 API 导致失败
- 曾出现成本统计遗漏免费额度使用
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.free_ai_router import FreeAIRouter, ProviderType


class TestFreeAIRouter:
    """免费 AI 路由端到端测试"""

    def __init__(self):
        self.test_results = []
        self.router = FreeAIRouter(trendradar_path="/tmp/test_free_ai")

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_light_task_selects_free_provider(self):
        """测试1: 轻量任务选择免费 Provider"""
        result = self.router.select_provider("summarization", estimated_tokens=500)
        if result["cost"] == 0.0:
            self._log("轻量任务免费", True, f"选择 {result['name']}，成本 ¥0")
        else:
            self._log("轻量任务免费", False, f"轻量任务不应付费: {result['reason']}")

    def test_high_quality_selects_deepseek(self):
        """测试2: 高质量要求选择 DeepSeek"""
        result = self.router.select_provider("article_generation", estimated_tokens=2000, require_high_quality=True)
        if result["provider"] == "deepseek":
            self._log("高质量兜底", True, f"高质量任务选择 {result['name']}")
        else:
            self._log("高质量兜底", False, f"应选 DeepSeek，实际: {result['provider']}")

    def test_quota_exhausted_fallback(self):
        """测试3: 额度耗尽后降级"""
        # 模拟用光 Cloudflare 额度
        original_usage = self.router.today_usage.get(ProviderType.CLOUDFLARE_WORKERS_AI.value, 0)
        self.router.today_usage[ProviderType.CLOUDFLARE_WORKERS_AI.value] = 20000
        result = self.router.select_provider("summarization", estimated_tokens=500)
        # 恢复状态，避免影响后续测试
        self.router.today_usage[ProviderType.CLOUDFLARE_WORKERS_AI.value] = original_usage
        # 此时 Cloudflare 额度耗尽，应该选其他免费或 DeepSeek
        if result["provider"] != "cloudflare_workers_ai":
            self._log("额度耗尽降级", True, f"Cloudflare 耗尽后选择 {result['name']}")
        else:
            self._log("额度耗尽降级", False, "额度耗尽后仍选择 Cloudflare")

    def test_quota_status(self):
        """测试4: 额度状态正确"""
        status = self.router.get_free_quota_status()
        if "cloudflare_workers_ai" in status and "google_gemini" in status:
            cf = status["cloudflare_workers_ai"]
            if "remaining" in cf and "status" in cf:
                self._log("额度状态", True, f"Cloudflare 剩余 {cf['remaining']} {cf.get('quota_unit', '')}")
            else:
                self._log("额度状态", False, "额度状态字段缺失")
        else:
            self._log("额度状态", False, "Provider 状态缺失")

    def test_cost_report(self):
        """测试5: 成本报告"""
        self.router.record_usage("deepseek", "article_generation", 1000, 0.001, 2.0, True)
        report = self.router.get_cost_report()
        if report and "total_cost" in report and "saved" in report:
            self._log("成本报告", True, f"总成本 ¥{report['total_cost']:.4f}, 节省 ¥{report['saved']:.4f}")
        else:
            self._log("成本报告", False, "成本报告字段缺失")

    def test_translation_task(self):
        """测试6: 翻译任务匹配 Gemini"""
        result = self.router.select_provider("translation", estimated_tokens=300)
        # Gemini 最适合翻译，且额度充足时应选 Gemini
        if result["provider"] == "google_gemini" and result["cost"] == 0.0:
            self._log("翻译任务路由", True, f"翻译任务选择 {result['name']}（免费）")
        else:
            self._log("翻译任务路由", False, f"翻译应选 Gemini，实际: {result['provider']}")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("免费 AI 路由端到端测试")
        print("=" * 60)

        self.test_light_task_selects_free_provider()
        self.test_high_quality_selects_deepseek()
        self.test_quota_exhausted_fallback()
        self.test_quota_status()
        self.test_cost_report()
        self.test_translation_task()

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
    tester = TestFreeAIRouter()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
