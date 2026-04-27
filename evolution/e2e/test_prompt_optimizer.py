import sys
import os
import tempfile
import shutil
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.prompt_optimizer import PromptOptimizer, get_optimized_prompt_params


class TestPromptOptimizer:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_po_")
        self.optimizer = PromptOptimizer(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_calculate_weights_high_effect(self):
        data = {
            "f1": {"effect_delta": 2.0, "uses": 15, "avg_score": 8.5}
        }
        weights = self.optimizer.calculate_fragment_weights(data)
        assert weights["f1"] > 2.0  # 高效果+高使用次数
        return True

    def test_calculate_weights_low_effect(self):
        data = {
            "f1": {"effect_delta": -1.5, "uses": 5, "avg_score": 5.0}
        }
        weights = self.optimizer.calculate_fragment_weights(data)
        assert weights["f1"] <= -0.5  # 负效果
        return True

    def test_generate_plan_boost(self):
        data = {
            "f1": {"name": "高质量片段", "effect_delta": 2.5, "uses": 20, "avg_score": 9.0, "category": "质量"}
        }
        plan = self.optimizer.generate_optimization_plan(data)
        assert len(plan["boost"]) == 1
        assert plan["boost"][0]["id"] == "f1"
        return True

    def test_generate_plan_remove(self):
        data = {
            "f1": {"name": "低质量片段", "effect_delta": -2.0, "uses": 10, "avg_score": 4.0, "category": "内容"}
        }
        plan = self.optimizer.generate_optimization_plan(data)
        assert len(plan["remove"]) == 1
        assert plan["remove"][0]["id"] == "f1"
        return True

    def test_generate_plan_new_suggestions(self):
        # 只提供部分category，触发新片段建议
        data = {
            "f1": {"name": "质量片段", "effect_delta": 1.0, "uses": 10, "avg_score": 7.0, "category": "质量"}
        }
        plan = self.optimizer.generate_optimization_plan(data)
        # 缺少的内容/风格/深度等类别应产生新建议
        assert len(plan["new_suggestions"]) > 0
        return True

    def test_save_load_optimization(self):
        opt = {"timestamp": "2024-01-01T00:00:00", "boost": [], "reduce": [], "remove": [], "new_suggestions": [], "reorder": []}
        self.optimizer._save_optimization(opt)
        history = self.optimizer._load_optimization_history()
        assert len(history) == 1
        assert history[0]["timestamp"] == "2024-01-01T00:00:00"
        return True

    def test_optimized_params_long_prompt(self):
        long_prompt = "x" * 7000
        summary, temp, tokens = get_optimized_prompt_params(long_prompt, base_temp=0.7, base_tokens=4000)
        assert tokens > 4000  # 长prompt增加tokens
        assert temp < 0.7     # 长prompt降低temperature
        return True

    def test_optimized_params_short_prompt(self):
        short_prompt = "short"
        summary, temp, tokens = get_optimized_prompt_params(short_prompt, base_temp=0.7, base_tokens=4000)
        assert temp > 0.7  # 短prompt提高temperature
        return True

    def test_optimized_params_with_history(self):
        # 清空之前测试留下的数据
        opt_file = self.optimizer.optimize_file
        if os.path.exists(opt_file):
            os.remove(opt_file)
        # 创建优化历史到 optimizer 实例路径
        history = [
            {"boost": [{"weight": 3.0}, {"weight": 3.0}], "timestamp": "2024-01-01"},
            {"boost": [{"weight": 3.0}, {"weight": 3.0}], "timestamp": "2024-01-02"},
            {"boost": [{"weight": 3.0}, {"weight": 3.0}], "timestamp": "2024-01-03"},
        ]
        for opt in history:
            self.optimizer._save_optimization(opt)

        loaded = self.optimizer._load_optimization_history()
        assert len(loaded) == 3, f"expected 3, got {len(loaded)}"
        # 验证历史数据存在且可被加载
        assert loaded[-1]["timestamp"] == "2024-01-03"
        return True

    def test_empty_fragment_data(self):
        plan = self.optimizer.generate_optimization_plan({})
        assert plan["boost"] == []
        assert plan["remove"] == []
        assert plan["reorder"] == []
        return True

    def test_reorder_sorted_by_weight(self):
        data = {
            "f1": {"name": "A", "effect_delta": 1.0, "uses": 10, "avg_score": 7.0, "category": "质量"},
            "f2": {"name": "B", "effect_delta": 3.0, "uses": 10, "avg_score": 9.0, "category": "内容"},
        }
        plan = self.optimizer.generate_optimization_plan(data)
        reorder = plan["reorder"]
        assert reorder[0]["id"] == "f2"  # 权重高的排前面
        assert reorder[1]["id"] == "f1"
        return True

    def run_all(self):
        tests = [
            self.test_calculate_weights_high_effect,
            self.test_calculate_weights_low_effect,
            self.test_generate_plan_boost,
            self.test_generate_plan_remove,
            self.test_generate_plan_new_suggestions,
            self.test_save_load_optimization,
            self.test_optimized_params_long_prompt,
            self.test_optimized_params_short_prompt,
            self.test_optimized_params_with_history,
            self.test_empty_fragment_data,
            self.test_reorder_sorted_by_weight,
        ]
        results = []
        passed = failed = 0
        for t in tests:
            try:
                t()
                results.append({"test": t.__name__, "passed": True, "message": "通过"})
                passed += 1
            except Exception as e:
                results.append({"test": t.__name__, "passed": False, "message": str(e)})
                failed += 1
        self._teardown()
        return {
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": results
        }
