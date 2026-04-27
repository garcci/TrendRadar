import sys
import os
import tempfile
import shutil
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.ab_testing import (
    ABTestingFramework, TestDimension, ABTest, TestResult,
    run_ab_test_decision
)


class TestABTesting:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_ab_")
        self.framework = ABTestingFramework(self.tmpdir)
        self.framework.min_sample_size = 2  # 降低以便测试

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_test(self):
        test_id = self.framework.create_test(
            TestDimension.PROMPT_VERSION,
            variant_a={"level": "normal"},
            variant_b={"level": "high"},
            sample_size=5
        )
        assert test_id.startswith("prompt_version_")
        assert os.path.exists(self.framework.tests_file)
        return True

    def test_assign_variant(self):
        test_id = self.framework.create_test(
            TestDimension.MODEL,
            variant_a={"model": "chat"},
            variant_b={"model": "reasoner"},
            sample_size=5
        )
        variant = self.framework.assign_variant(test_id)
        assert variant in ("A", "B")
        return True

    def test_assign_variant_inactive(self):
        variant = self.framework.assign_variant("nonexistent")
        assert variant == "A"
        return True

    def test_record_result(self):
        test_id = self.framework.create_test(
            TestDimension.TEMPERATURE,
            variant_a={"temp": 0.6},
            variant_b={"temp": 0.8},
            sample_size=5
        )
        self.framework.record_result(test_id, "A", overall_score=8.0, dimensions={})
        results = self.framework._get_results(test_id)
        assert len(results) == 1
        assert results[0].variant == "A"
        return True

    def test_get_test_summary(self):
        test_id = self.framework.create_test(
            TestDimension.ARTICLE_STRUCTURE,
            variant_a={"template": "default"},
            variant_b={"template": "contrast"},
            sample_size=5
        )
        summary = self.framework.get_test_summary(test_id)
        assert summary["test_id"] == test_id
        assert summary["status"] == "running"
        return True

    def test_auto_select_winner(self):
        test_id = self.framework.create_test(
            TestDimension.MAX_TOKENS,
            variant_a={"tokens": 2000},
            variant_b={"tokens": 4000},
            sample_size=5
        )
        # A组得高分，B组得低分
        for _ in range(3):
            self.framework.record_result(test_id, "A", overall_score=9.0, dimensions={})
        for _ in range(3):
            self.framework.record_result(test_id, "B", overall_score=5.0, dimensions={})
        summary = self.framework.get_test_summary(test_id)
        assert summary["winner"] == "A"
        assert not summary["is_active"]
        return True

    def test_calculate_significance(self):
        sig = self.framework._calculate_significance([9, 9, 9], [5, 5, 5])
        assert sig >= 0.95
        sig2 = self.framework._calculate_significance([7, 7, 7], [7, 7, 7])
        assert sig2 == 0.0
        return True

    def test_get_recommendations(self):
        test_id = self.framework.create_test(
            TestDimension.RSS_SOURCES,
            variant_a={"source": "A"},
            variant_b={"source": "B"},
            sample_size=5
        )
        for _ in range(3):
            self.framework.record_result(test_id, "A", overall_score=9.0, dimensions={})
        for _ in range(3):
            self.framework.record_result(test_id, "B", overall_score=6.0, dimensions={})
        recs = self.framework.get_recommendations()
        assert len(recs) > 0
        assert recs[0]["winner"] == "A"
        return True

    def test_auto_create_tests(self):
        ids = self.framework.auto_create_tests(["增加技术细节", "使用对比模板"])
        assert len(ids) >= 2
        return True

    def test_run_ab_test_decision(self):
        variant = run_ab_test_decision(self.tmpdir, "temperature",
                                       {"temp": 0.6}, {"temp": 0.8})
        assert variant in ("A", "B")
        return True

    def test_run_ab_test_decision_invalid_dimension(self):
        variant = run_ab_test_decision(self.tmpdir, "invalid_dim",
                                       {"a": 1}, {"b": 2})
        assert variant == "A"
        return True

    def run_all(self):
        tests = [
            self.test_create_test,
            self.test_assign_variant,
            self.test_assign_variant_inactive,
            self.test_record_result,
            self.test_get_test_summary,
            self.test_auto_select_winner,
            self.test_calculate_significance,
            self.test_get_recommendations,
            self.test_auto_create_tests,
            self.test_run_ab_test_decision,
            self.test_run_ab_test_decision_invalid_dimension,
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
