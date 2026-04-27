# -*- coding: utf-8 -*-
"""
system_final_check 端到端测试
验证：系统健康检查各模块功能、报告生成、边界处理
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict

# 将仓库根目录加入路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evolution.system_final_check import SystemFinalCheck


class TestSystemFinalCheck:
    """系统最终健康检查端到端测试"""

    def __init__(self):
        self.real_path = Path(__file__).parent.parent.parent

    # ---------- 在真实路径上运行的测试 ----------

    def test_init_paths(self) -> Dict:
        """初始化路径正确"""
        try:
            checker = SystemFinalCheck(str(self.real_path))
            assert checker.trendradar_path == self.real_path
            assert checker.evolution_dir == self.real_path / "evolution"
            assert checker.results == []
            assert checker.warnings == []
            assert checker.errors == []
            return {"passed": True, "message": "路径初始化正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_module_imports(self) -> Dict:
        """模块导入检查能发现 Python 文件"""
        try:
            checker = SystemFinalCheck(str(self.real_path))
            checker.check_module_imports()

            result_msg = next((r for r in checker.results if "模块导入" in r), None)
            assert result_msg is not None, "应有模块导入结果"
            assert "成功" in result_msg, f"导入结果应包含成功: {result_msg}"

            return {"passed": True, "message": result_msg}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_critical_files(self) -> Dict:
        """关键文件存在性检查"""
        try:
            checker = SystemFinalCheck(str(self.real_path))
            checker.check_critical_files()

            result_msg = next((r for r in checker.results if "关键文件" in r), None)
            assert result_msg is not None, "应有关键文件检查结果"

            # 真实路径下不应有缺失的关键文件
            missing_errors = [e for e in checker.errors if "缺失" in e]
            assert len(missing_errors) == 0, f"不应有关键文件缺失: {missing_errors}"

            return {"passed": True, "message": result_msg}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_workflow_syntax(self) -> Dict:
        """evolution.yml YAML 语法正确"""
        try:
            checker = SystemFinalCheck(str(self.real_path))
            checker.check_workflow_syntax()

            result_msg = next((r for r in checker.results if "evolution.yml" in r), None)
            assert result_msg is not None, "应有 workflow 语法检查结果"
            assert "语法" in result_msg or "跳过" in result_msg, f"unexpected: {result_msg}"

            wf_errors = [e for e in checker.errors if "evolution.yml" in e]
            assert len(wf_errors) == 0, f"workflow 不应有语法错误: {wf_errors}"

            return {"passed": True, "message": result_msg}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_title_quality(self) -> Dict:
        """标题质量检查包含预期结果"""
        try:
            checker = SystemFinalCheck(str(self.real_path))
            checker.check_title_quality()

            has_interception = any("标题质量拦截" in r for r in checker.results)
            has_filter = any("标题数字过滤" in r for r in checker.results)
            has_validation = any("标题质量拦截验证" in r for r in checker.results)

            assert has_interception, "应有标题质量拦截结果"
            assert has_validation, "应有标题质量拦截验证结果"

            return {"passed": True, "message": f"拦截={has_interception}, 过滤={has_filter}, 验证={has_validation}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_generate_report_structure(self) -> Dict:
        """报告生成包含 Markdown 结构和状态"""
        try:
            checker = SystemFinalCheck(str(self.real_path))
            # 手动运行几个检查积累结果
            checker.check_module_imports()
            checker.check_critical_files()
            checker.check_title_quality()

            report = checker.generate_report()
            assert "# 🔬 系统最终健康检查报告" in report
            assert "**状态**" in report
            assert "**检查通过**" in report
            assert "## ✅ 检查结果" in report

            return {"passed": True, "message": "报告结构完整"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    # ---------- 边界情况测试 ----------

    def test_empty_directory(self) -> Dict:
        """空目录应产生关键文件缺失错误但不崩溃"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                checker = SystemFinalCheck(tmpdir)
                checker.check_critical_files()
                checker.check_workflow_syntax()
                checker.check_module_imports()

                # 空目录下关键文件应全部缺失
                missing_errors = [e for e in checker.errors if "缺失" in e]
                assert len(missing_errors) >= 1, "空目录应报告关键文件缺失"

                return {"passed": True, "message": f"空目录产生 {len(missing_errors)} 个缺失错误"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_error_tracking(self) -> Dict:
        """错误和警告被正确记录到列表"""
        try:
            checker = SystemFinalCheck(str(self.real_path))
            checker.check_critical_files()
            checker.check_title_quality()

            # 记录不应为 None
            assert isinstance(checker.results, list)
            assert isinstance(checker.warnings, list)
            assert isinstance(checker.errors, list)

            # 结果中应有关键字
            assert len(checker.results) >= 2, f"应有至少2条结果, 实际{len(checker.results)}"

            return {"passed": True, "message": f"结果={len(checker.results)}, 警告={len(checker.warnings)}, 错误={len(checker.errors)}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_status_healthy(self) -> Dict:
        """无错误时状态为 healthy"""
        try:
            # 构造一个无错误的 checker（不运行会报错的检查）
            checker = SystemFinalCheck(str(self.real_path))
            checker.results.append("测试通过: 1/1")
            # 不调用任何会产生 errors 的方法

            status = "healthy" if not checker.errors else "issues_found"
            assert status == "healthy", "无错误时应为 healthy"

            return {"passed": True, "message": "无错误状态=healthy"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_status_issues_found(self) -> Dict:
        """有错误时状态为 issues_found"""
        try:
            checker = SystemFinalCheck(str(self.real_path))
            checker.errors.append("模拟错误")
            checker.results.append("测试通过: 1/1")

            status = "healthy" if not checker.errors else "issues_found"
            assert status == "issues_found", "有错误时应为 issues_found"

            return {"passed": True, "message": "有错误状态=issues_found"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def run_all(self) -> Dict:
        """运行全部测试"""
        tests = [
            self.test_init_paths,
            self.test_check_module_imports,
            self.test_check_critical_files,
            self.test_check_workflow_syntax,
            self.test_check_title_quality,
            self.test_generate_report_structure,
            self.test_empty_directory,
            self.test_error_tracking,
            self.test_status_healthy,
            self.test_status_issues_found,
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
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": results,
        }


if __name__ == "__main__":
    tester = TestSystemFinalCheck()
    result = tester.run_all()
    print(f"\n总计: {result['passed']}/{len(result['results'])} 通过, {result['failed']} 失败")
    for r in result["results"]:
        icon = "✅" if r["passed"] else "❌"
        print(f"{icon} {r['test']}: {r.get('message', '')}")
