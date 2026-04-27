import sys
import os
import tempfile
import shutil
import json
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import evolution.unified_logger as ul


class TestUnifiedLogger:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_ul_")
        self.log_file = Path(self.tmpdir) / "log.jsonl"
        self.orig_log_path = ul._log_path
        ul._log_path = lambda: self.log_file
        ul.clear_article_id()

    def _teardown(self):
        ul._log_path = self.orig_log_path
        ul.clear_article_id()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_set_get_article_id(self):
        ul.set_article_id("article-001")
        assert ul.get_article_id() == "article-001"
        ul.clear_article_id()
        assert ul.get_article_id() is None
        return True

    def test_log_info_writes_file(self):
        ul.log_info("test_module", "info message")
        assert self.log_file.exists()
        with open(self.log_file, "r") as f:
            record = json.loads(f.readline())
        assert record["level"] == "INFO"
        assert record["module"] == "test_module"
        assert record["message"] == "info message"
        return True

    def test_log_warn_level(self):
        ul.log_warn("test_module", "warn message")
        with open(self.log_file, "r") as f:
            record = json.loads(f.readline())
        assert record["level"] == "WARN"
        return True

    def test_log_error_level(self):
        ul.log_error("test_module", "error message")
        with open(self.log_file, "r") as f:
            record = json.loads(f.readline())
        assert record["level"] == "ERROR"
        return True

    def test_log_debug_no_console(self):
        ul.log_debug("test_module", "debug message")
        with open(self.log_file, "r") as f:
            record = json.loads(f.readline())
        assert record["level"] == "DEBUG"
        return True

    def test_log_with_article_id(self):
        ul.set_article_id("article-123")
        ul.log_info("test_module", "with article id")
        with open(self.log_file, "r") as f:
            record = json.loads(f.readline())
        assert record["article_id"] == "article-123"
        ul.clear_article_id()
        return True

    def test_get_run_summary(self):
        ul.log_info("m1", "info1")
        ul.log_warn("m2", "warn1")
        ul.log_error("m3", "error1")
        summary = ul.get_run_summary()
        assert summary["total_logs"] == 3
        assert summary["errors"] == 1
        assert summary["warns"] == 1
        return True

    def test_step_timer_success(self):
        with ul.StepTimer("test", "step1"):
            pass
        with open(self.log_file, "r") as f:
            lines = f.readlines()
        # Should have start and end log
        assert len(lines) >= 2
        return True

    def test_step_timer_exception(self):
        try:
            with ul.StepTimer("test", "fail_step"):
                raise ValueError("test error")
        except ValueError:
            pass
        with open(self.log_file, "r") as f:
            lines = f.readlines()
        # Should have start, end, and error log
        assert len(lines) >= 3
        # Check error log exists
        records = [json.loads(l) for l in lines]
        error_msgs = [r["message"] for r in records if r["level"] == "ERROR"]
        assert any("失败" in m or "error" in m.lower() for m in error_msgs)
        return True

    def run_all(self):
        tests = [
            self.test_set_get_article_id,
            self.test_log_info_writes_file,
            self.test_log_warn_level,
            self.test_log_error_level,
            self.test_log_debug_no_console,
            self.test_log_with_article_id,
            self.test_get_run_summary,
            self.test_step_timer_success,
            self.test_step_timer_exception,
        ]
        results = []
        passed = failed = 0
        for t in tests:
            # 每次测试前清空日志文件，确保测试隔离
            if self.log_file.exists():
                self.log_file.write_text("")
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
