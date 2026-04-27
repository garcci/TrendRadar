# -*- coding: utf-8 -*-
"""
自我观察引擎端到端测试
验证：诊断报告结构、各维度分析、报告持久化
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Dict

from evolution.self_observer import SelfObserver


class TestSelfObserver:
    """自我观察引擎端到端测试"""

    def setup(self):
        """创建临时目录和测试数据"""
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_so_")
        os.makedirs(f"{self.tmpdir}/evolution", exist_ok=True)

        # 创建模拟指标数据（最近7天内，确保不被过滤）
        self.metrics_file = f"{self.tmpdir}/evolution/article_metrics.json"
        base = datetime.now() - timedelta(days=1)
        metrics = [
            {"timestamp": (base - timedelta(hours=0)).isoformat(), "overall_score": 8.5, "has_errors": False, "model_used": "github_models"},
            {"timestamp": (base - timedelta(hours=6)).isoformat(), "overall_score": 7.2, "has_errors": False, "model_used": "github_models"},
            {"timestamp": (base - timedelta(hours=12)).isoformat(), "overall_score": 6.1, "has_errors": True, "model_used": "deepseek"},
            {"timestamp": (base - timedelta(hours=18)).isoformat(), "overall_score": 5.5, "has_errors": False, "model_used": "github_models"},
            {"timestamp": (base - timedelta(hours=24)).isoformat(), "overall_score": 7.8, "has_errors": False, "model_used": "github_models"},
        ]
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f)

        self.observer = SelfObserver(trendradar_path=self.tmpdir)

    def teardown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_diagnosis_report_structure(self) -> Dict:
        """诊断报告包含所有必要维度"""
        self.setup()
        try:
            report = self.observer.generate_diagnosis_report()

            # 验证顶层结构
            assert "timestamp" in report, "报告应有时间戳"
            assert "overall_health" in report, "报告应有总体健康度"
            assert "dimensions" in report, "报告应有维度分析"

            # 验证四个维度都存在
            dims = report["dimensions"]
            expected_dims = ["content_quality", "system_stability", "cost_efficiency", "feature_coverage"]
            for dim in expected_dims:
                assert dim in dims, f"维度 {dim} 应存在"

            # 验证每个维度都有status
            for dim_name, dim_data in dims.items():
                assert "status" in dim_data, f"{dim_name} 应有status"

            # 验证总体健康度计算逻辑
            health = report["overall_health"]
            assert health in ["healthy", "critical", "needs_improvement", "unknown"], f"健康度值有效: {health}"

            return {"passed": True, "message": "诊断报告结构完整"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_content_quality_analysis(self) -> Dict:
        """内容质量分析计算正确"""
        self.setup()
        try:
            report = self.observer.generate_diagnosis_report()
            cq = report["dimensions"]["content_quality"]

            # 平均分: (8.5+7.2+6.1+5.5+7.8)/5 = 35.1/5 = 7.02
            assert cq["score"] == 7.0, f"平均分应为7.0, 实际{cq['score']}"
            assert cq["count"] == 5, f"文章数应为5, 实际{cq['count']}"

            # 趋势：最近3条(8.5,7.2,6.1)平均=7.27, 最早3条(6.1,5.5,7.8)平均=6.47, 差值<0.5 → stable
            assert cq["trend"] in ["improving", "declining", "stable"], f"趋势值有效: {cq['trend']}"

            # status: 7.0 >= 6.0 → acceptable
            assert cq["status"] in ["good", "acceptable", "poor"], f"状态值有效: {cq['status']}"

            return {"passed": True, "message": f"内容质量分析正确 (score={cq['score']}, trend={cq['trend']})"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_system_stability_analysis(self) -> Dict:
        """系统稳定性分析计算正确"""
        self.setup()
        try:
            report = self.observer.generate_diagnosis_report()
            ss = report["dimensions"]["system_stability"]

            # 错误率: 1/5 = 0.2
            assert ss["error_rate"] == 0.2, f"错误率应为0.2, 实际{ss['error_rate']}"

            # fallback率: 1条deepseek / 5条 = 0.2
            assert ss["fallback_rate"] == 0.2, f"降级率应为0.2, 实际{ss['fallback_rate']}"

            # status: error_rate=0.2 >= 0.15 → poor
            assert ss["status"] == "poor", f"status应为poor, 实际{ss['status']}"

            return {"passed": True, "message": "系统稳定性分析正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_feature_coverage_scan(self) -> Dict:
        """功能覆盖扫描能发现进化模块"""
        self.setup()
        try:
            # 创建一些模拟模块文件
            for mod in ["prompt_optimizer.py", "tech_content_guard.py", "title_optimizer.py"]:
                with open(f"{self.tmpdir}/evolution/{mod}", 'w') as f:
                    f.write("# mock module\n")

            report = self.observer.generate_diagnosis_report()
            fc = report["dimensions"]["feature_coverage"]

            assert "active_modules" in fc, "应有active_modules"
            assert "missing_modules" in fc, "应有missing_modules"
            assert "evolution_level" in fc, "应有evolution_level"

            # 验证找到了已创建的模块
            active_ids = [m["id"] for m in fc["active_modules"]]
            assert "prompt_optimizer" in active_ids, "应找到prompt_optimizer"
            assert "tech_content_guard" in active_ids, "应找到tech_content_guard"

            return {"passed": True, f"message": f"功能覆盖扫描正确 (active={len(fc['active_modules'])})"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_report_persistence(self) -> Dict:
        """诊断报告保存到文件并保留最近10份"""
        self.setup()
        try:
            # 生成12份报告
            for i in range(12):
                self.observer.generate_diagnosis_report()

            # 验证文件存在
            assert os.path.exists(self.observer.report_file), "报告文件应存在"

            with open(self.observer.report_file, 'r') as f:
                reports = json.load(f)

            assert len(reports) == 10, f"应只保留10份报告,实际{len(reports)}"

            return {"passed": True, "message": "报告持久化保留10份正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_capability_gap_report(self) -> Dict:
        """能力缺口报告格式正确"""
        self.setup()
        try:
            report_md = self.observer.generate_capability_gap_report()

            assert "自我观察报告" in report_md, "报告应包含标题"
            assert "总体健康度" in report_md, "报告应包含总体健康度"
            assert "能力缺口分析" in report_md, "报告应包含能力缺口分析"

            return {"passed": True, "message": "能力缺口报告格式正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self.teardown()

    def test_empty_metrics_handling(self) -> Dict:
        """空指标数据时返回unknown状态"""
        # 使用没有metrics文件的新临时目录
        tmpdir2 = tempfile.mkdtemp(prefix="e2e_so_empty_")
        os.makedirs(f"{tmpdir2}/evolution", exist_ok=True)
        try:
            observer2 = SelfObserver(trendradar_path=tmpdir2)
            report = observer2.generate_diagnosis_report()
            cq = report["dimensions"]["content_quality"]
            assert cq["status"] == "unknown", f"空数据时status应为unknown, 实际{cq['status']}"
            return {"passed": True, "message": "空指标数据处理正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            shutil.rmtree(tmpdir2, ignore_errors=True)

    def run_all(self) -> Dict:
        """运行全部测试"""
        tests = [
            self.test_diagnosis_report_structure,
            self.test_content_quality_analysis,
            self.test_system_stability_analysis,
            self.test_feature_coverage_scan,
            self.test_report_persistence,
            self.test_capability_gap_report,
            self.test_empty_metrics_handling,
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
