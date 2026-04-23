# -*- coding: utf-8 -*-
"""
Cloudflare D1 持久化存储 - 替代GitHub Issues，支持完整数据存储

为什么需要D1：
1. GitHub Issues有内容长度限制（标题256字符，内容65535字符）
2. Issues不支持结构化查询，无法做SQL分析
3. 数据可能被截断，导致进化分析不准确
4. D1支持完整的关系型数据存储和SQL查询

D1免费额度（完全够用）：
- 每天500万次行读取
- 每天10万次行写入
- 足够存储数年数据

表设计：
- article_metrics: 文章质量指标
- rss_health: RSS源健康状态
- error_incidents: 错误事件
- ab_test_results: A/B测试结果
- model_usage: 模型使用记录
- trend_predictions: 热点预测记录
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class D1Storage:
    """Cloudflare D1 存储后端"""
    
    def __init__(self, account_id: str = None, database_id: str = None, api_token: str = None):
        self.account_id = account_id or os.environ.get("CF_ACCOUNT_ID", "")
        self.database_id = database_id or os.environ.get("D1_DATABASE_ID", "")
        self.api_token = api_token or os.environ.get("CF_API_TOKEN", "")
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/d1/database/{self.database_id}"
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """发送D1 API请求"""
        import requests
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            if not result.get("success"):
                raise Exception(f"D1 API错误: {result.get('errors', [])}")
            
            return result
        except Exception as e:
            print(f"[D1存储] API请求失败: {e}")
            raise
    
    def query(self, sql: str, params: List = None) -> List[Dict]:
        """执行SQL查询"""
        data = {"sql": sql}
        if params:
            data["params"] = params
        
        result = self._request("POST", "/query", data)
        return result.get("result", [{}])[0].get("results", [])
    
    def execute(self, sql: str, params: List = None) -> Dict:
        """执行SQL语句"""
        data = {"sql": sql}
        if params:
            data["params"] = params
        
        result = self._request("POST", "/query", data)
        return result.get("result", [{}])[0]
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.account_id and self.database_id and self.api_token)


class EvolutionDataStore:
    """进化数据存储 - 基于D1"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.d1 = D1Storage()
        self._fallback_to_file = not self.d1.is_configured()
    
    # ═══════════════════════════════════════════════════════════
    # 表结构初始化
    # ═══════════════════════════════════════════════════════════
    
    def init_tables(self):
        """初始化所有表"""
        if self._fallback_to_file:
            print("[D1存储] D1未配置，跳过表初始化")
            return
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS article_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                title TEXT,
                overall_score REAL,
                tech_content_ratio REAL,
                analysis_depth REAL,
                style_diversity REAL,
                insightfulness REAL,
                readability REAL,
                prompt_version TEXT,
                model_used TEXT,
                cost REAL,
                tokens_used INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS rss_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                source_name TEXT,
                url TEXT,
                success INTEGER,
                error_message TEXT,
                date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS error_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                category TEXT,
                severity TEXT,
                message TEXT,
                fix_strategy TEXT,
                auto_fixed INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ab_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT NOT NULL,
                variant TEXT,
                overall_score REAL,
                cost REAL,
                model_used TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS model_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT,
                task_type TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost REAL,
                latency REAL,
                success INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_metrics_date ON article_metrics(date)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_rss_source_date ON rss_health(source_id, date)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_errors_date ON error_incidents(created_at)
            """
        ]
        
        for sql in tables:
            try:
                self.d1.execute(sql)
            except Exception as e:
                print(f"[D1存储] 创建表失败: {e}")
        
        print("[D1存储] 表初始化完成")
    
    # ═══════════════════════════════════════════════════════════
    # 文章指标存储
    # ═══════════════════════════════════════════════════════════
    
    def save_article_metric(self, metric: Dict):
        """保存文章指标"""
        if self._fallback_to_file:
            self._save_to_file("article_metrics", metric)
            return
        
        sql = """
        INSERT INTO article_metrics 
        (date, title, overall_score, tech_content_ratio, analysis_depth, 
         style_diversity, insightfulness, readability, prompt_version, 
         model_used, cost, tokens_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            metric.get("date", datetime.now().strftime("%Y-%m-%d")),
            metric.get("title", ""),
            metric.get("overall_score", 0),
            metric.get("tech_content_ratio", 0),
            metric.get("analysis_depth", 0),
            metric.get("style_diversity", 0),
            metric.get("insightfulness", 0),
            metric.get("readability", 0),
            metric.get("prompt_version", "v1"),
            metric.get("model_used", "unknown"),
            metric.get("cost", 0),
            metric.get("tokens_used", 0)
        ]
        
        try:
            self.d1.execute(sql, params)
        except Exception as e:
            print(f"[D1存储] 保存文章指标失败: {e}")
            self._save_to_file("article_metrics", metric)
    
    def get_article_metrics(self, days: int = 30) -> List[Dict]:
        """获取最近N天的文章指标"""
        if self._fallback_to_file:
            return self._load_from_file("metrics_history", days)
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = """
        SELECT * FROM article_metrics 
        WHERE date >= ? 
        ORDER BY date DESC
        """
        
        try:
            return self.d1.query(sql, [cutoff])
        except Exception as e:
            print(f"[D1存储] 查询文章指标失败: {e}")
            return self._load_from_file("metrics_history", days)
    
    def get_average_scores(self, days: int = 7) -> Dict[str, float]:
        """获取平均分数"""
        if self._fallback_to_file:
            metrics = self._load_from_file("metrics_history", days)
            if not metrics:
                return {}
            return {
                "overall": sum(m.get("overall_score", 0) for m in metrics) / len(metrics),
                "tech_content": sum(m.get("tech_content_ratio", 0) for m in metrics) / len(metrics),
                "insightfulness": sum(m.get("insightfulness", 0) for m in metrics) / len(metrics),
                "style": sum(m.get("style_diversity", 0) for m in metrics) / len(metrics)
            }
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = """
        SELECT 
            AVG(overall_score) as overall,
            AVG(tech_content_ratio) as tech_content,
            AVG(insightfulness) as insightfulness,
            AVG(style_diversity) as style
        FROM article_metrics 
        WHERE date >= ?
        """
        
        try:
            result = self.d1.query(sql, [cutoff])
            return result[0] if result else {}
        except Exception as e:
            print(f"[D1存储] 查询平均分数失败: {e}")
            return {}
    
    # ═══════════════════════════════════════════════════════════
    # RSS健康存储
    # ═══════════════════════════════════════════════════════════
    
    def save_rss_health(self, source_id: str, source_name: str, url: str, 
                       success: bool, error: str = ""):
        """保存RSS健康状态"""
        if self._fallback_to_file:
            self._save_to_file("rss_health", {
                "source_id": source_id,
                "source_name": source_name,
                "url": url,
                "success": success,
                "error": error,
                "date": datetime.now().strftime("%Y-%m-%d")
            })
            return
        
        sql = """
        INSERT INTO rss_health (source_id, source_name, url, success, error_message, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = [source_id, source_name, url, 1 if success else 0, error, 
                 datetime.now().strftime("%Y-%m-%d")]
        
        try:
            self.d1.execute(sql, params)
        except Exception as e:
            print(f"[D1存储] 保存RSS健康失败: {e}")
            self._save_to_file("rss_health", {"source_id": source_id, "success": success})
    
    def get_rss_success_rate(self, source_id: str, days: int = 7) -> float:
        """获取RSS源成功率"""
        if self._fallback_to_file:
            return 1.0  # 简化处理
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = """
        SELECT 
            CAST(SUM(success) AS REAL) / COUNT(*) as rate
        FROM rss_health 
        WHERE source_id = ? AND date >= ?
        """
        
        try:
            result = self.d1.query(sql, [source_id, cutoff])
            return result[0].get("rate", 0) if result else 0
        except Exception:
            return 1.0
    
    # ═══════════════════════════════════════════════════════════
    # 错误事件存储
    # ═══════════════════════════════════════════════════════════
    
    def save_error_incident(self, incident: Dict):
        """保存错误事件"""
        if self._fallback_to_file:
            self._save_to_file("error_incidents", incident)
            return
        
        sql = """
        INSERT INTO error_incidents (incident_id, category, severity, message, fix_strategy, auto_fixed)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = [
            incident.get("incident_id", ""),
            incident.get("category", ""),
            incident.get("severity", ""),
            incident.get("message", ""),
            incident.get("fix_strategy", ""),
            1 if incident.get("auto_fixed") else 0
        ]
        
        try:
            self.d1.execute(sql, params)
        except Exception as e:
            print(f"[D1存储] 保存错误事件失败: {e}")
            self._save_to_file("error_incidents", incident)
    
    # ═══════════════════════════════════════════════════════════
    # 模型使用记录
    # ═══════════════════════════════════════════════════════════
    
    def save_model_usage(self, usage: Dict):
        """保存模型使用记录"""
        if self._fallback_to_file:
            self._save_to_file("model_usage", usage)
            return
        
        sql = """
        INSERT INTO model_usage (provider, task_type, input_tokens, output_tokens, cost, latency, success)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            usage.get("provider", ""),
            usage.get("task_type", ""),
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            usage.get("cost", 0),
            usage.get("latency", 0),
            1 if usage.get("success") else 0
        ]
        
        try:
            self.d1.execute(sql, params)
        except Exception as e:
            print(f"[D1存储] 保存模型使用失败: {e}")
            self._save_to_file("model_usage", usage)
    
    def get_daily_cost(self) -> float:
        """获取今日成本"""
        if self._fallback_to_file:
            return 0.0
        
        today = datetime.now().strftime("%Y-%m-%d")
        sql = """
        SELECT SUM(cost) as total_cost
        FROM model_usage 
        WHERE date(created_at) = ?
        """
        
        try:
            result = self.d1.query(sql, [today])
            return result[0].get("total_cost", 0) if result else 0
        except Exception:
            return 0.0
    
    # ═══════════════════════════════════════════════════════════
    # 降级到文件存储
    # ═══════════════════════════════════════════════════════════
    
    def _save_to_file(self, data_type: str, data: Dict):
        """降级到文件存储"""
        file_path = f"{self.trendradar_path}/evolution/{data_type}.json"
        
        try:
            records = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            
            records.append(data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[D1存储] 文件存储失败: {e}")
    
    def _load_from_file(self, data_type: str, days: int) -> List[Dict]:
        """从文件加载"""
        file_path = f"{self.trendradar_path}/evolution/{data_type}.json"
        
        try:
            if not os.path.exists(file_path):
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            return [r for r in records if r.get("date", "") >= cutoff]
        except Exception:
            return []


# 便捷函数
def get_evolution_data_store(trendradar_path: str = ".") -> EvolutionDataStore:
    """获取进化数据存储实例"""
    return EvolutionDataStore(trendradar_path)


def init_d1_storage(trendradar_path: str = "."):
    """初始化D1存储"""
    store = EvolutionDataStore(trendradar_path)
    store.init_tables()
    return store
