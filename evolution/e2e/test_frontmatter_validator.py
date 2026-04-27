# -*- coding: utf-8 -*-
"""
Frontmatter Validator 端到端测试
验证 frontmatter 解析、检测和自动修复逻辑
"""

import os
import tempfile
import shutil
from typing import Dict
from evolution.frontmatter_validator import FrontmatterValidator, validate_article, batch_validate_files


class TestFrontmatterValidator:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_fv_")
        self.validator = FrontmatterValidator()

    def __del__(self):
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_validate_complete_frontmatter(self) -> Dict:
        """完整 frontmatter 验证通过"""
        try:
            content = '''---
title: "AI芯片市场新格局"
published: 2026-04-21T08:00:00+08:00
tags: [科技, AI, 芯片]
category: news
draft: false
image: https://picsum.photos/seed/test/1600/900
description: "测试描述"
---

正文内容
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            assert valid, f"完整 frontmatter 应通过验证，错误: {errors}"
            assert fixed == content, "无需修复时应返回原内容"
            return {"passed": True, "message": "完整 frontmatter 验证通过"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_missing_frontmatter(self) -> Dict:
        """缺少 frontmatter 时自动添加"""
        try:
            content = "\n正文内容，没有 frontmatter\n"
            valid, errors, fixed = self.validator.validate(content, "2026-04-21-test.md")
            assert "---" in fixed, "应自动添加 frontmatter"
            assert "title:" in fixed, "应包含 title 字段"
            assert any("缺少 frontmatter" in e for e in errors), "应报告缺少 frontmatter"
            return {"passed": True, "message": "缺少 frontmatter 自动添加正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_title_quote_nesting(self) -> Dict:
        """title 引号嵌套检测和修复"""
        try:
            content = '''---
title: "AI\\"深度\\"解析"
published: 2026-04-21T08:00:00+08:00
tags: [科技]
category: news
draft: false
---

正文
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            assert any("引号嵌套" in e for e in errors), "应检测到引号嵌套"
            assert "title: '" in fixed, "应修复为单引号包裹"
            return {"passed": True, "message": "title 引号嵌套检测和修复正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_description_quote_nesting(self) -> Dict:
        """description 引号嵌套检测和修复"""
        try:
            content = '''---
title: "测试标题"
published: 2026-04-21T08:00:00+08:00
tags: [科技]
category: news
draft: false
description: "包含\\"嵌套\\"引号"
---

正文
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            assert any("description 存在引号嵌套" in e for e in errors), "应检测到 description 引号嵌套"
            return {"passed": True, "message": "description 引号嵌套检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_published_format(self) -> Dict:
        """published 格式不正确检测"""
        try:
            content = '''---
title: "测试标题"
published: "2026-04-21"
tags: [科技]
category: news
draft: false
---

正文
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            assert any("published 格式不正确" in e for e in errors), "应检测到 published 格式错误"
            return {"passed": True, "message": "published 格式检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_tags_not_list(self) -> Dict:
        """tags 不是数组时检测"""
        try:
            content = '''---
title: "测试标题"
published: 2026-04-21T08:00:00+08:00
tags: "科技, AI"
category: news
draft: false
---

正文
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            assert any("tags 必须是数组" in e for e in errors), "应检测到 tags 不是数组"
            return {"passed": True, "message": "tags 格式检测正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_duplicate_keys(self) -> Dict:
        """重复键检测和清理"""
        try:
            content = '''---
title: "测试标题"
published: 2026-04-21T08:00:00+08:00
tags: [科技]
category: news
draft: false
image: https://example.com/1.jpg
image: https://example.com/2.jpg
---

正文
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            assert any("重复键" in e for e in errors), "应检测到重复键"
            # 统计 fixed 中 image 出现的次数
            image_count = fixed.count("image:")
            assert image_count == 1, f"应清理重复键，只剩 1 个 image，当前有 {image_count} 个"
            return {"passed": True, "message": "重复键检测和清理正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_missing_required_fields(self) -> Dict:
        """缺少必要字段自动补全"""
        try:
            content = '''---
title: "测试标题"
published: 2026-04-21T08:00:00+08:00
---

正文
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            assert any("缺少必要字段" in e for e in errors), "应检测到缺少必要字段"
            assert "category:" in fixed, "应自动补全 category"
            assert "draft:" in fixed, "应自动补全 draft"
            assert any("已自动补全" in e for e in errors), "应报告自动补全"
            return {"passed": True, "message": "缺少字段自动补全正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_yaml_syntax_error(self) -> Dict:
        """YAML 语法错误修复"""
        try:
            # 制造一个 title 引号嵌套的 YAML 错误
            content = '''---
title: "AI"深度"解析"
published: 2026-04-21T08:00:00+08:00
tags: [科技]
category: news
draft: false
---

正文
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            # 我们的简单 YAML 解析器可能无法解析这种错误，所以会尝试修复
            assert fixed != content or any("YAML" in e for e in errors), "应检测到或修复 YAML 问题"
            return {"passed": True, "message": "YAML 语法处理正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_validate_leading_whitespace(self) -> Dict:
        """允许开头有空行的 frontmatter"""
        try:
            content = '''
---
title: "测试标题"
published: 2026-04-21T08:00:00+08:00
tags: [科技]
category: news
draft: false
---

正文
'''
            valid, errors, fixed = self.validator.validate(content, "test.md")
            assert valid, f"开头有空行应通过验证，错误: {errors}"
            return {"passed": True, "message": "开头空行兼容正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_convenience_validate_article(self) -> Dict:
        """便捷函数 validate_article"""
        try:
            content = '''---
title: "测试"
published: 2026-04-21T08:00:00+08:00
tags: [科技]
category: news
draft: false
---

正文
'''
            valid, errors, fixed = validate_article(content, "test.md")
            assert isinstance(valid, bool), "应返回布尔值 valid"
            assert isinstance(errors, list), "应返回列表 errors"
            assert isinstance(fixed, str), "应返回字符串 fixed"
            return {"passed": True, "message": "便捷函数工作正常"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def test_batch_validate_files(self) -> Dict:
        """批量验证文件"""
        try:
            # 创建测试文件
            f1 = os.path.join(self.tmpdir, "valid.md")
            f2 = os.path.join(self.tmpdir, "invalid.md")
            with open(f1, 'w') as f:
                f.write('---\ntitle: "有效"\npublished: 2026-04-21T08:00:00+08:00\ntags: [科技]\ncategory: news\ndraft: false\n---\n\n正文')
            with open(f2, 'w') as f:
                f.write('无 frontmatter 的内容')

            results = batch_validate_files([f1, f2])
            assert f1 in results, "应包含有效文件结果"
            assert f2 in results, "应包含无效文件结果"
            assert results[f1]["valid"] == True, "有效文件应标记为 valid"
            assert results[f2]["valid"] == False, "无效文件应标记为 invalid"
            return {"passed": True, "message": "批量验证正确"}
        except Exception as e:
            return {"passed": False, "message": str(e)}

    def run_all(self) -> Dict:
        tests = [
            self.test_validate_complete_frontmatter,
            self.test_validate_missing_frontmatter,
            self.test_validate_title_quote_nesting,
            self.test_validate_description_quote_nesting,
            self.test_validate_published_format,
            self.test_validate_tags_not_list,
            self.test_validate_duplicate_keys,
            self.test_validate_missing_required_fields,
            self.test_validate_yaml_syntax_error,
            self.test_validate_leading_whitespace,
            self.test_convenience_validate_article,
            self.test_batch_validate_files,
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
            "suite": "frontmatter_validator",
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "results": results,
        }


if __name__ == "__main__":
    tester = TestFrontmatterValidator()
    report = tester.run_all()
    print(f"\n## frontmatter_validator ({report['passed']}/{report['total']})")
    for r in report["results"]:
        emoji = "✅" if r["passed"] else "❌"
        print(f"- {emoji} **{r['test']}**: {r['message']}")
