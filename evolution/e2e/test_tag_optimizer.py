# -*- coding: utf-8 -*-
"""
标签优化端到端测试

测试场景：
1. 从标题提取标签
2. 标签分布分析
3. 过度使用标签检测
4. 缺失标签检测
5. 低质量标签检测
6. 生成优化建议
7. 报告生成

历史教训：
- 曾出现标签过度集中（如全部标"AI"）
- 曾出现标题与标签不匹配
"""

import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.tag_optimizer import TagOptimizer


class TestTagOptimizer:
    """标签优化端到端测试"""

    def __init__(self):
        self.test_results = []
        self.temp_dir = tempfile.mkdtemp()
        self.optimizer = TagOptimizer(trendradar_path=self.temp_dir)

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_extract_tags_from_title(self):
        """测试1: 从标题提取标签"""
        title = "OpenAI GPT-5 发布：多模态大模型性能提升 30%"
        tags = self.optimizer.extract_tags(title)
        if "AI" in tags:
            self._log("标题提取标签", True, f"提取到标签: {tags}")
        else:
            self._log("标题提取标签", False, f"应包含 AI，实际: {tags}")

    def test_extract_tags_no_match(self):
        """测试2: 无匹配时返回默认"""
        title = "今日天气预报"
        tags = self.optimizer.extract_tags(title)
        if tags == ["科技"]:
            self._log("默认标签", True, "无匹配时返回默认 '科技'")
        else:
            self._log("默认标签", False, f"应返回 ['科技']，实际: {tags}")

    def test_analyze_distribution(self):
        """测试3: 标签分布分析"""
        metrics = [
            {"title": "GPT-5 发布", "overall_score": 8.5},
            {"title": "华为芯片突破", "overall_score": 7.2},
            {"title": "特斯拉自动驾驶", "overall_score": 6.8},
        ]
        analysis = self.optimizer.analyze_tag_distribution(metrics)
        dist = analysis.get("tag_distribution", {})
        if len(dist) > 0:
            self._log("标签分布", True, f"分析到 {len(dist)} 个标签")
        else:
            self._log("标签分布", False, "未分析到标签")

    def test_detect_overused_tags(self):
        """测试4: 过度使用标签检测"""
        metrics = [{"title": f"AI 新闻 {i}", "overall_score": 7.0} for i in range(6)]
        analysis = self.optimizer.analyze_tag_distribution(metrics)
        issues = self.optimizer.find_tag_issues(analysis)
        overused = [i for i in issues if i["type"] == "overused"]
        if overused:
            self._log("过度使用检测", True, f"检测到 {len(overused)} 个过度使用标签")
        else:
            self._log("过度使用检测", False, "未检测到过度使用标签")

    def test_detect_missing_tags(self):
        """测试5: 缺失标签检测"""
        metrics = [{"title": "普通新闻", "overall_score": 6.0}]
        analysis = self.optimizer.analyze_tag_distribution(metrics)
        issues = self.optimizer.find_tag_issues(analysis)
        missing = [i for i in issues if i["type"] == "missing"]
        if missing:
            self._log("缺失标签检测", True, "检测到缺失具体标签的文章")
        else:
            self._log("缺失标签检测", False, "未检测到缺失标签")

    def test_detect_low_quality_tags(self):
        """测试6: 低质量标签检测"""
        metrics = [
            {"title": "芯片新闻 1", "overall_score": 4.0},
            {"title": "芯片新闻 2", "overall_score": 4.5},
        ]
        analysis = self.optimizer.analyze_tag_distribution(metrics)
        issues = self.optimizer.find_tag_issues(analysis)
        low_quality = [i for i in issues if i["type"] == "low_quality"]
        if low_quality:
            self._log("低质量标签", True, f"检测到 {len(low_quality)} 个低质量标签")
        else:
            self._log("低质量标签", False, "未检测到低质量标签")

    def test_generate_recommendations(self):
        """测试7: 生成优化建议"""
        metrics = [
            {"title": "GPT-5 发布", "overall_score": 9.0},
            {"title": "华为芯片", "overall_score": 8.5},
        ]
        import json
        import os
        os.makedirs(f"{self.temp_dir}/evolution", exist_ok=True)
        with open(f"{self.temp_dir}/evolution/article_metrics.json", "w") as f:
            json.dump(metrics, f)

        rec = self.optimizer.generate_recommendations()
        if "recommendations" in rec and len(rec["recommendations"]) > 0:
            self._log("生成建议", True, f"生成 {len(rec['recommendations'])} 条建议")
        else:
            self._log("生成建议", False, "未生成建议")

    def test_report_generation(self):
        """测试8: 报告生成"""
        report = self.optimizer.generate_report()
        if "标签优化报告" in report:
            self._log("报告生成", True, "报告生成成功")
        else:
            self._log("报告生成", False, "报告未生成")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("标签优化端到端测试")
        print("=" * 60)

        self.test_extract_tags_from_title()
        self.test_extract_tags_no_match()
        self.test_analyze_distribution()
        self.test_detect_overused_tags()
        self.test_detect_missing_tags()
        self.test_detect_low_quality_tags()
        self.test_generate_recommendations()
        self.test_report_generation()

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
    tester = TestTagOptimizer()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
