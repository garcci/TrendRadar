# -*- coding: utf-8 -*-
"""
全系统进化引擎 - 让整个 TrendRadar 系统自我改进

不仅文章生成会进化，以下组件也会进化：
1. 热点抓取系统 - 优化平台和 RSS 源配置
2. 成本控制系统 - 提升 Token 使用效率
3. 记忆系统 - 优化去重和上下文质量
4. 标签系统 - 提升分类准确性
5. 整体配置 - Workflow 效率优化
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class SystemEvolutionEngine:
    """全系统进化引擎"""
    
    def __init__(self, repo_owner: str, repo_name: str, token: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.evolution_log_dir = "evolution/system_logs"
        
    def analyze_system_performance(self, run_stats: Dict) -> Dict:
        """
        分析系统整体性能，生成优化建议
        
        Args:
            run_stats: 本次运行的统计数据
                {
                    'crawl_time': 抓取耗时,
                    'ai_generation_time': AI生成耗时,
                    'total_time': 总耗时,
                    'tokens_used': Token使用量,
                    'platforms_crawled': 抓取的平台列表,
                    'rss_sources_crawled': 抓取的RSS源列表,
                    'article_generated': 是否生成文章,
                    'cache_hit': 是否命中缓存,
                    'errors': 错误列表
                }
        """
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'good',
            'components': {},
            'bottlenecks': [],
            'optimization_suggestions': []
        }
        
        # 1. 抓取系统分析
        crawl_time = run_stats.get('crawl_time', 0)
        platforms = run_stats.get('platforms_crawled', [])
        rss_sources = run_stats.get('rss_sources_crawled', [])
        
        analysis['components']['crawler'] = {
            'status': 'good' if crawl_time < 60 else 'slow',
            'crawl_time': crawl_time,
            'platform_count': len(platforms),
            'rss_count': len(rss_sources),
            'issues': []
        }
        
        if crawl_time > 60:
            analysis['components']['crawler']['issues'].append(
                f"抓取耗时过长 ({crawl_time}s)，建议减少平台或优化并发"
            )
            analysis['bottlenecks'].append('crawler_speed')
        
        if len(rss_sources) == 0:
            analysis['components']['crawler']['issues'].append(
                "RSS 源未抓取到数据，建议检查 RSS 配置或源可用性"
            )
            analysis['bottlenecks'].append('rss_empty')
        
        # 2. AI 生成系统分析
        ai_time = run_stats.get('ai_generation_time', 0)
        tokens_used = run_stats.get('tokens_used', 0)
        cache_hit = run_stats.get('cache_hit', False)
        
        analysis['components']['ai_generator'] = {
            'status': 'good' if ai_time < 120 else 'slow',
            'generation_time': ai_time,
            'tokens_used': tokens_used,
            'cache_hit': cache_hit,
            'issues': []
        }
        
        if ai_time > 120:
            analysis['components']['ai_generator']['issues'].append(
                f"AI 生成耗时过长 ({ai_time}s)，建议优化 Prompt 或降低 max_tokens"
            )
            analysis['bottlenecks'].append('ai_slow')
        
        if tokens_used > 150000:
            analysis['components']['ai_generator']['issues'].append(
                f"Token 消耗过高 ({tokens_used})，建议优化输入压缩"
            )
            analysis['bottlenecks'].append('token_high')
        
        # 3. 成本分析
        analysis['components']['cost'] = {
            'status': 'good',
            'estimated_cost': tokens_used * 0.002 / 1000,  # DeepSeek 价格
            'issues': []
        }
        
        # 4. 错误分析
        errors = run_stats.get('errors', [])
        if errors:
            analysis['components']['stability'] = {
                'status': 'warning' if len(errors) < 3 else 'critical',
                'error_count': len(errors),
                'errors': errors[:5],
                'issues': []
            }
            for error in errors[:3]:
                analysis['components']['stability']['issues'].append(
                    f"运行错误: {error}"
                )
            analysis['bottlenecks'].append('errors')
        
        # 5. 生成整体优化建议
        if 'crawler_speed' in analysis['bottlenecks']:
            analysis['optimization_suggestions'].append({
                'component': 'crawler',
                'priority': 'medium',
                'action': '减少抓取平台数量或增加并发度',
                'expected_improvement': '减少 20-30% 抓取时间'
            })
        
        if 'rss_empty' in analysis['bottlenecks']:
            analysis['optimization_suggestions'].append({
                'component': 'rss',
                'priority': 'high',
                'action': '检查 RSS 源配置，添加备用源，或调整抓取频率',
                'expected_improvement': '提升科技内容占比'
            })
        
        if 'ai_slow' in analysis['bottlenecks']:
            analysis['optimization_suggestions'].append({
                'component': 'ai',
                'priority': 'medium',
                'action': '缩短 Prompt，减少上下文长度，或使用更快的模型',
                'expected_improvement': '减少 30-50% 生成时间'
            })
        
        if 'token_high' in analysis['bottlenecks']:
            analysis['optimization_suggestions'].append({
                'component': 'cost',
                'priority': 'high',
                'action': '压缩输入数据，减少 max_tokens，或启用更积极的缓存策略',
                'expected_improvement': '降低 20-40% Token 消耗'
            })
        
        if 'errors' in analysis['bottlenecks']:
            analysis['optimization_suggestions'].append({
                'component': 'stability',
                'priority': 'critical',
                'action': '修复运行错误，添加重试机制，或添加降级策略',
                'expected_improvement': '提升系统稳定性'
            })
        
        # 评估整体健康度
        if len(analysis['bottlenecks']) == 0:
            analysis['overall_health'] = 'excellent'
        elif len(analysis['bottlenecks']) <= 2:
            analysis['overall_health'] = 'good'
        else:
            analysis['overall_health'] = 'needs_improvement'
        
        return analysis
    
    def generate_system_evolution_prompt(self, analysis: Dict) -> str:
        """
        基于系统分析生成进化 Prompt
        """
        if not analysis['optimization_suggestions']:
            return ""
        
        prompt_parts = ["\n\n### 🧬 系统进化反馈（基于运行性能分析）"]
        prompt_parts.append(f"系统整体健康度: {analysis['overall_health']}\n")
        
        # 添加各组件状态
        for component, data in analysis['components'].items():
            status_emoji = "✅" if data['status'] == 'good' else "⚠️" if data['status'] == 'warning' else "❌"
            prompt_parts.append(f"{status_emoji} **{component}**: {data['status']}")
            for issue in data.get('issues', [])[:2]:
                prompt_parts.append(f"  - {issue}")
        
        # 添加优化建议
        if analysis['optimization_suggestions']:
            prompt_parts.append("\n**优先优化方向：**")
            for suggestion in sorted(
                analysis['optimization_suggestions'],
                key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x['priority'], 4)
            ):
                priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                    suggestion['priority'], "⚪"
                )
                prompt_parts.append(
                    f"{priority_emoji} [{suggestion['component']}] {suggestion['action']}"
                )
                prompt_parts.append(f"   预期效果: {suggestion['expected_improvement']}")
        
        return "\n".join(prompt_parts)
    
    def save_system_analysis(self, analysis: Dict) -> bool:
        """
        保存系统分析日志
        """
        try:
            import requests
            
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{self.evolution_log_dir}/{date_str}-system-analysis.json"
            
            content = json.dumps(analysis, ensure_ascii=False, indent=2)
            
            # 检查文件是否已存在
            check_url = f"{self.base_url}/contents/{filename}"
            response = requests.get(check_url, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })
            
            if response.status_code == 200:
                existing = response.json()
                sha = existing["sha"]
                update_data = {
                    "message": f"feat: 追加系统分析 - {analysis['overall_health']}",
                    "content": self._encode_content(content),
                    "sha": sha
                }
            else:
                update_data = {
                    "message": f"feat: 添加系统分析 - {analysis['overall_health']}",
                    "content": self._encode_content(content)
                }
            
            response = requests.put(
                f"{self.base_url}/contents/{filename}",
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=update_data
            )
            
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"[系统进化] 保存分析失败: {e}")
            return False
    
    def get_system_evolution_context(self) -> str:
        """
        获取系统进化上下文
        """
        try:
            import requests
            
            logs_url = f"{self.base_url}/contents/{self.evolution_log_dir}"
            response = requests.get(logs_url, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })
            
            if response.status_code != 200:
                return ""
            
            files = response.json()
            if not files:
                return ""
            
            # 获取最新的分析文件
            latest_file = sorted(files, key=lambda x: x["name"], reverse=True)[0]
            content_url = latest_file["download_url"]
            content_response = requests.get(content_url)
            
            if content_response.status_code == 200:
                analysis = json.loads(content_response.text)
                return self.generate_system_evolution_prompt(analysis)
            
            return ""
        except Exception as e:
            print(f"[系统进化] 加载上下文失败: {e}")
            return ""
    
    def _encode_content(self, content: str) -> str:
        """编码内容为 base64"""
        import base64
        return base64.b64encode(content.encode("utf-8")).decode("utf-8")


def evolve_system(run_stats: Dict, repo_owner: str, repo_name: str, token: str) -> str:
    """
    系统进化便捷函数
    
    Args:
        run_stats: 运行统计数据
        repo_owner: 仓库所有者
        repo_name: 仓库名称
        token: GitHub Token
        
    Returns:
        系统进化反馈 Prompt
    """
    engine = SystemEvolutionEngine(repo_owner, repo_name, token)
    
    # 分析系统性能
    analysis = engine.analyze_system_performance(run_stats)
    
    # 保存分析结果
    engine.save_system_analysis(analysis)
    
    # 生成进化反馈
    evolution_prompt = engine.generate_system_evolution_prompt(analysis)
    
    print(f"[系统进化] 分析完成，系统健康度: {analysis['overall_health']}")
    print(f"[系统进化] 发现 {len(analysis['bottlenecks'])} 个瓶颈")
    print(f"[系统进化] 生成 {len(analysis['optimization_suggestions'])} 条优化建议")
    
    return evolution_prompt
