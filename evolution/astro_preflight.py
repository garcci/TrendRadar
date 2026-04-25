# -*- coding: utf-8 -*-
"""
Astro 构建预检 — 推送前模拟验证，防止构建失败

检查项：
1. frontmatter YAML 语法
2. 必需字段完整性
3. 日期格式
4. 图片 URL 格式
5. 标签格式
6. 文件名格式
7. 引号嵌套问题
8. 特殊字符转义
9. 与 Astro Content Schema 兼容性
"""

import re
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class AstroPreflight:
    """Astro 构建预检器"""

    # Astro Content Schema 要求的必需字段
    REQUIRED_FIELDS = ["title", "published", "description", "image", "tags", "category", "draft"]

    # 已知会导致构建失败的模式
    DANGEROUS_PATTERNS = [
        (r'^\s*---\s*\n', "frontmatter 缺少开头的 ---"),
        (r'title:\s*"[^"]*"[^\s]', "title 引号内有未转义字符"),
        (r'description:\s*"[^"]*"[^\s]', "description 引号内有未转义字符"),
        (r':\s*\n\s*\n', "YAML 字段后有多余空行（可能导致解析错误）"),
        (r'title:\s*[^"\']', "title 值未用引号包裹"),
        (r'published:\s*\d{4}-\d{2}-\d{2}$', "published 缺少时间部分"),
        (r'draft:\s*[^truefals]', "draft 值格式错误"),
        (r'category:\s*[^"\']', "category 值未用引号包裹"),
        (r'image:\s*[^h]', "image 值不是 URL"),
    ]

    def __init__(self):
        self.issues = []
        self.warnings = []

    def check(self, content: str, filename: str = "") -> Tuple[bool, List[str], List[str]]:
        """
        执行完整预检

        Returns:
            (is_passed, errors, warnings)
        """
        self.issues = []
        self.warnings = []

        # 1. 提取 frontmatter
        frontmatter, body = self._extract_frontmatter(content)
        if frontmatter is None:
            self.issues.append("无法提取 frontmatter：缺少 --- 分隔符")
            return False, self.issues, self.warnings

        # 2. YAML 语法检查
        yaml_data = self._check_yaml_syntax(frontmatter, filename)
        if yaml_data is None:
            return False, self.issues, self.warnings

        # 3. 必需字段检查
        self._check_required_fields(yaml_data)

        # 4. 字段格式检查
        self._check_field_formats(yaml_data)

        # 5. 引号嵌套检查
        self._check_quote_nesting(frontmatter, filename)

        # 6. 文件名格式检查
        if filename:
            self._check_filename(filename)

        # 7. 危险模式检查
        self._check_dangerous_patterns(content)

        # 8. 图片 URL 格式检查
        self._check_image_url(yaml_data)

        is_passed = len(self.issues) == 0
        return is_passed, self.issues, self.warnings

    def _extract_frontmatter(self, content: str) -> Tuple[Optional[str], str]:
        """提取 frontmatter 和正文"""
        if not content.startswith("---"):
            return None, content

        # 找到第二个 ---
        match = re.search(r'\n---\s*\n', content[3:])
        if not match:
            return None, content

        end_pos = 3 + match.end()
        frontmatter = content[3:end_pos - 4].strip()
        body = content[end_pos:].strip()
        return frontmatter, body

    def _check_yaml_syntax(self, frontmatter: str, filename: str) -> Optional[Dict]:
        """检查 YAML 语法"""
        try:
            import yaml
            data = yaml.safe_load(frontmatter)
            if not isinstance(data, dict):
                self.issues.append("frontmatter 解析结果不是对象")
                return None
            return data
        except yaml.YAMLError as e:
            # 提取具体错误信息
            error_msg = str(e)
            # 简化错误信息
            if "mapping values are not allowed" in error_msg:
                self.issues.append(f"YAML 语法错误: 冒号后缺少空格或缩进错误")
            elif "could not determine a constructor" in error_msg:
                self.issues.append(f"YAML 语法错误: 特殊字符未转义")
            else:
                self.issues.append(f"YAML 语法错误: {error_msg[:100]}")
            return None
        except Exception as e:
            self.issues.append(f"YAML 解析失败: {e}")
            return None

    def _check_required_fields(self, data: Dict):
        """检查必需字段"""
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                self.issues.append(f"缺少必需字段: {field}")

    def _check_field_formats(self, data: Dict):
        """检查字段格式"""
        # title
        title = data.get("title", "")
        if isinstance(title, str):
            if "\n" in title or "\r" in title:
                self.issues.append("title 包含换行符")
            if len(title) > 200:
                self.warnings.append("title 过长（>200字符）")
            if '"' in title and not title.startswith('"'):
                self.warnings.append("title 包含未转义的双引号")

        # published
        published = data.get("published")
        if published:
            published_str = str(published)
            # 检查是否为 ISO 8601 格式
            if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', published_str):
                if re.match(r'^\d{4}-\d{2}-\d{2}$', published_str):
                    self.warnings.append("published 只有日期部分，缺少时间")
                else:
                    self.issues.append(f"published 格式错误: {published_str[:30]}")

        # description
        desc = data.get("description", "")
        if isinstance(desc, str) and len(desc) > 500:
            self.warnings.append("description 过长（>500字符）")

        # tags
        tags = data.get("tags")
        if tags is not None:
            if not isinstance(tags, list):
                self.issues.append("tags 必须是列表格式")
            else:
                for i, tag in enumerate(tags):
                    if not isinstance(tag, str):
                        self.issues.append(f"tags[{i}] 不是字符串")
                    elif ',' in tag:
                        self.warnings.append(f"tags[{i}] 包含逗号，可能导致解析问题")

        # draft
        draft = data.get("draft")
        if draft is not None and not isinstance(draft, bool):
            self.issues.append("draft 必须是布尔值 true/false")

        # category
        category = data.get("category")
        if category is not None and not isinstance(category, str):
            self.issues.append("category 必须是字符串")

    def _check_quote_nesting(self, frontmatter: str, filename: str):
        """检查引号嵌套问题"""
        lines = frontmatter.split('\n')
        for i, line in enumerate(lines, 1):
            # 检查双引号内的双引号
            if ':' in line:
                value_part = line.split(':', 1)[1].strip()
                if value_part.startswith('"'):
                    # 找到结束引号
                    inner = value_part[1:]
                    # 简单检查：如果内部有未转义的双引号
                    # 这只是一个启发式检查，不完全准确
                    pass

        # 更精确的检查：YAML 已经解析成功了，但如果原始内容中有中文引号，警告
        if '「' in frontmatter or '」' in frontmatter or '"' in frontmatter:
            self.warnings.append("frontmatter 包含中文引号或特殊引号字符")

    def _check_filename(self, filename: str):
        """检查文件名格式"""
        basename = filename.split('/')[-1] if '/' in filename else filename
        if not basename.endswith('.md'):
            self.issues.append("文件名必须以 .md 结尾")

        # 标准格式: YYYY-MM-DD-slug.md
        if not re.match(r'^\d{4}-\d{2}-\d{2}-', basename):
            self.warnings.append("文件名不以日期前缀开头")

        # 检查是否有特殊字符
        name_part = basename[:-3]
        if re.search(r'[^\w\-]', name_part):
            self.warnings.append("文件名包含非标准字符（建议使用字母、数字、连字符）")

    def _check_dangerous_patterns(self, content: str):
        """检查已知危险模式"""
        for pattern, desc in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.MULTILINE):
                self.warnings.append(f"检测到潜在问题: {desc}")

    def _check_image_url(self, data: Dict):
        """检查图片 URL 格式"""
        image = data.get("image", "")
        if image:
            if not isinstance(image, str):
                self.issues.append("image 必须是字符串 URL")
                return

            if not image.startswith(("http://", "https://")):
                self.issues.append(f"image URL 格式错误: {image[:50]}")
                return

            # 检查 URL 编码问题
            try:
                parsed = urllib.parse.urlparse(image)
                if not parsed.netloc:
                    self.issues.append("image URL 缺少域名")
            except Exception:
                self.issues.append("image URL 解析失败")

    def get_report(self) -> str:
        """生成预检报告"""
        lines = ["# Astro 构建预检报告", ""]

        if self.issues:
            lines.append(f"## ❌ 错误 ({len(self.issues)})")
            for issue in self.issues:
                lines.append(f"- {issue}")
            lines.append("")

        if self.warnings:
            lines.append(f"## ⚠️ 警告 ({len(self.warnings)})")
            for warning in self.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        if not self.issues and not self.warnings:
            lines.append("✅ 所有检查通过，可以安全推送")

        return '\n'.join(lines)


def preflight_check(content: str, filename: str = "") -> Tuple[bool, str]:
    """
    便捷函数：执行预检并返回结果

    Returns:
        (is_passed, report)
    """
    checker = AstroPreflight()
    is_passed, errors, warnings = checker.check(content, filename)
    report = checker.get_report()
    return is_passed, report


if __name__ == "__main__":
    # 测试用例
    test_content = '''---
title: "测试文章"
published: 2026-04-25T10:00:00+08:00
description: "这是一个测试"
image: https://picsum.photos/seed/test/1600/900
tags: ["AI", "测试"]
category: news
draft: false
---

测试内容
'''
    passed, report = preflight_check(test_content, "2026-04-25-test.md")
    print(report)
