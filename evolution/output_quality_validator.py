# -*- coding: utf-8 -*-
"""
Lv45: 输出质量验证器

解决核心问题：为什么 Issue 截断没有在进化过程中被发现？

根本原因：
1. 异常监控只捕获"运行时异常"（ImportError/TypeError），但截断是"逻辑错误"
2. 自主测试只验证"能运行"，不验证"输出内容是否正确"
3. 没有机制检查"生成的内容是否符合预期格式"
4. 反馈循环断裂：生成 → 无验证 → 发布

解决方案：
- 对关键输出进行质量验证
- 检测"静默错误"（代码运行正常但输出错误）
- 建立"结果 → 质量检查 → 修复建议"闭环

验证维度：
1. Issue内容: 是否包含frontmatter残留、是否被截断
2. 文章frontmatter: 字段完整性、格式正确性
3. 文章正文: 图片seed去重、链接有效性
4. 生成的代码: 语法正确性、逻辑合理性
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests


class OutputQualityValidator:
    """输出质量验证器 - 捕获静默错误"""
    
    # 常见的静默错误模式
    SILENT_ERROR_PATTERNS = {
        "frontmatter_leak": {
            "name": "Frontmatter内容泄漏",
            "description": "excerpt/description中包含frontmatter字段",
            "patterns": [
                r'^\s*\d+/\d+\s*$',  # "600/900" 这样的截断标记
                r'description:\s*"',  # description: "..."
                r'published:\s*\d',  # published: 2026...
                r'image:\s*https?://',  # image: url
                r'draft:\s*(true|false)',  # draft: true/false
                r'category:\s*\w+',  # category: news
            ],
            "severity": "high"
        },
        "truncation_marker": {
            "name": "截断标记残留",
            "description": "内容中包含截断标记",
            "patterns": [
                r'\[内容已截断',
                r'\[Truncated',
                r'\.\.\.\s*\n\s*\[.*截断',
            ],
            "severity": "medium"
        },
        "markdown_in_excerpt": {
            "name": "Markdown标记混入摘要",
            "description": "excerpt中包含markdown格式符号",
            "patterns": [
                r'^\s*#+\s',  # 标题标记
                r'^\s*[-*+]\s',  # 列表标记
                r'^\s*\d+\.\s',  # 数字列表
                r'^\s*>`',  # 引用块
            ],
            "severity": "low"
        },
        "empty_content": {
            "name": "内容为空",
            "description": "关键字段内容为空或仅空白",
            "check_func": lambda text: not text or not text.strip(),
            "severity": "high"
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.validation_log = []
    
    def validate_issue_content(self, body: str) -> Dict:
        """验证GitHub Issue内容质量"""
        issues = []
        
        # 检查frontmatter泄漏
        for pattern_str in self.SILENT_ERROR_PATTERNS["frontmatter_leak"]["patterns"]:
            if re.search(pattern_str, body, re.MULTILINE | re.IGNORECASE):
                issues.append({
                    "type": "frontmatter_leak",
                    "severity": "high",
                    "detail": f"发现frontmatter字段泄漏: {pattern_str[:30]}...",
                    "suggestion": "excerpt应跳过frontmatter，只提取纯文本内容"
                })
        
        # 检查截断标记
        for pattern_str in self.SILENT_ERROR_PATTERNS["truncation_marker"]["patterns"]:
            if re.search(pattern_str, body, re.IGNORECASE):
                issues.append({
                    "type": "truncation_marker",
                    "severity": "medium",
                    "detail": "内容中包含截断标记",
                    "suggestion": "增加MAX_ISSUE_BODY_LENGTH或精简内容"
                })
        
        # 检查Excerpt字段
        excerpt_match = re.search(r'\*\*Excerpt\*\*:[ \t]*\n(.+?)(?=\n\n|\n---|$)', body, re.DOTALL)
        if excerpt_match:
            excerpt = excerpt_match.group(1).strip()
            
            # 检查excerpt是否为空
            if not excerpt:
                issues.append({
                    "type": "empty_excerpt",
                    "severity": "high",
                    "detail": "Excerpt字段为空",
                    "suggestion": "确保生成内容时提取有效的摘要文本"
                })
            
            # 检查excerpt长度
            if len(excerpt) < 10:
                issues.append({
                    "type": "short_excerpt",
                    "severity": "medium",
                    "detail": f"Excerpt过短: {len(excerpt)}字符",
                    "suggestion": "excerpt应至少包含50-300字符的有意义内容"
                })
            
            # 检查markdown混入
            for pattern_str in self.SILENT_ERROR_PATTERNS["markdown_in_excerpt"]["patterns"]:
                if re.search(pattern_str, excerpt):
                    issues.append({
                        "type": "markdown_in_excerpt",
                        "severity": "low",
                        "detail": "Excerpt包含markdown格式标记",
                        "suggestion": "清理excerpt中的markdown标记"
                    })
        
        # 检查body整体长度
        if len(body) > 64000:
            issues.append({
                "type": "body_too_long",
                "severity": "medium",
                "detail": f"Issue body过长: {len(body)}字符",
                "suggestion": "精简内容或增加截断处理的智能性"
            })
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_issues": len(issues),
            "high_severity": sum(1 for i in issues if i["severity"] == "high"),
            "medium_severity": sum(1 for i in issues if i["severity"] == "medium"),
            "low_severity": sum(1 for i in issues if i["severity"] == "low")
        }
    
    def validate_article_frontmatter(self, content: str) -> Dict:
        """验证文章frontmatter完整性"""
        issues = []
        
        # 检查frontmatter是否存在
        if '---' not in content:
            issues.append({
                "type": "missing_frontmatter",
                "severity": "high",
                "detail": "文章缺少frontmatter",
                "suggestion": "确保AI生成的内容包含完整的frontmatter"
            })
            return {"valid": False, "issues": issues}
        
        # 提取frontmatter
        fm_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            issues.append({
                "type": "invalid_frontmatter",
                "severity": "high",
                "detail": "frontmatter格式不正确",
                "suggestion": "frontmatter必须以---开始和结束"
            })
            return {"valid": False, "issues": issues}
        
        frontmatter = fm_match.group(1)
        
        # 检查必需字段
        required_fields = ["title", "published", "tags", "category"]
        for field in required_fields:
            if f"{field}:" not in frontmatter:
                issues.append({
                    "type": "missing_field",
                    "severity": "high",
                    "detail": f"缺少必需字段: {field}",
                    "suggestion": f"在frontmatter中添加{field}字段"
                })
        
        # 检查tags格式
        tags_match = re.search(r'tags:\s*\[(.*?)\]', frontmatter)
        if tags_match:
            tags_str = tags_match.group(1)
            tags = [t.strip() for t in tags_str.split(',') if t.strip()]
            if len(tags) < 2:
                issues.append({
                    "type": "too_few_tags",
                    "severity": "medium",
                    "detail": f"标签数量过少: {len(tags)}个",
                    "suggestion": "tags应包含3-5个标签"
                })
        
        # 检查description/excerpt
        if 'description:' not in frontmatter and 'excerpt:' not in frontmatter:
            issues.append({
                "type": "missing_description",
                "severity": "low",
                "detail": "缺少description或excerpt字段",
                "suggestion": "添加description字段以提高SEO"
            })
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_issues": len(issues)
        }
    
    def validate_recent_issues(self, owner: str, repo: str, token: str, days: int = 3) -> Dict:
        """验证最近生成的GitHub Issues"""
        print(f"[质量验证] 检查最近{days}天的Issues...")
        
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            since = (datetime.now() - __import__('datetime').timedelta(days=days)).isoformat()
            
            response = requests.get(
                url,
                headers=headers,
                params={"labels": "memory,article-history", "since": since, "state": "all", "per_page": 10},
                timeout=10
            )
            
            if response.status_code != 200:
                return {"error": f"API错误: {response.status_code}"}
            
            issues_data = response.json()
            results = []
            
            for issue in issues_data:
                body = issue.get("body", "")
                validation = self.validate_issue_content(body)
                
                results.append({
                    "issue_number": issue.get("number"),
                    "title": issue.get("title", ""),
                    "validation": validation
                })
                
                if not validation["valid"]:
                    print(f"  ⚠️ Issue #{issue.get('number')}: 发现{validation['total_issues']}个问题")
                    for issue_detail in validation["issues"]:
                        print(f"    - [{issue_detail['severity']}] {issue_detail['type']}: {issue_detail['detail'][:50]}")
                else:
                    print(f"  ✅ Issue #{issue.get('number')}: 内容质量正常")
            
            total_checked = len(results)
            total_with_issues = sum(1 for r in results if not r["validation"]["valid"])
            
            return {
                "total_checked": total_checked,
                "total_with_issues": total_with_issues,
                "results": results
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def generate_validation_report(self, owner: str = None, repo: str = None, token: str = None) -> str:
        """生成质量验证报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("🔍 输出质量验证报告")
        lines.append("=" * 60)
        
        # 如果有GitHub配置，检查实际Issues
        if owner and repo and token:
            result = self.validate_recent_issues(owner, repo, token)
            
            if "error" in result:
                lines.append(f"\n⚠️ 无法获取Issues: {result['error']}")
            else:
                lines.append(f"\n📊 检查了{result['total_checked']}个Issues")
                lines.append(f"❌ 发现{result['total_with_issues']}个问题Issues")
                
                if result['total_with_issues'] > 0:
                    lines.append("\n⚠️ 需要修复的问题:")
                    for r in result["results"]:
                        if not r["validation"]["valid"]:
                            lines.append(f"\n  Issue #{r['issue_number']}: {r['title'][:40]}")
                            for issue in r["validation"]["issues"]:
                                lines.append(f"    [{issue['severity'].upper()}] {issue['type']}")
                                lines.append(f"    建议: {issue['suggestion']}")
        
        # 通用建议
        lines.append("\n💡 质量改进建议:")
        lines.append("  1. excerpt应跳过frontmatter，提取纯文本")
        lines.append("  2. Issue body长度应控制在65000字符以内")
        lines.append("  3. 摘要不应包含markdown格式标记")
        lines.append("  4. 定期检查生成内容的质量")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


# 便捷函数
def validate_output_quality(owner: str = None, repo: str = None, token: str = None) -> str:
    """验证输出质量并返回报告"""
    validator = OutputQualityValidator()
    return validator.generate_validation_report(owner, repo, token)


def check_issue_quality(body: str) -> Dict:
    """检查单个Issue内容质量"""
    validator = OutputQualityValidator()
    return validator.validate_issue_content(body)


if __name__ == "__main__":
    # 测试：验证示例内容
    test_body = """## Article Metadata

**Date**: 2026-04-24
**Title**: 测试文章

**Keywords**: AI, 测试

**Hot Topics**: 话题1, 话题2

**Platforms**: 知乎

**Excerpt**:
600/900
description: "这是测试描述"

---
*Auto-generated*
"""
    
    validator = OutputQualityValidator()
    result = validator.validate_issue_content(test_body)
    print(f"验证结果: {'通过' if result['valid'] else '未通过'}")
    print(f"问题数: {result['total_issues']}")
    for issue in result['issues']:
        print(f"  - [{issue['severity']}] {issue['type']}: {issue['detail']}")
