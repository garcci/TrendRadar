# -*- coding: utf-8 -*-
"""TrendPredictor 端到端测试"""

import json
import os
import tempfile
from datetime import datetime, timedelta


class TestTrendPredictor:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_tp_")
        os.makedirs(f"{self.tmpdir}/evolution", exist_ok=True)
        from evolution.trend_predictor import TrendPredictor
        self.predictor = TrendPredictor(self.tmpdir)

    def _write_metrics(self, data):
        path = f"{self.tmpdir}/evolution/article_metrics.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def test_analyze_topic_frequency(self):
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self._write_metrics([
            {"timestamp": datetime.now().isoformat(), "date": today,
             "keywords": ["AI"], "hot_topics": ["芯片"], "overall_score": 8},
            {"timestamp": (datetime.now() - timedelta(days=1)).isoformat(), "date": yesterday,
             "keywords": ["AI"], "hot_topics": ["芯片"], "overall_score": 7},
            {"timestamp": (datetime.now() - timedelta(days=2)).isoformat(), "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
             "keywords": ["区块链"], "hot_topics": [], "overall_score": 6},
        ])
        result = self.predictor.analyze_topic_frequency(days=30)
        assert "AI" in result, "AI should be in topic frequency"
        assert result["AI"]["count"] >= 2, f"AI count should be >= 2, got {result['AI']['count']}"
        return True

    def test_analyze_topic_frequency_empty(self):
        self._write_metrics([])
        result = self.predictor.analyze_topic_frequency()
        assert result == {}, "Empty metrics should return empty dict"
        return True

    def test_get_seasonal_trends(self):
        trends = self.predictor.get_seasonal_trends()
        month = datetime.now().month
        expected = self.predictor.SEASONAL_EVENTS.get(month, [])
        assert trends == expected, f"Seasonal trends mismatch: {trends} vs {expected}"
        return True

    def test_predict_trends(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_metrics([
            {"timestamp": datetime.now().isoformat(), "date": today,
             "keywords": ["AI", "芯片", "大模型"], "hot_topics": ["大模型"], "overall_score": 9},
            {"timestamp": (datetime.now() - timedelta(days=1)).isoformat(), "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
             "keywords": ["AI", "芯片"], "hot_topics": ["大模型"], "overall_score": 8},
            {"timestamp": (datetime.now() - timedelta(days=2)).isoformat(), "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
             "keywords": ["AI", "芯片"], "hot_topics": ["大模型"], "overall_score": 8},
        ])
        result = self.predictor.predict_trends()
        assert isinstance(result["hot_topics"], list), "hot_topics should be a list"
        assert isinstance(result["seasonal"], list), "seasonal should be a list"
        return True

    def test_predict_trends_empty(self):
        self._write_metrics([])
        result = self.predictor.predict_trends()
        assert result["hot_topics"] == [], "Empty input should yield empty hot_topics"
        assert result["recurring"] == [], "Empty input should yield empty recurring"
        return True

    def test_generate_suggestion(self):
        suggestion = self.predictor._generate_suggestion(
            hot_topics=["AI", "芯片"],
            seasonal=["发布会"],
            recurring=[{"topic": "大模型", "count": 3, "trend": "上升"}]
        )
        assert "AI" in suggestion or "芯片" in suggestion, "Suggestion should mention hot topics"
        assert "发布会" in suggestion, "Suggestion should mention seasonal event"
        return True

    def test_generate_prompt_insight(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_metrics([
            {"timestamp": datetime.now().isoformat(), "date": today,
             "keywords": ["AI"], "hot_topics": ["芯片"], "overall_score": 8},
        ])
        insight = self.predictor.generate_prompt_insight()
        assert isinstance(insight, str), "Insight should be a string"
        return True

    def test_generate_prompt_insight_empty(self):
        self._write_metrics([])
        insight = self.predictor.generate_prompt_insight()
        # 即使 metrics 为空，季节性事件仍存在，insight 可能非空
        assert isinstance(insight, str), "Insight should be a string"
        return True

    def test_recurring_topics(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_metrics([
            {"timestamp": datetime.now().isoformat(), "date": today,
             "keywords": ["AI"], "hot_topics": [], "overall_score": 8},
            {"timestamp": (datetime.now() - timedelta(days=2)).isoformat(), "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
             "keywords": ["AI"], "hot_topics": [], "overall_score": 7},
            {"timestamp": (datetime.now() - timedelta(days=4)).isoformat(), "date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
             "keywords": ["AI"], "hot_topics": [], "overall_score": 7},
        ])
        result = self.predictor.predict_trends()
        recurring_topics = [r["topic"] for r in result["recurring"]]
        assert "AI" in recurring_topics, "AI should be identified as recurring"
        return True

    def test_hot_topics_rising(self):
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self._write_metrics([
            {"timestamp": datetime.now().isoformat(), "date": today,
             "keywords": ["AI"], "hot_topics": ["大模型"], "overall_score": 9},
            {"timestamp": (datetime.now() - timedelta(days=1)).isoformat(), "date": yesterday,
             "keywords": ["AI"], "hot_topics": ["大模型"], "overall_score": 8},
        ])
        result = self.predictor.predict_trends()
        assert len(result["hot_topics"]) > 0, "Should detect rising hot topics"
        return True

    def run_all(self):
        results = []
        passed = 0
        for name in dir(self):
            if name.startswith("test_"):
                try:
                    self.__getattribute__(name)()
                    results.append({"name": name, "status": "PASS"})
                    passed += 1
                except Exception as e:
                    results.append({"name": name, "status": "FAIL", "error": str(e)})
        return {"all_passed": passed == len(results), "passed": passed, "failed": len(results) - passed, "results": results}
