# -*- coding: utf-8 -*-
"""
文章质量回溯库 — Lv75 进化

问题：
1. 文章推送后无法回溯其 frontmatter、评分、标签
2. 无法分析文章质量趋势
3. 无法比较不同策略的效果

解决方案：
1. 每次生成文章时，记录完整的文章元数据
2. 支持按时间/标签/评分查询历史文章
3. 为 A/B 测试和模块贡献度分析提供数据基础
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


def _db_path() -> Path:
    """质量数据库路径"""
    return Path(".") / "evolution" / "data_pipeline" / "article_quality.jsonl"


def record_article_quality(
    article_id: str,
    title: str,
    date: str,
    tags: List[str],
    scores: Dict[str, Any],
    is_draft: bool,
    source_count: int,
    total_items: int,
    content_length: int,
    modules_used: Optional[List[str]] = None,
) -> bool:
    """
    记录文章质量数据

    Args:
        article_id: 文章唯一标识
        title: 文章标题
        date: 发布日期
        tags: 标签列表
        scores: 评分结果字典（含 overall_score, tech_content_ratio, penalties 等）
        is_draft: 是否为草稿
        source_count: RSS 源数量
        total_items: 抓取的新闻总数
        content_length: 文章内容长度
        modules_used: 本次生成使用的进化模块列表
    """
    record = {
        "article_id": article_id,
        "title": title,
        "date": date,
        "timestamp": datetime.now().isoformat(),
        "tags": tags or [],
        "overall_score": scores.get("overall_score", 0) if scores else 0,
        "tech_content_ratio": scores.get("tech_content_ratio", 0) if scores else 0,
        "penalties": scores.get("penalties", {}) if scores else {},
        "is_draft": is_draft,
        "source_count": source_count,
        "total_items": total_items,
        "content_length": content_length,
        "modules_used": modules_used or [],
    }

    try:
        db_file = _db_path()
        db_file.parent.mkdir(parents=True, exist_ok=True)
        with open(db_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print(f"[article_quality_db] 写入失败: {e}")
        return False


def query_articles(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    tag: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    查询历史文章质量记录

    Args:
        start_date: 起始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        min_score: 最低 overall_score
        max_score: 最高 overall_score
        tag: 筛选特定标签
        limit: 返回数量上限
    """
    results = []
    db_file = _db_path()
    if not db_file.exists():
        return results

    try:
        with open(db_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)

                    # 日期筛选
                    if start_date and record.get("date", "") < start_date:
                        continue
                    if end_date and record.get("date", "") > end_date:
                        continue

                    # 评分筛选
                    if min_score is not None and record.get("overall_score", 0) < min_score:
                        continue
                    if max_score is not None and record.get("overall_score", 0) > max_score:
                        continue

                    # 标签筛选
                    if tag and tag not in record.get("tags", []):
                        continue

                    results.append(record)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[article_quality_db] 查询失败: {e}")

    # 按时间倒序，取最新 limit 条
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results[:limit]


def get_quality_trend(days: int = 30) -> Dict[str, Any]:
    """
    获取文章质量趋势

    Args:
        days: 最近 N 天的数据

    Returns:
        {
            "count": 文章数量,
            "avg_score": 平均评分,
            "avg_tech_ratio": 平均科技占比,
            "score_trend": "up" | "down" | "stable",
            "best_article": 最佳文章,
            "worst_article": 最差文章,
        }
    """
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    articles = query_articles(start_date=start, end_date=end, limit=1000)

    if not articles:
        return {"count": 0, "avg_score": 0, "avg_tech_ratio": 0}

    scores = [a["overall_score"] for a in articles]
    tech_ratios = [a["tech_content_ratio"] for a in articles]

    # 计算趋势：前一半 vs 后一半
    mid = len(scores) // 2
    first_half = sum(scores[:mid]) / max(mid, 1)
    second_half = sum(scores[mid:]) / max(len(scores) - mid, 1)

    if second_half > first_half + 0.5:
        trend = "up"
    elif second_half < first_half - 0.5:
        trend = "down"
    else:
        trend = "stable"

    # 最佳/最差文章
    sorted_by_score = sorted(articles, key=lambda x: x.get("overall_score", 0), reverse=True)
    best = sorted_by_score[0] if sorted_by_score else None
    worst = sorted_by_score[-1] if sorted_by_score else None

    return {
        "count": len(articles),
        "avg_score": round(sum(scores) / len(scores), 2),
        "avg_tech_ratio": round(sum(tech_ratios) / len(tech_ratios), 2),
        "score_trend": trend,
        "best_article": {
            "title": best["title"] if best else "",
            "score": best["overall_score"] if best else 0,
            "date": best["date"] if best else "",
        } if best else None,
        "worst_article": {
            "title": worst["title"] if worst else "",
            "score": worst["overall_score"] if worst else 0,
            "date": worst["date"] if worst else "",
        } if worst else None,
    }


def get_module_contribution(module_name: str, days: int = 30) -> Dict[str, Any]:
    """
    计算特定模块的贡献度（使用该模块 vs 未使用时的平均评分差异）

    Args:
        module_name: 模块名称
        days: 最近 N 天

    Returns:
        {
            "with_module_avg": 使用该模块时的平均评分,
            "without_module_avg": 未使用该模块时的平均评分,
            "contribution": 净贡献值,
            "sample_count": 样本数量,
        }
    """
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    articles = query_articles(start_date=start, end_date=end, limit=1000)

    with_scores = []
    without_scores = []

    for article in articles:
        modules = article.get("modules_used", [])
        score = article.get("overall_score", 0)
        if module_name in modules:
            with_scores.append(score)
        else:
            without_scores.append(score)

    with_avg = sum(with_scores) / len(with_scores) if with_scores else 0
    without_avg = sum(without_scores) / len(without_scores) if without_scores else 0

    return {
        "with_module_avg": round(with_avg, 2),
        "without_module_avg": round(without_avg, 2),
        "contribution": round(with_avg - without_avg, 2),
        "with_count": len(with_scores),
        "without_count": len(without_scores),
    }


def generate_quality_report(days: int = 7) -> str:
    """生成质量趋势报告文本"""
    trend = get_quality_trend(days)
    lines = [
        f"📊 文章质量报告（最近 {days} 天）",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"文章总数: {trend['count']}",
        f"平均评分: {trend['avg_score']}/10",
        f"平均科技占比: {trend['avg_tech_ratio']}/10",
        f"质量趋势: {'📈 上升' if trend['score_trend'] == 'up' else ('📉 下降' if trend['score_trend'] == 'down' else '➡️ 稳定')}",
    ]
    if trend.get("best_article"):
        lines.append(f"最佳文章: {trend['best_article']['title']} ({trend['best_article']['score']}分)")
    if trend.get("worst_article"):
        lines.append(f"最差文章: {trend['worst_article']['title']} ({trend['worst_article']['score']}分)")
    return "\n".join(lines)
