import sys
import os
import tempfile
import shutil
import json
import gzip

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.data_archiver import DataArchiver, run_auto_archive, get_archive_report


class TestDataArchiver:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_da_")
        self.archiver = DataArchiver(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_json_file(self, name, data):
        path = os.path.join(self.tmpdir, "evolution", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_compress_file(self):
        path = os.path.join(self.tmpdir, "test.txt")
        with open(path, "w") as f:
            f.write("A" * 1000)
        result = self.archiver.compress_file(path)
        assert result["status"] == "success"
        assert result["original_size_kb"] > 0
        assert os.path.exists(result["archive_path"])
        return True

    def test_compress_file_not_found(self):
        result = self.archiver.compress_file("/nonexistent/file.txt")
        assert result["status"] == "skipped"
        return True

    def test_archive_json_by_age(self):
        old = ("2024-01-01T00:00:00", {"timestamp": "2024-01-01T00:00:00", "score": 5})
        recent = ("2099-01-01T00:00:00", {"timestamp": "2099-01-01T00:00:00", "score": 8})
        self._create_json_file("metrics.json", [old[1], recent[1]])
        result = self.archiver.archive_json_by_age("evolution/metrics.json", retain_days=30)
        assert result["status"] == "success"
        assert result["archived_count"] == 1
        assert result["retained_count"] == 1
        return True

    def test_archive_json_by_age_no_old_data(self):
        recent = {"timestamp": "2099-01-01T00:00:00", "score": 8}
        self._create_json_file("metrics2.json", [recent])
        result = self.archiver.archive_json_by_age("evolution/metrics2.json", retain_days=30)
        assert result["status"] == "skipped"
        return True

    def test_archive_json_by_count(self):
        data = [{"id": i, "score": i} for i in range(15)]
        self._create_json_file("exceptions.json", data)
        result = self.archiver.archive_json_by_count("evolution/exceptions.json", retain_count=10)
        assert result["status"] == "success"
        assert result["retained_count"] == 10
        assert result["archived_count"] == 5
        return True

    def test_archive_json_by_count_under_limit(self):
        data = [{"id": i} for i in range(3)]
        self._create_json_file("small.json", data)
        result = self.archiver.archive_json_by_count("evolution/small.json", retain_count=10)
        assert result["status"] == "skipped"
        return True

    def test_archive_old_databases(self):
        db_dir = os.path.join(self.tmpdir, "output", "news")
        os.makedirs(db_dir, exist_ok=True)
        old_db = os.path.join(db_dir, "old.db")
        with open(old_db, "w") as f:
            f.write("x" * 100)
        # 设置修改时间为10天前
        old_time = os.path.getmtime(old_db) - 86400 * 10
        os.utime(old_db, (old_time, old_time))
        result = self.archiver.archive_old_databases("output/news", retain_days=7)
        assert result["status"] == "success"
        assert result["archived_count"] >= 1
        return True

    def test_generate_archive_report(self):
        results = [
            {"status": "success", "file": "a.json", "archived_count": 5, "compress_result": {"savings_kb": 10}},
            {"status": "skipped", "reason": "no_old_data"},
        ]
        report = self.archiver.generate_archive_report(results)
        assert "归档报告" in report
        assert "a.json" in report
        return True

    def test_generate_archive_report_empty(self):
        report = self.archiver.generate_archive_report([])
        assert "没有需要归档的数据" in report
        return True

    def test_run_auto_archive_skips_missing(self):
        result = self.archiver.run_auto_archive()
        assert isinstance(result, list)
        # 所有配置的文件都不存在，应该都是 skipped
        for r in result:
            assert r["status"] in ("skipped", "success")
        return True

    def run_all(self):
        tests = [
            self.test_compress_file,
            self.test_compress_file_not_found,
            self.test_archive_json_by_age,
            self.test_archive_json_by_age_no_old_data,
            self.test_archive_json_by_count,
            self.test_archive_json_by_count_under_limit,
            self.test_archive_old_databases,
            self.test_generate_archive_report,
            self.test_generate_archive_report_empty,
            self.test_run_auto_archive_skips_missing,
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
