import sys
import os
import tempfile
import shutil
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.smart_scheduler import (
    ContentQualityEvaluator, SmartScheduler, should_publish_today
)


class TestSmartScheduler:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_ss_")
        self.scheduler = SmartScheduler(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_evaluate_high_quality(self):
        result = self.scheduler.evaluator.evaluate_daily_data(
            news_items_count=150, tech_items_count=80, rss_success_rate=0.9
        )
        assert result["total_score"] >= 7  # 数量3 + 科技3 + RSS2 + 历史2 = 10
        assert len(result["issues"]) == 0
        return True

    def test_evaluate_low_quality(self):
        result = self.scheduler.evaluator.evaluate_daily_data(
            news_items_count=10, tech_items_count=1, rss_success_rate=0.3
        )
        assert result["total_score"] < 4  # 数量0 + 科技0 + RSS0 = 低分
        assert len(result["issues"]) > 0
        return True

    def test_make_decision_publish(self):
        decision = self.scheduler.make_decision(150, 80, 0.9)
        assert decision["action"] == "publish"
        assert "优秀" in decision["reason"]
        return True

    def test_make_decision_skip(self):
        decision = self.scheduler.make_decision(10, 1, 0.3)
        assert decision["action"] == "skip"
        assert "不足" in decision["reason"]
        return True

    def test_make_decision_draft(self):
        # 中等质量：数量50(2分) + 科技15/50=0.3(2分) + RSS0.7(1分) = 5分 → draft
        decision = self.scheduler.make_decision(50, 15, 0.7)
        # 无历史数据时history_trend=2，总分可能>=7，调整参数
        # 数量20(1) + 科技3/20=0.15(1) + RSS0.6(1) + history(2) = 5 → draft
        decision = self.scheduler.make_decision(20, 3, 0.6)
        assert decision["action"] == "draft"
        return True

    def test_history_trend_no_data(self):
        score = self.scheduler.evaluator._evaluate_history_trend()
        assert score == 2  # 无历史数据默认满分
        return True

    def test_history_trend_good(self):
        metrics_file = os.path.join(self.tmpdir, "evolution", "article_metrics.json")
        os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
        with open(metrics_file, 'w') as f:
            json.dump([
                {"overall_score": 8.0},
                {"overall_score": 8.5},
                {"overall_score": 7.5},
            ], f)
        score = self.scheduler.evaluator._evaluate_history_trend()
        assert score == 2  # 平均分>=7
        return True

    def test_schedule_stats(self):
        # 清空之前的决策记录，避免前面测试数据干扰
        if os.path.exists(self.scheduler.decision_log):
            os.remove(self.scheduler.decision_log)
        # 产生3种决策
        self.scheduler.make_decision(150, 80, 0.9)   # publish
        self.scheduler.make_decision(10, 1, 0.3)     # skip
        self.scheduler.make_decision(20, 3, 0.6)     # draft (1+1+1+2=5)

        stats = self.scheduler.get_schedule_stats()
        assert stats["total"] == 3, f"expected 3, got {stats['total']}"
        assert stats["publish"] == 1, f"expected publish=1, got {stats['publish']}"
        assert stats["skip"] == 1, f"expected skip=1, got {stats['skip']}"
        assert stats["draft"] == 1, f"expected draft=1, got {stats['draft']}"
        return True

    def test_should_publish_today(self):
        should, reason = should_publish_today(150, 80, 0.9, self.tmpdir)
        assert should is True
        assert "优秀" in reason
        return True

    def test_log_decision_retention(self):
        log_file = os.path.join(self.tmpdir, "evolution", "scheduler_decisions.json")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        old_date = "2020-01-01"
        recent_date = "2099-01-01"
        with open(log_file, 'w') as f:
            json.dump([
                {"date": old_date, "action": "publish"},
                {"date": recent_date, "action": "skip"},
            ], f)

        # 再写入一条触发清理
        self.scheduler._log_decision({"date": recent_date, "action": "draft"})

        with open(log_file, 'r') as f:
            decisions = json.load(f)
        # 旧日期应被过滤掉（超过30天）
        dates = [d["date"] for d in decisions]
        assert old_date not in dates
        assert recent_date in dates
        return True

    def test_metrics_in_decision(self):
        decision = self.scheduler.make_decision(100, 50, 0.8)
        assert "metrics" in decision
        assert decision["metrics"]["news_count"] == 100
        assert decision["metrics"]["tech_count"] == 50
        return True

    def run_all(self):
        tests = [
            self.test_evaluate_high_quality,
            self.test_evaluate_low_quality,
            self.test_make_decision_publish,
            self.test_make_decision_skip,
            self.test_make_decision_draft,
            self.test_history_trend_no_data,
            self.test_history_trend_good,
            self.test_schedule_stats,
            self.test_should_publish_today,
            self.test_log_decision_retention,
            self.test_metrics_in_decision,
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
