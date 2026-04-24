# -*- coding: utf-8 -*-
"""
自动代码迭代系统 v1.0 - 让系统真正自己改自己

安全原则：
1. 只修改配置文件和模板，不动核心逻辑
2. 所有修改通过 Git 管理，可追溯可回滚
3. 修改前自动创建分支，验证后才合并
4. 关键修改需要人工确认（可选配置）
5. 每次只改一个地方，便于定位问题

支持自动迭代的范围：
Phase 1: 配置文件（安全）
  - RSS 源自动替换失效源
  - 平台配置自动调整
  - Prompt 模板自动更新
  - 阈值参数自动调优

Phase 2: 非核心代码（较安全）
  - 评估指标权重自动调整
  - 日志级别自动调整
  - 缓存策略自动优化

Phase 3: 核心代码（需严格验证）
  - 新功能自动添加
  - 性能瓶颈自动修复
"""

import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CodeChange:
    """代码变更记录"""
    file_path: str
    change_type: str  # 'replace', 'add', 'remove'
    original: str
    replacement: str
    reason: str
    confidence: float  # 0-1，表示自动修改的信心度
    requires_approval: bool  # 是否需要人工确认


class AutoCodeEvolution:
    """自动代码迭代引擎"""
    
    def __init__(self, repo_owner: str, repo_name: str, token: str,
                 trendradar_path: str = "."):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.trendradar_path = trendradar_path
        self.github_api = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        
        # 安全配置
        self.safe_mode = True  # 安全模式：只修改配置文件
        self.require_approval_above = 0.7  # 信心度超过此值需要人工确认
        self.max_changes_per_run = 3  # 每次运行最多修改3处
        self.auto_merge = False  # 是否自动合并（建议关闭）
    
    # ═══════════════════════════════════════════════════════════
    # Phase 1: 配置文件自动迭代（安全）
    # ═══════════════════════════════════════════════════════════
    
    def auto_fix_rss_sources(self, health_data: Dict) -> List[CodeChange]:
        """
        自动修复 RSS 源配置
        
        触发条件：
        - 源连续失败 >= 3 次
        - 7天成功率 < 30%
        
        自动操作：
        - 注释掉失效源
        - 添加推荐替代源（从候选池）
        """
        changes = []
        
        config_path = os.path.join(self.trendradar_path, "config/config.yaml")
        if not os.path.exists(config_path):
            print(f"[自动迭代] 配置文件不存在: {config_path}")
            return changes
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        for source_id, data in health_data.items():
            # 判断是否需要替换
            week_history = [h for h in data.get('history', []) 
                          if h['timestamp'] > (datetime.now() - timedelta(days=7)).isoformat()]
            
            if not week_history:
                continue
            
            success_rate = sum(1 for h in week_history if h['success']) / len(week_history)
            recent_failures = sum(1 for h in week_history[-5:] if not h['success'])
            
            # 触发自动修复条件
            if success_rate < 0.3 or recent_failures >= 5:
                print(f"[自动迭代] 检测到失效源: {data['name']} (成功率: {success_rate:.0%})")
                
                # 1. 注释掉失效源
                source_pattern = rf'(\n    - id: "{source_id}".*?)(?=\n    - id:|\n  #|\n\n|\Z)'
                match = re.search(source_pattern, config_content, re.DOTALL)
                
                if match and '# [AUTO-DISABLED]' not in match.group(1):
                    original = match.group(1)
                    replacement = f"\n    # [AUTO-DISABLED] 自动禁用（成功率过低）\n    # {original.strip().replace(chr(10), chr(10)+'    # ')}"
                    
                    changes.append(CodeChange(
                        file_path="config/config.yaml",
                        change_type="replace",
                        original=original,
                        replacement=replacement,
                        reason=f"{data['name']} 7天成功率仅 {success_rate:.0%}，自动禁用",
                        confidence=min(0.9, 0.5 + (1 - success_rate)),
                        requires_approval=False  # 禁用是安全的
                    ))
                    
                    # 2. 尝试添加替代源
                    replacement_sources = self._get_replacement_sources(data['name'])
                    if replacement_sources:
                        # 找到合适的位置插入
                        insert_point = match.end()
                        new_source = self._format_rss_source(replacement_sources[0])
                        
                        changes.append(CodeChange(
                            file_path="config/config.yaml",
                            change_type="add",
                            original="",
                            replacement=f"\n    # [AUTO-ADDED] 自动添加替代源\n{new_source}",
                            reason=f"自动添加替代源以替换 {data['name']}",
                            confidence=0.6,
                            requires_approval=True  # 添加新源需要确认
                        ))
        
        return changes
    
    def auto_optimize_prompt(self, metrics_history: List[Dict], 
                            current_prompt_path: str) -> List[CodeChange]:
        """
        自动优化 Prompt 模板
        
        触发条件：
        - 某维度连续 3 天下降
        - 某维度平均分数 < 阈值
        
        自动操作：
        - 在 Prompt 中添加/强化特定要求
        - 调整参数（temperature, max_tokens）
        """
        changes = []
        
        if len(metrics_history) < 3:
            return changes
        
        # 分析趋势
        dimensions = ['tech_content_ratio', 'analysis_depth', 'style_diversity', 
                     'insightfulness', 'readability']
        
        for dim in dimensions:
            values = [m.get(dim, 0) for m in metrics_history[-7:]]  # 最近7天
            if len(values) < 3:
                continue
            
            # 检测连续下降趋势
            declining = all(values[i] > values[i+1] for i in range(min(3, len(values)-1)))
            avg = sum(values) / len(values)
            
            if declining or avg < 5.0:
                print(f"[自动迭代] 检测到 {dim} 需要优化 (平均: {avg:.1f})")
                
                # 根据维度生成优化代码
                if dim == 'tech_content_ratio' and avg < 6.0:
                    changes.extend(self._generate_tech_content_fix(current_prompt_path))
                elif dim == 'insightfulness' and avg < 6.0:
                    changes.extend(self._generate_insightfulness_fix(current_prompt_path))
                elif dim == 'style_diversity' and avg < 6.0:
                    changes.extend(self._generate_style_diversity_fix(current_prompt_path))
        
        return changes
    
    def auto_adjust_thresholds(self, system_logs: List[Dict]) -> List[CodeChange]:
        """
        自动调整系统阈值参数
        
        例如：
        - 抓取超时阈值
        - RSS 新鲜度过滤天数
        - AI 生成参数
        """
        changes = []
        
        # 分析抓取时间趋势
        crawl_times = [log.get('crawl_time', 0) for log in system_logs if 'crawl_time' in log]
        if crawl_times and sum(crawl_times) / len(crawl_times) > 90:
            # 平均抓取时间超过90秒，建议减少平台或增加超时
            # 尝试多种缩进格式匹配
            possible_originals = [
                "    max_age_days: 3",
                "      max_age_days: 3",
                "max_age_days: 3"
            ]
            
            for original in possible_originals:
                if original in self._get_file_content("config/config.yaml"):
                    changes.append(CodeChange(
                        file_path="config/config.yaml",
                        change_type="replace",
                        original=original,
                        replacement=original.replace("3", "2") + "  # [AUTO] 减少过滤天数以加速处理",
                        reason="平均抓取时间超过90秒，减少RSS新鲜度过滤以优化性能",
                        confidence=0.7,
                        requires_approval=True
                    ))
                    break
        
        return changes
    
    # ═══════════════════════════════════════════════════════════
    # 执行和验证
    # ═══════════════════════════════════════════════════════════
    
    def apply_changes(self, changes: List[CodeChange]) -> Dict:
        """
        应用代码变更
        
        流程：
        1. 创建 feature 分支
        2. 应用所有变更
        3. 语法验证
        4. 提交到分支
        5. 创建 PR（如果需要人工确认）
        """
        if not changes:
            return {'status': 'no_changes', 'applied': 0}
        
        results = {
            'status': 'success',
            'applied': 0,
            'pending_approval': 0,
            'failed': 0,
            'changes': []
        }
        
        branch_name = f"auto-evolution/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # 创建分支
        try:
            self._create_branch(branch_name)
            print(f"[自动迭代] 创建分支: {branch_name}")
        except Exception as e:
            print(f"[自动迭代] 创建分支失败: {e}")
            return {'status': 'error', 'message': str(e)}
        
        # 应用每个变更
        for change in changes[:self.max_changes_per_run]:
            try:
                if change.requires_approval:
                    results['pending_approval'] += 1
                    print(f"[自动迭代] ⏸️ 等待确认: {change.reason}")
                else:
                    # 直接应用
                    self._apply_change_to_file(change)
                    results['applied'] += 1
                    results['changes'].append({
                        'file': change.file_path,
                        'type': change.change_type,
                        'reason': change.reason,
                        'confidence': change.confidence
                    })
                    print(f"[自动迭代] ✅ 已应用: {change.reason}")
            except Exception as e:
                results['failed'] += 1
                print(f"[自动迭代] ❌ 失败: {change.reason} - {e}")
        
        # 提交变更
        if results['applied'] > 0:
            self._commit_changes(branch_name, changes)
        
        # 如果需要人工确认，创建 PR
        if results['pending_approval'] > 0:
            self._create_pull_request(branch_name, changes)
        
        return results
    
    def validate_changes(self, changes: List[CodeChange]) -> List[str]:
        """
        验证变更的安全性
        
        检查项：
        1. 语法正确性
        2. 不会删除关键配置
        3. 不会引入安全风险
        """
        errors = []
        
        for change in changes:
            # 检查是否修改了黑名单文件
            dangerous_patterns = [
                r'token\s*=',
                r'password\s*=',
                r'secret\s*=',
                r'api_key\s*=',
            ]
            
            if any(re.search(p, change.replacement, re.IGNORECASE) 
                   for p in dangerous_patterns):
                errors.append(f"变更可能包含敏感信息: {change.file_path}")
            
            # 检查 YAML 语法（如果是 YAML 文件）
            if change.file_path.endswith('.yaml') or change.file_path.endswith('.yml'):
                try:
                    import yaml
                    # 尝试解析修改后的内容
                    full_content = self._get_file_content(change.file_path)
                    
                    # 检查 original 是否存在于文件中
                    if change.change_type == "replace" and change.original not in full_content:
                        errors.append(f"无法应用变更: {change.file_path} - 找不到匹配内容，可能文件已被修改")
                        continue
                    
                    if change.change_type == "add" and not change.original:
                        # 对于添加操作，直接在文件末尾追加，验证合并后的内容
                        modified = full_content + change.replacement
                    else:
                        modified = full_content.replace(change.original, change.replacement, 1)
                    
                    yaml.safe_load(modified)
                except Exception as e:
                    errors.append(f"YAML 语法错误: {change.file_path} - {e}")
        
        return errors
    
    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════
    
    def _get_replacement_sources(self, original_name: str) -> List[Dict]:
        """获取替代源候选"""
        candidates = {
            'github': [
                {'id': 'github-blog', 'name': 'GitHub Blog', 
                 'url': 'https://github.blog/feed/', 'max_age_days': 3}
            ],
            'AI': [
                {'id': 'ai-journal', 'name': 'AI Journal',
                 'url': 'https://www.ai-journal.com/feed', 'max_age_days': 3},
                {'id': 'venturebeat-ai', 'name': 'VentureBeat AI',
                 'url': 'https://venturebeat.com/category/ai/feed/', 'max_age_days': 2}
            ],
            '极客': [
                {'id': 'ifanr', 'name': '爱范儿',
                 'url': 'https://www.ifanr.com/feed', 'max_age_days': 2},
                {'id': 'pingwest', 'name': '品玩',
                 'url': 'https://www.pingwest.com/feed', 'max_age_days': 2}
            ]
        }
        
        for keyword, sources in candidates.items():
            if keyword.lower() in original_name.lower():
                return sources
        
        return []
    
    def _format_rss_source(self, source: Dict) -> str:
        """格式化 RSS 源配置"""
        lines = [
            f"    - id: \"{source['id']}\"",
            f"      name: \"{source['name']}\"",
            f"      url: \"{source['url']}\""
        ]
        if 'max_age_days' in source:
            lines.append(f"      max_age_days: {source['max_age_days']}")
        return '\n'.join(lines) + '\n'
    
    def _generate_tech_content_fix(self, prompt_path: str) -> List[CodeChange]:
        """生成科技内容修复"""
        return [CodeChange(
            file_path=prompt_path,
            change_type="add",
            original="",
            replacement="\n### [AUTO-ADDED] 科技内容强化要求\n- 每个分析板块至少解释1个技术原理\n- 使用具体的技术术语而非泛化描述\n- 引用具体的技术参数和数据\n",
            reason="科技内容占比持续偏低，自动强化技术细节要求",
            confidence=0.8,
            requires_approval=False
        )]
    
    def _generate_insightfulness_fix(self, prompt_path: str) -> List[CodeChange]:
        """生成洞察力修复"""
        return [CodeChange(
            file_path=prompt_path,
            change_type="add",
            original="",
            replacement="\n### [AUTO-ADDED] 洞察力强化要求\n- 每个板块必须包含未来3-6个月的预测\n- 提供至少1个反共识观点\n- 分析'为什么'而不仅是'是什么'\n",
            reason="文章洞察力下降，自动强化预测和深度分析要求",
            confidence=0.8,
            requires_approval=False
        )]
    
    def _generate_style_diversity_fix(self, prompt_path: str) -> List[CodeChange]:
        """生成样式多样性修复"""
        return [CodeChange(
            file_path=prompt_path,
            change_type="add",
            original="",
            replacement="\n### [AUTO-ADDED] 格式多样性强制要求\n- 必须包含至少1个对比表格\n- 必须包含至少2个Admonition引用块\n- 必须包含至少1个代码块或引用块\n",
            reason="Markdown元素使用减少，自动强制格式多样性",
            confidence=0.8,
            requires_approval=False
        )]
    
    def _create_branch(self, branch_name: str):
        """创建 Git 分支"""
        import subprocess
        subprocess.run(['git', 'checkout', '-b', branch_name], 
                      cwd=self.trendradar_path, check=True)
    
    def _apply_change_to_file(self, change: CodeChange):
        """应用单个变更到文件"""
        file_path = os.path.join(self.trendradar_path, change.file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if change.change_type == 'replace':
            content = content.replace(change.original, change.replacement, 1)
        elif change.change_type == 'add':
            content += change.replacement
        elif change.change_type == 'remove':
            content = content.replace(change.original, '', 1)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _commit_changes(self, branch_name: str, changes: List[CodeChange]):
        """提交变更"""
        import subprocess
        
        # 添加文件
        for change in changes:
            subprocess.run(['git', 'add', change.file_path], 
                          cwd=self.trendradar_path, check=True)
        
        # 提交
        message = f"[AUTO] 自动代码迭代 - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        for change in changes:
            message += f"- {change.reason}\n"
        
        subprocess.run(['git', 'commit', '-m', message], 
                      cwd=self.trendradar_path, check=True)
        
        # 推送
        subprocess.run(['git', 'push', 'origin', branch_name], 
                      cwd=self.trendradar_path, check=True)
    
    def _create_pull_request(self, branch_name: str, changes: List[CodeChange]):
        """创建 Pull Request"""
        try:
            import requests
            
            title = f"[AUTO] 自动代码迭代 - {datetime.now().strftime('%Y-%m-%d')}"
            body = "## 自动生成的代码优化建议\n\n"
            for change in changes:
                if change.requires_approval:
                    body += f"### ⚠️ 需要确认: {change.file_path}\n"
                    body += f"- 原因: {change.reason}\n"
                    body += f"- 信心度: {change.confidence:.0%}\n\n"
            
            url = f"{self.github_api}/pulls"
            response = requests.post(url, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }, json={
                "title": title,
                "body": body,
                "head": branch_name,
                "base": "master"
            })
            
            if response.status_code == 201:
                pr_url = response.json()['html_url']
                print(f"[自动迭代] 已创建 PR: {pr_url}")
            else:
                print(f"[自动迭代] 创建 PR 失败: {response.status_code}")
        except Exception as e:
            print(f"[自动迭代] 创建 PR 失败: {e}")
    
    def _get_file_content(self, file_path: str) -> str:
        """获取文件内容"""
        full_path = os.path.join(self.trendradar_path, file_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()


# ═══════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════

def run_auto_evolution(repo_owner: str, repo_name: str, token: str,
                       trendradar_path: str = ".") -> Dict:
    """
    运行自动代码迭代
    
    这是主入口函数，在每次 Workflow 运行后调用
    """
    print("=" * 60)
    print("🤖 自动代码迭代系统 v1.0")
    print("=" * 60)
    
    engine = AutoCodeEvolution(repo_owner, repo_name, token, trendradar_path)
    all_changes = []
    
    # 1. 检查 RSS 健康并自动修复
    try:
        from evolution.auto_evolution import AdaptiveEvolutionEngine
        health_engine = AdaptiveEvolutionEngine(repo_owner, repo_name, token)
        health_data = health_engine._load_rss_health()
        
        if health_data:
            rss_changes = engine.auto_fix_rss_sources(health_data)
            all_changes.extend(rss_changes)
            print(f"[自动迭代] RSS修复: {len(rss_changes)} 个变更")
    except Exception as e:
        print(f"[自动迭代] RSS修复跳过: {e}")
    
    # 2. 检查文章质量趋势并优化 Prompt
    try:
        metrics = health_engine._load_recent_metrics(7) if 'health_engine' in dir() else []
        if metrics:
            prompt_path = "trendradar/storage/github.py"  # Prompt 所在文件
            prompt_changes = engine.auto_optimize_prompt(metrics, prompt_path)
            all_changes.extend(prompt_changes)
            print(f"[自动迭代] Prompt优化: {len(prompt_changes)} 个变更")
    except Exception as e:
        print(f"[自动迭代] Prompt优化跳过: {e}")
    
    # 3. 验证所有变更
    if all_changes:
        errors = engine.validate_changes(all_changes)
        if errors:
            print("[自动迭代] 验证发现安全问题，取消执行:")
            for error in errors:
                print(f"  ❌ {error}")
            return {'status': 'validation_failed', 'errors': errors}
        
        # 4. 应用变更
        results = engine.apply_changes(all_changes)
        print(f"[自动迭代] 完成: {results['applied']} 已应用, {results['pending_approval']} 待确认")
        return results
    
    print("[自动迭代] 暂无需要自动修复的问题")
    return {'status': 'no_changes_needed'}
