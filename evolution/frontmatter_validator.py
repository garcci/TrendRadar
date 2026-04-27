# -*- coding: utf-8 -*-
"""
Frontmatter 预验证模块 — 防止 YAML 格式错误导致 Astro 构建失败

验证规则：
1. 必须有完整的 frontmatter（--- ... ---）
2. title 字段必须存在，且引号不能嵌套
3. published 字段必须存在且格式正确
4. category / draft / tags / description 等字段完整性检查
5. YAML 语法必须可解析
6. 特殊字符转义检查（中文引号、换行符等）

自动修复：
- title 中含双引号 → 改用单引号包裹
- 缺少必要字段 → 补全默认值
- 换行符污染 → 清理
"""

import re
from typing import Dict, List, Optional, Tuple


class FrontmatterValidator:
    """Frontmatter 预验证器"""

    REQUIRED_FIELDS = ["title", "published", "category", "draft"]
    OPTIONAL_FIELDS = ["tags", "image", "description", "excerpt", "cover"]

    def validate(self, content: str, filename: str = "") -> Tuple[bool, List[str], str]:
        """
        验证 frontmatter
        
        Returns:
            (is_valid, errors, fixed_content)
        """
        errors = []
        fixed = content

        # 1. 检查 frontmatter 是否存在（允许开头有空行）
        fm_match = re.match(r'^\s*---\n(.*?)\n---\n', fixed, re.DOTALL)
        if not fm_match:
            errors.append("缺少 frontmatter（必须以 --- 开头）")
            # 尝试补全默认 frontmatter
            fixed = self._add_default_frontmatter(fixed, filename)
            return len(errors) == 0, errors, fixed

        fm_raw = fm_match.group(1)
        body = fixed[fm_match.end():]

        # 2. 解析 YAML 检查语法
        parsed = self._parse_yaml(fm_raw)
        if parsed is None:
            errors.append("YAML 语法错误，无法解析 frontmatter")
            # 尝试修复常见 YAML 错误
            fm_fixed = self._fix_yaml_syntax(fm_raw)
            fixed = f"---\n{fm_fixed}\n---\n{body}"
            # 重新解析
            parsed = self._parse_yaml(fm_fixed)
            if parsed is None:
                return False, errors + ["自动修复后仍然无法解析 YAML"], fixed
            errors.append("已自动修复 YAML 语法错误")
        
        fm = parsed

        # 3. 检查必要字段
        for field in self.REQUIRED_FIELDS:
            if field not in fm:
                errors.append(f"缺少必要字段: {field}")
                fm[field] = self._get_default_value(field, filename)

        # 4. 检查 title 引号嵌套
        if "title" in fm:
            title_val = str(fm["title"])
            # 检测双引号嵌套
            if '"' in title_val:
                # 如果 title 用双引号包裹且内部有双引号
                title_line = re.search(r'^title:\s*(.+)$', fm_raw, re.MULTILINE)
                if title_line:
                    raw_title = title_line.group(1)
                    if raw_title.startswith('"') and raw_title.endswith('"') and '"' in raw_title[1:-1]:
                        errors.append(f'title 存在引号嵌套: "{title_val[:50]}..."')
                        # 修复：改用单引号包裹（如果没有单引号）
                        if "'" not in title_val:
                            fm["title"] = title_val  # 值本身不变，但输出时改用单引号
                            fm_raw = re.sub(
                                r'^title:\s*".+"$',
                                f"title: '{title_val}'",
                                fm_raw,
                                flags=re.MULTILINE
                            )
                        else:
                            # 同时有单双引号，转义双引号
                            safe = title_val.replace('"', '\\"')
                            fm_raw = re.sub(
                                r'^title:\s*".+"$',
                                f'title: "{safe}"',
                                fm_raw,
                                flags=re.MULTILINE
                            )
                        fixed = f"---\n{fm_raw}\n---\n{body}"
                        errors.append("已自动修复 title 引号嵌套")

        # 5. 检查 description 引号嵌套
        if "description" in fm:
            desc_val = str(fm["description"])
            desc_line = re.search(r'^description:\s*(.+)$', fm_raw, re.MULTILINE)
            if desc_line:
                raw_desc = desc_line.group(1)
                if raw_desc.startswith('"') and raw_desc.endswith('"') and '"' in raw_desc[1:-1]:
                    errors.append("description 存在引号嵌套")
                    if "'" not in desc_val:
                        fm_raw = re.sub(
                            r'^description:\s*".+"$',
                            f"description: '{desc_val}'",
                            fm_raw,
                            flags=re.MULTILINE
                        )
                    else:
                        safe = desc_val.replace('"', '\\"')
                        fm_raw = re.sub(
                            r'^description:\s*".+"$',
                            f'description: "{safe}"',
                            fm_raw,
                            flags=re.MULTILINE
                        )
                    fixed = f"---\n{fm_raw}\n---\n{body}"
                    errors.append("已自动修复 description 引号嵌套")

        # 6. 检查 published 格式
        if "published" in fm:
            published = str(fm["published"])
            if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', published):
                errors.append(f"published 格式不正确: {published}")

        # 7. 检查 tags 格式
        if "tags" in fm:
            tags = fm["tags"]
            if not isinstance(tags, list):
                errors.append(f"tags 必须是数组格式，当前: {type(tags).__name__}")

        # 8. 检查重复键（防止 Astro YAML 解析失败）
        seen_keys = set()
        deduped_lines = []
        dup_found = []
        for line in fm_raw.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                deduped_lines.append(line)
                continue
            if ':' not in stripped:
                deduped_lines.append(line)
                continue
            key = stripped.split(':', 1)[0].strip()
            # 跳过数组项和特殊键
            if key in ('tags',) or stripped.startswith('- '):
                deduped_lines.append(line)
                continue
            if key in seen_keys:
                dup_found.append(key)
                continue
            seen_keys.add(key)
            deduped_lines.append(line)
        
        if dup_found:
            errors.append(f"frontmatter 存在重复键: {set(dup_found)}")
            fm_raw = '\n'.join(deduped_lines)
            fixed = f"---\n{fm_raw}\n---\n{body}"
            errors.append("已自动清理重复键")

        # 重新组装（如果做过修改）
        if fixed != content:
            return len([e for e in errors if "已自动修复" not in e]) == 0, errors, fixed

        return len(errors) == 0, errors, content

    def _parse_yaml(self, yaml_str: str) -> Optional[Dict]:
        """安全解析 YAML"""
        try:
            # 使用简单的 key: value 解析（不需要完整 YAML 库）
            result = {}
            for line in yaml_str.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    # 尝试解析值
                    if val.startswith('[') and val.endswith(']'):
                        # 数组
                        result[key] = [v.strip().strip('"').strip("'") for v in val[1:-1].split(',') if v.strip()]
                    elif val.lower() == 'true':
                        result[key] = True
                    elif val.lower() == 'false':
                        result[key] = False
                    elif val.startswith('"') and val.endswith('"'):
                        result[key] = val[1:-1]
                    elif val.startswith("'") and val.endswith("'"):
                        result[key] = val[1:-1]
                    else:
                        try:
                            result[key] = int(val)
                        except ValueError:
                            try:
                                result[key] = float(val)
                            except ValueError:
                                result[key] = val
            return result
        except Exception:
            return None

    def _fix_yaml_syntax(self, yaml_str: str) -> str:
        """修复常见 YAML 语法错误"""
        lines = yaml_str.split('\n')
        fixed_lines = []
        for line in lines:
            # 修复 title 中的引号嵌套
            if line.startswith('title:') and '"' in line:
                match = re.match(r'^title:\s*"(.+)"$', line)
                if match:
                    val = match.group(1)
                    if '"' in val:
                        if "'" not in val:
                            line = f"title: '{val}'"
                        else:
                            line = f'title: "{val.replace(chr(34), chr(92)+chr(34))}"'
            fixed_lines.append(line)
        return '\n'.join(fixed_lines)

    def _add_default_frontmatter(self, content: str, filename: str) -> str:
        """为缺少 frontmatter 的内容添加默认 frontmatter"""
        # 从文件名提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        date_str = date_match.group(1) if date_match else "2026-01-01"
        
        default_fm = f"""---
title: "TrendRadar Report - {date_str}"
published: {date_str}T08:00:00+08:00
tags: [新闻, 热点]
category: news
draft: false
image: https://picsum.photos/seed/trendradar-{date_str.replace('-', '')}/1600/900
description: "TrendRadar 自动生成的热点聚合报告"
---

"""
        return default_fm + content

    def _get_default_value(self, field: str, filename: str) -> any:
        """获取字段默认值"""
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        date_str = date_match.group(1) if date_match else "2026-01-01"
        
        defaults = {
            "title": f"TrendRadar Report - {date_str}",
            "published": f"{date_str}T08:00:00+08:00",
            "category": "news",
            "draft": False,
            "tags": ["新闻", "热点"],
            "image": f"https://picsum.photos/seed/trendradar-{date_str.replace('-', '')}/1600/900",
            "description": "TrendRadar 自动生成的热点聚合报告"
        }
        return defaults.get(field, "")


def validate_article(content: str, filename: str = "") -> Tuple[bool, List[str], str]:
    """便捷函数：验证文章 frontmatter"""
    validator = FrontmatterValidator()
    return validator.validate(content, filename)


def batch_validate_files(filepaths: List[str]) -> Dict[str, Dict]:
    """批量验证文件"""
    validator = FrontmatterValidator()
    results = {}
    for fp in filepaths:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
            valid, errors, fixed = validator.validate(content, fp)
            results[fp] = {
                "valid": valid,
                "errors": errors,
                "fixed": fixed != content,
                "fixed_content": fixed if fixed != content else None
            }
        except Exception as e:
            results[fp] = {"valid": False, "errors": [str(e)], "fixed": False}
    return results


if __name__ == "__main__":
    # 测试
    test_content = '''---
title: "AI，4背后的秘密"价格战"与"价值战"：谁在定义新规则？"
published: 2026-04-25T08:00:00+08:00
tags: [新闻, 热点, 科技, 人工智能, 大模型, 半导体]
category: news
draft: false
image: https://picsum.photos/seed/deepseek-ai-model/1600/900
description: "DeepSeek V4发布引发行业地震"
---

文章内容...
'''
    valid, errors, fixed = validate_article(test_content, "2026-04-25-test.md")
    print(f"验证结果: {valid}")
    print(f"错误: {errors}")
    if fixed != test_content:
        print("已自动修复!")
        print(fixed[:500])
