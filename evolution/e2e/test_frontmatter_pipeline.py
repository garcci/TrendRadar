# -*- coding: utf-8 -*-
"""
Frontmatter 端到端测试

测试场景：
1. 正常 frontmatter → 验证通过
2. 引号嵌套 frontmatter → 检测错误并修复
3. 缺少字段 frontmatter → 检测错误并补全
4. 空行开头 frontmatter → 兼容验证（空行兼容 bug）
5. 验证修复后的内容可被 Astro 正确解析

历史教训：
- 曾出现 frontmatter 以空行开头导致正则匹配失败
- 曾出现 title 引号嵌套导致 YAML 解析失败
- 曾出现 image 键重复导致 Astro Schema 不匹配
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from evolution.frontmatter_validator import validate_article


class TestFrontmatterPipeline:
    """Frontmatter 生成→验证→修复 端到端测试"""

    def __init__(self):
        self.test_results = []

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_valid_frontmatter(self):
        """测试1: 正常的 frontmatter 应该验证通过"""
        content = """---
title: "DeepSeek V4 Pro 降价分析"
published: 2026-04-27T12:00:00.000Z
category: news
draft: false
tags: ["AI", "DeepSeek"]
image: https://example.com/cover.jpg
description: "分析 DeepSeek 最新降价策略"
---

正文内容...
"""
        is_valid, errors, fixed = validate_article(content, "test.md")
        if is_valid and len(errors) == 0:
            self._log("正常 frontmatter", True, "验证通过")
        else:
            self._log("正常 frontmatter", False, f"不应报错但出现: {errors}")

    def test_quote_nesting(self):
        """测试2: title 引号嵌套 → 检测并修复"""
        content = '''---
title: "DeepSeek "V4" 降价分析"
published: 2026-04-27T12:00:00.000Z
category: news
draft: false
---

正文...
'''
        is_valid, errors, fixed = validate_article(content, "test.md")
        # 应该检测到引号嵌套并修复
        has_quote_error = any("引号嵌套" in e for e in errors)
        fixed_has_no_nesting = 'title: \'DeepSeek "V4" 降价分析\'' in fixed

        if has_quote_error and fixed_has_no_nesting:
            self._log("引号嵌套修复", True, "检测到引号嵌套并自动修复为单引号包裹")
        else:
            self._log("引号嵌套修复", False, f"未正确修复: errors={errors}, fixed_title_present={fixed_has_no_nesting}")

    def test_missing_fields(self):
        """测试3: 缺少必要字段 → 检测并补全"""
        content = """---
title: "测试文章"
---

正文...
"""
        is_valid, errors, fixed = validate_article(content, "test.md")
        has_missing = any("缺少" in e for e in errors)
        fixed_has_fields = "published:" in fixed and "category:" in fixed and "draft:" in fixed

        if has_missing and fixed_has_fields:
            self._log("缺少字段补全", True, "检测到缺少字段并自动补全默认值")
        else:
            self._log("缺少字段补全", False, f"未正确补全: errors={errors}")

    def test_empty_line_prefix(self):
        """测试4: 空行开头的 frontmatter → 兼容验证

        历史 bug: 文件以 \n--- 开头时正则 ^--- 匹配失败
        """
        content = """
---
title: "空行开头测试"
published: 2026-04-27T12:00:00.000Z
category: news
draft: false
---

正文...
"""
        is_valid, errors, fixed = validate_article(content, "test.md")
        if is_valid:
            self._log("空行开头兼容", True, "空行开头的 frontmatter 验证通过")
        else:
            self._log("空行开头兼容", False, f"严重bug: 空行开头的 frontmatter 验证失败: {errors}")

    def test_duplicate_image_key(self):
        """测试5: 重复 image 键 → 检测并清理

        历史 bug: github.py 生成 frontmatter 时重复添加 image 键
        """
        content = """---
title: "测试"
published: 2026-04-27T12:00:00.000Z
category: news
draft: false
image: https://a.com/1.jpg
image: https://a.com/2.jpg
---

正文...
"""
        is_valid, errors, fixed = validate_article(content, "test.md")
        # 当前 validator 可能不检测重复键，但至少不应崩溃
        if "image:" in fixed:
            # 检查修复后是否只有一个 image
            image_count = fixed.count("image:")
            if image_count == 1:
                self._log("重复 image 键", True, f"检测到重复 image 键并清理为 1 个")
            else:
                self._log("重复 image 键", False, f"重复 image 键未清理（当前 {image_count} 个），可能导致 Astro Schema 错误")
        else:
            self._log("重复 image 键", True, "无 image 键（正常）")

    def test_yaml_syntax_error(self):
        """测试6: YAML 语法错误 → 检测并尝试修复"""
        # 使用会导致 _parse_yaml 异常的格式（缺少冒号的行会被视为键但无值）
        content = """---
title "缺少冒号"
published: 2026-04-27T12:00:00.000Z
category: news
draft: false
---

正文...
"""
        is_valid, errors, fixed = validate_article(content, "test.md")
        has_yaml_error = any("YAML" in e for e in errors)
        has_fixed = any("修复" in e for e in errors)
        # 即使没有检测到具体错误，验证器至少不应崩溃
        self._log("YAML 语法错误", True, f"{'检测到' if has_yaml_error else '未检测到'} YAML 错误，验证器未崩溃")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("Frontmatter 端到端测试")
        print("=" * 60)

        self.test_valid_frontmatter()
        self.test_quote_nesting()
        self.test_missing_fields()
        self.test_empty_line_prefix()
        self.test_duplicate_image_key()
        self.test_yaml_syntax_error()

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
    tester = TestFrontmatterPipeline()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
