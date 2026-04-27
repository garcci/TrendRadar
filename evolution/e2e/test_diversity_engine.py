import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.diversity_engine import ArticleDiversityEngine, PerspectiveRotator, get_diversity_instructions
import evolution.diversity_engine as de_module


class TestDiversityEngine:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_de_")
        self.engine = ArticleDiversityEngine(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init_has_templates(self):
        assert len(self.engine.templates) == 7, f"Expected 7 templates, got {len(self.engine.templates)}"
        return True

    def test_select_template_match_topic(self):
        orig_random = de_module.random.random
        orig_uniform = de_module.random.uniform
        de_module.random.random = lambda: 1.0
        de_module.random.uniform = lambda a, b: 0.0
        try:
            template = self.engine.select_template(["技术选型"], recent_templates=[])
            assert template.name == "对比分析型", f"Expected 对比分析型, got {template.name}"
        finally:
            de_module.random.random = orig_random
            de_module.random.uniform = orig_uniform
        return True

    def test_select_template_no_match_fallback(self):
        orig_random = de_module.random.random
        de_module.random.random = lambda: 1.0
        try:
            template = self.engine.select_template(["完全不相关的话题"], recent_templates=[])
            assert template.name in [t.name for t in self.engine.templates]
        finally:
            de_module.random.random = orig_random
        return True

    def test_select_template_avoids_recent(self):
        # topics=["创业","AI"] matches 故事叙事型(创业), 问题解答型(AI), 反直觉型(AI)
        # If 故事叙事型 was recently used, weight drops to 0.3
        # With uniform=0.5 (> 0.3), it should skip 故事叙事型
        orig_random = de_module.random.random
        orig_uniform = de_module.random.uniform
        de_module.random.random = lambda: 1.0
        de_module.random.uniform = lambda a, b: 0.5
        try:
            template = self.engine.select_template(["创业", "AI"], recent_templates=["故事叙事型"])
            assert template.name != "故事叙事型", f"Should avoid recent template, got {template.name}"
        finally:
            de_module.random.random = orig_random
            de_module.random.uniform = orig_uniform
        return True

    def test_generate_instructions_format(self):
        template = self.engine.templates[0]
        instructions = self.engine.generate_template_instructions(template)
        assert template.name in instructions
        assert "要求:" in instructions
        assert template.tone in instructions
        return True

    def test_generate_instructions_required_marker(self):
        template = next(t for t in self.engine.templates if t.name == "对比分析型")
        instructions = self.engine.generate_template_instructions(template)
        assert "[必须]" in instructions
        return True

    def test_record_and_get_recent_templates(self):
        self.engine.record_template_usage("对比分析型", "Test Article")
        recent = self.engine.get_recent_templates(days=7)
        assert "对比分析型" in recent, f"Expected 对比分析型 in recent, got {recent}"
        return True

    def test_get_recent_templates_empty(self):
        fresh_dir = tempfile.mkdtemp(prefix="e2e_de_fresh_")
        try:
            fresh_engine = ArticleDiversityEngine(fresh_dir)
            recent = fresh_engine.get_recent_templates(days=7)
            assert recent == [], f"Expected empty list, got {recent}"
        finally:
            shutil.rmtree(fresh_dir, ignore_errors=True)
        return True

    def test_perspective_rotator_count(self):
        result = PerspectiveRotator.get_rotated_perspectives(count=3)
        count = result.count("视角")
        assert count == 3, f"Expected 3 perspectives, got {count}"
        return True

    def test_perspective_rotator_format(self):
        result = PerspectiveRotator.get_rotated_perspectives(count=2)
        assert "分析角度轮换" in result
        assert "•" in result
        return True

    def test_get_diversity_instructions(self):
        result = get_diversity_instructions(self.tmpdir, ["技术选型"])
        assert isinstance(result, str)
        assert len(result) > 50
        return True

    def run_all(self):
        tests = [
            self.test_init_has_templates,
            self.test_select_template_match_topic,
            self.test_select_template_no_match_fallback,
            self.test_select_template_avoids_recent,
            self.test_generate_instructions_format,
            self.test_generate_instructions_required_marker,
            self.test_record_and_get_recent_templates,
            self.test_get_recent_templates_empty,
            self.test_perspective_rotator_count,
            self.test_perspective_rotator_format,
            self.test_get_diversity_instructions,
        ]
        passed = 0
        failed = []
        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                failed.append((test.__name__, str(e)))
        self._teardown()
        return {"passed": passed, "failed": failed, "total": len(tests)}
