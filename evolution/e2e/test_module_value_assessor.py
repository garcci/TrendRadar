import sys
import os
import tempfile
import shutil
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.module_value_assessor import ModuleValueAssessor, assess_idle_modules


class TestModuleValueAssessor:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_mva_")
        self.assessor = ModuleValueAssessor(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_module_file(self, name: str, content: str):
        evo_dir = Path(self.tmpdir) / "evolution"
        evo_dir.mkdir(parents=True, exist_ok=True)
        (evo_dir / f"{name}.py").write_text(content, encoding="utf-8")

    def _make_module(self, name="test_mod", lines=200, last_modified="2024-01-01"):
        return SimpleNamespace(name=name, lines_of_code=lines, last_modified=last_modified, status="idle")

    def test_calculate_complexity_optimal(self):
        content = "\n".join([f"# line {i}" for i in range(200)])
        content += "\nclass A:\n    pass\nclass B:\n    pass\n"
        content += "\n".join([f"def f{i}(): pass" for i in range(5)])
        score = self.assessor._calculate_complexity(content)
        assert score >= 15, f"Expected high complexity score, got {score}"
        return True

    def test_calculate_complexity_small(self):
        content = "# small\ndef f(): pass\n"
        score = self.assessor._calculate_complexity(content)
        assert score <= 10, f"Expected low complexity score, got {score}"
        return True

    def test_calculate_functional_value(self):
        content = '"""Quality scoring module"""\ndef assess_quality(score: int) -> dict:\n    try:\n        return {"quality": score}\n    except Exception:\n        return {}\n'
        score = self.assessor._calculate_functional_value(content)
        assert score > 0, f"Expected positive functional score, got {score}"
        return True

    def test_calculate_integration_difficulty(self):
        content = "import requests\nimport sqlite3\ndef run_check(): pass\n"
        diff = self.assessor._calculate_integration_difficulty(content)
        assert diff > 0, f"Expected positive difficulty, got {diff}"
        return True

    def test_calculate_integration_easy(self):
        content = "def get_report():\n    return 'ok'\nif __name__ == '__main__':\n    pass\n"
        diff = self.assessor._calculate_integration_difficulty(content)
        assert diff < 5, f"Expected low difficulty, got {diff}"
        return True

    def test_calculate_maturity(self):
        content = '"""Doc1"""\n"""Doc2"""\n# comment\n# another\ntry:\n    pass\nexcept:\n    pass\ndef f() -> int:\n    return 1\n'
        score = self.assessor._calculate_maturity(content, self._make_module())
        assert score >= 10, f"Expected high maturity, got {score}"
        return True

    def test_get_recommendation_high(self):
        rec = self.assessor._get_recommendation("mod", 75)
        assert "高价值" in rec or "立即" in rec
        return True

    def test_get_recommendation_low(self):
        rec = self.assessor._get_recommendation("mod", 30)
        assert "有限" in rec or "归档" in rec or "观察" in rec
        return True

    def test_assess_module(self):
        content = '"""Module doc"""\nclass Test:\n    pass\ndef run_test():\n    try:\n        return 1\n    except:\n        return 0\n'
        self._create_module_file("test_assess", content)
        module = self._make_module("test_assess", lines=10, last_modified="2024-01-01")
        score, details = self.assessor._assess_module(module)
        assert score >= 0
        assert "complexity_score" in details
        assert "functional_score" in details
        return True

    def test_generate_report(self):
        report = self.assessor.generate_report()
        assert isinstance(report, str)
        assert "闲置模块价值评估报告" in report
        return True

    def run_all(self):
        tests = [
            self.test_calculate_complexity_optimal,
            self.test_calculate_complexity_small,
            self.test_calculate_functional_value,
            self.test_calculate_integration_difficulty,
            self.test_calculate_integration_easy,
            self.test_calculate_maturity,
            self.test_get_recommendation_high,
            self.test_get_recommendation_low,
            self.test_assess_module,
            self.test_generate_report,
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
