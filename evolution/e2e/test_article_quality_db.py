# -*- coding: utf-8 -*-
"""
Article Quality DB 端到端测试
验证文章质量回溯库的读写一致性和查询功能
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict

# 在导入前准备临时目录
_TMPDIR = tempfile.mkdtemp(prefix="e2e_aq_")
_DB_FILE = Path(_TMPDIR) / "article_quality.jsonl"
_DB_FILE.parent.mkdir(parents=True, exist_ok=True)

# Monkey-patch _db_path
import evolution.article_quality_db as aqd
aqd._db_path = lambda: _DB_FILE

from evolution.article_quality_db import (
    record_article_quality,
    query_articles,
    get_quality_trend,
    get_module_contribution,
    generate_quality_report,
)


class TestArticleQualityDB:
    def __init__(self):
        self.tmpdir = _TMPDIR
        self.db_file = _DB_FILE
        # 清空数据库
        if self.db_file.exists():
            self.db_file.unlink()

    def __del__(self):
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def _seed_data(self):
        """写入测试数据"""
        record_article_quality(
            article_id="art-001",
            title="高质量文章",
            date="2026-04-20",
            tags=["AI", "芯片"],
            scores={"overall_score": 8.5, "tech_content_ratio": 0.8, "penalties": {}},
            is_draft=False,
            source_count=5,
            total_items=20,
            content_length=3000,
            modules_used=["tech_content_guard", "title_optimizer"],
        )
        record_article_quality(
            article_id="art-002",
            title="低质量文章",
            date="2026-04-21",
            tags=["科技", "新闻"],
            scores={"overall_score": 5.0, "tech_content_ratio": 0.4, "penalties": {}},
            is_draft=False,
            source_count=3,
            total_items=10,
            content_length=1500,
            modules_used=["title_optimizer"],
        )
        record_article_quality(
            article_id="art-003",
            title="中等质量",
            date="2026-04-22",
            tags=["AI", "新闻"],
            scores={"overall_score": 7.0, "tech_content_ratio": 0.7, "penalties": {}},
            is_draft=True,
            source_count=4,
            total_items=15,
            content_length=2500,
            modules_used=["tech_content_guard"],
        )

    def test_record_and_query(self) -> Dict:
        """记录并查询一致性"""
        try:
            self._seed_data()
            articles = query_articles(limit=10)
            assert len(articles) == 3, f"应查询到 3 条记录，实际 {len(articles)}"
            titles = [a["title"] for a in articles]
            assert "高质量文章" in titles, "应包含高质量文章"
            return {"passed": True, "message": f"记录查询一致: {len(articles)} 条"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def test_query_by_date_range(self) -> Dict:
        """按日期范围查询"""
        try:
            self._seed_data()
            articles = query_articles(start_date="2026-04-21", end_date="2026-04-21")
            assert len(articles) == 1, f"应查询到 1 条 4-21 记录，实际 {len(articles)}"
            assert articles[0]["date"] == "2026-04-21", "日期应匹配"
            return {"passed": True, "message": "日期范围查询正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def test_query_by_score(self) -> Dict:
        """按评分范围查询"""
        try:
            self._seed_data()
            articles = query_articles(min_score=7.0)
            assert len(articles) == 2, f"应查询到 2 条评分>=7.0 记录，实际 {len(articles)}"
            scores = [a["overall_score"] for a in articles]
            assert all(s >= 7.0 for s in scores), "所有记录评分应>=7.0"
            return {"passed": True, "message": f"评分查询正确: {len(articles)} 条"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def test_query_by_tag(self) -> Dict:
        """按标签查询"""
        try:
            self._seed_data()
            articles = query_articles(tag="AI")
            assert len(articles) == 2, f"应查询到 2 条含 AI 标签记录，实际 {len(articles)}"
            return {"passed": True, "message": f"标签查询正确: {len(articles)} 条"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def test_query_limit(self) -> Dict:
        """查询数量限制"""
        try:
            self._seed_data()
            articles = query_articles(limit=2)
            assert len(articles) == 2, f"应限制为 2 条，实际 {len(articles)}"
            return {"passed": True, "message": "查询数量限制正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def test_get_quality_trend(self) -> Dict:
        """质量趋势计算"""
        try:
            self._seed_data()
            trend = get_quality_trend(days=30)
            assert "count" in trend, "应包含 count"
            assert "avg_score" in trend, "应包含 avg_score"
            assert "score_trend" in trend, "应包含 score_trend"
            assert trend["count"] == 3, f"应统计 3 篇文章，实际 {trend['count']}"
            assert trend["avg_score"] > 0, "平均评分应大于 0"
            assert trend["score_trend"] in ["up", "down", "stable"], "趋势应为 up/down/stable"
            return {"passed": True, "message": f"趋势: {trend['score_trend']}, 均分: {trend['avg_score']}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def test_get_module_contribution(self) -> Dict:
        """模块贡献度计算"""
        try:
            self._seed_data()
            contrib = get_module_contribution("tech_content_guard", days=30)
            assert "with_module_avg" in contrib, "应包含 with_module_avg"
            assert "without_module_avg" in contrib, "应包含 without_module_avg"
            assert "contribution" in contrib, "应包含 contribution"
            assert contrib["with_count"] > 0, "应有使用模块的文章"
            return {"passed": True, "message": f"模块贡献度: {contrib['contribution']}, 样本: {contrib['with_count']}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def test_generate_quality_report(self) -> Dict:
        """质量报告格式"""
        try:
            self._seed_data()
            report = generate_quality_report(days=7)
            assert "文章质量报告" in report, "应包含报告标题"
            assert "文章总数" in report, "应包含文章总数"
            assert "平均评分" in report, "应包含平均评分"
            return {"passed": True, "message": "质量报告格式正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def test_empty_db_query(self) -> Dict:
        """空数据库查询"""
        try:
            # 不写入任何数据
            articles = query_articles(limit=10)
            assert articles == [], "空数据库应返回空列表"
            trend = get_quality_trend(days=30)
            assert trend["count"] == 0, "空数据库趋势 count 应为 0"
            report = generate_quality_report(days=7)
            assert "文章总数: 0" in report, "报告应显示 0 篇文章"
            return {"passed": True, "message": "空数据库处理正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}
        finally:
            if self.db_file.exists():
                self.db_file.unlink()

    def run_all(self) -> Dict:
        tests = [
            self.test_record_and_query,
            self.test_query_by_date_range,
            self.test_query_by_score,
            self.test_query_by_tag,
            self.test_query_limit,
            self.test_get_quality_trend,
            self.test_get_module_contribution,
            self.test_generate_quality_report,
            self.test_empty_db_query,
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
            "suite": "article_quality_db",
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "results": results,
        }


if __name__ == "__main__":
    tester = TestArticleQualityDB()
    report = tester.run_all()
    print(f"\n## article_quality_db ({report['passed']}/{report['total']})")
    for r in report["results"]:
        emoji = "✅" if r["passed"] else "❌"
        print(f"- {emoji} **{r['test']}**: {r['message']}")
