# -*- coding: utf-8 -*-
"""
自适应进化系统 v3.0 - 让系统真正自动进化

核心能力：
1. 长期趋势分析 - 分析最近 N 篇文章的评分趋势
2. Prompt 自动优化 - 根据评估结果自动修改 system prompt
3. RSS 健康监控 - 自动检测失效源并标记
4. A/B 测试追踪 - 比较不同策略的效果
5. 配置自动调优 - 根据性能数据调整系统参数

架构原则：
- 所有优化都有数据支撑
- 所有修改都可回滚
- 所有进化都可追溯
"""

import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class ArticleMetrics:
    """文章质量指标"""
    date: str
    overall_score: float
    tech_content_ratio: float
    analysis_depth: float
    style_diversity: float
    insightfulness: float
    readability: float
    word_count: int
    prompt_version: str  # 追踪使用的 Prompt 版本


@dataclass
class PromptVersion:
    """Prompt 版本记录"""
    version: str
    timestamp: str
    changes: List[str]
    metrics_before: Dict
    metrics_after: Dict
    improvement: float


@dataclass
class RSSSourceHealth:
    """RSS 源健康状态"""
    source_id: str
    name: str
    url: str
    success_rate: float  # 最近 7 天成功率
    last_success: str
    last_failure: str
    failure_reason: str
    recommended_action: str


class AdaptiveEvolutionEngine:
    """自适应进化引擎"""
    
    def __init__(self, repo_owner: str, repo_name: str, token: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        
        # 进化数据目录
        self.evolution_dir = "evolution"
        self.metrics_file = f"{self.evolution_dir}/metrics_history.json"
        self.prompt_versions_file = f"{self.evolution_dir}/prompt_versions.json"
        self.rss_health_file = f"{self.evolution_dir}/rss_health.json"
        self.ab_tests_file = f"{self.evolution_dir}/ab_tests.json"
    
    def analyze_long_term_trends(self, days: int = 7) -> Dict:
        """
        分析最近 N 天的文章质量趋势
        
        Returns:
            {
                'trend': 'improving' | 'stable' | 'declining',
                'metrics_trends': {
                    'tech_content_ratio': {'avg': X, 'trend': 'up' | 'down'},
                    ...
                },
                'recommendations': [...]
            }
        """
        metrics = self._load_recent_metrics(days)
        
        if len(metrics) < 3:
            return {
                'trend': 'insufficient_data',
                'message': f'需要至少 3 天数据，当前只有 {len(metrics)} 天',
                'recommendations': []
            }
        
        # 计算各指标的趋势
        trends = {}
        for dimension in ['tech_content_ratio', 'analysis_depth', 'style_diversity', 
                          'insightfulness', 'readability', 'overall_score']:
            values = [m.get(dimension, 0) for m in metrics]
            avg = sum(values) / len(values)
            
            # 线性回归判断趋势
            if len(values) >= 3:
                first_half = sum(values[:len(values)//2]) / (len(values)//2)
                second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
                
                if second_half > first_half * 1.05:
                    trend = 'improving'
                elif second_half < first_half * 0.95:
                    trend = 'declining'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            trends[dimension] = {
                'avg': round(avg, 2),
                'trend': trend,
                'values': values
            }
        
        # 判断整体趋势
        improving_count = sum(1 for t in trends.values() if t['trend'] == 'improving')
        declining_count = sum(1 for t in trends.values() if t['trend'] == 'declining')
        
        if improving_count > declining_count + 1:
            overall_trend = 'improving'
        elif declining_count > improving_count + 1:
            overall_trend = 'declining'
        else:
            overall_trend = 'stable'
        
        # 生成建议
        recommendations = []
        
        if trends.get('tech_content_ratio', {}).get('trend') == 'declining':
            recommendations.append({
                'priority': 'high',
                'component': 'content',
                'issue': '科技内容占比持续下降',
                'action': '增加科技 RSS 源权重，或调整 Prompt 强调科技内容',
                'expected_improvement': 'tech_content_ratio 提升 20%'
            })
        
        if trends.get('insightfulness', {}).get('trend') == 'declining':
            recommendations.append({
                'priority': 'high',
                'component': 'prompt',
                'issue': '文章洞察力持续下降',
                'action': '在 Prompt 中增加预测性分析要求',
                'expected_improvement': 'insightfulness 提升 30%'
            })
        
        if trends.get('style_diversity', {}).get('trend') == 'declining':
            recommendations.append({
                'priority': 'medium',
                'component': 'prompt',
                'issue': 'Markdown 元素使用减少',
                'action': '强制要求使用表格、代码块等多样元素',
                'expected_improvement': 'style_diversity 提升 25%'
            })
        
        if overall_trend == 'improving' and trends['overall_score']['avg'] > 8.0:
            recommendations.append({
                'priority': 'low',
                'component': 'system',
                'issue': '系统运行良好',
                'action': '保持当前策略，继续监控',
                'expected_improvement': '维持高质量输出'
            })
        
        return {
            'trend': overall_trend,
            'days_analyzed': len(metrics),
            'metrics_trends': trends,
            'recommendations': recommendations
        }
    
    def generate_smart_prompt_optimization(self, current_prompt: str, 
                                           metrics_history: List[Dict]) -> Optional[Dict]:
        """
        基于历史数据智能生成 Prompt 优化建议
        
        不同于简单的文本追加，这个系统会：
        1. 识别 Prompt 中已有的优化点
        2. 避免重复添加相同建议
        3. 根据趋势确定优先级
        """
        if len(metrics_history) < 3:
            return None
        
        # 分析最近的趋势
        trends = self.analyze_long_term_trends(days=len(metrics_history))
        
        # 识别当前 Prompt 中已有的优化点
        existing_optimizations = self._extract_existing_optimizations(current_prompt)
        
        optimizations = []
        
        # 检查科技内容
        if (trends['metrics_trends'].get('tech_content_ratio', {}).get('trend') == 'declining' and
            'tech_content_priority' not in existing_optimizations):
            optimizations.append({
                'type': 'add_section',
                'target': 'content_strategy',
                'content': self._get_tech_content_optimization(),
                'reason': '科技内容占比持续下降'
            })
        
        # 检查洞察力
        if (trends['metrics_trends'].get('insightfulness', {}).get('trend') == 'declining' and
            'insightfulness_requirement' not in existing_optimizations):
            optimizations.append({
                'type': 'add_section',
                'target': 'analysis_requirements',
                'content': self._get_insightfulness_optimization(),
                'reason': '文章洞察力持续下降'
            })
        
        # 检查 Markdown 多样性
        if (trends['metrics_trends'].get('style_diversity', {}).get('trend') == 'declining' and
            'markdown_diversity' not in existing_optimizations):
            optimizations.append({
                'type': 'add_section',
                'target': 'formatting_requirements',
                'content': self._get_markdown_diversity_optimization(),
                'reason': 'Markdown 元素使用减少'
            })
        
        if not optimizations:
            return None
        
        return {
            'timestamp': datetime.now().isoformat(),
            'trend_analysis': trends,
            'optimizations': optimizations,
            'estimated_improvement': self._calculate_estimated_improvement(trends, optimizations)
        }
    
    def update_rss_source_health(self, source_id: str, name: str, url: str, 
                                  success: bool, error: str = "") -> RSSSourceHealth:
        """
        更新 RSS 源健康状态
        
        自动检测：
        - 连续失败超过 3 次的源
        - 7 天内成功率低于 50% 的源
        - 返回推荐的行动
        """
        health_data = self._load_rss_health()
        
        # 更新或创建源记录
        if source_id not in health_data:
            health_data[source_id] = {
                'name': name,
                'url': url,
                'history': [],
                'total_attempts': 0,
                'total_successes': 0
            }
        
        source = health_data[source_id]
        now = datetime.now().isoformat()
        
        # 记录本次结果
        source['history'].append({
            'timestamp': now,
            'success': success,
            'error': error
        })
        
        # 只保留最近 14 天的记录
        cutoff = (datetime.now() - timedelta(days=14)).isoformat()
        source['history'] = [h for h in source['history'] if h['timestamp'] > cutoff]
        
        source['total_attempts'] += 1
        if success:
            source['total_successes'] += 1
            source['last_success'] = now
        else:
            source['last_failure'] = now
            source['failure_reason'] = error
        
        # 计算最近 7 天成功率
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        week_history = [h for h in source['history'] if h['timestamp'] > week_ago]
        success_rate = sum(1 for h in week_history if h['success']) / len(week_history) if week_history else 1.0
        
        # 确定推荐行动
        recommended_action = "keep"
        if success_rate < 0.3:
            recommended_action = "replace"
        elif success_rate < 0.7:
            recommended_action = "monitor"
        
        # 检查连续失败
        recent_failures = sum(1 for h in source['history'][-5:] if not h['success'])
        if recent_failures >= 5:
            recommended_action = "replace"
        
        # 保存更新后的健康数据
        self._save_rss_health(health_data)
        
        return RSSSourceHealth(
            source_id=source_id,
            name=name,
            url=url,
            success_rate=round(success_rate, 2),
            last_success=source.get('last_success', ''),
            last_failure=source.get('last_failure', ''),
            failure_reason=error,
            recommended_action=recommended_action
        )
    
    def get_rss_replacement_suggestions(self) -> List[Dict]:
        """
        获取需要替换的 RSS 源建议
        
        Returns:
            [
                {
                    'source_id': '...',
                    'name': '...',
                    'current_url': '...',
                    'issue': '...',
                    'suggested_replacements': [...]
                }
            ]
        """
        health_data = self._load_rss_health()
        suggestions = []
        
        for source_id, data in health_data.items():
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            week_history = [h for h in data.get('history', []) if h['timestamp'] > week_ago]
            
            if not week_history:
                continue
            
            success_rate = sum(1 for h in week_history if h['success']) / len(week_history)
            recent_failures = sum(1 for h in week_history[-5:] if not h['success'])
            
            if success_rate < 0.5 or recent_failures >= 5:
                suggestions.append({
                    'source_id': source_id,
                    'name': data['name'],
                    'current_url': data['url'],
                    'issue': f'7天成功率 {success_rate:.0%}，最近5次失败{recent_failures}次',
                    'suggested_replacements': self._get_replacement_candidates(data['name'])
                })
        
        return suggestions
    
    def _load_recent_metrics(self, days: int) -> List[Dict]:
        """加载最近 N 天的评估指标"""
        try:
            import requests
            
            # 从 GitHub 获取 metrics 文件
            url = f"{self.base_url}/contents/{self.metrics_file}"
            response = requests.get(url, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })
            
            if response.status_code == 200:
                content = response.json()
                import base64
                data = json.loads(base64.b64decode(content['content']).decode('utf-8'))
                
                # 过滤最近 N 天的数据
                cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                return [m for m in data if m.get('date', '') >= cutoff]
        except Exception:
            pass
        
        return []
    
    def _extract_existing_optimizations(self, prompt: str) -> set:
        """提取当前 Prompt 中已有的优化点标识"""
        optimizations = set()
        
        if '内容偏好' in prompt or '科技' in prompt:
            optimizations.add('tech_content_priority')
        
        if '预测' in prompt or '洞察' in prompt:
            optimizations.add('insightfulness_requirement')
        
        if '表格' in prompt:
            optimizations.add('markdown_diversity')
        
        return optimizations
    
    def _get_tech_content_optimization(self) -> str:
        """获取科技内容优化模板"""
        return """
### 内容偏好（科技优先）
你服务的读者是科技从业者。优先选题：AI技术突破 > 开源生态 > 科技商业 > 产品创新 > 技术深度。
避免：纯政治事件、社会八卦、娱乐新闻。
"""
    
    def _get_insightfulness_optimization(self) -> str:
        """获取洞察力优化模板"""
        return """
### 洞察力要求
每个深度分析板块必须包含：
1. 预测性判断：未来3-6个月的发展趋势
2. 反共识观点：与主流观点不同的独到见解
3. 跨领域关联：发现不同事件间的隐藏逻辑
"""
    
    def _get_markdown_diversity_optimization(self) -> str:
        """获取 Markdown 多样性优化模板"""
        return """
### 格式多样性要求
每篇文章必须包含至少：
- 1个对比表格
- 2个Admonition引用块
- 1个引用块（金句）
- 1个有序或无序列表
"""
    
    def _get_replacement_candidates(self, source_name: str) -> List[str]:
        """根据源名称获取替代候选"""
        # 基于源名称的类别推荐替代源
        candidates = {
            'AI': [
                'https://www.ai-journal.com/feed',
                'https://venturebeat.com/category/ai/feed/',
                'https://www.artificialintelligence-news.com/feed/'
            ],
            'GitHub': [
                'https://rsshub.app/github/trending/daily/any',
                'https://github.blog/feed/',
                'https://rsshub.app/github/search/AI/sort=updated'
            ],
            '开源': [
                'https://opensource.com/feed',
                'https://www.oschina.net/news/rss',
                'https://solidot.org/index.rss'
            ],
            '技术': [
                'https://news.ycombinator.com/rss',
                'https://dev.to/feed',
                'https://www.infoq.cn/feed'
            ]
        }
        
        # 根据源名称匹配类别
        for category, urls in candidates.items():
            if category in source_name:
                return urls
        
        return candidates.get('技术', [])
    
    def _calculate_estimated_improvement(self, trends: Dict, optimizations: List[Dict]) -> Dict:
        """计算预估改进效果"""
        improvements = {}
        
        for opt in optimizations:
            target = opt['target']
            if target == 'content_strategy':
                improvements['tech_content_ratio'] = '+15-25%'
            elif target == 'analysis_requirements':
                improvements['insightfulness'] = '+20-30%'
            elif target == 'formatting_requirements':
                improvements['style_diversity'] = '+15-20%'
        
        return improvements
    
    def _load_rss_health(self) -> Dict:
        """加载 RSS 健康数据"""
        try:
            import requests
            url = f"{self.base_url}/contents/{self.rss_health_file}"
            response = requests.get(url, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })
            
            if response.status_code == 200:
                content = response.json()
                import base64
                return json.loads(base64.b64decode(content['content']).decode('utf-8'))
        except Exception:
            pass
        
        return {}
    
    def _save_rss_health(self, data: Dict):
        """保存 RSS 健康数据"""
        try:
            import requests
            
            url = f"{self.base_url}/contents/{self.rss_health_file}"
            content = json.dumps(data, ensure_ascii=False, indent=2)
            
            # 检查文件是否存在
            check = requests.get(url, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })
            
            if check.status_code == 200:
                sha = check.json()['sha']
                requests.put(url, headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }, json={
                    "message": f"更新 RSS 健康数据 - {datetime.now().strftime('%Y-%m-%d')}",
                    "content": content.encode('utf-8').decode('utf-8'),
                    "sha": sha
                })
            else:
                requests.put(url, headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }, json={
                    "message": f"创建 RSS 健康数据 - {datetime.now().strftime('%Y-%m-%d')}",
                    "content": content.encode('utf-8').decode('utf-8')
                })
        except Exception as e:
            print(f"[自适应进化] 保存 RSS 健康数据失败: {e}")


def get_evolution_summary(repo_owner: str, repo_name: str, token: str, 
                          current_prompt: str, days: int = 7) -> str:
    """
    获取进化总结，用于注入到 Prompt 中
    
    这个函数是自适应进化系统的入口点，返回结构化的进化反馈
    """
    engine = AdaptiveEvolutionEngine(repo_owner, repo_name, token)
    
    # 1. 长期趋势分析
    trends = engine.analyze_long_term_trends(days)
    
    # 2. 生成智能优化建议
    metrics = engine._load_recent_metrics(days)
    optimization = engine.generate_smart_prompt_optimization(current_prompt, metrics)
    
    # 3. RSS 健康检查
    rss_suggestions = engine.get_rss_replacement_suggestions()
    
    # 4. 构建反馈文本
    feedback_parts = ["\n\n### 🧬 自适应进化反馈（基于最近7天数据分析）"]
    
    # 添加趋势总结
    trend_emoji = {
        'improving': '📈',
        'stable': '➡️',
        'declining': '📉',
        'insufficient_data': '⏳'
    }
    
    feedback_parts.append(f"{trend_emoji.get(trends['trend'], '➡️')} 整体趋势: {trends['trend']}")
    
    if 'metrics_trends' in trends:
        for metric, data in trends['metrics_trends'].items():
            emoji = {'improving': '↑', 'declining': '↓', 'stable': '→'}.get(data['trend'], '→')
            feedback_parts.append(f"  {emoji} {metric}: 平均 {data['avg']} ({data['trend']})")
    
    # 添加具体优化建议
    if optimization and optimization.get('optimizations'):
        feedback_parts.append("\n💡 智能优化建议：")
        for i, opt in enumerate(optimization['optimizations'], 1):
            feedback_parts.append(f"{i}. [{opt['target']}] {opt['reason']}")
    
    # 添加 RSS 健康提醒
    if rss_suggestions:
        feedback_parts.append("\n⚠️ RSS 源健康提醒：")
        for suggestion in rss_suggestions[:3]:
            feedback_parts.append(f"  - {suggestion['name']}: {suggestion['issue']}")
    
    # 添加长期建议
    if trends.get('recommendations'):
        feedback_parts.append("\n📋 长期优化方向：")
        for rec in trends['recommendations'][:3]:
            feedback_parts.append(f"  - [{rec['priority']}] {rec['action']}")
    
    return "\n".join(feedback_parts)


def record_article_metrics(repo_owner: str, repo_name: str, token: str, 
                           evaluation: Dict, prompt_version: str = "v1"):
    """
    记录文章指标到历史数据
    
    这是数据收集的入口，每次文章评估后调用
    """
    engine = AdaptiveEvolutionEngine(repo_owner, repo_name, token)
    
    try:
        import requests
        
        # 构建指标记录
        metric = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'overall_score': evaluation.get('overall_score', 0),
            'tech_content_ratio': evaluation.get('dimensions', {}).get('tech_content_ratio', {}).get('score', 0),
            'analysis_depth': evaluation.get('dimensions', {}).get('analysis_depth', {}).get('score', 0),
            'style_diversity': evaluation.get('dimensions', {}).get('style_diversity', {}).get('score', 0),
            'insightfulness': evaluation.get('dimensions', {}).get('insightfulness', {}).get('score', 0),
            'readability': evaluation.get('dimensions', {}).get('readability', {}).get('score', 0),
            'word_count': evaluation.get('dimensions', {}).get('readability', {}).get('description', ''),
            'prompt_version': prompt_version
        }
        
        # 加载现有数据
        url = f"{engine.base_url}/contents/{engine.metrics_file}"
        response = requests.get(url, headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })
        
        metrics_history = []
        sha = None
        
        if response.status_code == 200:
            content = response.json()
            import base64
            metrics_history = json.loads(base64.b64decode(content['content']).decode('utf-8'))
            sha = content['sha']
        
        # 添加新记录
        metrics_history.append(metric)
        
        # 只保留最近 30 天
        cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        metrics_history = [m for m in metrics_history if m.get('date', '') >= cutoff]
        
        # 保存
        content = json.dumps(metrics_history, ensure_ascii=False, indent=2)
        
        if sha:
            requests.put(url, headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }, json={
                "message": f"记录文章指标 - {metric['date']}",
                "content": content.encode('utf-8').decode('utf-8'),
                "sha": sha
            })
        else:
            requests.put(url, headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }, json={
                "message": f"创建文章指标记录 - {metric['date']}",
                "content": content.encode('utf-8').decode('utf-8')
            })
        
        print(f"[自适应进化] 已记录文章指标: overall_score={metric['overall_score']}")
        
    except Exception as e:
        print(f"[自适应进化] 记录指标失败: {e}")


def update_rss_health(repo_owner: str, repo_name: str, token: str,
                      source_id: str, name: str, url: str, 
                      success: bool, error: str = ""):
    """
    更新 RSS 源健康状态的便捷函数
    """
    engine = AdaptiveEvolutionEngine(repo_owner, repo_name, token)
    health = engine.update_rss_source_health(source_id, name, url, success, error)
    
    if health.recommended_action == "replace":
        print(f"[RSS健康] ⚠️ {health.name} 需要替换 (成功率: {health.success_rate:.0%})")
    elif health.recommended_action == "monitor":
        print(f"[RSS健康] 👀 {health.name} 需要关注 (成功率: {health.success_rate:.0%})")
    else:
        print(f"[RSS健康] ✅ {health.name} 健康 (成功率: {health.success_rate:.0%})")
    
    return health
