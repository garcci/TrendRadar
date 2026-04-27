# -*- coding: utf-8 -*-
"""
进化效果仪表盘 — Lv79 进化

功能：
1. 读取 data_pipeline/log.jsonl 计算各模块平均执行时间
2. 读取 article_quality.jsonl 分析文章质量评分趋势
3. 统计 Workflow 成功率（基于日志中的 success/error 比例）
4. 生成 Markdown 报告到 evolution/dashboard.md
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


def _log_path() -> Path:
    return Path(".") / "evolution" / "data_pipeline" / "log.jsonl"


def _quality_path() -> Path:
    return Path(".") / "evolution" / "data_pipeline" / "article_quality.jsonl"


def _load_all_jsonl(path: Path) -> List[Dict[str, Any]]:
    """加载全部 JSONL 记录"""
    results = []
    if not path.exists():
        return results
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return results


def calc_module_timing(logs: List[Dict[str, Any]], days: int = 7) -> Dict[str, Dict[str, Any]]:
    """计算各模块最近 N 天的平均执行时间"""
    cutoff = datetime.now() - timedelta(days=days)
    module_data: Dict[str, List[float]] = {}

    for log in logs:
        ts = log.get("timestamp", "")
        if not ts:
            continue
        try:
            log_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if log_dt < cutoff:
                continue
        except ValueError:
            continue

        module = log.get("module", "unknown")
        elapsed = log.get("elapsed_ms")
        if elapsed and isinstance(elapsed, (int, float)) and elapsed > 0:
            if module not in module_data:
                module_data[module] = []
            module_data[module].append(float(elapsed))

    result = {}
    for module, times in module_data.items():
        result[module] = {
            "count": len(times),
            "avg_ms": round(sum(times) / len(times), 2),
            "max_ms": round(max(times), 2),
            "min_ms": round(min(times), 2),
        }
    return result


def calc_workflow_success_rate(logs: List[Dict[str, Any]], days: int = 7) -> Dict[str, Any]:
    """计算 Workflow 步骤成功率"""
    cutoff = datetime.now() - timedelta(days=days)
    step_results: Dict[str, Dict[str, int]] = {}

    for log in logs:
        ts = log.get("timestamp", "")
        if not ts:
            continue
        try:
            log_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if log_dt < cutoff:
                continue
        except ValueError:
            continue

        step = log.get("step", log.get("module", "unknown"))
        status = log.get("status", "")
        if not step or not status:
            continue

        if step not in step_results:
            step_results[step] = {"success": 0, "error": 0}
        if status == "success":
            step_results[step]["success"] += 1
        elif status == "error":
            step_results[step]["error"] += 1

    total_success = sum(v["success"] for v in step_results.values())
    total_error = sum(v["error"] for v in step_results.values())
    total = total_success + total_error

    return {
        "total_runs": total,
        "success_rate": round(total_success / total * 100, 1) if total > 0 else 0,
        "step_breakdown": {
            step: {
                "success": v["success"],
                "error": v["error"],
                "rate": round(v["success"] / (v["success"] + v["error"]) * 100, 1)
                if (v["success"] + v["error"]) > 0 else 0,
            }
            for step, v in step_results.items()
        },
    }


def calc_quality_trend(quality_records: List[Dict[str, Any]], days: int = 14) -> Dict[str, Any]:
    """计算文章质量评分趋势（按天分桶）"""
    cutoff = datetime.now() - timedelta(days=days)
    daily_scores: Dict[str, List[float]] = {}

    for record in quality_records:
        ts = record.get("timestamp", "")
        if not ts:
            continue
        try:
            record_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if record_dt < cutoff:
                continue
        except ValueError:
            continue

        day = record_dt.strftime("%Y-%m-%d")
        score = record.get("overall_score", 0)
        if score > 0:
            if day not in daily_scores:
                daily_scores[day] = []
            daily_scores[day].append(float(score))

    if not daily_scores:
        return {"count": 0, "avg": 0, "trend": "no_data", "daily": []}

    daily_avg = []
    for day in sorted(daily_scores.keys()):
        scores = daily_scores[day]
        daily_avg.append({
            "date": day,
            "count": len(scores),
            "avg": round(sum(scores) / len(scores), 2),
        })

    # 趋势判断：前半段 vs 后半段
    mid = len(daily_avg) // 2
    if mid > 0:
        first = sum(d["avg"] for d in daily_avg[:mid]) / mid
        second = sum(d["avg"] for d in daily_avg[mid:]) / max(len(daily_avg) - mid, 1)
        if second > first + 0.3:
            trend = "up"
        elif second < first - 0.3:
            trend = "down"
        else:
            trend = "stable"
    else:
        trend = "stable"

    all_scores = [s for scores in daily_scores.values() for s in scores]
    return {
        "count": len(all_scores),
        "avg": round(sum(all_scores) / len(all_scores), 2),
        "trend": trend,
        "daily": daily_avg,
    }


def calc_cost_distribution(quality_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析成本分布（基于文章使用的模块数量估算）"""
    module_usage: Dict[str, int] = {}
    total_modules = 0

    for record in quality_records:
        modules = record.get("modules_used", [])
        for m in modules:
            module_usage[m] = module_usage.get(m, 0) + 1
            total_modules += 1

    sorted_usage = sorted(module_usage.items(), key=lambda x: x[1], reverse=True)
    return {
        "total_invocations": total_modules,
        "top_modules": [
            {"module": m, "count": c, "percentage": round(c / total_modules * 100, 1)}
            for m, c in sorted_usage[:10]
        ] if total_modules > 0 else [],
    }


def generate_dashboard() -> str:
    """生成完整仪表盘 Markdown 报告"""
    logs = _load_all_jsonl(_log_path())
    quality = _load_all_jsonl(_quality_path())

    timing = calc_module_timing(logs, days=7)
    workflow = calc_workflow_success_rate(logs, days=7)
    quality_trend = calc_quality_trend(quality, days=14)
    cost = calc_cost_distribution(quality)

    lines = ["# 📊 TrendRadar 进化效果仪表盘", ""]
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**数据范围**: 最近 7-14 天")
    lines.append("")

    # Workflow 成功率
    lines.append("## 🎯 Workflow 成功率")
    lines.append(f"- 总执行次数: {workflow['total_runs']}")
    lines.append(f"- 成功率: {workflow['success_rate']}%")
    if workflow['step_breakdown']:
        lines.append("")
        lines.append("| 步骤 | 成功 | 失败 | 成功率 |")
        lines.append("|------|------|------|--------|")
        for step, data in sorted(
            workflow['step_breakdown'].items(),
            key=lambda x: x[1]['rate'],
            reverse=True,
        )[:10]:
            lines.append(f"| {step} | {data['success']} | {data['error']} | {data['rate']}% |")
    lines.append("")

    # 文章质量趋势
    lines.append("## 📈 文章质量趋势")
    if quality_trend['count'] > 0:
        trend_emoji = {"up": "📈", "down": "📉", "stable": "➡️", "no_data": "❓"}
        lines.append(f"- 文章总数: {quality_trend['count']}")
        lines.append(f"- 平均评分: {quality_trend['avg']}/10")
        lines.append(f"- 趋势: {trend_emoji.get(quality_trend['trend'], '➡️')} {quality_trend['trend']}")
        if quality_trend['daily']:
            lines.append("")
            lines.append("| 日期 | 文章数 | 平均评分 |")
            lines.append("|------|--------|----------|")
            for d in quality_trend['daily'][-7:]:
                lines.append(f"| {d['date']} | {d['count']} | {d['avg']} |")
    else:
        lines.append("- 暂无文章质量数据")
    lines.append("")

    # 模块执行时间
    lines.append("## ⏱️ 模块平均执行时间")
    if timing:
        lines.append("| 模块 | 执行次数 | 平均(ms) | 最大(ms) | 最小(ms) |")
        lines.append("|------|----------|----------|----------|----------|")
        for module, data in sorted(timing.items(), key=lambda x: x[1]['avg_ms'], reverse=True):
            lines.append(
                f"| {module} | {data['count']} | {data['avg_ms']} | {data['max_ms']} | {data['min_ms']} |"
            )
    else:
        lines.append("- 暂无执行时间数据")
    lines.append("")

    # 成本分布
    lines.append("## 💰 模块调用分布")
    if cost['top_modules']:
        lines.append(f"- 总调用次数: {cost['total_invocations']}")
        lines.append("")
        lines.append("| 模块 | 调用次数 | 占比 |")
        lines.append("|------|----------|------|")
        for m in cost['top_modules']:
            lines.append(f"| {m['module']} | {m['count']} | {m['percentage']}% |")
    else:
        lines.append("- 暂无模块调用数据")
    lines.append("")

    # 综合评估
    lines.append("## 🏆 综合评估")
    healthy_score = 0
    if workflow['success_rate'] >= 90:
        healthy_score += 1
        lines.append("- ✅ Workflow 成功率 ≥ 90%")
    elif workflow['success_rate'] >= 70:
        lines.append("- ⚠️ Workflow 成功率 70-90%")
    else:
        lines.append("- ❌ Workflow 成功率 < 70%")

    if quality_trend['avg'] >= 7.0:
        healthy_score += 1
        lines.append("- ✅ 文章平均评分 ≥ 7.0")
    elif quality_trend['avg'] >= 5.0:
        lines.append("- ⚠️ 文章平均评分 5.0-7.0")
    else:
        lines.append("- ❌ 文章平均评分 < 5.0")

    if quality_trend['trend'] == "up":
        healthy_score += 1
        lines.append("- ✅ 质量趋势上升")
    elif quality_trend['trend'] == "stable":
        lines.append("- ➡️ 质量趋势稳定")
    else:
        lines.append("- 📉 质量趋势下降")

    lines.append("")
    lines.append(f"**健康度**: {healthy_score}/3")
    lines.append("")
    lines.append("---")
    lines.append("*Lv79 进化效果仪表盘：数据驱动决策*")

    return "\n".join(lines)


def write_dashboard() -> str:
    """生成并写入仪表盘报告"""
    report = generate_dashboard()
    output_path = Path(".") / "evolution" / "dashboard.md"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        return f"仪表盘已写入 {output_path}"
    except Exception as e:
        return f"仪表盘写入失败: {e}"


if __name__ == "__main__":
    print(generate_dashboard())
    print(write_dashboard())
