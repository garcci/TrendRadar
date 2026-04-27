# -*- coding: utf-8 -*-
"""
github.py 核心流程端到端测试

测试场景（无需 AI 调用）：
1. _sanitize_frontmatter: 各种 frontmatter 问题的修复
2. _validate_article_format: 文章格式验证
3. 文件名生成一致性

历史教训：
- 曾出现 frontmatter 重复 image 键导致 Astro Schema 错误
- 曾出现 title 引号嵌套导致 YAML 解析失败
- 曾出现空行开头的 frontmatter 导致正则匹配失败
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# 设置假 token 避免初始化报错（只测试静态方法）
os.environ.setdefault("ASTRO_GITHUB_TOKEN", "fake_token_for_testing")

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from trendradar.storage.github import GitHubStorageBackend


class TestGitHubPipeline:
    """github.py 核心流程端到端测试"""

    def __init__(self):
        self.test_results = []
        self.storage = GitHubStorageBackend()

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_sanitize_quote_nesting(self):
        """测试1: 双引号嵌套修复"""
        content = '''---
title: "DeepSeek "V4" 降价"
published: 2026-04-27T08:00:00+08:00
category: news
draft: false
---

正文...
'''
        fixed = self.storage._sanitize_frontmatter(content, "2026-04-27", "默认标题")
        # 修复后 title 应该用单引号包裹
        has_single_quotes = "title: '" in fixed
        has_nested_quotes = 'title: "DeepSeek "V4"' in fixed

        if has_single_quotes and not has_nested_quotes:
            self._log("引号嵌套修复", True, "双引号嵌套已修复为单引号包裹")
        else:
            self._log("引号嵌套修复", False, f"引号嵌套未正确修复")

    def test_sanitize_duplicate_keys(self):
        """测试2: 重复键去重"""
        content = '''---
title: "测试"
published: 2026-04-27T08:00:00+08:00
category: news
draft: false
image: https://a.com/1.jpg
image: https://a.com/2.jpg
---

正文...
'''
        fixed = self.storage._sanitize_frontmatter(content, "2026-04-27", "默认标题")
        image_count = fixed.count("image:")

        if image_count == 1:
            self._log("重复键去重", True, "重复 image 键已清理为 1 个")
        else:
            self._log("重复键去重", False, f"重复 image 键未清理（当前 {image_count} 个）")

    def test_sanitize_missing_frontmatter(self):
        """测试3: 缺少 frontmatter → 添加默认"""
        content = "纯正文内容，没有 frontmatter"
        fixed = self.storage._sanitize_frontmatter(content, "2026-04-27", "默认标题")
        has_fm = fixed.lstrip().startswith("---")
        has_title = "title:" in fixed

        if has_fm and has_title:
            self._log("缺少 frontmatter", True, "缺少 frontmatter 时已自动添加默认")
        else:
            self._log("缺少 frontmatter", False, "未正确添加默认 frontmatter")

    def test_sanitize_empty_line_prefix(self):
        """测试4: 空行开头兼容"""
        content = '''
---
title: "空行开头测试"
published: 2026-04-27T08:00:00+08:00
category: news
draft: false
---

正文...
'''
        fixed = self.storage._sanitize_frontmatter(content, "2026-04-27", "默认标题")
        # 修复后应该能正确解析 frontmatter
        has_title = "title:" in fixed

        if has_title:
            self._log("空行开头兼容", True, "空行开头的 frontmatter 正确解析")
        else:
            self._log("空行开头兼容", False, "空行开头的 frontmatter 解析失败")

    def test_validate_article_format(self):
        """测试5: 文章格式验证"""
        # 正常文章
        valid_content = '''---
title: "正常文章"
published: 2026-04-27T08:00:00+08:00
tags: ["AI"]
category: news
draft: false
image: https://example.com/cover.jpg
description: "这是一篇关于人工智能技术的深度分析文章，探讨了最新发展趋势"
---

## 核心观点

1. 观点一

这是一篇测试文章的完整正文内容。在这里我们填充了足够多的文字，
以满足文章长度验证的要求。人工智能正在快速发展，各个行业都在
积极探索 AI 技术的应用。从自然语言处理到计算机视觉，从自动驾驶
到医疗诊断，AI 的影响力无处不在。我们需要深入理解这些技术的原理、
应用场景以及潜在风险，才能更好地把握未来发展方向。此外，数据隐私
和算法公平性也是当前亟需解决的重要问题。
'''
        is_valid, msg = self.storage._validate_article_format(valid_content, "2026-04-27")
        if is_valid:
            self._log("文章格式验证", True, "正常文章格式验证通过")
        else:
            self._log("文章格式验证", False, f"正常文章验证失败: {msg}")

    def test_validate_missing_fields(self):
        """测试6: 缺少必要字段 → 验证失败"""
        bad_content = '''---
title: "缺少字段"
---

正文...
'''
        is_valid, msg = self.storage._validate_article_format(bad_content, "2026-04-27")
        if not is_valid and "缺少" in msg:
            self._log("缺少字段检测", True, "缺少必要字段时验证正确失败")
        else:
            self._log("缺少字段检测", False, f"应失败但未失败: {msg}")

    def test_sanitize_unquoted_title(self):
        """测试7: 未用引号包裹的 title → 强制加引号"""
        content = '''---
title: 没有用引号的标题
published: 2026-04-27T08:00:00+08:00
category: news
draft: false
---

正文...
'''
        fixed = self.storage._sanitize_frontmatter(content, "2026-04-27", "默认标题")
        # title 应该被引号包裹
        title_line = [l for l in fixed.split('\n') if l.strip().startswith('title:')]
        if title_line:
            val = title_line[0].split(':', 1)[1].strip()
            is_quoted = (val.startswith('"') and val.endswith('"')) or \
                       (val.startswith("'") and val.endswith("'"))
            if is_quoted:
                self._log("title 强制引号", True, "未用引号包裹的 title 已强制加引号")
            else:
                self._log("title 强制引号", False, f"title 仍未加引号: {val}")
        else:
            self._log("title 强制引号", False, "未找到 title 行")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("github.py 核心流程端到端测试")
        print("=" * 60)

        self.test_sanitize_quote_nesting()
        self.test_sanitize_duplicate_keys()
        self.test_sanitize_missing_frontmatter()
        self.test_sanitize_empty_line_prefix()
        self.test_validate_article_format()
        self.test_validate_missing_fields()
        self.test_sanitize_unquoted_title()

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
    tester = TestGitHubPipeline()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
