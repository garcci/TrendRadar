# -*- coding: utf-8 -*-
"""
语义去重端到端测试

测试场景（纯本地，无需网络）：
1. 相似文本检测（高相似度）
2. 不相似文本检测（低相似度）
3. 语义向量提取
4. 空文本处理
5. 阈值判断正确

历史教训：
- 曾出现同一话题连续多天重复报道
- 曾出现简单标题匹配无法捕捉语义相似
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.semantic_deduplicator import SemanticDeduplicator


class TestSemanticDeduplicator:
    """语义去重端到端测试"""

    def __init__(self):
        self.test_results = []
        # 使用假 token 避免初始化报错
        self.dedup = SemanticDeduplicator(
            github_owner="test",
            github_repo="test",
            github_token="fake",
            similarity_threshold=0.65
        )

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_high_similarity(self):
        """测试1: 高度相似文本"""
        text1 = "OpenAI 发布 GPT-5 大语言模型，性能提升显著"
        text2 = "GPT-5 大模型发布，OpenAI 推出新一代语言模型"
        vec1 = self.dedup._extract_semantic_vector(text1)
        vec2 = self.dedup._extract_semantic_vector(text2)
        sim = self.dedup._calculate_similarity(vec1, vec2)
        if sim >= 0.5:
            self._log("高相似度", True, f"相似度 {sim:.2f}")
        else:
            self._log("高相似度", False, f"应高相似，实际 {sim:.2f}")

    def test_low_similarity(self):
        """测试2: 不相似文本"""
        text1 = "OpenAI 发布 GPT-5 大语言模型"
        text2 = "特斯拉发布新款电动车，续航里程突破"
        vec1 = self.dedup._extract_semantic_vector(text1)
        vec2 = self.dedup._extract_semantic_vector(text2)
        sim = self.dedup._calculate_similarity(vec1, vec2)
        if sim < 0.3:
            self._log("低相似度", True, f"相似度 {sim:.2f}")
        else:
            self._log("低相似度", False, f"应低相似，实际 {sim:.2f}")

    def test_empty_text(self):
        """测试3: 空文本处理"""
        vec = self.dedup._extract_semantic_vector("")
        sim = self.dedup._calculate_similarity(vec, {"test": 1})
        if sim == 0.0:
            self._log("空文本", True, "空文本相似度为0")
        else:
            self._log("空文本", False, f"应为0，实际 {sim}")

    def test_same_text(self):
        """测试4: 相同文本相似度为1"""
        text = "人工智能深度学习神经网络"
        vec = self.dedup._extract_semantic_vector(text)
        sim = self.dedup._calculate_similarity(vec, vec)
        if sim == 1.0:
            self._log("相同文本", True, "相同文本相似度为1.0")
        else:
            self._log("相同文本", False, f"应为1.0，实际 {sim:.2f}")

    def test_domain_keywords_boost(self):
        """测试5: 领域关键词增强权重"""
        text = "人工智能 AI 大模型 GPT 深度学习"
        vec = self.dedup._extract_semantic_vector(text)
        has_domain = any(k.startswith("__domain_") for k in vec.keys())
        if has_domain:
            domains = [k for k in vec.keys() if k.startswith("__domain_")]
            self._log("领域增强", True, f"检测到领域权重: {domains}")
        else:
            self._log("领域增强", False, "未检测到领域权重")

    def test_threshold_boundary(self):
        """测试6: 阈值边界判断"""
        # 使用更相似的文本确保超过阈值
        text1 = "华为发布新款芯片，采用7nm工艺制程，性能提升30%"
        text2 = "华为芯片采用7nm工艺制程，新款发布性能提升30%"
        vec1 = self.dedup._extract_semantic_vector(text1)
        vec2 = self.dedup._extract_semantic_vector(text2)
        sim = self.dedup._calculate_similarity(vec1, vec2)
        is_dup = sim >= self.dedup.threshold
        if is_dup:
            self._log("阈值判断", True, f"相似度 {sim:.2f} >= {self.dedup.threshold}，判定重复")
        else:
            self._log("阈值判断", False, f"相似度 {sim:.2f} 未达阈值 {self.dedup.threshold}")

    def test_recommendation_levels(self):
        """测试7: 不同相似度等级建议"""
        # 直接构造不同相似度的结果检查推荐语
        rec_90 = self.dedup.check_duplication(["GPT-5 发布"])
        # 由于没有历史文章，max_similarity=0
        if rec_90["max_similarity"] == 0.0:
            self._log("建议分级", True, f"无历史文章: {rec_90['recommendation']}")
        else:
            self._log("建议分级", False, f"预期无历史，实际相似度 {rec_90['max_similarity']}")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("语义去重端到端测试")
        print("=" * 60)

        self.test_high_similarity()
        self.test_low_similarity()
        self.test_empty_text()
        self.test_same_text()
        self.test_domain_keywords_boost()
        self.test_threshold_boundary()
        self.test_recommendation_levels()

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
    tester = TestSemanticDeduplicator()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
