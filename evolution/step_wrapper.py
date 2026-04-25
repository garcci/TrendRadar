# -*- coding: utf-8 -*-
"""
进化步骤包装器 — 统一超时控制、异常捕获与降级处理

功能：
1. 为每个进化步骤设置独立超时（默认60s，可配置）
2. 捕获异常并记录到异常知识库，不中断整个 Workflow
3. 测量每个步骤的运行时间，识别性能瓶颈
4. 步骤失败时返回降级结果而非崩溃

使用方式：
    uv run python -m evolution.step_wrapper --module health_check --func get_health_report --timeout 30
"""

import argparse
import importlib
import json
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional


class StepWrapper:
    """进化步骤包装器"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.metrics_file = os.path.join(trendradar_path, "evolution", "step_metrics.json")
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)

    def run(
        self,
        module_name: str,
        function_name: str = None,
        timeout: int = 60,
        args: tuple = (),
        kwargs: dict = None,
    ) -> Dict:
        """
        执行进化步骤，带超时和异常处理

        Returns:
            {
                "success": bool,
                "result": Any,
                "elapsed_seconds": float,
                "error": str or None,
                "timeout": bool,
            }
        """
        kwargs = kwargs or {}
        start = time.time()
        result = {
            "success": False,
            "result": None,
            "elapsed_seconds": 0.0,
            "error": None,
            "timeout": False,
            "module": module_name,
            "function": function_name,
            "timestamp": datetime.now().isoformat(),
        }

        # 超时处理（仅 Unix-like 系统支持 SIGALRM）
        use_alarm = hasattr(__import__("signal"), "SIGALRM")
        old_handler = None

        def timeout_handler(signum, frame):
            raise TimeoutError(f"步骤超时 ({timeout}s)")

        try:
            if use_alarm and timeout > 0:
                import signal
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)

            # 动态导入模块
            module = importlib.import_module(f"evolution.{module_name}")

            # 查找目标函数
            if function_name:
                func = getattr(module, function_name)
            else:
                # 自动查找常见的入口函数
                candidates = ["run", "get_report", "generate_report", "check", "verify"]
                func = None
                for candidate in candidates:
                    if hasattr(module, candidate):
                        func = getattr(module, candidate)
                        result["function"] = candidate
                        break

            if not func or not callable(func):
                raise ValueError(f"模块 {module_name} 中未找到可调用函数")

            # 执行
            func_result = func(*args, **kwargs)
            result["success"] = True
            result["result"] = func_result

            # 打印结果（如果是字符串）
            if isinstance(func_result, str):
                print(func_result)

        except TimeoutError as e:
            result["timeout"] = True
            result["error"] = str(e)
            print(f"⏱️ [{module_name}] 超时: {e}", file=sys.stderr)
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            print(f"❌ [{module_name}] 失败: {e}", file=sys.stderr)
            # 记录详细 traceback
            traceback.print_exc()

            # 记录到异常知识库
            self._record_exception(module_name, result["error"])
        finally:
            if use_alarm and timeout > 0:
                import signal
                signal.alarm(0)
                if old_handler:
                    signal.signal(signal.SIGALRM, old_handler)

        elapsed = time.time() - start
        result["elapsed_seconds"] = round(elapsed, 2)

        # 记录指标
        self._save_metric(result)

        status = "✅" if result["success"] else ("⏱️" if result["timeout"] else "❌")
        print(f"{status} [{module_name}] 完成 ({elapsed:.1f}s)")

        return result

    def _record_exception(self, module_name: str, error: str):
        """记录异常到知识库"""
        try:
            from evolution.exception_monitor import ExceptionMonitor
            monitor = ExceptionMonitor(self.trendradar_path)
            monitor.record_exception(
                "StepWrapperError",
                f"进化步骤失败: {module_name}",
                error,
                context=f"module:{module_name}",
                module="step_wrapper",
            )
            monitor._save_knowledge_base()
        except Exception:
            pass

    def _save_metric(self, result: Dict):
        """保存步骤执行指标"""
        try:
            metrics = []
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    metrics = json.load(f)

            # 只保留最近 200 条记录
            metrics.append(result)
            metrics = metrics[-200:]

            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def get_step_summary(trendradar_path: str = ".") -> str:
    """获取步骤执行摘要"""
    metrics_file = os.path.join(trendradar_path, "evolution", "step_metrics.json")
    if not os.path.exists(metrics_file):
        return "暂无执行记录"

    try:
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        if not metrics:
            return "暂无执行记录"

        # 统计最近 24 小时
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        recent = [m for m in metrics if m.get("timestamp", "") > cutoff]

        total = len(recent)
        success = len([m for m in recent if m.get("success")])
        timeouts = len([m for m in recent if m.get("timeout")])
        failures = total - success - timeouts

        # 最慢的步骤
        sorted_by_time = sorted(recent, key=lambda x: x.get("elapsed_seconds", 0), reverse=True)
        slowest = sorted_by_time[:3]

        lines = ["# 步骤执行摘要（最近24小时）"]
        lines.append(f"总执行: {total} | ✅成功: {success} | ❌失败: {failures} | ⏱️超时: {timeouts}")
        lines.append("")
        lines.append("最慢步骤:")
        for s in slowest:
            lines.append(f"  - {s['module']} ({s.get('function', '?')}): {s['elapsed_seconds']:.1f}s")

        return "\n".join(lines)
    except Exception as e:
        return f"读取执行记录失败: {e}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="进化步骤包装器")
    parser.add_argument("--module", required=True, help="模块名")
    parser.add_argument("--func", default=None, help="函数名（可选）")
    parser.add_argument("--timeout", type=int, default=60, help="超时秒数")
    parser.add_argument("--summary", action="store_true", help="显示执行摘要")

    args = parser.parse_args()

    if args.summary:
        print(get_step_summary())
        sys.exit(0)

    wrapper = StepWrapper()
    result = wrapper.run(args.module, args.func, args.timeout)

    sys.exit(0 if result["success"] else 1)
