import sys
import os
import tempfile
import shutil
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.reader_behavior_analyzer import ReaderBehaviorAnalyzer, run_reader_analysis


class TestReaderBehaviorAnalyzer:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_rba_")
        self.analyzer = ReaderBehaviorAnalyzer(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_metrics(self, data):
        path = os.path.join(self.tmpdir, "evolution", "article_metrics.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)

    def _create_rss_health(self, data):
        path = os.path.join(self.tmpdir, "evolution", "rss_health.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)

    def test_analyze_tag_popularity(self):
        metrics = [
            {"title": "AI芯片 breakthrough", "overall_score": 9},
            {"title": "GPT-5 发布", "overall_score": 8},
            {"title": "量子计算进展", "overall_score": 7},
        ]
        result = self.analyzer.analyze_tag_popularity(metrics)
        assert "AI" in result or "芯片" in result
        return True

    def test_analyze_tag_popularity_empty(self):
        result = self.analyzer.analyze_tag_popularity([])
        assert result == {}
        return True

    def test_analyze_quality_trends(self):
        metrics = [
            {"overall_score": 5, "tech_content_ratio": 60, "analysis_depth": 4},
            {"overall_score": 6, "tech_content_ratio": 65, "analysis_depth": 5},
            {"overall_score": 7, "tech_content_ratio": 70, "analysis_depth": 6},
            {"overall_score": 8, "tech_content_ratio": 75, "analysis_depth": 7},
            {"overall_score": 9, "tech_content_ratio": 80, "analysis_depth": 8},
            {"overall_score": 9, "tech_content_ratio": 82, "analysis_depth": 9},
        ]
        result = self.analyzer.analyze_quality_trends(metrics)
        assert result["total_articles"] == 6
        assert result["trend"] == "improving"
        assert result["avg_score"] > 0
        return True

    def test_analyze_quality_trends_stable(self):
        metrics = [{"overall_score": 7, "tech_content_ratio": 70, "analysis_depth": 5} for _ in range(10)]
        result = self.analyzer.analyze_quality_trends(metrics)
        assert result["trend"] == "stable"
        return True

    def test_analyze_source_quality(self):
        self._create_rss_health({"sources": [
            {"name": "SourceA", "success": True},
            {"name": "SourceB", "success": False, "error": "timeout"},
        ]})
        result = self.analyzer.analyze_source_quality()
        assert "SourceA" in result
        assert result["SourceA"]["recommendation"] == "✅ 核心源"
        assert result["SourceB"]["recommendation"] == "🔴 待优化"
        return True

    def test_analyze_source_quality_list_format(self):
        self._create_rss_health([
            {"source_name": "Src1", "success": True},
            {"source_name": "Src2", "success": False},
        ])
        result = self.analyzer.analyze_source_quality()
        assert "Src1" in result
        return True

    def test_identify_content_gaps(self):
        tag_analysis = {
            "AI": {"avg_score": 9.0, "count": 1},
            "芯片": {"avg_score": 6.0, "count": 1},
            "GPT": {"avg_score": 8.5, "count": 1},
        }
        gaps = self.analyzer.identify_content_gaps(tag_analysis, [])
        assert len(gaps) > 0
        assert gaps[0]["topic"] in ("AI", "GPT")
        return True

    def test_generate_content_strategy(self):
        self._create_metrics([
            {"title": "AI芯片 breakthrough", "overall_score": 9, "tech_content_ratio": 80, "analysis_depth": 7},
            {"title": "GPT-5 发布", "overall_score": 8, "tech_content_ratio": 75, "analysis_depth": 6},
        ])
        strategy = self.analyzer.generate_content_strategy()
        assert "strategies" in strategy
        assert "quality_trends" in strategy
        assert "top_tags" in strategy
        return True

    def test_generate_content_strategy_empty(self):
        self._create_metrics([])
        strategy = self.analyzer.generate_content_strategy()
        assert "error" in strategy
        return True

    def test_generate_report(self):
        self._create_metrics([
            {"title": "AI芯片", "overall_score": 9, "tech_content_ratio": 80, "analysis_depth": 7},
        ])
        report = self.analyzer.generate_report()
        assert "读者行为深度分析报告" in report
        assert "质量趋势" in report
        return True

    def test_save_outputs(self):
        self._create_metrics([
            {"title": "AI芯片", "overall_score": 9, "tech_content_ratio": 80, "analysis_depth": 7},
        ])
        self.analyzer.save_outputs()
        assert os.path.exists(self.analyzer.report_file)
        assert os.path.exists(self.analyzer.strategy_file)
        return True

    def test_extract_keywords(self):
        keywords = ReaderBehaviorAnalyzer._extract_keywords("英伟达发布新AI芯片")
        assert "AI" in keywords
        assert "芯片" in keywords
        assert len(keywords) <= 5
        return True

    def test_extract_keywords_empty(self):
        keywords = ReaderBehaviorAnalyzer._extract_keywords("日常随笔")
        assert isinstance(keywords, list)
        return True

    def run_all(self):
        tests = [
            self.test_analyze_tag_popularity,
            self.test_analyze_tag_popularity_empty,
            self.test_analyze_quality_trends,
            self.test_analyze_quality_trends_stable,
            self.test_analyze_source_quality,
            self.test_analyze_source_quality_list_format,
            self.test_identify_content_gaps,
            self.test_generate_content_strategy,
            self.test_generate_content_strategy_empty,
            self.test_generate_report,
            self.test_save_outputs,
            self.test_extract_keywords,
            self.test_extract_keywords_empty,
        ]
        results = []
        passed = failed = 0
        for t in tests:
            try:
                t()
                results.append({"test": t.__name__, "passed": True, "message": "通过"})
                passed += 1
            except Exception as e:
                results.append({"test": t.__name__, "passed": False, "message": str(e)})
                failed += 1
        self._teardown()
        return {
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": results
        }
