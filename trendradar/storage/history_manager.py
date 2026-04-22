# coding=utf-8
"""
Article History Manager - 文章历史管理和记忆系统

提供增量更新、热点追踪、上下文记忆功能
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path


class ArticleHistoryManager:
    """管理文章历史和热点追踪"""
    
    def __init__(self, history_dir: str = "data/article_history"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.history_dir / "index.json"
        self.topics_file = self.history_dir / "topics.json"
        
    def save_article_metadata(self, article_data: Dict):
        """
        保存文章元数据
        
        Args:
            article_data: {
                'date': str,
                'title': str,
                'excerpt': str,
                'keywords': List[str],
                'hot_topics': List[str],
                'platforms': List[str],
                'timestamp': str
            }
        """
        # 加载现有索引
        index = self._load_index()
        
        # 添加新文章
        index.append(article_data)
        
        # 只保留最近90天
        cutoff_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        index = [item for item in index if item['date'] >= cutoff_date]
        
        # 保存
        self._save_index(index)
        
        # 更新热点话题追踪
        self._update_topic_tracking(article_data)
    
    def get_recent_articles(self, days: int = 7) -> List[Dict]:
        """获取最近N天的文章摘要"""
        index = self._load_index()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        return [
            item for item in index 
            if item['date'] >= cutoff_date
        ]
    
    def track_hot_topic_evolution(self, topic_keyword: str, days: int = 30) -> Dict:
        """
        追踪某个热点话题的演变
        
        Returns:
            {
                'topic': str,
                'mentions': int,
                'timeline': List[{'date': str, 'context': str}],
                'sentiment_trend': str,
                'related_topics': List[str]
            }
        """
        index = self._load_index()
        topics_db = self._load_topics()
        
        mentions = []
        for article in index:
            if topic_keyword in article.get('keywords', []) or \
               topic_keyword in article.get('hot_topics', []):
                mentions.append({
                    'date': article['date'],
                    'title': article['title'],
                    'excerpt': article.get('excerpt', '')[:100]
                })
        
        # 获取相关话题
        related = topics_db.get(topic_keyword, {}).get('related', [])
        
        return {
            'topic': topic_keyword,
            'mentions': len(mentions),
            'timeline': mentions[-10:],  # 最近10次提及
            'sentiment_trend': 'stable',  # TODO: 情感分析
            'related_topics': related
        }
    
    def generate_context_summary(self, days: int = 3) -> str:
        """
        生成近期热点背景摘要，供 AI 参考
        
        Returns:
            格式化的上下文字符串
        """
        recent = self.get_recent_articles(days)
        
        if not recent:
            return "（无近期历史记录）"
        
        lines = [
            "## 📚 近期热点背景（供参考）\n",
            f"*以下信息来自过去{days}天的报道，帮助理解今日热点的延续性*\n"
        ]
        
        # 提取主要话题
        all_topics = {}
        for article in recent:
            for topic in article.get('hot_topics', []):
                if topic not in all_topics:
                    all_topics[topic] = []
                all_topics[topic].append(article['date'])
        
        # 持续关注的热点
        ongoing_topics = [
            topic for topic, dates in all_topics.items()
            if len(dates) >= 2  # 至少出现2次
        ]
        
        if ongoing_topics:
            lines.append("\n### 🔥 持续关注的话题")
            for topic in ongoing_topics[:5]:
                dates = all_topics[topic]
                lines.append(f"- **{topic}**: 已连续{len(dates)}天出现在热点中")
        
        # 最近的重要事件
        lines.append("\n### 📅 近期重要事件回顾")
        for article in recent[:5]:
            lines.append(f"- **{article['date']}**: {article['title']}")
            if article.get('excerpt'):
                lines.append(f"  > {article['excerpt'][:80]}...")
        
        return "\n".join(lines)
    
    def _load_index(self) -> List[Dict]:
        """加载文章索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_index(self, index: List[Dict]):
        """保存文章索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def _load_topics(self) -> Dict:
        """加载话题数据库"""
        if self.topics_file.exists():
            with open(self.topics_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_topics(self, topics: Dict):
        """保存话题数据库"""
        with open(self.topics_file, 'w', encoding='utf-8') as f:
            json.dump(topics, f, ensure_ascii=False, indent=2)
    
    def _update_topic_tracking(self, article_data: Dict):
        """更新话题追踪数据库"""
        topics_db = self._load_topics()
        
        for topic in article_data.get('hot_topics', []):
            if topic not in topics_db:
                topics_db[topic] = {
                    'first_seen': article_data['date'],
                    'last_seen': article_data['date'],
                    'mention_count': 0,
                    'related': []
                }
            
            topics_db[topic]['last_seen'] = article_data['date']
            topics_db[topic]['mention_count'] += 1
            
            # 更新相关话题（共现分析）
            for other_topic in article_data.get('hot_topics', []):
                if other_topic != topic and other_topic not in topics_db[topic]['related']:
                    topics_db[topic]['related'].append(other_topic)
        
        self._save_topics(topics_db)
    
    def get_trending_topics(self, window_days: int = 7, min_mentions: int = 2) -> List[str]:
        """获取 trending 话题（在指定时间窗口内多次出现）"""
        topics_db = self._load_topics()
        cutoff_date = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
        
        trending = []
        for topic, data in topics_db.items():
            if data['last_seen'] >= cutoff_date and data['mention_count'] >= min_mentions:
                trending.append((topic, data['mention_count']))
        
        # 按提及次数排序
        trending.sort(key=lambda x: x[1], reverse=True)
        return [topic for topic, count in trending[:10]]
