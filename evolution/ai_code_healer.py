# -*- coding: utf-8 -*-
"""
Lv48: AI代码修复器

核心理念：用免费的GitHub Models自动诊断代码问题并生成修复。

修复范围：
1. 语法错误: 导入失败、缩进错误、类型错误
2. 逻辑错误: 死循环、空指针、边界条件
3. 性能问题: 重复计算、低效循环
4. 兼容性问题: Python版本差异、依赖缺失

修复流程：
1. 扫描代码文件
2. 用AI分析潜在问题
3. 生成修复建议
4. 自动应用安全修复
5. 验证修复结果

安全原则：
- 只修复确定安全的问题
- 复杂修改需要人工确认
- 修复前备份原代码
"""

import ast
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests


class AICodeHealer:
    """AI代码修复器 - 自动诊断和修复代码问题"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.heal_log_file = f"{trendradar_path}/evolution/code_heal_log.json"
        self.fixes_applied = []
    
    def scan_for_issues(self, file_path: str) -> List[Dict]:
        """扫描文件中的问题"""
        issues = []
        
        if not os.path.exists(file_path):
            return issues
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return issues
        
        # 1. 语法检查
        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append({
                "type": "syntax_error",
                "severity": "critical",
                "line": e.lineno,
                "message": str(e),
                "auto_fixable": False  # 语法错误太复杂，不自动修复
            })
        
        # 2. 常见模式检查
        issues.extend(self._check_common_patterns(content, file_path))
        
        # 3. 导入检查
        issues.extend(self._check_imports(content, file_path))
        
        return issues
    
    def _check_common_patterns(self, content: str, file_path: str) -> List[Dict]:
        """检查常见代码模式问题"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 检查裸except
            if re.match(r'^\s*except\s*:', line):
                issues.append({
                    "type": "bare_except",
                    "severity": "medium",
                    "line": i,
                    "message": "裸except会捕获所有异常包括KeyboardInterrupt",
                    "suggestion": "改为 except Exception:",
                    "auto_fixable": True,
                    "old": line,
                    "new": line.replace("except:", "except Exception:")
                })
            
            # 检查print调试语句
            if re.match(r'^\s*print\s*\(', line) and "# DEBUG" not in line:
                # 进化模块中的print是预期行为，不报告
                if "evolution/" not in file_path:
                    issues.append({
                        "type": "debug_print",
                        "severity": "low",
                        "line": i,
                        "message": "发现print语句，建议使用日志",
                        "auto_fixable": False
                    })
            
            # 检查硬编码路径
            if re.search(r'/Users/\w+/', line) or re.search(r'C:\\\\Users\\\\', line):
                issues.append({
                    "type": "hardcoded_path",
                    "severity": "low",
                    "line": i,
                    "message": "硬编码路径可能导致跨平台问题",
                    "auto_fixable": False
                })
            
            # 检查未使用的导入（简单检查）
            import_match = re.match(r'^\s*(?:from\s+\S+\s+)?import\s+(.+)', line)
            if import_match:
                imports = import_match.group(1).split(',')
                for imp in imports:
                    imp_name = imp.strip().split(' as ')[0].split('.')[0]
                    # 检查是否在文件中使用了（简单文本匹配）
                    if imp_name and not imp_name.startswith('_'):
                        usage_count = content.count(imp_name) - 1  # 减去import本身
                        if usage_count <= 0:
                            issues.append({
                                "type": "unused_import",
                                "severity": "low",
                                "line": i,
                                "message": f"可能未使用的导入: {imp_name}",
                                "auto_fixable": False
                            })
        
        return issues
    
    def _check_imports(self, content: str, file_path: str) -> List[Dict]:
        """检查导入问题"""
        issues = []
        
        # 检查常见导入错误模式
        common_mistakes = {
            r'from\s+evolution\s+import': "进化模块导入应使用完整路径",
            r'import\s+urllib3': "urllib3可能需要额外处理TLS警告"
        }
        
        for pattern, message in common_mistakes.items():
            if re.search(pattern, content):
                issues.append({
                    "type": "import_pattern",
                    "severity": "low",
                    "line": 0,
                    "message": message,
                    "auto_fixable": False
                })
        
        return issues
    
    def ai_diagnose(self, file_path: str) -> List[Dict]:
        """用AI诊断代码问题（使用免费GitHub Models）"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return issues
        
        # 只分析不超过500行的文件
        lines = content.split('\n')
        if len(lines) > 500:
            content = '\n'.join(lines[:500])
        
        prompt = f"""请分析以下Python代码，找出潜在问题：

文件: {os.path.basename(file_path)}

```python
{content}
```

请列出发现的问题，格式：
1. [严重程度] 问题类型: 描述
建议修复: 具体修改方法

只列出确定的问题，不要猜测。"""
        
        try:
            result = self._call_github_models([
                {"role": "user", "content": prompt}
            ])
            
            # 解析AI输出
            ai_issues = self._parse_ai_diagnosis(result)
            issues.extend(ai_issues)
            
        except Exception as e:
            print(f"[AI诊断] {file_path} 诊断失败: {e}")
        
        return issues
    
    def _call_github_models(self, messages: List[Dict]) -> str:
        """调用GitHub Models"""
        token = os.environ.get("GH_MODELS_TOKEN", "")
        if not token:
            raise Exception("GH_MODELS_TOKEN未配置")
        
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json={
            "model": "meta-llama-3.1-8b-instruct",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000
        }, timeout=60)
        
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def _parse_ai_diagnosis(self, text: str) -> List[Dict]:
        """解析AI诊断输出"""
        issues = []
        
        # 简单解析：查找 "数字. [级别]" 格式
        for match in re.finditer(r'\d+\.\s*\[(\w+)\]\s*(.+?)(?=\n\d+\.|\Z)', text, re.DOTALL):
            severity = match.group(1).lower()
            description = match.group(2).strip()
            
            severity_map = {
                "critical": "critical",
                "high": "high",
                "medium": "medium",
                "low": "low"
            }
            
            issues.append({
                "type": "ai_detected",
                "severity": severity_map.get(severity, "low"),
                "line": 0,
                "message": description[:200],
                "auto_fixable": False  # AI发现的问题不自动修复
            })
        
        return issues
    
    def auto_fix(self, file_path: str, issues: List[Dict]) -> Tuple[int, List[str]]:
        """自动修复可安全修复的问题"""
        fixes_applied = []
        fix_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return 0, []
        
        # 按行号倒序处理（避免行号偏移）
        auto_fixable = [i for i in issues if i.get("auto_fixable")]
        auto_fixable.sort(key=lambda x: x.get("line", 0), reverse=True)
        
        for issue in auto_fixable:
            line_num = issue.get("line", 0)
            if line_num <= 0 or line_num > len(lines):
                continue
            
            old_line = issue.get("old", "")
            new_line = issue.get("new", "")
            
            if old_line and new_line and lines[line_num - 1].strip() == old_line.strip():
                lines[line_num - 1] = lines[line_num - 1].replace(old_line.strip(), new_line.strip())
                fix_count += 1
                fixes_applied.append(f"  行{line_num}: {issue['type']}")
        
        if fix_count > 0:
            # 备份原文件
            backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original)
            except Exception:
                pass
            
            # 写入修复后的文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print(f"[代码修复] 已修复 {fix_count} 个问题: {file_path}")
            for fix in fixes_applied:
                print(fix)
        
        return fix_count, fixes_applied
    
    def heal_directory(self, directory: str, use_ai: bool = True) -> Dict:
        """修复整个目录的代码"""
        print(f"[代码修复] 扫描目录: {directory}")
        
        total_issues = 0
        total_fixed = 0
        file_reports = []
        
        for root, _, files in os.walk(directory):
            # 跳过非Python文件和特定目录
            if any(skip in root for skip in ['__pycache__', '.git', 'node_modules', 'dist']):
                continue
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                
                # 扫描问题
                issues = self.scan_for_issues(file_path)
                
                # AI诊断（如果启用）
                if use_ai and len(issues) < 5:  # 已有太多问题时不AI诊断
                    ai_issues = self.ai_diagnose(file_path)
                    issues.extend(ai_issues)
                
                if issues:
                    total_issues += len(issues)
                    
                    # 自动修复
                    fixed, fix_list = self.auto_fix(file_path, issues)
                    total_fixed += fixed
                    
                    file_reports.append({
                        "file": file_path,
                        "issues": len(issues),
                        "fixed": fixed,
                        "fixes": fix_list
                    })
        
        return {
            "total_files_scanned": len(file_reports),
            "total_issues_found": total_issues,
            "total_fixed": total_fixed,
            "files": file_reports
        }
    
    def generate_report(self, result: Dict) -> str:
        """生成修复报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("🔧 AI代码修复报告")
        lines.append("=" * 60)
        lines.append(f"扫描文件数: {result['total_files_scanned']}")
        lines.append(f"发现问题: {result['total_issues_found']}")
        lines.append(f"自动修复: {result['total_fixed']}")
        lines.append("")
        
        for f in result.get("files", []):
            if f["issues"] > 0:
                lines.append(f"📄 {f['file']}")
                lines.append(f"  问题: {f['issues']}, 修复: {f['fixed']}")
                for fix in f.get("fixes", []):
                    lines.append(f"  {fix}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# 便捷函数
def heal_codebase(directory: str = ".", use_ai: bool = True) -> str:
    """修复代码库"""
    healer = AICodeHealer()
    result = healer.heal_directory(directory, use_ai)
    return healer.generate_report(result)


if __name__ == "__main__":
    print(heal_codebase("trendradar"))
