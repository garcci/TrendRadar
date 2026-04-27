import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.emotion_analyzer import EmotionAnalyzer, analyze_emotion, get_emotion_insight


class TestEmotionAnalyzer:
    def test_analyze_positive(self):
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze_text("技术突破创新，产品非常优秀，前景广阔")
        assert result["sentiment"] == "positive", f"Expected positive, got {result['sentiment']}"
        assert "突破" in result["positive_words"] or "创新" in result["positive_words"]
        return True

    def test_analyze_negative(self):
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze_text("公司裁员倒闭，危机严重，员工愤怒抗议")
        assert result["sentiment"] == "negative", f"Expected negative, got {result['sentiment']}"
        assert "裁员" in result["negative_words"] or "倒闭" in result["negative_words"]
        return True

    def test_analyze_neutral(self):
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze_text("今天天气晴朗，适合出门散步")
        assert result["sentiment"] == "neutral", f"Expected neutral, got {result['sentiment']}"
        assert result["score"] == 0
        return True

    def test_analyze_empty(self):
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze_text("")
        assert result["sentiment"] == "neutral"
        assert result["score"] == 0
        assert result["intensity"] == "weak"
        return True

    def test_analyze_controversial(self):
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze_text("曝光内幕引发争议，双方互相举报投诉")
        assert result["is_controversial"] is True
        return True

    def test_analyze_not_controversial(self):
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze_text("技术突破创新，取得重大进展")
        assert result["is_controversial"] is False
        return True

    def test_analyze_intensity(self):
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze_text("非常极其特别强大，简直是完美的突破")
        assert result["intensity"] == "strong", f"Expected strong, got {result['intensity']}"
        return True

    def test_analyze_batch(self):
        analyzer = EmotionAnalyzer()
        texts = [
            "技术创新取得突破",
            "公司裁员引发危机",
            "今天天气晴朗",
        ]
        result = analyzer.analyze_batch(texts)
        assert result["overall_sentiment"] in ["positive", "negative", "neutral"]
        assert abs(result["positive_ratio"] + result["negative_ratio"] + result["neutral_ratio"] - 1.0) < 0.02
        return True

    def test_analyze_batch_empty(self):
        analyzer = EmotionAnalyzer()
        result = analyzer.analyze_batch([])
        assert result["overall_sentiment"] == "neutral"
        assert result["neutral_ratio"] == 1
        return True

    def test_generate_insight(self):
        analyzer = EmotionAnalyzer()
        texts = ["技术创新突破", "公司裁员危机"]
        insight = analyzer.generate_emotion_insight(texts)
        assert isinstance(insight, str)
        assert len(insight) > 0
        assert "情感分析洞察" in insight
        return True

    def test_convenience_analyze_emotion(self):
        result = analyze_emotion("开源免费，开发者非常兴奋")
        assert result["sentiment"] == "positive"
        return True

    def run_all(self):
        tests = [
            self.test_analyze_positive,
            self.test_analyze_negative,
            self.test_analyze_neutral,
            self.test_analyze_empty,
            self.test_analyze_controversial,
            self.test_analyze_not_controversial,
            self.test_analyze_intensity,
            self.test_analyze_batch,
            self.test_analyze_batch_empty,
            self.test_generate_insight,
            self.test_convenience_analyze_emotion,
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
        return {
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": results
        }
