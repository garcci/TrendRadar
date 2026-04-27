# -*- coding: utf-8 -*-
"""
输出质量验证器端到端测试
验证：Issue内容检测、frontmatter验证、便捷函数
"""

from typing import Dict

from evolution.output_quality_validator import OutputQualityValidator, check_issue_quality


class TestOutputQualityValidator:
    """输出质量验证器端到端测试"""

    def __init__(self):
        self.validator = OutputQualityValidator()

    def test_validate_issue_frontmatter_leak(self) -> Dict:
        """检测frontmatter字段泄漏到excerpt"""
        try:
            body = """## Article Metadata

**Excerpt**:
600/900
description: "这是测试描述"
published: 2024-01-15
image: https://example.com/img.jpg

---
*Auto-generated*
"""
            result = self.validator.validate_issue_content(body)
            assert result["valid"] is False, "应检测为不通过"
            assert result["total_issues"] > 0, "应有发现问题"

            leak_issues = [i for i in result["issues"] if i["type"] == "frontmatter_leak"]
            assert len(leak_issues) > 0, "应检测到frontmatter泄漏"

            return {"passed": True, "message": f"检测到{len(leak_issues)}个frontmatter泄漏"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_issue_truncation_marker(self) -> Dict:
        """检测截断标记残留"""
        try:
            body = """## Article

**Excerpt**:
这是正常摘要

[内容已截断，请查看完整文章]

---
"""
            result = self.validator.validate_issue_content(body)
            trunc_issues = [i for i in result["issues"] if i["type"] == "truncation_marker"]
            assert len(trunc_issues) > 0, "应检测到截断标记"
            return {"passed": True, "message": "截断标记检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_issue_empty_excerpt(self) -> Dict:
        """检测空excerpt"""
        try:
            # Excerpt 后加空格+换行，避免 \s* 贪婪跨行匹配换行符
            body = """## Article

**Excerpt**: 


---
*Auto-generated*
"""
            result = self.validator.validate_issue_content(body)
            empty_issues = [i for i in result["issues"] if i["type"] == "empty_excerpt"]
            assert len(empty_issues) > 0, "应检测到空excerpt"
            return {"passed": True, "message": "空excerpt检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_issue_short_excerpt(self) -> Dict:
        """检测过短excerpt"""
        try:
            body = """## Article

**Excerpt**:
AI

**Keywords**: 测试

---
"""
            result = self.validator.validate_issue_content(body)
            short_issues = [i for i in result["issues"] if i["type"] == "short_excerpt"]
            assert len(short_issues) > 0, "应检测到excerpt过短"
            return {"passed": True, "message": "excerpt过短检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_issue_markdown_in_excerpt(self) -> Dict:
        """检测markdown标记混入excerpt"""
        try:
            body = """## Article

**Excerpt**:
# 这是标题标记
- 这是列表标记

**Keywords**: 测试

---
"""
            result = self.validator.validate_issue_content(body)
            md_issues = [i for i in result["issues"] if i["type"] == "markdown_in_excerpt"]
            assert len(md_issues) > 0, "应检测到markdown混入"
            return {"passed": True, "message": f"markdown混入检测正确: {len(md_issues)}个"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_issue_clean(self) -> Dict:
        """干净的Issue内容应通过"""
        try:
            body = """## Article Metadata

**Date**: 2024-01-15
**Title**: 测试文章

**Excerpt**:
这是一段正常的摘要内容，描述了文章的核心观点和关键信息。

**Keywords**: AI, 测试

---
*Auto-generated*
"""
            result = self.validator.validate_issue_content(body)
            assert result["valid"] is True, f"干净内容应通过, 实际{result['total_issues']}个问题"
            assert result["total_issues"] == 0, "不应有问题"
            return {"passed": True, "message": "干净Issue验证通过"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_article_frontmatter_complete(self) -> Dict:
        """完整frontmatter验证通过"""
        try:
            content = """---
title: "测试文章"
published: 2024-01-15T08:00:00+08:00
tags: ["科技", "AI"]
category: news
description: "这是一篇测试文章"
---

正文内容
"""
            result = self.validator.validate_article_frontmatter(content)
            assert result["valid"] is True, f"完整frontmatter应通过, 实际{result['total_issues']}个问题"
            return {"passed": True, "message": "完整frontmatter验证通过"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_article_frontmatter_missing(self) -> Dict:
        """缺少frontmatter"""
        try:
            content = "没有frontmatter的文章内容"
            result = self.validator.validate_article_frontmatter(content)
            assert result["valid"] is False, "应检测为不通过"
            missing = [i for i in result["issues"] if i["type"] == "missing_frontmatter"]
            assert len(missing) > 0, "应检测到缺少frontmatter"
            return {"passed": True, "message": "缺少frontmatter检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_article_frontmatter_missing_field(self) -> Dict:
        """frontmatter缺少必需字段"""
        try:
            content = """---
title: "测试文章"
published: 2024-01-15T08:00:00+08:00
---

正文
"""
            result = self.validator.validate_article_frontmatter(content)
            assert result["valid"] is False, "应检测为不通过"
            missing_fields = [i for i in result["issues"] if i["type"] == "missing_field"]
            assert len(missing_fields) >= 2, f"应至少检测到2个缺少字段, 实际{len(missing_fields)}"
            return {"passed": True, "message": f"检测到{len(missing_fields)}个缺少字段"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_article_frontmatter_too_few_tags(self) -> Dict:
        """标签数量过少"""
        try:
            content = """---
title: "测试文章"
published: 2024-01-15T08:00:00+08:00
tags: ["科技"]
category: news
---

正文
"""
            result = self.validator.validate_article_frontmatter(content)
            few_tags = [i for i in result["issues"] if i["type"] == "too_few_tags"]
            assert len(few_tags) > 0, "应检测到标签过少"
            return {"passed": True, "message": "标签过少检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_check_issue_quality_convenience(self) -> Dict:
        """便捷函数 check_issue_quality"""
        try:
            body = "**Excerpt**: \ndescription: leaked\n"
            result = check_issue_quality(body)
            assert "valid" in result, "应有valid字段"
            assert "issues" in result, "应有issues字段"
            return {"passed": True, "message": "便捷函数工作正常"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_body_too_long(self) -> Dict:
        """Issue body过长检测"""
        try:
            body = "**Excerpt**: \n正常摘要\n\n" + "x" * 64000
            result = self.validator.validate_issue_content(body)
            long_issues = [i for i in result["issues"] if i["type"] == "body_too_long"]
            assert len(long_issues) > 0, "应检测到body过长"
            return {"passed": True, "message": "body过长检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def run_all(self) -> Dict:
        """运行全部测试"""
        tests = [
            self.test_validate_issue_frontmatter_leak,
            self.test_validate_issue_truncation_marker,
            self.test_validate_issue_empty_excerpt,
            self.test_validate_issue_short_excerpt,
            self.test_validate_issue_markdown_in_excerpt,
            self.test_validate_issue_clean,
            self.test_validate_article_frontmatter_complete,
            self.test_validate_article_frontmatter_missing,
            self.test_validate_article_frontmatter_missing_field,
            self.test_validate_article_frontmatter_too_few_tags,
            self.test_check_issue_quality_convenience,
            self.test_body_too_long,
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
