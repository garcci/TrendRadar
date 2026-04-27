import sys
import os
import tempfile
import shutil
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.prompt_tracker import PromptTracker


class TestPromptTracker:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_pt_")
        self.tracker = PromptTracker(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_record_usage(self):
        self.tracker.record_prompt_usage("article_1", ["quality_feedback", "data_enhancement"])
        tracks = self.tracker._load_tracks()
        assert len(tracks) == 1
        assert tracks[0]["article_id"] == "article_1"
        assert "quality_feedback" in tracks[0]["fragments"]
        return True

    def test_analyze_effectiveness(self):
        # 准备追踪数据
        self.tracker._save_tracks([
            {"article_id": "a1", "fragments": ["f1"]},
            {"article_id": "a2", "fragments": ["f1", "f2"]},
            {"article_id": "a3", "fragments": ["f2"]},
        ])
        # 准备评分数据
        metrics_file = os.path.join(self.tmpdir, "evolution", "article_metrics.json")
        os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
        with open(metrics_file, 'w') as f:
            json.dump([
                {"article_id": "a1", "overall_score": 9.0},
                {"article_id": "a2", "overall_score": 8.0},
                {"article_id": "a3", "overall_score": 6.0},
            ], f)

        results = self.tracker.analyze_fragment_effectiveness()
        assert "f1" in results
        assert "f2" in results
        # f1 在 a1(9.0) 和 a2(8.0) 中使用，平均分 8.5；不使用 f1 的是 a3(6.0)
        assert results["f1"]["effect_delta"] > 0
        return True

    def test_assess_effect_significant(self):
        assert self.tracker._assess_effect(0.8) == "显著提升"
        assert self.tracker._assess_effect(-0.8) == "显著下降"
        return True

    def test_assess_effect_none(self):
        assert self.tracker._assess_effect(0.0) == "无影响"
        assert self.tracker._assess_effect(0.1) == "轻微提升"
        assert self.tracker._assess_effect(-0.1) == "轻微下降"
        return True

    def test_get_top_fragments(self):
        # 准备数据
        self.tracker._save_tracks([
            {"article_id": "a1", "fragments": ["f1"]},
            {"article_id": "a2", "fragments": ["f1"]},
            {"article_id": "a3", "fragments": ["f1"]},
        ])
        metrics_file = os.path.join(self.tmpdir, "evolution", "article_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump([
                {"article_id": "a1", "overall_score": 9.0},
                {"article_id": "a2", "overall_score": 9.0},
                {"article_id": "a3", "overall_score": 9.0},
            ], f)

        top = self.tracker.get_top_fragments(min_uses=3)
        assert len(top) >= 1
        assert top[0]["id"] == "f1"
        return True

    def test_get_weak_fragments(self):
        # a1/a2 使用 f1 且低分，a3 不使用 f1 且高分
        self.tracker._save_tracks([
            {"article_id": "a1", "fragments": ["f1"]},
            {"article_id": "a2", "fragments": ["f1"]},
            {"article_id": "a3", "fragments": ["f2"]},  # 不使用f1
        ])
        metrics_file = os.path.join(self.tmpdir, "evolution", "article_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump([
                {"article_id": "a1", "overall_score": 4.0},
                {"article_id": "a2", "overall_score": 4.0},
                {"article_id": "a3", "overall_score": 9.0},
            ], f)

        weak = self.tracker.get_weak_fragments(min_uses=2)
        assert len(weak) >= 1
        assert weak[0]["effect_delta"] < 0
        return True

    def test_top_fragments_min_uses_filter(self):
        # f1 只用1次，不满足min_uses=3
        self.tracker._save_tracks([
            {"article_id": "a1", "fragments": ["f1"]},
        ])
        metrics_file = os.path.join(self.tmpdir, "evolution", "article_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump([{"article_id": "a1", "overall_score": 9.0}], f)

        top = self.tracker.get_top_fragments(min_uses=3)
        assert len(top) == 0  # 使用次数不足被过滤
        return True

    def test_empty_tracks(self):
        results = self.tracker.analyze_fragment_effectiveness()
        assert results == {}
        return True

    def test_single_track_insufficient(self):
        # 只有1条数据，无法计算效果（需要至少2条）
        self.tracker._save_tracks([
            {"article_id": "a1", "fragments": ["f1"]},
        ])
        metrics_file = os.path.join(self.tmpdir, "evolution", "article_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump([{"article_id": "a1", "overall_score": 9.0}], f)

        results = self.tracker.analyze_fragment_effectiveness()
        # 使用次数不足2次，不会出现在结果中
        assert "f1" not in results
        return True

    def test_save_load_tracks(self):
        tracks = [
            {"article_id": "a1", "fragments": ["f1"], "timestamp": "2024-01-01"}
        ]
        self.tracker._save_tracks(tracks)
        loaded = self.tracker._load_tracks()
        assert len(loaded) == 1
        assert loaded[0]["article_id"] == "a1"
        return True

    def run_all(self):
        tests = [
            self.test_record_usage,
            self.test_analyze_effectiveness,
            self.test_assess_effect_significant,
            self.test_assess_effect_none,
            self.test_get_top_fragments,
            self.test_get_weak_fragments,
            self.test_top_fragments_min_uses_filter,
            self.test_empty_tracks,
            self.test_single_track_insufficient,
            self.test_save_load_tracks,
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
