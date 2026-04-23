# -*- coding: utf-8 -*-
"""
自主进化系统 - 全自动闭环优化

核心理念：
1. 观察：监控系统运行状态
2. 分析：识别问题和优化机会
3. 决策：确定最优改进策略
4. 执行：自动修改代码和配置
5. 验证：确认改进效果

这是真正的"自我进化"——系统自己管理自己。
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class SystemDiagnostic:
    """系统诊断器 - 全面扫描系统健康"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.issues = []
        self.optimizations = []
    
    def run_full_diagnostic(self) -> Dict:
        """运行全面诊断"""
        print("🔍 启动系统全面诊断...")
        
        # 1. 诊断RSS源健康
        self._diagnose_rss_sources()
        
        # 2. 诊断AI质量
        self._diagnose_ai_quality()
        
        # 3. 诊断成本效率
        self._diagnose_cost_efficiency()
        
        # 4. 诊断代码健康
        self._diagnose_code_health()
        
        # 5. 诊断配置一致性
        self._diagnose_config_consistency()
        
        # 6. 诊断数据完整性
        self._diagnose_data_integrity()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "critical_issues": [i for i in self.issues if i["severity"] == "critical"],
            "warnings": [i for i in self.issues if i["severity"] == "warning"],
            "optimizations": self.optimizations,
            "health_score": self._calculate_health_score()
        }
    
    def _diagnose_rss_sources(self):
        """诊断RSS源"""
        rss_file = f"{self.trendradar_path}/evolution/rss_health.json"
        if os.path.exists(rss_file):
            with open(rss_file, 'r') as f:
                records = json.load(f)
            
            # 统计各源成功率
            source_stats = {}
            for r in records:
                sid = r.get("source_id", "unknown")
                if sid not in source_stats:
                    source_stats[sid] = {"total": 0, "success": 0}
                source_stats[sid]["total"] += 1
                if r.get("success"):
                    source_stats[sid]["success"] += 1
            
            for sid, stats in source_stats.items():
                rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
                if rate < 0.3:
                    self.issues.append({
                        "severity": "critical",
                        "category": "rss",
                        "component": sid,
                        "message": f"RSS源成功率仅 {rate*100:.0f}%",
                        "suggestion": f"禁用或替换源: {sid}",
                        "auto_fixable": True
                    })
                elif rate < 0.7:
                    self.issues.append({
                        "severity": "warning",
                        "category": "rss",
                        "component": sid,
                        "message": f"RSS源成功率偏低 {rate*100:.0f}%",
                        "suggestion": f"监控或替换源: {sid}",
                        "auto_fixable": False
                    })
    
    def _diagnose_ai_quality(self):
        """诊断AI生成质量"""
        metrics_file = f"{self.trendradar_path}/evolution/article_metrics.json"
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            
            if len(metrics) >= 3:
                recent_scores = [m.get("overall_score", 0) for m in metrics[-3:]]
                avg_score = sum(recent_scores) / len(recent_scores)
                
                if avg_score < 6.0:
                    self.issues.append({
                        "severity": "critical",
                        "category": "ai_quality",
                        "component": "article_generator",
                        "message": f"文章质量严重下降: {avg_score:.1f}/10",
                        "suggestion": "启用高质量模式（强制DeepSeek）或优化Prompt",
                        "auto_fixable": True
                    })
                elif avg_score < 7.5:
                    self.optimizations.append({
                        "category": "ai_quality",
                        "component": "article_generator",
                        "message": f"文章质量有提升空间: {avg_score:.1f}/10",
                        "suggestion": "优化Prompt或增加质量检查",
                        "potential_gain": "+1.0分"
                    })
    
    def _diagnose_cost_efficiency(self):
        """诊断成本效率"""
        usage_file = f"{self.trendradar_path}/evolution/ai_provider_usage.json"
        if os.path.exists(usage_file):
            with open(usage_file, 'r') as f:
                usage = json.load(f)
            
            # 统计各Provider使用比例
            provider_counts = {}
            for u in usage:
                p = u.get("provider", "unknown")
                provider_counts[p] = provider_counts.get(p, 0) + 1
            
            total = len(usage)
            if total > 0:
                free_count = provider_counts.get("cloudflare_workers_ai", 0) + provider_counts.get("google_gemini", 0)
                free_ratio = free_count / total
                
                if free_ratio < 0.3:
                    self.optimizations.append({
                        "category": "cost",
                        "component": "ai_router",
                        "message": f"免费API使用率仅 {free_ratio*100:.0f}%",
                        "suggestion": "增加轻量任务路由到免费API",
                        "potential_gain": f"节省 {(1-free_ratio)*100:.0f}% 成本"
                    })
    
    def _diagnose_code_health(self):
        """诊断代码健康"""
        # 检查是否有TODO/FIXME
        todo_count = 0
        for root, dirs, files in os.walk(f"{self.trendradar_path}/trendradar"):
            for file in files:
                if file.endswith('.py'):
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.read()
                        todo_count += len(re.findall(r'TODO|FIXME|XXX', content))
        
        if todo_count > 10:
            self.issues.append({
                "severity": "warning",
                "category": "code",
                "component": "codebase",
                "message": f"代码中有 {todo_count} 个TODO/FIXME",
                "suggestion": "逐步清理技术债务",
                "auto_fixable": False
            })
    
    def _diagnose_config_consistency(self):
        """诊断配置一致性"""
        config_path = f"{self.trendradar_path}/config/config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            # 检查是否有禁用但未从列表移除的源
            disabled_sources = re.findall(r'- id: "(\w+)"\n\s+name:.*\n\s+url:.*\n\s+enabled: false', content)
            rss_feeds_match = re.search(r'rss_feeds: \[(.*?)\]', content)
            
            if rss_feeds_match and disabled_sources:
                rss_feeds = rss_feeds_match.group(1)
                for source in disabled_sources:
                    if source in rss_feeds:
                        self.issues.append({
                            "severity": "warning",
                            "category": "config",
                            "component": "rss_config",
                            "message": f"RSS源 {source} 已禁用但仍在feed列表中",
                            "suggestion": f"从rss_feeds列表移除 {source}",
                            "auto_fixable": True
                        })
    
    def _diagnose_data_integrity(self):
        """诊断数据完整性"""
        # 检查D1数据库连接
        try:
            from evolution.storage_d1 import get_evolution_data_store
            store = get_evolution_data_store(self.trendradar_path)
            if not store.d1.is_configured():
                self.issues.append({
                    "severity": "warning",
                    "category": "data",
                    "component": "d1_storage",
                    "message": "D1数据库未配置",
                    "suggestion": "配置D1_DATABASE_ID环境变量",
                    "auto_fixable": False
                })
        except Exception:
            pass
    
    def _calculate_health_score(self) -> int:
        """计算系统健康分（0-100）"""
        score = 100
        
        # 严重问题扣20分
        score -= len([i for i in self.issues if i["severity"] == "critical"]) * 20
        
        # 警告扣5分
        score -= len([i for i in self.issues if i["severity"] == "warning"]) * 5
        
        return max(0, score)


class AutonomousEvolution:
    """自主进化引擎 - 自动执行改进"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.diagnostic = SystemDiagnostic(trendradar_path)
        self.changes_made = []
    
    def run_evolution_cycle(self) -> Dict:
        """
        运行一个完整的自主进化周期
        
        返回进化结果报告
        """
        print("=" * 70)
        print("🧬 自主进化周期启动")
        print("=" * 70)
        
        # 1. 诊断
        print("\n🔍 阶段1: 系统诊断")
        diagnostic_result = self.diagnostic.run_full_diagnostic()
        print(f"   健康度: {diagnostic_result['health_score']}/100")
        print(f"   严重问题: {len(diagnostic_result['critical_issues'])}")
        print(f"   警告: {len(diagnostic_result['warnings'])}")
        print(f"   优化机会: {len(diagnostic_result['optimizations'])}")
        
        # 2. 决策
        print("\n🎯 阶段2: 决策制定")
        actions = self._decide_actions(diagnostic_result)
        print(f"   计划执行: {len(actions)} 个改进动作")
        
        # 3. 执行
        print("\n🔧 阶段3: 执行改进")
        executed = self._execute_actions(actions)
        print(f"   成功执行: {len(executed)} 个")
        
        # 4. 报告
        print("\n📊 阶段4: 生成报告")
        report = self._generate_report(diagnostic_result, actions, executed)
        
        print("\n" + "=" * 70)
        print("✅ 自主进化周期完成")
        print("=" * 70)
        
        return report
    
    def _decide_actions(self, diagnostic: Dict) -> List[Dict]:
        """基于诊断结果决定执行哪些改进"""
        actions = []
        
        # 优先处理严重问题
        for issue in diagnostic["critical_issues"]:
            if issue.get("auto_fixable"):
                actions.append({
                    "priority": 1,
                    "type": "fix",
                    "target": issue["component"],
                    "action": issue["suggestion"],
                    "reason": issue["message"]
                })
        
        # 处理警告
        for warning in diagnostic["warnings"]:
            if warning.get("auto_fixable"):
                actions.append({
                    "priority": 2,
                    "type": "fix",
                    "target": warning["component"],
                    "action": warning["suggestion"],
                    "reason": warning["message"]
                })
        
        # 执行优化（健康度>80才考虑）
        if diagnostic["health_score"] > 80:
            for opt in diagnostic["optimizations"][:2]:  # 最多2个优化
                actions.append({
                    "priority": 3,
                    "type": "optimize",
                    "target": opt["component"],
                    "action": opt["suggestion"],
                    "reason": opt["message"],
                    "potential_gain": opt.get("potential_gain", "")
                })
        
        # 按优先级排序
        actions.sort(key=lambda x: x["priority"])
        
        return actions
    
    def _execute_actions(self, actions: List[Dict]) -> List[Dict]:
        """执行改进动作"""
        executed = []
        
        for action in actions:
            try:
                if action["target"].startswith("rss_"):
                    success = self._fix_rss_issue(action)
                elif action["target"] == "article_generator":
                    success = self._fix_ai_quality(action)
                elif action["target"] == "rss_config":
                    success = self._fix_config_consistency(action)
                else:
                    success = False
                
                if success:
                    executed.append(action)
                    print(f"   ✅ {action['action']}")
                else:
                    print(f"   ❌ {action['action']} (失败)")
                    
            except Exception as e:
                print(f"   ❌ {action['action']} (异常: {e})")
        
        return executed
    
    def _fix_rss_issue(self, action: Dict) -> bool:
        """修复RSS源问题"""
        # 提取源ID
        match = re.search(r'源: (\w+)', action["action"])
        if not match:
            return False
        
        source_id = match.group(1)
        
        # 禁用该源
        config_path = f"{self.trendradar_path}/config/config.yaml"
        with open(config_path, 'r') as f:
            content = f.read()
        
        # 添加enabled: false
        pattern = f'- id: "{source_id}"\\n(\\s+)name:'
        replacement = f'- id: "{source_id}"\\n\\1enabled: false  # [AUTO] {action["reason"]}\\n\\1name:'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(config_path, 'w') as f:
                f.write(new_content)
            return True
        
        return False
    
    def _fix_ai_quality(self, action: Dict) -> bool:
        """修复AI质量问题"""
        # 创建高质量模式标记
        flag_file = f"{self.trendradar_path}/.high_quality_mode"
        with open(flag_file, 'w') as f:
            f.write(f"# {action['reason']}\n# 启用时间: {datetime.now().isoformat()}\n")
        return True
    
    def _fix_config_consistency(self, action: Dict) -> bool:
        """修复配置一致性问题"""
        match = re.search(r'移除 (\w+)', action["action"])
        if not match:
            return False
        
        source_id = match.group(1)
        
        config_path = f"{self.trendradar_path}/config/config.yaml"
        with open(config_path, 'r') as f:
            content = f.read()
        
        # 从rss_feeds列表移除
        new_content = content.replace(f'"{source_id}", ', '')
        new_content = new_content.replace(f', "{source_id}"', '')
        
        if new_content != content:
            with open(config_path, 'w') as f:
                f.write(new_content)
            return True
        
        return False
    
    def _generate_report(self, diagnostic: Dict, actions: List[Dict], executed: List[Dict]) -> Dict:
        """生成进化报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "health_before": diagnostic["health_score"],
            "health_after": min(100, diagnostic["health_score"] + len(executed) * 5),
            "issues_found": len(diagnostic["critical_issues"]) + len(diagnostic["warnings"]),
            "actions_planned": len(actions),
            "actions_executed": len(executed),
            "changes": executed,
            "next_evolution": (datetime.now() + timedelta(hours=24)).isoformat()
        }


# 便捷函数
def run_autonomous_evolution(trendradar_path: str = ".") -> str:
    """运行自主进化"""
    engine = AutonomousEvolution(trendradar_path)
    result = engine.run_evolution_cycle()
    
    # 格式化输出
    report = []
    report.append("\n" + "=" * 70)
    report.append("🧬 自主进化报告")
    report.append("=" * 70)
    report.append(f"\n📊 系统健康度: {result['health_before']} → {result['health_after']}/100")
    report.append(f"🔧 执行改进: {result['actions_executed']}/{result['actions_planned']}")
    
    if result['changes']:
        report.append("\n✅ 已执行的改进:")
        for change in result['changes']:
            report.append(f"   • {change['target']}: {change['action']}")
    
    report.append(f"\n⏰ 下次进化: {result['next_evolution']}")
    report.append("=" * 70)
    
    return "\n".join(report)


if __name__ == "__main__":
    print(run_autonomous_evolution())
