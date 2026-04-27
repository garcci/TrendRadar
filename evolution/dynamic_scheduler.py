# -*- coding: utf-8 -*-
"""
进化步骤动态编排器 — Lv78 进化

问题：
1. evolution.yml 步骤固定执行，无新异常时也跑 Exception Intervention
2. 文章质量稳定时仍执行 Prompt Evolution，浪费 API 调用
3. 缺少根据实时数据动态决策的能力

解决方案：
1. 读取 data_pipeline/log.jsonl 和 article_quality.jsonl
2. 根据最近 24h 数据动态决定每个步骤应运行/跳过
3. 输出 Markdown 调度报告，供 system_final_check 参考
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _log_path() -> Path:
    return Path(".") / "evolution" / "data_pipeline" / "log.jsonl"


def _quality_path() -> Path:
    return Path(".") / "evolution" / "data_pipeline" / "article_quality.jsonl"


def _load_jsonl(path: Path, hours: int = 24) -> List[Dict[str, Any]]:
    """加载最近 N 小时的 JSONL 记录"""
    results = []
    cutoff = datetime.now() - timedelta(hours=hours)
    if not path.exists():
        return results
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    ts = record.get("timestamp", "")
                    if ts:
                        try:
                            record_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if record_dt >= cutoff:
                                results.append(record)
                        except ValueError:
                            continue
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return results


def analyze_recent_logs(hours: int = 24) -> Dict[str, Any]:
    """分析最近日志，提取关键信号"""
    logs = _load_jsonl(_log_path(), hours)
    quality = _load_jsonl(_quality_path(), hours)

    # 统计各模块的错误/成功情况
    module_stats: Dict[str, Dict[str, int]] = {}
    for log in logs:
        module = log.get("module", "unknown")
        level = log.get("level", "INFO")
        if module not in module_stats:
            module_stats[module] = {"info": 0, "warn": 0, "error": 0, "success": 0}
        if level == "ERROR":
            module_stats[module]["error"] += 1
        elif level == "WARN":
            module_stats[module]["warn"] += 1
        else:
            module_stats[module]["info"] += 1
        if log.get("status") == "success":
            module_stats[module]["success"] += 1

    # 统计文章质量趋势
    avg_score = 0.0
    if quality:
        scores = [q.get("overall_score", 0) for q in quality]
        avg_score = round(sum(scores) / len(scores), 2)

    # 异常信号：是否有 ERROR 级别日志
    has_errors = any(s["error"] > 0 for s in module_stats.values())

    # 质量信号：最近文章平均评分
    quality_stable = avg_score >= 7.0 if avg_score > 0 else False

    return {
        "has_errors": has_errors,
        "quality_stable": quality_stable,
        "avg_score": avg_score,
        "article_count": len(quality),
        "module_stats": module_stats,
    }


# 步骤定义与调度规则
STEP_RULES = {
    "System Health Check": {"always": True, "reason": "基础检查必须执行"},
    "Autonomous Evolution": {"always": True, "reason": "自主进化是核心"},
    "Exception Intervention": {
        "skip_if": lambda s: not s["has_errors"],
        "reason": "最近 24h 无异常，跳过干预",
    },
    "Astro Build Health Check": {"always": True, "reason": "构建健康检查必须执行"},
    "Repo Cleanup": {
        "skip_if": lambda s: s["article_count"] == 0,
        "reason": "最近 24h 无新文章，跳过清理",
    },
    "Prompt Evolution": {
        "skip_if": lambda s: s["quality_stable"] and s["avg_score"] > 0,
        "reason": "文章质量稳定(≥7.0)，跳过 Prompt 调优",
    },
    "Auto Optimization": {
        "skip_if": lambda s: s["quality_stable"] and s["avg_score"] > 0,
        "reason": "文章质量稳定，跳过自动优化",
    },
    "Output Quality Validation": {"always": True, "reason": "输出质量验证必须执行"},
    "Free Resource Scheduler": {"always": True, "reason": "免费资源调度必须执行"},
    "Auto Calibration": {
        "skip_if": lambda s: s["quality_stable"] and s["avg_score"] > 0,
        "reason": "质量稳定，跳过自动校准",
    },
    "AI Code Healer": {
        "skip_if": lambda s: not s["has_errors"],
        "reason": "最近 24h 无代码异常，跳过修复",
    },
    "Regression Guard": {"always": True, "reason": "退化检测必须执行"},
    "Auto Healing": {
        "skip_if": lambda s: not s["has_errors"],
        "reason": "最近 24h 无需自愈",
    },
    "System Final Check": {"always": True, "reason": "最终检查必须执行"},
}


def generate_schedule(signals: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """生成动态调度计划"""
    if signals is None:
        signals = analyze_recent_logs()

    schedule = []
    for step_name, rule in STEP_RULES.items():
        if rule.get("always"):
            schedule.append({
                "step": step_name,
                "action": "run",
                "reason": rule["reason"],
                "confidence": 1.0,
            })
        elif "skip_if" in rule:
            should_skip = rule["skip_if"](signals)
            schedule.append({
                "step": step_name,
                "action": "skip" if should_skip else "run",
                "reason": rule["reason"] if should_skip else "条件不满足，正常执行",
                "confidence": 0.85 if should_skip else 0.7,
            })
    return schedule


def generate_schedule_report() -> str:
    """生成调度报告 Markdown"""
    signals = analyze_recent_logs()
    schedule = generate_schedule(signals)

    lines = ["# 🎛️ 进化步骤动态编排报告", ""]
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**数据窗口**: 最近 24 小时")
    lines.append("")
    lines.append("## 📊 数据信号")
    lines.append(f"- 异常信号: {'⚠️ 发现错误' if signals['has_errors'] else '✅ 无异常'}")
    lines.append(f"- 质量稳定: {'✅ 稳定' if signals['quality_stable'] else '⏳ 待观察'} (平均评分: {signals['avg_score']})")
    lines.append(f"- 新文章数: {signals['article_count']}")
    lines.append("")

    run_steps = [s for s in schedule if s["action"] == "run"]
    skip_steps = [s for s in schedule if s["action"] == "skip"]

    lines.append(f"## ✅ 执行步骤 ({len(run_steps)} 个)")
    for s in run_steps:
        lines.append(f"- **{s['step']}** — {s['reason']}")

    if skip_steps:
        lines.append("")
        lines.append(f"## ⏭️ 跳过步骤 ({len(skip_steps)} 个)")
        for s in skip_steps:
            lines.append(f"- **{s['step']}** — {s['reason']} (置信度: {s['confidence']})")

    # 计算预估节省
    total_steps = len(schedule)
    skip_count = len(skip_steps)
    lines.append("")
    lines.append("## 📈 效率预估")
    lines.append(f"- 总步骤: {total_steps}")
    lines.append(f"- 跳过: {skip_count} ({round(skip_count / total_steps * 100, 1)}%)")
    lines.append(f"- 预估节省 API 调用: ~{skip_count * 2} 次")
    lines.append("")
    lines.append("---")
    lines.append("*Lv78 动态编排器：根据实时数据自动调整进化策略*")

    return "\n".join(lines)


def get_step_decision(step_name: str) -> Tuple[bool, str]:
    """查询单个步骤是否应该执行

    Returns:
        (should_run, reason)
    """
    signals = analyze_recent_logs()
    schedule = generate_schedule(signals)
    for s in schedule:
        if s["step"] == step_name:
            return s["action"] == "run", s["reason"]
    return True, "未在规则中定义，默认执行"


if __name__ == "__main__":
    print(generate_schedule_report())
