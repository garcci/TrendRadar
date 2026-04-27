# -*- coding: utf-8 -*-
"""
异常监控端到端测试

测试场景：
1. record_exception → 异常被正确记录到知识库
2. 记录后能从知识库读出
3. 异常分类是否正确
4. 重复异常指纹计数是否正确
5. monitor 装饰器是否能捕获异常

历史教训：
- 曾出现异常记录后未被正确分类
- 曾出现知识库文件损坏后无法加载
"""

import json
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.exception_monitor import ExceptionMonitor


class TestExceptionMonitorConsistency:
    """异常监控读写一致性测试"""

    def __init__(self):
        self.test_results = []
        self.temp_dir = tempfile.mkdtemp()
        # 确保 evolution 目录存在
        import os
        os.makedirs(f"{self.temp_dir}/evolution", exist_ok=True)
        self.monitor = ExceptionMonitor(self.temp_dir)

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_record_and_read(self):
        """测试1: 记录后能读出"""
        record = self.monitor.record_exception(
            exc_type="ValueError",
            exc_msg="测试异常",
            stack_trace="Traceback: test.py:1",
            context="test_context",
            module="test_module"
        )

        # 检查记录是否包含必要字段
        required_fields = ["timestamp", "fingerprint", "type", "message", "category"]
        has_all = all(f in record for f in required_fields)

        # 检查知识库文件是否存在且可读
        kb_file = Path(self.temp_dir) / "evolution" / "exception_knowledge.json"
        if kb_file.exists():
            try:
                with open(kb_file, 'r') as f:
                    kb = json.load(f)
                has_record = len(kb.get("exceptions", [])) > 0
            except Exception:
                has_record = False
        else:
            has_record = False

        if has_all and has_record:
            self._log("记录读取一致性", True, f"异常已记录，指纹={record['fingerprint'][:8]}...")
        else:
            self._log("记录读取一致性", False, f"字段完整={has_all}, 知识库有记录={has_record}")

    def test_exception_classification(self):
        """测试2: 异常分类是否正确"""
        test_cases = [
            ("ConnectionError", "无法连接到服务器", "network"),
            ("TimeoutError", "请求超时", "network"),  # Timeout 归到 network
            ("ValueError", "参数无效", "unknown"),  # 无匹配关键词
        ]

        all_correct = True
        for exc_type, exc_msg, expected in test_cases:
            record = self.monitor.record_exception(
                exc_type=exc_type,
                exc_msg=exc_msg,
                stack_trace="test"
            )
            if record["category"] != expected:
                all_correct = False
                break

        if all_correct:
            self._log("异常分类", True, "网络/超时/逻辑异常分类正确")
        else:
            self._log("异常分类", False, f"异常分类不正确")

    def test_fingerprint_counting(self):
        """测试3: 相同异常指纹计数递增"""
        # 记录 3 次相同的异常
        for _ in range(3):
            self.monitor.record_exception(
                exc_type="ValueError",
                exc_msg="同样的错误",
                stack_trace="同样的堆栈"
            )

        kb_file = Path(self.temp_dir) / "evolution" / "exception_knowledge.json"
        with open(kb_file, 'r') as f:
            kb = json.load(f)

        patterns = kb.get("patterns", {})
        # 找到对应的模式
        found = False
        for fp, info in patterns.items():
            if info.get("message_pattern") == "同样的错误":
                if info.get("count", 0) >= 3:
                    found = True
                    break

        if found:
            self._log("指纹计数", True, "相同异常指纹计数正确递增")
        else:
            self._log("指纹计数", False, "相同异常指纹计数未正确递增")

    def test_monitor_decorator(self):
        """测试4: monitor 装饰器能捕获异常"""
        captured = []

        @self.monitor.monitor(context="test_decorator", module="test")
        def raise_error():
            raise RuntimeError("装饰器测试异常")

        try:
            raise_error()
        except RuntimeError:
            pass

        # 检查是否记录了异常
        kb_file = Path(self.temp_dir) / "evolution" / "exception_knowledge.json"
        with open(kb_file, 'r') as f:
            kb = json.load(f)

        has_decorator_exception = any(
            e.get("context") == "test_decorator" and "装饰器测试异常" in e.get("message", "")
            for e in kb.get("exceptions", [])
        )

        if has_decorator_exception:
            self._log("装饰器捕获", True, "monitor 装饰器正确捕获并记录异常")
        else:
            self._log("装饰器捕获", False, "monitor 装饰器未正确记录异常")

    def test_statistics(self):
        """测试5: 统计功能正常"""
        self.monitor.record_exception(
            exc_type="TypeError",
            exc_msg="统计测试",
            stack_trace="test"
        )

        stats = self.monitor.get_exception_statistics(hours=24)

        if "message" not in stats or stats.get("message") != "No exceptions in the specified period":
            self._log("异常统计", True, "统计功能正常返回数据")
        else:
            self._log("异常统计", False, "统计功能未返回记录的数据")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("异常监控端到端测试")
        print("=" * 60)

        self.test_record_and_read()
        self.test_exception_classification()
        self.test_fingerprint_counting()
        self.test_monitor_decorator()
        self.test_statistics()

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
    tester = TestExceptionMonitorConsistency()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
