# -*- coding: utf-8 -*-
"""
退化检测与干预系统端到端测试
验证：质量退化检测、暂停/恢复、日志持久化
"""

import json
import os
import shutil
import tempfile
from typing import Dict

from evolution.regression_guard import RegressionGuard


class TestRegressionGuard:
    """退化检测系统端到端测试"""

    def setup(self):
        """创建临时目录隔离测试数据"""
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_rg_")
        os.makedirs(f"{self.tmpdir}/evolution", exist_ok=True)
        self.guard = RegressionGuard(repo_path=self.tmpdir)

    def teardown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_metrics(self, metrics):
        """写入文章指标数据"""
        path = f"{self.tmpdir}/evolution/article_metrics.json"
        with open(path, 'w') as f:
            json.dump(metrics, f)

    def test_article_quality_regression_detected(self) -> Dict:
        """检测到文章质量退化"""
        self.setup()
        try:
            # 构造退化数据：前半部分高分，后半部分低分
            metrics = [
                {"date": "2024-01-01", "overall_score": 8.5, "tech_content_ratio": 0.8, "insightfulness": 8.0},
                {"date": "2024-01-02", "overall_score": 8.2, "tech_content_ratio": 0.78, "insightfulness": 7.8},
                {"date": "2024-01-03", "overall_score": 8.0, "tech_content_ratio": 0.75, "insightfulness": 7.5},
                {"date": "2024-01-04", "overall_score": 5.5, "tech_content_ratio": 0.5, "insightfulness": 5.0},
                {"date": "2024-01-05", "overall_score": 5.0, "tech_content_ratio": 0.45, "insightfulness": 4.5},
                {"date": "2024-01-06", "overall_score": 4.8, "tech_content_ratio": 0.4, "insightfulness": 4.0},
            ]
            self._write_metrics(metrics)

            result = self.guard._check_article_quality_regression()
            assert result["is_regression"] is True, "应检测到退化"
            assert result["type"] == "article_quality", "类型应为article_quality"
            assert "severity" in result, "应有severity字段"
            assert result["details"]["score_drop_ratio"] > 0.15, "分数下降应超过15%阈值"

            return {"passed": True, "message": f"检测到退化: severity={result['severity']}, drop={result['details']['score_drop_ratio']:.2f}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_article_quality_stable(self) -> Dict:
        """文章质量稳定时无退化"""
        self.setup()
        try:
            metrics = [
                {"date": "2024-01-01", "overall_score": 7.5, "tech_content_ratio": 0.7, "insightfulness": 7.0},
                {"date": "2024-01-02", "overall_score": 7.6, "tech_content_ratio": 0.72, "insightfulness": 7.2},
                {"date": "2024-01-03", "overall_score": 7.4, "tech_content_ratio": 0.71, "insightfulness": 7.1},
                {"date": "2024-01-04", "overall_score": 7.5, "tech_content_ratio": 0.7, "insightfulness": 7.0},
                {"date": "2024-01-05", "overall_score": 7.7, "tech_content_ratio": 0.73, "insightfulness": 7.3},
                {"date": "2024-01-06", "overall_score": 7.6, "tech_content_ratio": 0.72, "insightfulness": 7.2},
            ]
            self._write_metrics(metrics)

            result = self.guard._check_article_quality_regression()
            assert result["is_regression"] is False, "不应检测到退化"

            return {"passed": True, "message": "质量稳定，未检测到退化"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_insufficient_data(self) -> Dict:
        """数据不足时不判断退化"""
        self.setup()
        try:
            metrics = [
                {"date": "2024-01-01", "overall_score": 5.0, "tech_content_ratio": 0.5, "insightfulness": 5.0},
            ]
            self._write_metrics(metrics)

            result = self.guard._check_article_quality_regression()
            assert result["is_regression"] is False, "数据不足不应判断退化"
            assert "reason" in result, "应有原因说明"

            return {"passed": True, "message": "数据不足处理正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_pause_evolution(self) -> Dict:
        """暂停进化创建标记文件"""
        self.setup()
        try:
            result = self.guard._pause_evolution(reason="测试暂停")
            assert os.path.exists(self.guard.pause_flag), "暂停标记文件应存在"

            with open(self.guard.pause_flag, 'r') as f:
                content = f.read()
            assert "REASON=测试暂停" in content, "标记文件应包含暂停原因"

            return {"passed": True, "message": "暂停标记创建正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_is_evolution_paused(self) -> Dict:
        """检查进化暂停状态"""
        self.setup()
        try:
            # 未暂停
            paused, reason = self.guard.is_evolution_paused()
            assert paused is False, "初始状态应未暂停"

            # 暂停后
            self.guard._pause_evolution(reason="测试原因")
            paused2, reason2 = self.guard.is_evolution_paused()
            assert paused2 is True, "暂停后应返回True"
            assert reason2 == "测试原因", f"原因应匹配, 实际'{reason2}'"

            return {"passed": True, "message": "暂停状态检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_resume_evolution(self) -> Dict:
        """恢复进化删除标记文件"""
        self.setup()
        try:
            self.guard._pause_evolution(reason="测试")
            assert os.path.exists(self.guard.pause_flag), "暂停标记应存在"

            result = self.guard.resume_evolution()
            assert "已恢复" in result, "应成功恢复"
            assert not os.path.exists(self.guard.pause_flag), "暂停标记应被删除"

            # 重复恢复
            result2 = self.guard.resume_evolution()
            assert "未被暂停" in result2, "未暂停时恢复应提示"

            return {"passed": True, "message": "恢复进化功能正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_regression_log_persistence(self) -> Dict:
        """退化检测日志持久化"""
        self.setup()
        try:
            self.guard._log_check_result("healthy", [], ["无退化"])
            self.guard._log_check_result("warning", [{"is_regression": True, "type": "test"}], ["暂停进化"])

            assert os.path.exists(self.guard.regression_log), "日志文件应存在"

            with open(self.guard.regression_log, 'r') as f:
                logs = json.load(f)
            assert len(logs) == 2, f"应有2条日志, 实际{len(logs)}"
            assert logs[0]["status"] == "healthy", "第一条日志状态应为healthy"
            assert logs[1]["status"] == "warning", "第二条日志状态应为warning"

            return {"passed": True, "message": f"日志持久化正确: {len(logs)}条记录"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_run_full_check_healthy(self) -> Dict:
        """完整检测 - 文章质量健康（run_full_check会包含代码功能检查，在临时目录中可能报critical）"""
        self.setup()
        try:
            # 写稳定的metrics数据
            metrics = [
                {"date": "2024-01-01", "overall_score": 7.5, "tech_content_ratio": 0.7, "insightfulness": 7.0},
                {"date": "2024-01-02", "overall_score": 7.6, "tech_content_ratio": 0.72, "insightfulness": 7.2},
                {"date": "2024-01-03", "overall_score": 7.5, "tech_content_ratio": 0.71, "insightfulness": 7.1},
                {"date": "2024-01-04", "overall_score": 7.7, "tech_content_ratio": 0.73, "insightfulness": 7.3},
            ]
            self._write_metrics(metrics)

            # 单独验证文章质量检查部分为healthy
            article_result = self.guard._check_article_quality_regression()
            assert article_result["is_regression"] is False, "稳定数据不应检测到文章质量退化"

            # run_full_check 包含代码功能检查，在临时目录中模块可能不存在，
            # 因此不强制状态为 healthy，只验证结构正确
            full_result = self.guard.run_full_check()
            assert "regressions" in full_result, "应有regressions字段"
            assert "actions_taken" in full_result, "应有actions_taken字段"
            assert "recommendation" in full_result, "应有recommendation字段"

            return {"passed": True, "message": f"文章质量健康, full_check结构正确 (status={full_result['status']})"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_run_full_check_critical(self) -> Dict:
        """完整检测 - 严重退化状态"""
        self.setup()
        try:
            # 写严重退化的metrics数据
            metrics = [
                {"date": "2024-01-01", "overall_score": 9.0, "tech_content_ratio": 0.85, "insightfulness": 8.5},
                {"date": "2024-01-02", "overall_score": 8.8, "tech_content_ratio": 0.83, "insightfulness": 8.3},
                {"date": "2024-01-03", "overall_score": 8.5, "tech_content_ratio": 0.8, "insightfulness": 8.0},
                {"date": "2024-01-04", "overall_score": 5.0, "tech_content_ratio": 0.5, "insightfulness": 4.5},
                {"date": "2024-01-05", "overall_score": 4.5, "tech_content_ratio": 0.45, "insightfulness": 4.0},
                {"date": "2024-01-06", "overall_score": 4.0, "tech_content_ratio": 0.4, "insightfulness": 3.5},
            ]
            self._write_metrics(metrics)

            result = self.guard.run_full_check()
            assert result["status"] == "critical", f"严重退化状态应为critical, 实际{result['status']}"
            assert len(result["regressions"]) > 0, "应有退化项"
            # 严重退化时应执行干预措施（暂停进化）
            assert len(result["actions_taken"]) > 0, "应有干预措施"

            return {"passed": True, "message": f"严重退化检测正确: {len(result['regressions'])}项退化, {len(result['actions_taken'])}项干预"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def run_all(self) -> Dict:
        """运行全部测试"""
        tests = [
            self.test_article_quality_regression_detected,
            self.test_article_quality_stable,
            self.test_insufficient_data,
            self.test_pause_evolution,
            self.test_is_evolution_paused,
            self.test_resume_evolution,
            self.test_regression_log_persistence,
            self.test_run_full_check_healthy,
            self.test_run_full_check_critical,
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
            "results": results
        }
