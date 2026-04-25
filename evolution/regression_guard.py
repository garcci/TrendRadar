# -*- coding: utf-8 -*-
"""
退化检测与自动干预系统 — Lv73: 进化安全护栏

核心能力：
1. 文章质量退化检测 — 对比最近N篇文章评分趋势
2. Workflow 稳定性检测 — 监控失败率是否异常上升
3. 成本异常检测 — 检测 token 消耗是否突然暴增
4. 代码功能退化检测 — 验证关键模块是否仍然可导入/可运行
5. 自动干预 — 发现退化时自动回滚 + 暂停进化 + 创建告警

干预策略：
- 轻微退化（1个指标下降<10%）→ 记录警告，继续监控
- 中度退化（1个指标下降≥10% 或 2个指标下降）→ 暂停自动进化，创建 Issue
- 严重退化（Workflow失败率>50% 或 文章质量评分骤降>20%）→ 自动回滚代码 + 暂停进化 + 紧急告警
"""

import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class RegressionGuard:
    """退化检测与干预系统"""
    
    # 退化阈值配置
    THRESHOLDS = {
        'article_score_drop': 0.15,      # 文章评分下降超过15%视为退化
        'workflow_failure_rate': 0.30,    # Workflow失败率超过30%视为退化
        'cost_spike_ratio': 2.0,          # 成本超过历史均值2倍视为异常
        'tech_content_drop': 0.20,        # 科技内容占比下降超过20%视为退化
        'min_samples': 3,                 # 最少需要3个样本才能判断趋势
    }
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.evolution_dir = os.path.join(repo_path, "evolution")
        self.metrics_file = os.path.join(self.evolution_dir, "article_metrics.json")
        self.history_file = os.path.join(self.evolution_dir, "metrics_history.json")
        self.regression_log = os.path.join(self.evolution_dir, "regression_log.json")
        self.pause_flag = os.path.join(self.evolution_dir, ".pause_evolution")
        
        # 确保目录存在
        os.makedirs(self.evolution_dir, exist_ok=True)
    
    def run_full_check(self) -> Dict:
        """
        运行完整的退化检测，返回检测结果和干预建议
        
        Returns:
            {
                'status': 'healthy' | 'warning' | 'critical',
                'regressions': [...],
                'actions_taken': [...],
                'recommendation': '...'
            }
        """
        regressions = []
        actions_taken = []
        
        # 1. 检测文章质量退化
        article_regression = self._check_article_quality_regression()
        if article_regression['is_regression']:
            regressions.append(article_regression)
        
        # 2. 检测 Workflow 稳定性退化
        workflow_regression = self._check_workflow_stability()
        if workflow_regression['is_regression']:
            regressions.append(workflow_regression)
        
        # 3. 检测成本异常
        cost_regression = self._check_cost_anomaly()
        if cost_regression['is_regression']:
            regressions.append(cost_regression)
        
        # 4. 检测代码功能退化（关键模块可导入性）
        code_regression = self._check_code_functionality()
        if code_regression['is_regression']:
            regressions.append(code_regression)
        
        # 根据退化程度确定状态
        critical_count = sum(1 for r in regressions if r.get('severity') == 'critical')
        warning_count = sum(1 for r in regressions if r.get('severity') == 'warning')
        
        if critical_count > 0:
            status = 'critical'
        elif warning_count > 0:
            status = 'warning'
        else:
            status = 'healthy'
        
        # 执行干预措施
        if status == 'critical':
            # 严重退化：自动回滚 + 暂停进化
            rollback_result = self._auto_rollback()
            if rollback_result['success']:
                actions_taken.append(f"自动回滚到稳定版本: {rollback_result['commit']}")
            
            pause_result = self._pause_evolution(reason="严重退化 detected")
            actions_taken.append(f"暂停自动进化: {pause_result}")
            
            self._create_alert_issue(regressions, actions_taken)
            recommendation = "系统已自动回滚并暂停进化，请人工检查最近的代码变更"
            
        elif status == 'warning':
            # 中度退化：暂停进化，不回滚
            pause_result = self._pause_evolution(reason="中度退化 detected")
            actions_taken.append(f"暂停自动进化: {pause_result}")
            
            self._create_alert_issue(regressions, actions_taken)
            recommendation = "系统已暂停自动进化，请检查指标下降趋势"
            
        else:
            recommendation = "系统健康，无需干预"
            # 如果之前暂停了，且现在健康，可以考虑恢复（暂不自动恢复，需人工确认）
        
        # 记录检测结果
        self._log_check_result(status, regressions, actions_taken)
        
        return {
            'status': status,
            'regressions': regressions,
            'actions_taken': actions_taken,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        }
    
    def _check_article_quality_regression(self) -> Dict:
        """检测文章质量是否退化"""
        metrics = self._load_article_metrics()
        
        if len(metrics) < self.THRESHOLDS['min_samples']:
            return {'is_regression': False, 'reason': '数据不足'}
        
        # 按时间排序（最新的在后面）
        metrics = sorted(metrics, key=lambda x: x.get('date', ''))
        
        # 分段比较：前一半 vs 后一半
        mid = len(metrics) // 2
        old_scores = [m.get('overall_score', 0) for m in metrics[:mid]]
        new_scores = [m.get('overall_score', 0) for m in metrics[mid:]]
        
        old_avg = sum(old_scores) / len(old_scores) if old_scores else 0
        new_avg = sum(new_scores) / len(new_scores) if new_scores else 0
        
        drop_ratio = (old_avg - new_avg) / old_avg if old_avg > 0 else 0
        
        # 检查科技内容占比
        old_tech = [m.get('tech_content_ratio', 0) for m in metrics[:mid]]
        new_tech = [m.get('tech_content_ratio', 0) for m in metrics[mid:]]
        old_tech_avg = sum(old_tech) / len(old_tech) if old_tech else 0
        new_tech_avg = sum(new_tech) / len(new_tech) if new_tech else 0
        tech_drop = (old_tech_avg - new_tech_avg) / old_tech_avg if old_tech_avg > 0 else 0
        
        # 检查洞察力
        old_insight = [m.get('insightfulness', 0) for m in metrics[:mid]]
        new_insight = [m.get('insightfulness', 0) for m in metrics[mid:]]
        old_insight_avg = sum(old_insight) / len(old_insight) if old_insight else 0
        new_insight_avg = sum(new_insight) / len(new_insight) if new_insight else 0
        insight_drop = (old_insight_avg - new_insight_avg) / old_insight_avg if old_insight_avg > 0 else 0
        
        regressions_found = []
        if drop_ratio > self.THRESHOLDS['article_score_drop']:
            regressions_found.append(f"overall_score 下降 {drop_ratio*100:.1f}%")
        if tech_drop > self.THRESHOLDS['tech_content_drop']:
            regressions_found.append(f"tech_content_ratio 下降 {tech_drop*100:.1f}%")
        if insight_drop > self.THRESHOLDS['article_score_drop']:
            regressions_found.append(f"insightfulness 下降 {insight_drop*100:.1f}%")
        
        if regressions_found:
            severity = 'critical' if drop_ratio > 0.25 or tech_drop > 0.30 else 'warning'
            return {
                'is_regression': True,
                'type': 'article_quality',
                'severity': severity,
                'details': {
                    'score_drop_ratio': round(drop_ratio, 3),
                    'tech_drop_ratio': round(tech_drop, 3),
                    'insight_drop_ratio': round(insight_drop, 3),
                    'old_avg_score': round(old_avg, 2),
                    'new_avg_score': round(new_avg, 2),
                    'samples': len(metrics)
                },
                'message': f"文章质量退化: {', '.join(regressions_found)}"
            }
        
        return {
            'is_regression': False,
            'type': 'article_quality',
            'details': {
                'score_trend': 'stable' if abs(drop_ratio) < 0.05 else ('improving' if drop_ratio < 0 else 'slight_decline'),
                'old_avg': round(old_avg, 2),
                'new_avg': round(new_avg, 2)
            }
        }
    
    def _check_workflow_stability(self) -> Dict:
        """检测 Workflow 失败率是否异常"""
        try:
            # 通过 GitHub CLI 获取最近10次运行记录
            result = subprocess.run(
                ['gh', 'run', 'list', '--limit', '20', '--json', 'status,conclusion,createdAt'],
                capture_output=True, text=True, cwd=self.repo_path, timeout=30
            )
            
            if result.returncode != 0:
                return {'is_regression': False, 'reason': f'无法获取 Workflow 数据: {result.stderr}'}
            
            runs = json.loads(result.stdout) if result.stdout else []
            
            if len(runs) < 5:
                return {'is_regression': False, 'reason': 'Workflow 运行记录不足'}
            
            # 计算失败率
            failures = sum(1 for r in runs if r.get('conclusion') == 'failure')
            failure_rate = failures / len(runs)
            
            # 检查最近5次是否有连续失败
            recent_runs = runs[:5]
            recent_failures = sum(1 for r in recent_runs if r.get('conclusion') == 'failure')
            
            if failure_rate > self.THRESHOLDS['workflow_failure_rate']:
                return {
                    'is_regression': True,
                    'type': 'workflow_stability',
                    'severity': 'critical' if recent_failures >= 3 else 'warning',
                    'details': {
                        'failure_rate': round(failure_rate, 2),
                        'failures': failures,
                        'total_runs': len(runs),
                        'recent_failures': recent_failures
                    },
                    'message': f"Workflow 失败率 {failure_rate*100:.0f}% ({failures}/{len(runs)})，超过阈值 {self.THRESHOLDS['workflow_failure_rate']*100:.0f}%"
                }
            
            return {
                'is_regression': False,
                'type': 'workflow_stability',
                'details': {
                    'failure_rate': round(failure_rate, 2),
                    'recent_failures': recent_failures
                }
            }
            
        except Exception as e:
            return {'is_regression': False, 'reason': f'检测异常: {e}'}
    
    def _check_cost_anomaly(self) -> Dict:
        """检测成本是否异常增长"""
        try:
            cost_file = os.path.join(self.evolution_dir, "data_pipeline", "cost.jsonl")
            if not os.path.exists(cost_file):
                return {'is_regression': False, 'reason': '无成本数据'}
            
            costs = []
            with open(cost_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        costs.append(json.loads(line))
            
            if len(costs) < 5:
                return {'is_regression': False, 'reason': '成本数据不足'}
            
            # 按日期排序
            costs = sorted(costs, key=lambda x: x.get('date', ''))
            
            # 比较最近3天 vs 前3天
            recent = costs[-3:]
            previous = costs[-6:-3] if len(costs) >= 6 else costs[:3]
            
            recent_avg = sum(c.get('tokens', 0) for c in recent) / len(recent)
            previous_avg = sum(c.get('tokens', 0) for c in previous) / len(previous)
            
            spike_ratio = recent_avg / previous_avg if previous_avg > 0 else 1.0
            
            if spike_ratio > self.THRESHOLDS['cost_spike_ratio']:
                return {
                    'is_regression': True,
                    'type': 'cost_anomaly',
                    'severity': 'warning',
                    'details': {
                        'spike_ratio': round(spike_ratio, 2),
                        'recent_avg': round(recent_avg, 0),
                        'previous_avg': round(previous_avg, 0)
                    },
                    'message': f"Token 消耗暴增 {spike_ratio:.1f} 倍（{recent_avg:.0f} vs {previous_avg:.0f}），可能存在无限循环或冗余调用"
                }
            
            return {
                'is_regression': False,
                'type': 'cost_anomaly',
                'details': {'spike_ratio': round(spike_ratio, 2)}
            }
            
        except Exception as e:
            return {'is_regression': False, 'reason': f'检测异常: {e}'}
    
    def _check_code_functionality(self) -> Dict:
        """检测关键代码模块是否仍然可导入/可运行"""
        critical_modules = [
            'trendradar.storage.github',
            'trendradar.ai.smart_client',
            'evolution.auto_evolution',
            'evolution.exception_monitor',
        ]
        
        failed_modules = []
        for module in critical_modules:
            try:
                # 使用 Python -c 方式导入，避免污染当前进程
                result = subprocess.run(
                    [os.sys.executable, '-c', f'import {module}'],
                    capture_output=True, text=True, cwd=self.repo_path, timeout=10
                )
                if result.returncode != 0:
                    failed_modules.append({
                        'module': module,
                        'error': result.stderr[:200]
                    })
            except Exception as e:
                failed_modules.append({
                    'module': module,
                    'error': str(e)[:200]
                })
        
        if failed_modules:
            return {
                'is_regression': True,
                'type': 'code_functionality',
                'severity': 'critical',
                'details': {'failed_modules': failed_modules},
                'message': f"{len(failed_modules)} 个关键模块无法导入: {', '.join(m['module'] for m in failed_modules)}"
            }
        
        return {
            'is_regression': False,
            'type': 'code_functionality',
            'details': {'all_modules_ok': True}
        }
    
    def _auto_rollback(self) -> Dict:
        """自动回滚到上一个稳定版本"""
        try:
            # 找到最近一次的非自动迭代提交
            result = subprocess.run(
                ['git', 'log', '--oneline', '-20'],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10
            )
            
            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}
            
            commits = result.stdout.strip().split('\n')
            
            # 找到最近的自动迭代提交
            auto_commit = None
            for commit in commits:
                if '[AUTO]' in commit or '自动代码迭代' in commit or '自动迭代' in commit:
                    auto_commit = commit.split()[0]
                    break
            
            if not auto_commit:
                return {'success': False, 'error': '未找到自动迭代提交，无法回滚'}
            
            # 执行 revert
            revert_result = subprocess.run(
                ['git', 'revert', '--no-edit', auto_commit],
                capture_output=True, text=True, cwd=self.repo_path, timeout=30
            )
            
            if revert_result.returncode != 0:
                return {'success': False, 'error': revert_result.stderr}
            
            # 推送回滚
            push_result = subprocess.run(
                ['git', 'push', 'origin', 'master'],
                capture_output=True, text=True, cwd=self.repo_path, timeout=30
            )
            
            return {
                'success': push_result.returncode == 0,
                'commit': auto_commit,
                'push_output': push_result.stdout if push_result.returncode == 0 else push_result.stderr
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _pause_evolution(self, reason: str) -> str:
        """暂停自动进化"""
        try:
            with open(self.pause_flag, 'w') as f:
                f.write(f"PAUSED_AT={datetime.now().isoformat()}\n")
                f.write(f"REASON={reason}\n")
            return f"已创建暂停标记: {self.pause_flag}"
        except Exception as e:
            return f"创建暂停标记失败: {e}"
    
    def _create_alert_issue(self, regressions: List[Dict], actions: List[str]):
        """创建 GitHub Issue 记录退化事件"""
        try:
            token = os.environ.get('GH_MEMORY_TOKEN') or os.environ.get('GITHUB_TOKEN')
            if not token:
                return
            
            owner = os.environ.get('ASTRO_REPO_OWNER', 'garcci')
            repo = os.environ.get('ASTRO_REPO_NAME', 'Astro')
            
            # 构建 Issue 内容
            severity = max((r.get('severity', 'warning') for r in regressions), key=lambda x: {'warning': 1, 'critical': 2}.get(x, 0))
            title = f"🚨 [退化告警] 系统进化出现{severity}级别退化"
            
            body = f"""## 退化检测报告

**检测时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**严重程度**: {severity.upper()}

### 检测到的退化项
"""
            for r in regressions:
                if r.get('is_regression'):
                    body += f"\n**{r['type']}** ({r.get('severity', 'unknown')})\n"
                    body += f"- {r.get('message', '无详细信息')}\n"
                    if 'details' in r:
                        body += f"- 详情: `{json.dumps(r['details'], ensure_ascii=False, indent=2)}`\n"
            
            body += "\n### 已执行的干预措施\n"
            for action in actions:
                body += f"- {action}\n"
            
            body += """
### 建议操作
1. 检查最近的自动代码迭代变更
2. 确认回滚后的代码是否正常工作
3. 分析问题根因后再恢复自动进化
4. 删除 `evolution/.pause_evolution` 文件可恢复自动进化

---
*此 Issue 由 RegressionGuard 自动生成*
"""
            
            import requests
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            response = requests.post(url, headers=headers, json={
                "title": title,
                "body": body,
                "labels": ["regression", "auto-alert", "进化系统"]
            }, timeout=30)
            
            if response.status_code == 201:
                return f"已创建告警 Issue: {response.json().get('html_url')}"
            else:
                return f"创建 Issue 失败: {response.status_code} {response.text[:200]}"
                
        except Exception as e:
            return f"创建告警 Issue 异常: {e}"
    
    def _load_article_metrics(self) -> List[Dict]:
        """加载文章质量指标"""
        metrics = []
        
        # 从 article_metrics.json 加载
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        metrics.extend(data)
            except Exception:
                pass
        
        # 从 metrics_history.json 加载（如果在 Astro 仓库）
        astro_metrics = os.path.join(self.repo_path, "..", "Astro", "evolution", "metrics_history.json")
        if os.path.exists(astro_metrics):
            try:
                with open(astro_metrics, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        metrics.extend(data)
            except Exception:
                pass
        
        return metrics
    
    def _log_check_result(self, status: str, regressions: List[Dict], actions: List[str]):
        """记录检测结果到日志文件"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'status': status,
                'regressions': [r for r in regressions if r.get('is_regression')],
                'actions': actions
            }
            
            logs = []
            if os.path.exists(self.regression_log):
                try:
                    with open(self.regression_log, 'r') as f:
                        logs = json.load(f)
                except Exception:
                    logs = []
            
            logs.append(log_entry)
            # 只保留最近50条记录
            logs = logs[-50:]
            
            with open(self.regression_log, 'w') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception:
            pass
    
    def is_evolution_paused(self) -> Tuple[bool, str]:
        """检查进化是否被暂停"""
        if not os.path.exists(self.pause_flag):
            return False, ""
        
        try:
            with open(self.pause_flag, 'r') as f:
                content = f.read()
            reason = ""
            for line in content.split('\n'):
                if line.startswith('REASON='):
                    reason = line.split('=', 1)[1]
            return True, reason
        except Exception:
            return True, "未知原因"
    
    def resume_evolution(self) -> str:
        """恢复自动进化（删除暂停标记）"""
        if os.path.exists(self.pause_flag):
            try:
                os.remove(self.pause_flag)
                return "已恢复自动进化"
            except Exception as e:
                return f"恢复失败: {e}"
        return "自动进化未被暂停"


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description='退化检测与干预系统')
    parser.add_argument('--repo-path', default='.', help='仓库路径')
    parser.add_argument('--check', action='store_true', help='运行完整检测')
    parser.add_argument('--status', action='store_true', help='检查进化暂停状态')
    parser.add_argument('--resume', action='store_true', help='恢复自动进化')
    args = parser.parse_args()
    
    guard = RegressionGuard(repo_path=args.repo_path)
    
    if args.resume:
        print(guard.resume_evolution())
        return
    
    if args.status:
        paused, reason = guard.is_evolution_paused()
        if paused:
            print(f"自动进化已暂停: {reason}")
        else:
            print("自动进化运行中")
        return
    
    if args.check:
        result = guard.run_full_check()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 如果有退化，返回非0退出码
        if result['status'] != 'healthy':
            exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
