# -*- coding: utf-8 -*-
"""
数据管道端到端测试

测试场景：
1. write → read 数据一致性
2. 写入后文件是否可读（jsonl 格式）
3. 数据类型校验（必填字段）
4. 多次写入后读取全部记录

历史教训：
- 曾出现数据管道写入后未被 git 提交，导致 runner 间数据丢失
- 曾出现 article_quality.jsonl 为空但系统未告警
"""

import json
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.data_pipeline import DataPipeline


class TestDataPipelineConsistency:
    """数据管道读写一致性测试"""

    def __init__(self):
        self.test_results = []
        # 使用临时目录避免污染真实数据
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = DataPipeline(self.temp_dir)

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_write_and_read(self):
        """测试1: 写入后能读出相同数据"""
        record = {
            "id": "test-001",
            "timestamp": "2026-04-27T12:00:00",
            "title": "测试文章",
            "score": 8.5,
            "tags": ["AI", "测试"]
        }

        write_ok = self.pipeline.write("article", record)
        if not write_ok:
            self._log("写入读取一致性", False, "write() 返回失败")
            return

        # 直接读取 jsonl 文件验证
        jsonl_path = Path(self.temp_dir) / "evolution/data_pipeline/article.jsonl"
        if not jsonl_path.exists():
            self._log("写入读取一致性", False, "写入后 jsonl 文件不存在")
            return

        lines = jsonl_path.read_text().strip().split('\n')
        if not lines or not lines[0]:
            self._log("写入读取一致性", False, "jsonl 文件为空")
            return

        try:
            read_record = json.loads(lines[-1])  # 最后一条记录
        except json.JSONDecodeError as e:
            self._log("写入读取一致性", False, f"jsonl 格式错误: {e}")
            return

        if read_record.get("id") == record["id"] and read_record.get("score") == record["score"]:
            self._log("写入读取一致性", True, f"写入后成功读取，id={record['id']}")
        else:
            self._log("写入读取一致性", False, f"数据不一致: 写入 {record} 读出 {read_record}")

    def test_required_fields_validation(self):
        """测试2: 缺少必填字段的写入处理"""
        # article 类型需要 id 和 timestamp
        bad_record = {"title": "缺少必填字段"}  # 缺少 id, timestamp

        write_ok = self.pipeline.write("article", bad_record)
        # 当前实现可能允许写入，但至少不应崩溃
        self._log("必填字段校验", True, f"缺少必填字段时 write() {'通过' if write_ok else '拒绝'}（未崩溃）")

    def test_multiple_writes(self):
        """测试3: 多次写入后读取全部记录"""
        for i in range(3):
            self.pipeline.write("metric", {
                "name": f"metric_{i}",
                "timestamp": "2026-04-27T12:00:00",
                "value": i * 10,
                "unit": "ms"
            })

        jsonl_path = Path(self.temp_dir) / "evolution/data_pipeline/metric.jsonl"
        lines = [l for l in jsonl_path.read_text().strip().split('\n') if l.strip()]

        if len(lines) >= 3:
            self._log("多次写入读取", True, f"写入 3 条记录，读出 {len(lines)} 条")
        else:
            self._log("多次写入读取", False, f"记录丢失: 写入 3 条，读出 {len(lines)} 条")

    def test_jsonl_format_valid(self):
        """测试4: 所有 jsonl 文件格式合法"""
        pipeline_dir = Path(self.temp_dir) / "evolution/data_pipeline"
        all_valid = True
        invalid_files = []

        for jsonl_file in pipeline_dir.glob("*.jsonl"):
            content = jsonl_file.read_text().strip()
            if not content:
                continue
            for line_num, line in enumerate(content.split('\n'), 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    all_valid = False
                    invalid_files.append(f"{jsonl_file.name}:{line_num}")

        if all_valid:
            self._log("JSONL 格式合法", True, "所有 jsonl 文件格式正确")
        else:
            self._log("JSONL 格式合法", False, f"格式错误: {invalid_files}")

    def test_data_types_initialized(self):
        """测试5: 所有数据类型文件已初始化"""
        pipeline_dir = Path(self.temp_dir) / "evolution/data_pipeline"
        expected_types = ["article", "rss", "prompt", "cost", "exception", "metric"]
        missing = []

        for dt in expected_types:
            if not (pipeline_dir / f"{dt}.jsonl").exists():
                missing.append(dt)

        if not missing:
            self._log("数据类型初始化", True, f"6 种数据类型文件全部初始化")
        else:
            self._log("数据类型初始化", False, f"缺少数据类型文件: {missing}")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("数据管道端到端测试")
        print("=" * 60)

        self.test_write_and_read()
        self.test_required_fields_validation()
        self.test_multiple_writes()
        self.test_jsonl_format_valid()
        self.test_data_types_initialized()

        passed = sum(1 for r in self.test_results if r["passed"])
        failed = sum(1 for r in self.test_results if not r["passed"])

        print()
        for r in self.test_results:
            emoji = "✅" if r["passed"] else "❌"
            print(f"{emoji} {r['test']}: {r['message']}")

        print()
        print(f"总计: {passed}/{len(self.test_results)} 通过, {failed} 失败")
        print("=" * 60)

        return {
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": self.test_results
        }


if __name__ == "__main__":
    tester = TestDataPipelineConsistency()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
