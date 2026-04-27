# -*- coding: utf-8 -*-
"""
智能摘要系统端到端测试
验证：TL;DR提取、核心观点、关键词、阅读时间、摘要注入
"""

from typing import Dict

from evolution.smart_summary import SmartSummary, get_article_summary


class TestSmartSummary:
    """智能摘要系统端到端测试"""

    def __init__(self):
        self.summarizer = SmartSummary()

    TEST_ARTICLE = """---
title: "AI芯片革命：英伟达的挑战者们"
published: 2024-01-15T08:00:00+08:00
tags: ["科技", "AI芯片", "半导体", "英伟达"]
description: "英伟达面临来自AMD、Intel和众多初创公司的激烈竞争"
---

今天，AI芯片市场发生了重大变化。

:::note[关键洞察]
英伟达的市场份额从95%下降到85%，这是一个历史性的转折点。
:::

**AMD的MI300X正在快速抢占市场**，其性能在某些场景下已经超越H100。

## 市场格局变化

1. AMD MI300X在推理场景下性能领先
2. Intel Gaudi 3开始获得云厂商订单
3. 中国厂商寒武纪、海光信息加速追赶

**未来趋势**: 预计未来6个月，AI芯片市场将呈现三足鼎立的格局。
"""

    TEST_ARTICLE_NO_DESC = """---
title: "量子计算新突破"
published: 2024-01-15T08:00:00+08:00
tags: ["量子计算", "科技"]
---

谷歌量子计算团队宣布实现了新的量子纠错里程碑。

:::tip[技术亮点]
量子比特错误率降低到了0.1%以下，这是一个重大突破。
:::

**超导量子比特技术路线**被认为是目前最有前景的方向。

1. 错误率降低使得量子计算机更加实用
2. 商业化时间线可能提前到2030年
"""

    def test_extract_tldr_from_description(self) -> Dict:
        """从description字段提取TL;DR"""
        try:
            tldr = self.summarizer.extract_tldr(self.TEST_ARTICLE)
            expected = "英伟达面临来自AMD、Intel和众多初创公司的激烈竞争"
            assert tldr == expected, f"TL;DR应为'{expected}', 实际'{tldr}'"
            return {"passed": True, "message": "从description提取TL;DR正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_extract_tldr_from_content(self) -> Dict:
        """无description时从正文提取TL;DR"""
        try:
            tldr = self.summarizer.extract_tldr(self.TEST_ARTICLE_NO_DESC)
            assert "谷歌量子计算团队" in tldr, f"TL;DR应包含正文内容, 实际'{tldr}'"
            assert len(tldr) <= 103, f"TL;DR应截断到100字+省略号, 实际长度{len(tldr)}"
            return {"passed": True, "message": f"从正文提取TL;DR正确: '{tldr[:30]}...'"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_extract_key_insights(self) -> Dict:
        """提取核心观点"""
        try:
            insights = self.summarizer.extract_key_insights(self.TEST_ARTICLE)
            assert len(insights) > 0, "应至少提取到1条核心观点"

            # 验证包含Admonition内容
            has_admonition = any("市场份额" in i for i in insights)
            assert has_admonition, "应提取到Admonition中的观点"

            # 验证包含加粗内容
            has_bold = any("AMD" in i for i in insights)
            assert has_bold, "应提取到加粗文本中的观点"

            # 验证包含列表项
            has_list = any("推理场景" in i for i in insights)
            assert has_list, "应提取到列表项中的观点"

            # 验证去重和上限
            assert len(insights) <= 5, f"核心观点不应超过5条, 实际{len(insights)}"

            return {"passed": True, "message": f"提取{len(insights)}条核心观点"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_extract_keywords_from_tags(self) -> Dict:
        """从tags提取关键词"""
        try:
            keywords = self.summarizer.extract_keywords(self.TEST_ARTICLE)
            assert len(keywords) > 0, "应提取到关键词"
            assert "科技" in keywords, "应包含'科技'标签"
            assert "AI芯片" in keywords, "应包含'AI芯片'标签"
            assert len(keywords) <= 8, f"关键词不应超过8个, 实际{len(keywords)}"
            return {"passed": True, "message": f"从tags提取关键词: {keywords}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_extract_keywords_fallback(self) -> Dict:
        """无tags时从内容提取关键词"""
        try:
            content_no_tags = "Python和人工智能正在改变软件开发的方式。机器学习模型越来越强大。"
            keywords = self.summarizer.extract_keywords(content_no_tags)
            # 无tags时会尝试提取中文词
            assert isinstance(keywords, list), "应返回列表"
            return {"passed": True, "message": f"无tags时关键词: {keywords}"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_estimate_reading_time(self) -> Dict:
        """阅读时间估算正确"""
        try:
            rt = self.summarizer.estimate_reading_time(self.TEST_ARTICLE)
            assert rt >= 1, f"阅读时间至少1分钟, 实际{rt}"

            # 短文章
            short = "这是一篇短文。"
            rt_short = self.summarizer.estimate_reading_time(short)
            assert rt_short == 1, f"短文阅读时间应为1分钟, 实际{rt_short}"

            return {"passed": True, "message": f"阅读时间估算: {rt}分钟"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_generate_summary_block(self) -> Dict:
        """生成摘要块格式正确"""
        try:
            block = self.summarizer.generate_summary_block(self.TEST_ARTICLE)
            assert ":::tip[" in block and "快速阅读" in block, "应包含tip引用块"
            assert "一句话总结" in block, "应包含一句话总结"
            assert "阅读时间" in block, "应包含阅读时间"
            assert "核心观点" in block, "应包含核心观点"
            assert "关键词" in block, "应包含关键词"
            assert ":::" in block.split("关键词")[-1], "应正确关闭tip块"
            return {"passed": True, "message": "摘要块格式正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_inject_summary_position(self) -> Dict:
        """摘要注入位置正确（frontmatter之后）"""
        try:
            result = self.summarizer.inject_summary(self.TEST_ARTICLE)
            # 验证frontmatter在摘要之前
            parts = result.split("---")
            assert len(parts) >= 3, "应保留frontmatter结构"

            # 验证摘要在frontmatter之后、正文之前
            after_fm = result.split("---")[2]
            assert "快速阅读" in after_fm, "摘要应在frontmatter之后"
            assert "今天，AI芯片市场发生了重大变化" in result, "正文应保留"

            return {"passed": True, "message": "摘要注入位置正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_inject_summary_no_frontmatter(self) -> Dict:
        """无frontmatter时摘要注入到开头"""
        try:
            content = "这是一篇没有frontmatter的文章。\n\n**重点内容**。"
            result = self.summarizer.inject_summary(content)
            # generate_summary_block 以空行开头，所以 result 以 \n 开头
            assert ":::tip[" in result and "快速阅读" in result, "无frontmatter时应包含摘要"
            assert "这是一篇没有frontmatter的文章" in result, "正文应保留"
            assert "这是一篇没有frontmatter的文章" in result, "正文应保留"
            return {"passed": True, "message": "无frontmatter注入正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_get_article_summary_dict(self) -> Dict:
        """便捷函数返回结构正确"""
        try:
            summary = get_article_summary(self.TEST_ARTICLE)
            assert "tldr" in summary, "应有tldr"
            assert "insights" in summary, "应有insights"
            assert "keywords" in summary, "应有keywords"
            assert "reading_time" in summary, "应有reading_time"
            assert isinstance(summary["insights"], list), "insights应为列表"
            assert isinstance(summary["reading_time"], int), "reading_time应为整数"
            return {"passed": True, "message": "便捷函数返回结构正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def run_all(self) -> Dict:
        """运行全部测试"""
        tests = [
            self.test_extract_tldr_from_description,
            self.test_extract_tldr_from_content,
            self.test_extract_key_insights,
            self.test_extract_keywords_from_tags,
            self.test_extract_keywords_fallback,
            self.test_estimate_reading_time,
            self.test_generate_summary_block,
            self.test_inject_summary_position,
            self.test_inject_summary_no_frontmatter,
            self.test_get_article_summary_dict,
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
