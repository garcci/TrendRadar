# -*- coding: utf-8 -*-
"""
热点预测端到端测试

测试场景：
1. 周期性事件预测
2. 季节性预测
3. 新兴趋势检测
4. 内容建议生成
5. 置信度排序

历史教训：
- 曾出现系统只能被动响应已有热点，无法提前预测
"""

import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.trend_forecast import TrendForecastEngine, TrendPrediction


class TestTrendForecast:
    """热点预测端到端测试"""

    def __init__(self):
        self.test_results = []
        self.engine = TrendForecastEngine(trendradar_path="/tmp/test_trend")

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_known_patterns_exist(self):
        """测试1: 已知周期性模式存在"""
        patterns = self.engine.known_patterns
        if len(patterns) >= 5:
            names = [p.pattern_name for p in patterns]
            self._log("已知模式", True, f"加载了 {len(patterns)} 个模式: {', '.join(names[:3])}...")
        else:
            self._log("已知模式", False, f"模式数量不足: {len(patterns)}")

    def test_analyze_upcoming_events(self):
        """测试2: 预测未来事件"""
        predictions = self.engine.analyze_upcoming_events(days_ahead=365)
        if isinstance(predictions, list):
            self._log("未来事件预测", True, f"预测到 {len(predictions)} 个事件")
        else:
            self._log("未来事件预测", False, "返回类型错误")

    def test_prediction_structure(self):
        """测试3: 预测结果结构正确"""
        predictions = self.engine.analyze_upcoming_events(days_ahead=365)
        if predictions:
            p = predictions[0]
            required = ["topic", "confidence", "predicted_date", "reasoning"]
            has_all = all(hasattr(p, attr) for attr in required)
            if has_all:
                self._log("预测结构", True, f"topic={p.topic}, confidence={p.confidence}")
            else:
                self._log("预测结构", False, "缺少必要字段")
        else:
            self._log("预测结构", True, "无近期预测，结构检查跳过")

    def test_seasonal_predictions(self):
        """测试4: 季节性预测"""
        # 模拟不同月份
        seasonal_6 = self.engine._get_seasonal_predictions(6, 30)
        seasonal_12 = self.engine._get_seasonal_predictions(12, 30)
        seasonal_9 = self.engine._get_seasonal_predictions(9, 30)
        total = len(seasonal_6) + len(seasonal_12) + len(seasonal_9)
        if total > 0:
            self._log("季节性预测", True, f"6月={len(seasonal_6)}, 9月={len(seasonal_9)}, 12月={len(seasonal_12)}")
        else:
            self._log("季节性预测", False, "未生成季节性预测")

    def test_detect_emerging_trends(self):
        """测试5: 新兴趋势检测"""
        recent = ["GPT-5", "Claude 4", "量子计算突破"]
        historical = ["GPT-4", "Claude 3", "AI监管"]
        trends = self.engine.detect_emerging_trends(recent, historical)
        new_topics = [t.topic for t in trends]
        if "量子计算突破" in new_topics:
            self._log("新兴趋势", True, f"检测到新趋势: {new_topics}")
        else:
            self._log("新兴趋势", False, f"未检测到新趋势: {new_topics}")

    def test_no_emerging_when_same(self):
        """测试6: 无新话题时返回空"""
        topics = ["GPT-4", "AI监管"]
        trends = self.engine.detect_emerging_trends(topics, topics)
        if len(trends) == 0:
            self._log("无新趋势", True, "相同话题正确返回空")
        else:
            self._log("无新趋势", False, f"应返回空，实际: {len(trends)}")

    def test_content_suggestions(self):
        """测试7: 内容建议生成"""
        predictions = [
            TrendPrediction(
                topic="Apple 发布会",
                confidence=0.9,
                predicted_date="2026-06",
                category="tech",
                reasoning="基于历史周期",
                source_signals=["周期"],
                suggested_action="准备相关内容"
            )
        ]
        suggestions = self.engine.generate_content_suggestions(predictions)
        if suggestions and len(suggestions) > 0:
            self._log("内容建议", True, f"生成 {len(suggestions)} 条建议")
        else:
            self._log("内容建议", False, "未生成建议")

    def test_confidence_sorted(self):
        """测试8: 按置信度排序"""
        predictions = self.engine.analyze_upcoming_events(days_ahead=365)
        if len(predictions) >= 2:
            confidences = [p.confidence for p in predictions]
            is_sorted = all(confidences[i] >= confidences[i+1] for i in range(len(confidences)-1))
            if is_sorted:
                self._log("置信度排序", True, f"置信度降序: {confidences[:3]}")
            else:
                self._log("置信度排序", False, "未按置信度降序排列")
        else:
            self._log("置信度排序", True, "预测不足2个，跳过排序检查")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("热点预测端到端测试")
        print("=" * 60)

        self.test_known_patterns_exist()
        self.test_analyze_upcoming_events()
        self.test_prediction_structure()
        self.test_seasonal_predictions()
        self.test_detect_emerging_trends()
        self.test_no_emerging_when_same()
        self.test_content_suggestions()
        self.test_confidence_sorted()

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
    tester = TestTrendForecast()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
