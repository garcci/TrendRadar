# -*- coding: utf-8 -*-
"""
统一日志收集器 — Lv73 进化

问题：
1. 各模块用 print/logger 随意输出，无法统一收集分析
2. 日志分散在 Workflow 输出中，难以回溯特定文章的处理流程
3. 无法量化各步骤耗时和成功率

解决方案：
1. 提供统一的日志接口，自动关联文章ID
2. 同时输出到控制台（保持可见性）和写入 data_pipeline/log.jsonl
3. 记录结构化数据：时间戳、模块、级别、内容、文章ID、耗时
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# 全局上下文：当前处理的文章ID
_current_article_id: Optional[str] = None
_current_run_start: float = 0.0


def set_article_id(article_id: str) -> None:
    """设置当前文章ID，后续日志自动关联"""
    global _current_article_id
    _current_article_id = article_id


def clear_article_id() -> None:
    """清除当前文章ID"""
    global _current_article_id
    _current_article_id = None


def get_article_id() -> Optional[str]:
    """获取当前文章ID"""
    return _current_article_id


def _log_path() -> Path:
    """日志文件路径"""
    return Path(".") / "evolution" / "data_pipeline" / "log.jsonl"


def _write_log(level: str, module: str, message: str, extra: Optional[Dict] = None) -> None:
    """写入结构化日志到 JSONL"""
    record = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "module": module,
        "message": message[:500],  # 限制长度
        "article_id": _current_article_id,
    }
    if extra:
        record.update({k: v for k, v in extra.items() if v is not None})

    try:
        log_file = _log_path()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 日志写入失败不应阻塞主流程


def log_info(module: str, message: str, **extra) -> None:
    """记录 INFO 级别日志"""
    print(f"[{module}] {message}")
    _write_log("INFO", module, message, extra)


def log_warn(module: str, message: str, **extra) -> None:
    """记录 WARN 级别日志"""
    print(f"[{module}] ⚠️ {message}", file=sys.stderr)
    _write_log("WARN", module, message, extra)


def log_error(module: str, message: str, **extra) -> None:
    """记录 ERROR 级别日志"""
    print(f"[{module}] ❌ {message}", file=sys.stderr)
    _write_log("ERROR", module, message, extra)


def log_debug(module: str, message: str, **extra) -> None:
    """记录 DEBUG 级别日志（仅写入文件，不输出到控制台）"""
    _write_log("DEBUG", module, message, extra)


class StepTimer:
    """步骤计时器：自动记录步骤耗时"""

    def __init__(self, module: str, step: str):
        self.module = module
        self.step = step
        self.start = time.time()

    def __enter__(self):
        log_info(self.module, f"开始: {self.step}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start
        status = "success" if exc_type is None else "error"
        log_info(
            self.module,
            f"完成: {self.step}",
            step=self.step,
            elapsed_ms=round(elapsed * 1000, 2),
            status=status,
        )
        if exc_type is not None:
            log_error(
                self.module,
                f"步骤失败: {self.step} — {exc_val}",
                step=self.step,
                elapsed_ms=round(elapsed * 1000, 2),
                error_type=exc_type.__name__,
            )
        return False  # 不吞异常


class PrintInterceptor:
    """拦截 print 输出并同时写入日志"""

    def __init__(self, original_stdout, module_hint: str = "unknown"):
        self.original = original_stdout
        self.module_hint = module_hint
        self._buffer = ""

    def write(self, text: str) -> None:
        self.original.write(text)
        # 对完整行写入日志
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                _write_log("INFO", self.module_hint, line.strip())

    def flush(self) -> None:
        self.original.flush()
        if self._buffer.strip():
            _write_log("INFO", self.module_hint, self._buffer.strip())
            self._buffer = ""


def install_print_interceptor(module_hint: str = "main") -> None:
    """安装 print 拦截器（谨慎使用，可能影响其他库）"""
    interceptor = PrintInterceptor(sys.stdout, module_hint)
    sys.stdout = interceptor


def uninstall_print_interceptor() -> None:
    """卸载 print 拦截器"""
    if hasattr(sys.stdout, "original"):
        sys.stdout = sys.stdout.original


def get_run_summary() -> Dict[str, Any]:
    """获取本次运行摘要"""
    log_file = _log_path()
    if not log_file.exists():
        return {"total_logs": 0, "errors": 0, "warns": 0}

    total = errors = warns = 0
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    total += 1
                    if record.get("level") == "ERROR":
                        errors += 1
                    elif record.get("level") == "WARN":
                        warns += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return {
        "total_logs": total,
        "errors": errors,
        "warns": warns,
        "article_id": _current_article_id,
    }
