# -*- coding: utf-8 -*-
"""
科技内容检测端到端测试

测试场景：
1. 高科技内容文章 → 通过
2. 低科技内容文章 → 失败
3. 含非科技关键词 → 检测出非科技占比
4. frontmatter 清理不影响检测
5. 强制 Prompt 生成

历史教训：
- 曾出现科技占比不足但文章仍被发布
- 曾出现 frontmatter 干扰检测精度
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.tech_content_guard import TechContentGuard, check_tech_content


class TestTechContentGuard:
    """科技内容检测端到端测试"""

    def __init__(self):
        self.test_results = []
        self.guard = TechContentGuard(min_tech_ratio=0.7)

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_high_tech_content_pass(self):
        """测试1: 高科技内容 → 通过"""
        content = """
DeepSeek 发布了 V4 版本，采用全新的 MoE 架构。
该模型拥有 6710 亿参数，每次前向传播激活 370 亿参数。
训练成本仅 557.6 万美元，相比 GPT-4 降低了 90%。
在代码生成任务上，HumanEval 得分达到 92.3%。
架构上采用 MLA（Multi-head Latent Attention）机制，
显著降低推理时的 KV Cache 显存占用。
与 Llama 3.1 405B 相比，推理速度提升 5 倍。
开源协议采用 MIT，允许商业使用。
"""
        result = self.guard.analyze(content)
        if result["is_pass"] and result["tech_ratio"] >= 0.7:
            self._log("高科技内容通过", True, f"科技占比 {result['tech_ratio']*100:.0f}%，深度 {result['depth_score']}/10")
        else:
            self._log("高科技内容通过", False, f"应通过但未通过，占比 {result['tech_ratio']*100:.0f}%")

    def test_low_tech_content_fail(self):
        """测试2: 低科技内容 → 失败"""
        content = """
今天娱乐圈发生重大事件。某明星宣布离婚，
引发网友热议。两人结婚三年，育有一子。
网友纷纷留言表示震惊和惋惜。
同时，某综艺节目收视率创新高，
嘉宾互动引发大量讨论。时尚博主发布了春季穿搭指南，
推荐今年流行的配色方案。
"""
        result = self.guard.analyze(content)
        if not result["is_pass"]:
            self._log("低科技内容拦截", True, f"正确拦截，占比 {result['tech_ratio']*100:.0f}%")
        else:
            self._log("低科技内容拦截", False, f"应拦截但未拦截，占比 {result['tech_ratio']*100:.0f}%")

    def test_non_tech_keyword_detection(self):
        """测试3: 非科技关键词检测"""
        content = """
明星离婚事件引发关注。同时，OpenAI 发布 GPT-5，
性能提升显著。娱乐八卦和人工智能技术并列报道。
美食博主推荐新餐厅，AI 算法优化推荐系统。
"""
        result = self.guard.analyze(content)
        has_non_tech_issue = any("非科技" in issue for issue in result["issues"])
        if has_non_tech_issue or result["non_tech_ratio"] > 0:
            self._log("非科技检测", True, f"检测到非科技内容，占比 {result['non_tech_ratio']*100:.0f}%")
        else:
            self._log("非科技检测", False, "未检测到非科技内容")

    def test_frontmatter_cleaning(self):
        """测试4: frontmatter 清理不影响检测"""
        content = """---
title: "测试"
published: 2026-04-27T08:00:00+08:00
category: news
draft: false
---

GPT-5 采用全新 Transformer 架构，参数规模达到万亿级别。
训练数据包含 15 万亿高质量 token，覆盖 100 多种语言。
在 MMLU 基准测试中得分 95.2%，超越人类平均水平。
推理速度比前代提升 3 倍，API 价格降低 50%。
"""
        result = self.guard.analyze(content)
        # 清理后应该能正确检测科技内容
        if result["tech_ratio"] > 0.3:
            self._log("frontmatter 清理", True, f"清理后正确检测，占比 {result['tech_ratio']*100:.0f}%")
        else:
            self._log("frontmatter 清理", False, f"清理后检测失败，占比 {result['tech_ratio']*100:.0f}%")

    def test_depth_score(self):
        """测试5: 技术深度评分"""
        content = """
该模型采用 Transformer 架构，基于自注意力机制。
原理上通过查询(Query)、键(Key)、值(Value)矩阵计算注意力权重。
与 RNN 相比，并行计算效率提升 10 倍以上。
实现上使用 CUDA 内核优化，显存占用降低 40%。
代码层面采用 PyTorch 框架，支持动态图和静态图切换。
协议方面遵循 Apache 2.0 开源协议。
"""
        result = self.guard.analyze(content)
        if result["depth_score"] >= 5:
            self._log("技术深度评分", True, f"深度评分 {result['depth_score']}/10")
        else:
            self._log("技术深度评分", False, f"深度评分偏低: {result['depth_score']}/10")

    def test_enforcement_prompt(self):
        """测试6: 强制 Prompt 生成"""
        content = "今天天气很好，适合出游。"
        passed, msg = check_tech_content(content, min_ratio=0.7)
        if not passed and "科技内容强化" in msg:
            self._log("强制 Prompt", True, "低质量内容正确生成强化 Prompt")
        else:
            self._log("强制 Prompt", False, f"未生成强化 Prompt: {msg[:50]}")

    def test_empty_content(self):
        """测试7: 空内容处理"""
        result = self.guard.analyze("")
        if "issues" in result and "内容为空" in result["issues"]:
            self._log("空内容处理", True, "空内容正确标记为不通过")
        else:
            self._log("空内容处理", False, "空内容未正确处理")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("科技内容检测端到端测试")
        print("=" * 60)

        self.test_high_tech_content_pass()
        self.test_low_tech_content_fail()
        self.test_non_tech_keyword_detection()
        self.test_frontmatter_cleaning()
        self.test_depth_score()
        self.test_enforcement_prompt()
        self.test_empty_content()

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
    tester = TestTechContentGuard()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
