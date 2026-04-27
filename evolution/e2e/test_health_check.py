# -*- coding: utf-8 -*-
"""
Health Check 端到端测试
验证系统健康检查器核心功能
"""

import os
import tempfile
import shutil
from typing import Dict
from evolution.health_check import SystemHealthChecker, run_health_check


class TestHealthCheck:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_hc_")
        self.checker = SystemHealthChecker(self.tmpdir)

    def __del__(self):
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_check_decorator_pass(self) -> Dict:
        """_check 装饰器通过情况"""
        try:
            result = self.checker._check("测试通过", lambda: "ok")
            assert result == True, "通过时应返回 True"
            assert len(self.checker.results) == 1, "应记录 1 条结果"
            assert self.checker.results[0]["status"] == "pass", "状态应为 pass"
            return {"passed": True, "message": "_check 通过情况正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_decorator_fail(self) -> Dict:
        """_check 装饰器失败情况"""
        try:
            def raise_error():
                raise ValueError("测试错误")
            result = self.checker._check("测试失败", raise_error)
            assert result == False, "失败时应返回 False"
            assert len(self.checker.errors) == 1, "应记录 1 条错误"
            assert "测试错误" in self.checker.errors[0], "错误信息应包含原始错误"
            return {"passed": True, "message": "_check 失败情况正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_warn(self) -> Dict:
        """_warn 记录警告"""
        try:
            checker = SystemHealthChecker(self.tmpdir)
            checker._warn("测试警告", "这是一个警告")
            assert len(checker.warnings) == 1, "应记录 1 条警告"
            assert checker.warnings[0] == "测试警告: 这是一个警告"
            assert len(checker.results) == 1, "应记录 1 条结果"
            assert checker.results[0]["status"] == "warn", "状态应为 warn"
            return {"passed": True, "message": "_warn 记录警告正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_python_syntax_valid(self) -> Dict:
        """Python 语法检查通过"""
        try:
            # 创建语法正确的 Python 文件
            py_dir = os.path.join(self.tmpdir, "evolution")
            os.makedirs(py_dir, exist_ok=True)
            with open(os.path.join(py_dir, "valid.py"), 'w') as f:
                f.write("def hello():\n    return 'world'\n")

            result = self.checker.check_python_syntax()
            assert result["status"] == "ok", f"语法正确应通过，错误: {result.get('errors')}"
            assert result["checked"] >= 1, "应至少检查 1 个文件"
            return {"passed": True, "message": "Python 语法检查通过正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_python_syntax_invalid(self) -> Dict:
        """Python 语法检查失败"""
        try:
            py_dir = os.path.join(self.tmpdir, "evolution")
            os.makedirs(py_dir, exist_ok=True)
            with open(os.path.join(py_dir, "invalid.py"), 'w') as f:
                f.write("def hello(\n    return 'world'\n")  # 语法错误

            result = self.checker.check_python_syntax()
            assert result["status"] == "fail", "语法错误应标记为 fail"
            assert len(result["errors"]) >= 1, "应报告语法错误"
            return {"passed": True, "message": "Python 语法检查失败正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_repo_size(self) -> Dict:
        """仓库大小检查"""
        try:
            # 创建一些文件
            with open(os.path.join(self.tmpdir, "file1.txt"), 'w') as f:
                f.write("x" * 200000)  # ~200KB 确保四舍五入后 > 0

            result = self.checker.check_repo_size()
            assert "size_mb" in result, "应返回 size_mb"
            assert result["size_mb"] > 0, "大小应大于 0"
            assert result["status"] in ["healthy", "warning", "critical"], "应有健康状态"
            return {"passed": True, "message": f"仓库大小检查正确: {result['size_mb']}MB"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_run_all_checks_structure(self) -> Dict:
        """run_all_checks 返回结构正确"""
        try:
            # 在临时目录创建最小结构，避免外部依赖失败
            os.makedirs(os.path.join(self.tmpdir, "config"), exist_ok=True)
            with open(os.path.join(self.tmpdir, "config", "config.yaml"), 'w') as f:
                f.write("test: true\n")
            with open(os.path.join(self.tmpdir, ".env.example"), 'w') as f:
                f.write("TEST=1\n")
            with open(os.path.join(self.tmpdir, "pyproject.toml"), 'w') as f:
                f.write("[project]\n")

            # 初始化 git
            import subprocess
            subprocess.run(["git", "init"], cwd=self.tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=self.tmpdir, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=self.tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=self.tmpdir, capture_output=True)

            checker = SystemHealthChecker(self.tmpdir)
            report = checker.run_all_checks()
            assert "timestamp" in report, "应包含 timestamp"
            assert "overall_status" in report, "应包含 overall_status"
            assert "summary" in report, "应包含 summary"
            assert "details" in report, "应包含 details"
            assert report["summary"]["total_checks"] >= 1, "应至少运行 1 个检查"
            return {"passed": True, "message": f"run_all_checks 结构正确, status={report['overall_status']}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_generate_health_report(self) -> Dict:
        """健康报告格式正确"""
        try:
            report = self.checker.generate_health_report()
            assert "系统健康检查报告" in report, "应包含报告标题"
            assert "总体状态" in report, "应包含总体状态"
            assert "通过:" in report, "应包含通过数量"
            return {"passed": True, "message": "健康报告格式正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_convenience_run_health_check(self) -> Dict:
        """便捷函数 run_health_check"""
        try:
            report = run_health_check(self.tmpdir)
            assert isinstance(report, dict), "应返回字典"
            assert "overall_status" in report, "应包含 overall_status"
            return {"passed": True, "message": "便捷函数返回结构正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def run_all(self) -> Dict:
        tests = [
            self.test_check_decorator_pass,
            self.test_check_decorator_fail,
            self.test_warn,
            self.test_check_python_syntax_valid,
            self.test_check_python_syntax_invalid,
            self.test_check_repo_size,
            self.test_run_all_checks_structure,
            self.test_generate_health_report,
            self.test_convenience_run_health_check,
        ]
        results = []
        passed = failed = 0
        for t in tests:
            r = t()
            r["test"] = t.__name__
            results.append(r)
            if r["passed"]:
                passed += 1
            else:
                failed += 1
        return {
            "suite": "health_check",
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "results": results,
        }


if __name__ == "__main__":
    tester = TestHealthCheck()
    report = tester.run_all()
    print(f"\n## health_check ({report['passed']}/{report['total']})")
    for r in report["results"]:
        emoji = "✅" if r["passed"] else "❌"
        print(f"- {emoji} **{r['test']}**: {r['message']}")
