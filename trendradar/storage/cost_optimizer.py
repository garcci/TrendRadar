# coding=utf-8
"""
AI Cost Optimizer - AI 使用成本优化器

在保证功能完整的前提下，通过以下策略控制 AI 使用成本：
1. 智能缓存：相似内容复用历史结果
2. 分级处理：重要热点深度分析，普通热点模板生成
3. Token 优化：精简输入，控制输出长度
4. 批量处理：合并多次调用为一次
5. 降级策略：API 失败时自动切换到模板
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AICostOptimizer:
    """AI 成本优化器"""
    
    def __init__(self, cache_dir: str = "data/ai_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "response_cache.json"
        self.stats_file = self.cache_dir / "usage_stats.json"
        
        # 配置参数
        self.max_cache_age_days = 7  # 缓存有效期
        self.daily_token_budget = 200000  # 每日 Token 预算（保守设置，约 1-2 篇文章）
        self.monthly_token_budget = 3000000  # 每月 Token 上限
        self.min_article_interval_hours = 20  # 最小文章间隔（避免一天内多次生成）
        
    def should_generate_article(self, last_generation_time: Optional[str] = None) -> Tuple[bool, str]:
        """
        判断是否应该生成新文章（基于时间间隔）
        
        Returns:
            (should_generate, reason)
        """
        if not last_generation_time:
            return True, "首次生成"
        
        try:
            last_time = datetime.fromisoformat(last_generation_time)
            hours_since = (datetime.now() - last_time).total_seconds() / 3600
            
            if hours_since < self.min_article_interval_hours:
                return False, f"距离上次生成仅 {hours_since:.1f} 小时，未到最小间隔"
            
            return True, f"距离上次生成 {hours_since:.1f} 小时，可以生成"
        except Exception as e:
            return True, f"解析时间失败: {e}"
    
    def get_cached_response(self, cache_key: str) -> Optional[str]:
        """
        获取缓存的 AI 响应
        
        Args:
            cache_key: 缓存键（基于输入内容的哈希）
            
        Returns:
            缓存的响应内容，如果不存在或过期则返回 None
        """
        cache = self._load_cache()
        
        if cache_key in cache:
            cached_item = cache[cache_key]
            cached_time = datetime.fromisoformat(cached_item['timestamp'])
            
            # 检查是否过期
            if (datetime.now() - cached_time).days < self.max_cache_age_days:
                self._record_cache_hit()
                return cached_item['response']
            else:
                # 删除过期缓存
                del cache[cache_key]
                self._save_cache(cache)
        
        return None
    
    def cache_response(self, cache_key: str, response: str, token_usage: int = 0):
        """
        缓存 AI 响应
        
        Args:
            cache_key: 缓存键
            response: AI 响应内容
            token_usage: 本次调用的 Token 使用量
        """
        cache = self._load_cache()
        
        cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'token_usage': token_usage
        }
        
        # 清理旧缓存（保留最近 100 条）
        if len(cache) > 100:
            sorted_items = sorted(
                cache.items(), 
                key=lambda x: x[1]['timestamp'], 
                reverse=True
            )
            cache = dict(sorted_items[:100])
        
        self._save_cache(cache)
        self._record_token_usage(token_usage)
    
    def generate_cache_key(self, news_data_summary: str, context_summary: str = "") -> str:
        """
        基于输入内容生成缓存键
        
        Args:
            news_data_summary: 热点数据摘要
            context_summary: 历史上下文摘要
            
        Returns:
            缓存键（MD5 哈希）
        """
        content = f"{news_data_summary}|{context_summary}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def assess_content_importance(self, news_data) -> str:
        """
        评估今日内容重要性，决定使用哪种生成策略
        
        Returns:
            'high' | 'medium' | 'low'
        """
        # 简单启发式规则
        total_items = sum(len(items) for items in news_data.items.values())
        
        # 检查是否有重大事件关键词
        major_keywords = ['战争', '地震', '疫情', '总统', '总理', '股市崩盘', '恐怖袭击']
        has_major_event = any(
            keyword in item.title 
            for items_list in news_data.items.values() 
            for item in items_list[:5]
            for keyword in major_keywords
        )
        
        if has_major_event or total_items > 300:
            return 'high'
        elif total_items > 200:
            return 'medium'
        else:
            return 'low'
    
    def get_optimized_params(self, importance_level: str) -> Dict:
        """
        根据重要性级别获取优化的 AI 调用参数
        
        Returns:
            {temperature, max_tokens, model}
        """
        params = {
            'high': {
                'temperature': 0.7,
                'max_tokens': 8000,
                'model_priority': 'deepseek/deepseek-chat'  # 高质量模型
            },
            'medium': {
                'temperature': 0.6,
                'max_tokens': 6000,
                'model_priority': 'deepseek/deepseek-chat'
            },
            'low': {
                'temperature': 0.5,
                'max_tokens': 4000,
                'model_priority': 'deepseek/deepseek-chat'  # 可以使用更便宜的模型
            }
        }
        
        return params.get(importance_level, params['medium'])
    
    def compress_input_data(self, news_data, max_items_per_source: int = 5) -> str:
        """
        压缩输入数据，减少 Token 消耗
        
        Args:
            news_data: 原始新闻数据
            max_items_per_source: 每个来源最多保留的条目数
            
        Returns:
            压缩后的文本
        """
        compressed = []
        
        for source_id, items_list in news_data.items.items():
            source_name = news_data.id_to_name.get(source_id, source_id)
            compressed.append(f"\n**{source_name}** (Top {max_items_per_source}):")
            
            # 只保留前 N 条
            for i, item in enumerate(items_list[:max_items_per_source], 1):
                # 进一步压缩标题（去除冗余词汇）
                title = item.title[:50]  # 限制标题长度
                compressed.append(f"  {i}. {title}")
        
        return "\n".join(compressed)
    
    def check_daily_budget(self) -> Tuple[bool, Dict]:
        """
        检查是否在每日 Token 预算内
        
        Returns:
            (within_budget, stats)
        """
        stats = self._load_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        current_month = datetime.now().strftime("%Y-%m")
        
        if today not in stats:
            stats[today] = {'tokens_used': 0, 'api_calls': 0, 'cache_hits': 0}
        
        today_stats = stats[today]
        remaining_daily = self.daily_token_budget - today_stats['tokens_used']
        
        # 检查月度预算
        monthly_used = sum(
            day['tokens_used'] 
            for date, day in stats.items() 
            if date.startswith(current_month)
        )
        remaining_monthly = self.monthly_token_budget - monthly_used
        
        within_budget = remaining_daily > 0 and remaining_monthly > 0
        
        return within_budget, {
            'today': today,
            'tokens_used': today_stats['tokens_used'],
            'api_calls': today_stats['api_calls'],
            'cache_hits': today_stats['cache_hits'],
            'remaining_daily': remaining_daily,
            'daily_budget': self.daily_token_budget,
            'monthly_used': monthly_used,
            'remaining_monthly': remaining_monthly,
            'monthly_budget': self.monthly_token_budget
        }
    
    def _load_cache(self) -> Dict:
        """加载缓存"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self, cache: Dict):
        """保存缓存"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    
    def _load_stats(self) -> Dict:
        """加载使用统计"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_stats(self, stats: Dict):
        """保存使用统计"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    
    def _record_token_usage(self, tokens: int):
        """记录 Token 使用"""
        stats = self._load_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in stats:
            stats[today] = {'tokens_used': 0, 'api_calls': 0, 'cache_hits': 0}
        
        stats[today]['tokens_used'] += tokens
        stats[today]['api_calls'] += 1
        
        self._save_stats(stats)
    
    def _record_cache_hit(self):
        """记录缓存命中"""
        stats = self._load_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in stats:
            stats[today] = {'tokens_used': 0, 'api_calls': 0, 'cache_hits': 0}
        
        stats[today]['cache_hits'] += 1
        
        self._save_stats(stats)
    
    def get_cost_report(self, days: int = 7) -> Dict:
        """
        生成成本报告
        
        Returns:
            包含使用情况统计的报告
        """
        stats = self._load_stats()
        report = {
            'daily_stats': {},
            'summary': {
                'total_tokens': 0,
                'total_calls': 0,
                'total_cache_hits': 0,
                'avg_tokens_per_call': 0,
                'cache_hit_rate': 0
            }
        }
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        for date, day_stats in stats.items():
            if date >= cutoff_date:
                report['daily_stats'][date] = day_stats
                report['summary']['total_tokens'] += day_stats.get('tokens_used', 0)
                report['summary']['total_calls'] += day_stats.get('api_calls', 0)
                report['summary']['total_cache_hits'] += day_stats.get('cache_hits', 0)
        
        # 计算平均值和命中率
        if report['summary']['total_calls'] > 0:
            report['summary']['avg_tokens_per_call'] = (
                report['summary']['total_tokens'] / report['summary']['total_calls']
            )
        
        total_requests = report['summary']['total_calls'] + report['summary']['total_cache_hits']
        if total_requests > 0:
            report['summary']['cache_hit_rate'] = (
                report['summary']['total_cache_hits'] / total_requests * 100
            )
        
        return report
