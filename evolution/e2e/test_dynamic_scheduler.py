# -*- coding: utf-8 -*-
"""DynamicScheduler 端到端测试"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


class TestDynamicScheduler:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_ds_")
        from evolution import dynamic_scheduler as ds
        self.ds = ds

    def test_load_jsonl(self):
        path = Path(self.tmpdir) / "test.jsonl"
        now = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp": now, "level": "INFO", "module": "test"}) + "\n")
            f.write(json.dumps({"timestamp": now, "level": "ERROR", "module": "test"}) + "\n")
        records = self.ds._load_jsonl(path, hours=24)
        assert len(records) == 2, f"Expected 2 records, got {len(records)}"
        return True

    def test_load_jsonl_empty(self):
        path = Path(self.tmpdir) / "empty.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        records = self.ds._load_jsonl(path, hours=24)
        assert records == [], "Empty file should return empty list"
        return True

    def test_load_jsonl_invalid(self):
        path = Path(self.tmpdir) / "invalid.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write(json.dumps({"timestamp": datetime.now().isoformat(), "level": "INFO"}) + "\n")
        records = self.ds._load_jsonl(path, hours=24)
        assert len(records) == 1, f"Expected 1 valid record, got {len(records)}"
        return True

    def test_generate_schedule_always_run(self):
        signals = {"has_errors": False, "quality_stable": False, "avg_score": 0.0, "article_count": 0, "module_stats": {}}
        schedule = self.ds.generate_schedule(signals)
        always_steps = [s for s in schedule if s["step"] in ("System Health Check", "Autonomous Evolution")]
        assert all(s["action"] == "run" for s in always_steps), "Always steps should be run"
        return True

    def test_generate_schedule_skip(self):
        signals = {"has_errors": False, "quality_stable": True, "avg_score": 8.0, "article_count": 0, "module_stats": {}}
        schedule = self.ds.generate_schedule(signals)
        prompt_step = next((s for s in schedule if s["step"] == "Prompt Evolution"), None)
        assert prompt_step is not None, "Prompt Evolution step should exist"
        assert prompt_step["action"] == "skip", f"Expected skip, got {prompt_step['action']}"
        return True

    def test_generate_schedule_run(self):
        signals = {"has_errors": True, "quality_stable": False, "avg_score": 5.0, "article_count": 2, "module_stats": {}}
        schedule = self.ds.generate_schedule(signals)
        prompt_step = next((s for s in schedule if s["step"] == "Prompt Evolution"), None)
        assert prompt_step is not None, "Prompt Evolution step should exist"
        assert prompt_step["action"] == "run", f"Expected run, got {prompt_step['action']}"
        return True

    def test_generate_schedule_skip_repo_cleanup(self):
        signals = {"has_errors": False, "quality_stable": False, "avg_score": 0.0, "article_count": 0, "module_stats": {}}
        schedule = self.ds.generate_schedule(signals)
        repo_step = next((s for s in schedule if s["step"] == "Repo Cleanup"), None)
        assert repo_step is not None, "Repo Cleanup step should exist"
        assert repo_step["action"] == "skip", f"Expected skip, got {repo_step['action']}"
        return True

    def test_get_step_decision_run(self):
        # System Health Check 是 always=True，无论 signals 如何都应执行
        should_run, reason = self.ds.get_step_decision("System Health Check")
        assert should_run is True, f"Expected True, got {should_run}"
        return True

    def test_get_step_decision_skip(self):
        signals = {"has_errors": False, "quality_stable": False, "avg_score": 0.0, "article_count": 0, "module_stats": {}}
        # get_step_decision 内部调用 analyze_recent_logs，无法直接 mock signals
        # 但它会读取当前目录下的 evolution/data_pipeline/log.jsonl
        # 为确保测试不依赖文件状态，我们直接测试 generate_schedule 的纯函数行为
        should_run, reason = self.ds.get_step_decision("Exception Intervention")
        # 如果当前目录没有日志，has_errors=False，应跳过
        assert should_run is False, f"Expected False when no errors, got {should_run}"
        return True

    def test_get_step_decision_unknown(self):
        should_run, reason = self.ds.get_step_decision("NonExistentStep")
        assert should_run is True, "Unknown step should default to run"
        assert "未在规则中定义" in reason or "默认执行" in reason, f"Unexpected reason: {reason}"
        return True

    def test_generate_schedule_report(self):
        # 此函数依赖当前目录的 evolution/data_pipeline/log.jsonl
        # 为了测试，我们在 tmpdir 下创建所需目录结构并 chdir
        old_cwd = os.getcwd()
        try:
            os.chdir(self.tmpdir)
            os.makedirs("evolution/data_pipeline", exist_ok=True)
            report = self.ds.generate_schedule_report()
            assert "进化步骤动态编排报告" in report, "Report should contain title"
            assert "总步骤:" in report, "Report should contain total steps"
        finally:
            os.chdir(old_cwd)
        return True

    def run_all(self):
        results = []
        passed = 0
        for name in dir(self):
            if name.startswith("test_"):
                try:
                    self.__getattribute__(name)()
                    results.append({"name": name, "status": "PASS"})
                    passed += 1
                except Exception as e:
                    results.append({"name": name, "status": "FAIL", "error": str(e)})
        return {"all_passed": passed == len(results), "passed": passed, "failed": len(results) - passed, "results": results}
