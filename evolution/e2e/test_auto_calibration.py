# -*- coding: utf-8 -*-
"""
自动校准系统端到端测试
验证：质量记录→分数计算→参数推荐→数据持久化
"""

import json
import os
import shutil
import tempfile
from typing import Dict, List

from evolution.auto_calibration import AutoCalibration


class TestAutoCalibration:
    """自动校准系统端到端测试"""

    def setup(self):
        """创建临时目录隔离测试数据"""
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_ac_")
        os.makedirs(f"{self.tmpdir}/evolution", exist_ok=True)
        self.cal = AutoCalibration(trendradar_path=self.tmpdir)

    def teardown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_record_quality_and_persist(self) -> Dict:
        """记录质量数据并验证文件持久化"""
        self.setup()
        try:
            self.cal.record_quality(
                task_type="article_generation",
                provider="deepseek",
                parameters={"temperature": 0.7, "max_tokens": 4000},
                quality_metrics={
                    "completeness": 0.9,
                    "coherence": 0.8,
                    "relevance": 0.85,
                    "length_ok": True,
                    "has_errors": False
                }
            )

            # 验证内存中有记录
            assert len(self.cal.quality_records) == 1, "内存中应有1条记录"

            # 验证文件已写入
            assert os.path.exists(self.cal.quality_file), "质量日志文件应存在"
            with open(self.cal.quality_file, 'r') as f:
                data = json.load(f)
            assert len(data) == 1, "文件中应有1条记录"
            assert data[0]["task_type"] == "article_generation"
            assert data[0]["provider"] == "deepseek"

            return {"passed": True, "message": "质量记录与持久化一致"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_overall_score_calculation(self) -> Dict:
        """验证综合分数计算权重正确"""
        self.setup()
        try:
            # 满分情况
            score = self.cal._calc_overall_score({
                "completeness": 1.0, "coherence": 1.0, "relevance": 1.0,
                "length_ok": True, "has_errors": False
            })
            assert abs(score - 1.0) < 0.01, f"满分应为1.0, 实际{score}"

            # 零分情况
            score_zero = self.cal._calc_overall_score({
                "completeness": 0.0, "coherence": 0.0, "relevance": 0.0,
                "length_ok": False, "has_errors": True
            })
            assert abs(score_zero - 0.0) < 0.01, f"零分应为0.0, 实际{score_zero}"

            # 部分分：验证权重
            # completeness=1.0*0.3 + coherence=0.0*0.25 + relevance=0.0*0.25 +
            # length_ok=True*0.1 + has_errors=False*0.1 = 0.3+0+0+0.1+0.1=0.5
            score_partial = self.cal._calc_overall_score({
                "completeness": 1.0, "coherence": 0.0, "relevance": 0.0,
                "length_ok": True, "has_errors": False
            })
            expected = 0.3 + 0.1 + 0.1
            assert abs(score_partial - expected) < 0.01, f"部分分应为{expected}, 实际{score_partial}"

            return {"passed": True, "message": "综合分数计算权重正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_optimal_params_recommendation(self) -> Dict:
        """记录多条数据后获取推荐参数"""
        self.setup()
        try:
            # 写入5条相同任务类型数据（触发校准的最低门槛）
            for i in range(5):
                self.cal.record_quality(
                    task_type="test_task",
                    provider="deepseek",
                    parameters={"temperature": 0.3 + i * 0.1, "max_tokens": 4000},
                    quality_metrics={
                        "completeness": 0.9,
                        "coherence": 0.8,
                        "relevance": 0.85,
                        "length_ok": True,
                        "has_errors": False
                    }
                )

            # 验证校准数据已生成
            assert "test_task" in self.cal.calibration, "应有test_task的校准数据"
            cal_data = self.cal.calibration["test_task"]
            assert "recommendations" in cal_data, "应有推荐参数"
            assert cal_data["sample_size"] >= 5, "样本数应≥5"

            # 验证可以获取最优参数
            params = self.cal.get_optimal_params("test_task", base_params={"max_tokens": 2000})
            assert "max_tokens" in params, "应返回max_tokens参数"

            return {"passed": True, "message": "参数推荐系统工作正常"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_recommendation_confidence_threshold(self) -> Dict:
        """低置信度参数不应被应用"""
        self.setup()
        try:
            # 直接写入低置信度校准数据
            self.cal.calibration["low_conf_task"] = {
                "recommendations": {
                    "temperature": {
                        "recommended_value": 0.1,
                        "expected_score": 0.9,
                        "confidence": 0.1  # 低于0.3阈值
                    }
                },
                "last_calibrated": "2024-01-01T00:00:00",
                "sample_size": 2
            }

            # 获取参数时低置信度不应被应用
            params = self.cal.get_optimal_params("low_conf_task", base_params={"temperature": 0.7})
            assert params.get("temperature") == 0.7, "低置信度参数不应覆盖原有值"

            # 高置信度应被应用
            self.cal.calibration["high_conf_task"] = {
                "recommendations": {
                    "temperature": {
                        "recommended_value": 0.5,
                        "expected_score": 0.9,
                        "confidence": 0.8  # 高于0.3阈值
                    }
                },
                "last_calibrated": "2024-01-01T00:00:00",
                "sample_size": 20
            }
            params2 = self.cal.get_optimal_params("high_conf_task", base_params={"temperature": 0.7})
            assert params2.get("temperature") == 0.5, "高置信度参数应被应用"

            return {"passed": True, "message": "置信度阈值过滤正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_quality_records_limit(self) -> Dict:
        """质量记录只保留最近100条"""
        self.setup()
        try:
            for i in range(105):
                self.cal.record_quality(
                    task_type="bulk_task",
                    provider="deepseek",
                    parameters={"temperature": 0.5},
                    quality_metrics={
                        "completeness": 0.5, "coherence": 0.5, "relevance": 0.5,
                        "length_ok": True, "has_errors": False
                    }
                )

            assert len(self.cal.quality_records) == 100, f"应只保留100条,实际{len(self.cal.quality_records)}"

            # 验证文件也只保留100条
            with open(self.cal.quality_file, 'r') as f:
                data = json.load(f)
            assert len(data) == 100, f"文件中应只保留100条,实际{len(data)}"

            return {"passed": True, "message": "记录上限100条正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_calibration_report_format(self) -> Dict:
        """校准报告格式正确"""
        self.setup()
        try:
            # 构造一些校准数据
            self.cal.calibration["task_a"] = {
                "recommendations": {
                    "temperature": {"recommended_value": 0.5, "expected_score": 0.9, "confidence": 0.8}
                },
                "last_calibrated": "2024-01-15T10:00:00",
                "sample_size": 10
            }

            report = self.cal.generate_calibration_report()
            assert "自动校准报告" in report, "报告标题应包含'自动校准报告'"
            assert "task_a" in report, "报告应包含task_a"
            assert "样本数: 10" in report, "报告应显示样本数"
            assert "temperature" in report, "报告应包含参数名"

            return {"passed": True, "message": "校准报告格式正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def run_all(self) -> Dict:
        """运行全部测试"""
        tests = [
            self.test_record_quality_and_persist,
            self.test_overall_score_calculation,
            self.test_optimal_params_recommendation,
            self.test_recommendation_confidence_threshold,
            self.test_quality_records_limit,
            self.test_calibration_report_format,
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
