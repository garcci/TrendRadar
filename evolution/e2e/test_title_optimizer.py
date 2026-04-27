# -*- coding: utf-8 -*-
"""
标题优化系统端到端测试
验证：话题提取、候选生成、标题评分、替换安全
"""

from typing import Dict

from evolution.title_optimizer import TitleOptimizer, optimize_article_title, replace_article_title


class TestTitleOptimizer:
    """标题优化系统端到端测试"""

    def __init__(self):
        self.optimizer = TitleOptimizer()

    TEST_CONTENT = """---
title: "TrendRadar Report - 2024-01-15"
tags: [科技, AI芯片, 半导体]
---

今天AI芯片市场发生了重大变化。

## 市场格局

**AMD的MI300X**正在快速抢占市场，性能提升40%。

**Intel Gaudi 3**开始获得云厂商订单。

## 数据亮点

1. 英伟达市场份额从95%下降到85%
2. AMD MI300X推理性能提升40%
3. 中国厂商加速追赶
"""

    def test_extract_topics(self) -> Dict:
        """从内容提取话题"""
        try:
            topics = self.optimizer.extract_topics_from_content(self.TEST_CONTENT)
            assert len(topics) > 0, "应至少提取到1个话题"
            assert "AMD" in topics or "AMD的MI300X" in topics, "应提取到AMD相关话题"
            assert "Intel" in topics or "Intel Gaudi 3" in topics, "应提取到Intel话题"
            assert len(topics) <= 10, f"话题不应超过10个, 实际{len(topics)}"
            return {"passed": True, "message": f"提取到{len(topics)}个话题: {topics[:3]}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_generate_candidates(self) -> Dict:
        """生成候选标题"""
        try:
            candidates = self.optimizer.generate_candidate_titles(self.TEST_CONTENT)
            assert len(candidates) >= 3, f"应至少生成3个候选标题, 实际{len(candidates)}"
            assert len(candidates) <= 4, f"不应超过4个候选标题, 实际{len(candidates)}"
            # 验证每个候选标题都不为空
            for c in candidates:
                assert len(c) > 0, "候选标题不应为空"
            return {"passed": True, "message": f"生成{len(candidates)}个候选标题"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_score_title_length(self) -> Dict:
        """标题长度评分"""
        try:
            # 最佳长度 15-30
            score_optimal = self.optimizer.score_title("AI芯片市场格局深度解析")
            # 太短
            score_short = self.optimizer.score_title("AI")
            # 过长 (>40字)
            score_long = self.optimizer.score_title("AI芯片市场格局深度解析以及未来发展趋势展望与投资建议分析报告")

            assert score_optimal >= score_short, "最佳长度标题分数应高于过短标题"
            assert score_optimal > score_long or score_optimal == score_long, f"最佳长度标题分数应不低于过长标题, 最佳={score_optimal}, 长={score_long}"
            assert 0 <= score_optimal <= 100, f"分数应在0-100之间, 实际{score_optimal}"
            return {"passed": True, "message": f"长度评分: 最佳={score_optimal}, 短={score_short}, 长={score_long}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_score_title_with_number(self) -> Dict:
        """包含数字的标题评分更高"""
        try:
            score_with_num = self.optimizer.score_title("3个数据揭示AI芯片真相")
            score_without = self.optimizer.score_title("数据揭示AI芯片真相")
            assert score_with_num > score_without, "含数字标题分数应更高"
            return {"passed": True, "message": f"含数字={score_with_num}, 不含={score_without}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_score_title_question(self) -> Dict:
        """疑问句式评分"""
        try:
            score_question = self.optimizer.score_title("AI芯片会改变什么？")
            score_statement = self.optimizer.score_title("AI芯片改变了很多")
            assert score_question > score_statement, "疑问句分数应高于陈述句"
            return {"passed": True, "message": f"疑问句={score_question}, 陈述句={score_statement}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_select_best_title(self) -> Dict:
        """选择最佳标题"""
        try:
            candidates = [
                "AI芯片市场格局",
                "3个数据揭示AI芯片真相",
                "AI芯片会改变什么？"
            ]
            best, score = self.optimizer.select_best_title(candidates)
            assert best in candidates, "最佳标题应在候选列表中"
            assert score > 0, "最佳标题分数应大于0"
            return {"passed": True, "message": f"最佳标题: '{best}' (评分: {score})"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_optimize_title(self) -> Dict:
        """完整优化流程"""
        try:
            result = self.optimizer.optimize_title(self.TEST_CONTENT, current_title="旧标题")
            assert len(result) > 0, "优化后的标题不应为空"
            assert "TrendRadar Report" not in result, "不应保留默认报告标题"
            return {"passed": True, "message": f"优化后标题: '{result[:30]}...'"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_replace_title_simple(self) -> Dict:
        """替换标题 - 简单情况"""
        try:
            content = '---\ntitle: "旧标题"\n---\n\n正文内容'
            new = "新标题"
            result = replace_article_title(content, new)
            assert 'title: "新标题"' in result, "应包含新标题"
            assert "旧标题" not in result, "不应包含旧标题"
            assert "正文内容" in result, "正文应保留"
            return {"passed": True, "message": "简单标题替换正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_replace_title_with_double_quotes(self) -> Dict:
        """替换包含双引号的标题 - 安全处理"""
        try:
            content = '---\ntitle: "旧标题"\n---\n\n正文内容'
            new_title = 'AI "深度" 解析'
            result = replace_article_title(content, new_title)
            # 由于包含双引号且无单引号，应使用单引号包裹
            assert "title: '" in result, "含双引号标题应使用单引号包裹"
            # 验证新标题已替换进去（单引号包裹，内部双引号保留）
            assert 'AI "深度" 解析' in result, "新标题应正确嵌入"
            assert "旧标题" not in result, "不应保留旧标题"
            assert "正文内容" in result, "正文应保留"
            return {"passed": True, "message": "双引号标题安全替换正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_replace_title_no_frontmatter(self) -> Dict:
        """无frontmatter时不崩溃"""
        try:
            content = "没有frontmatter的文章"
            result = replace_article_title(content, "新标题")
            assert result == content, "无frontmatter时应原样返回"
            return {"passed": True, "message": "无frontmatter处理正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_convenience_optimize_article_title(self) -> Dict:
        """便捷函数 optimize_article_title"""
        try:
            result = optimize_article_title(self.TEST_CONTENT)
            assert len(result) > 0, "便捷函数应返回非空标题"
            return {"passed": True, "message": f"便捷函数返回: '{result[:30]}...'"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def run_all(self) -> Dict:
        """运行全部测试"""
        tests = [
            self.test_extract_topics,
            self.test_generate_candidates,
            self.test_score_title_length,
            self.test_score_title_with_number,
            self.test_score_title_question,
            self.test_select_best_title,
            self.test_optimize_title,
            self.test_replace_title_simple,
            self.test_replace_title_with_double_quotes,
            self.test_replace_title_no_frontmatter,
            self.test_convenience_optimize_article_title,
        ]
        results = []
        passed = failed = 0
        for t in tests:
            r = t()
            r["test"] = t.__name__
            results.append(r)
            if r["passed"]:
                passed += 1
            else:
                failed += 1
        return {
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": results
        }
