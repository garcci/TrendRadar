# -*- coding: utf-8 -*-
"""
仓库体积监控端到端测试
验证：大小计算、大文件扫描、文件分布分析
"""

import os
import tempfile
from typing import Dict

from evolution.repo_size_monitor import RepoSizeMonitor


class TestRepoSizeMonitor:
    """仓库体积监控端到端测试"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="trendradar_test_repo_")
        self.monitor = RepoSizeMonitor(self.temp_dir)

    def _cleanup(self):
        """清理临时目录并在下次测试前重建"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = tempfile.mkdtemp(prefix="trendradar_test_repo_")
        self.monitor = RepoSizeMonitor(self.temp_dir)

    def test_get_total_size(self) -> Dict:
        """获取仓库总大小"""
        try:
            # 创建一些测试文件
            for i in range(3):
                with open(os.path.join(self.temp_dir, f"test_{i}.txt"), "w") as f:
                    f.write("A" * 1000)

            size = self.monitor.get_total_size()
            assert size > 0, "总大小应大于0"
            assert size >= 3000, f"总大小应至少3000字节, 实际{size}"
            return {"passed": True, "message": f"总大小: {size} 字节 ({size / 1024:.1f} KB)"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_get_total_size_empty(self) -> Dict:
        """空目录大小为0或极小"""
        try:
            size = self.monitor.get_total_size()
            assert size >= 0, "大小不应为负"
            return {"passed": True, "message": f"空目录大小: {size} 字节"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_scan_big_files(self) -> Dict:
        """扫描大文件"""
        try:
            # 创建一个大文件 (>100KB)
            big_file = os.path.join(self.temp_dir, "big_file.txt")
            with open(big_file, "w") as f:
                f.write("B" * 200 * 1024)  # 200KB

            # 创建一个小文件
            small_file = os.path.join(self.temp_dir, "small.txt")
            with open(small_file, "w") as f:
                f.write("small")

            big_files = self.monitor.scan_big_files(threshold_kb=100)
            assert len(big_files) >= 1, f"应至少发现1个大文件, 实际{len(big_files)}"
            assert any("big_file" in bf["path"] for bf in big_files), "应发现 big_file.txt"
            assert all(bf["size_kb"] >= 100 for bf in big_files), "所有报告的文件应>=100KB"

            return {"passed": True, "message": f"发现 {len(big_files)} 个大文件"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_scan_big_files_empty(self) -> Dict:
        """无大文件时返回空列表"""
        try:
            # 创建一个小文件
            with open(os.path.join(self.temp_dir, "small.txt"), "w") as f:
                f.write("tiny")

            big_files = self.monitor.scan_big_files(threshold_kb=100)
            assert len(big_files) == 0, f"应无大文件, 实际{len(big_files)}"
            return {"passed": True, "message": "无大文件，返回空列表"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_analyze_file_distribution(self) -> Dict:
        """分析文件类型分布"""
        try:
            # 创建不同类型的文件
            with open(os.path.join(self.temp_dir, "data.json"), "w") as f:
                f.write("{}" * 500)
            with open(os.path.join(self.temp_dir, "image.png"), "wb") as f:
                f.write(b"PNG" * 1000)
            with open(os.path.join(self.temp_dir, "readme.txt"), "w") as f:
                f.write("readme")

            result = self.monitor.analyze_file_distribution()
            dist = result["types"]
            assert len(dist) > 0, "应至少有一种文件类型"

            # 检查JSON类型是否存在
            json_types = [d for d in dist if d["type"] == "JSON数据"]
            assert len(json_types) > 0, "应检测到JSON数据类型"

            # 检查百分比总和约为100
            total_pct = sum(d["percentage"] for d in dist)
            assert 95 <= total_pct <= 105, f"百分比总和应约100, 实际{total_pct}"

            return {"passed": True, "message": f"检测到 {len(dist)} 种文件类型"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_analyze_file_distribution_empty(self) -> Dict:
        """空目录的文件分布"""
        try:
            result = self.monitor.analyze_file_distribution()
            dist = result["types"]
            assert len(dist) == 0 or all(d["count"] == 0 for d in dist), "空目录应无文件"
            return {"passed": True, "message": "空目录分布正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_size_thresholds(self) -> Dict:
        """体积阈值常量定义正确"""
        try:
            assert self.monitor.SIZE_THRESHOLDS["healthy"] == 20
            assert self.monitor.SIZE_THRESHOLDS["warning"] == 50
            assert self.monitor.SIZE_THRESHOLDS["critical"] == 100
            assert self.monitor.SIZE_THRESHOLDS["github_limit"] == 1024
            assert self.monitor.BIG_FILE_THRESHOLD == 100
            return {"passed": True, "message": "阈值定义正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_git_size_no_git(self) -> Dict:
        """无.git目录时返回0"""
        try:
            size = self.monitor.get_git_size()
            assert size == 0, f"无.git目录时应为0, 实际{size}"
            return {"passed": True, "message": "无.git目录返回0"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_big_file_info_fields(self) -> Dict:
        """大文件信息字段完整"""
        try:
            big_file = os.path.join(self.temp_dir, "test_big.json")
            with open(big_file, "w") as f:
                f.write("X" * 150 * 1024)

            big_files = self.monitor.scan_big_files(threshold_kb=100)
            assert len(big_files) >= 1, "应发现大文件"

            bf = big_files[0]
            required_fields = ["path", "size_kb", "size_mb", "type", "extension"]
            for field in required_fields:
                assert field in bf, f"缺少字段: {field}"

            assert bf["size_mb"] == round(bf["size_kb"] / 1024, 2), "MB转换正确"
            return {"passed": True, "message": f"字段完整: {', '.join(required_fields)}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def test_distribution_percentage_calculation(self) -> Dict:
        """百分比计算正确"""
        try:
            with open(os.path.join(self.temp_dir, "a.json"), "w") as f:
                f.write("A" * 1024)
            with open(os.path.join(self.temp_dir, "b.json"), "w") as f:
                f.write("B" * 1024)
            with open(os.path.join(self.temp_dir, "c.png"), "wb") as f:
                f.write(b"C" * 2048)

            result = self.monitor.analyze_file_distribution()
            dist = result["types"]
            json_entry = next((d for d in dist if d["type"] == "JSON数据"), None)
            png_entry = next((d for d in dist if d["type"] == "PNG图片"), None)

            if json_entry and png_entry:
                # JSON: 2KB, PNG: 2KB, total: 4KB
                assert json_entry["percentage"] == 50.0, f"JSON应占50%, 实际{json_entry['percentage']}"
                assert png_entry["percentage"] == 50.0, f"PNG应占50%, 实际{png_entry['percentage']}"

            return {"passed": True, "message": "百分比计算正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            self._cleanup()

    def run_all(self) -> Dict:
        """运行全部测试"""
        tests = [
            self.test_get_total_size,
            self.test_get_total_size_empty,
            self.test_scan_big_files,
            self.test_scan_big_files_empty,
            self.test_analyze_file_distribution,
            self.test_analyze_file_distribution_empty,
            self.test_size_thresholds,
            self.test_git_size_no_git,
            self.test_big_file_info_fields,
            self.test_distribution_percentage_calculation,
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
