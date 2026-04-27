import sys
import os
import tempfile
import shutil
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.cleanup_manager import CleanupManager, run_cleanup, get_cleanup_report


class TestCleanupManager:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_cm_")
        self.manager = CleanupManager(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init_creates_trash(self):
        assert os.path.exists(os.path.join(self.tmpdir, ".trash"))
        return True

    def test_is_protected_py(self):
        assert self.manager._is_protected(os.path.join(self.tmpdir, "test.py"))
        return True

    def test_is_protected_config(self):
        assert self.manager._is_protected(os.path.join(self.tmpdir, "config.yaml"))
        return True

    def test_is_protected_git(self):
        assert self.manager._is_protected(os.path.join(self.tmpdir, ".git", "config"))
        return True

    def test_is_not_protected_tmp(self):
        assert not self.manager._is_protected(os.path.join(self.tmpdir, "test.tmp"))
        return True

    def test_cleanup_temp_files(self):
        subdir = tempfile.mkdtemp(prefix="e2e_cm_t_", dir=self.tmpdir)
        manager = CleanupManager(subdir)
        tmpfile = os.path.join(subdir, "a.tmp")
        with open(tmpfile, 'w') as f:
            f.write("temp")
        result = manager.cleanup_temp_files()
        assert result["deleted_count"] >= 1
        assert not os.path.exists(tmpfile)
        trash = os.path.join(subdir, ".trash")
        assert os.path.exists(trash)
        assert any("a.tmp" in f for f in os.listdir(trash))
        return True

    def test_cleanup_python_cache(self):
        subdir = tempfile.mkdtemp(prefix="e2e_cm_p_", dir=self.tmpdir)
        manager = CleanupManager(subdir)
        pycache = os.path.join(subdir, "__pycache__")
        os.makedirs(pycache)
        pyc = os.path.join(pycache, "test.cpython-311.pyc")
        with open(pyc, 'w') as f:
            f.write("cache")
        result = manager.cleanup_python_cache()
        assert result["deleted_count"] >= 1
        assert not os.path.exists(pycache)
        return True

    def test_cleanup_old_logs(self):
        subdir = tempfile.mkdtemp(prefix="e2e_cm_l_", dir=self.tmpdir)
        manager = CleanupManager(subdir)
        old_log = os.path.join(subdir, "old.log")
        new_log = os.path.join(subdir, "new.log")
        with open(old_log, 'w') as f:
            f.write("old")
        with open(new_log, 'w') as f:
            f.write("new")
        old_time = time.time() - 86400 * 10
        os.utime(old_log, (old_time, old_time))
        result = manager.cleanup_old_logs()
        assert result["deleted_count"] == 1
        assert not os.path.exists(old_log)
        assert os.path.exists(new_log)
        return True

    def test_cleanup_empty_dirs(self):
        subdir = tempfile.mkdtemp(prefix="e2e_cm_e_", dir=self.tmpdir)
        manager = CleanupManager(subdir)
        empty_dir = os.path.join(subdir, "empty_folder")
        os.makedirs(empty_dir)
        result = manager.cleanup_empty_dirs()
        assert result["deleted_count"] >= 1
        assert not os.path.exists(empty_dir)
        return True

    def test_run_cleanup_returns_list(self):
        result = self.manager.run_cleanup()
        assert isinstance(result, list)
        assert len(result) == 5
        return True

    def test_generate_report(self):
        results = self.manager.run_cleanup()
        report = self.manager.generate_cleanup_report(results)
        assert isinstance(report, str)
        assert "清理报告" in report
        return True

    def run_all(self):
        tests = [
            self.test_init_creates_trash,
            self.test_is_protected_py,
            self.test_is_protected_config,
            self.test_is_protected_git,
            self.test_is_not_protected_tmp,
            self.test_cleanup_temp_files,
            self.test_cleanup_python_cache,
            self.test_cleanup_old_logs,
            self.test_cleanup_empty_dirs,
            self.test_run_cleanup_returns_list,
            self.test_generate_report,
        ]
        passed = 0
        failed = []
        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                failed.append((test.__name__, str(e)))
        self._teardown()
        return {"passed": passed, "failed": failed, "total": len(tests)}
