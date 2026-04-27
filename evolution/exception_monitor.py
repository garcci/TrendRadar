# -*- coding: utf-8 -*-
"""
实时异常监控 - Lv33

核心理念：
1. 捕获系统中所有异常，建立异常知识库
2. 自动分类异常（网络/API/解析/权限/配置）
3. 统计异常频率和模式
4. 为Lv34智能修复提供数据基础

异常分类：
- network: 网络问题（连接超时、DNS错误、SSL证书）
- api_rate_limit: API限流（429、too many requests）
- api_error: API错误（500、502、503）
- parse_error: 解析错误（JSON、XML、HTML解析失败）
- type_error: 类型错误（索引错误、None访问）
- permission: 权限问题（401、403、认证失败）
- config: 配置错误（缺少配置、格式错误）
- resource: 资源问题（内存不足、磁盘满）

输出：
- 异常知识库（JSON格式）
- 异常统计报告
- 高频异常预警
"""

import functools
import hashlib
import json
import os
import re
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional


class ExceptionMonitor:
    """异常监控器"""
    
    # 异常分类规则
    EXCEPTION_PATTERNS = {
        "network": {
            "keywords": ["Connection", "Timeout", "SSLError", "DNS", "Network", " unreachable",
                        "Connection refused", "Connection reset", "Remote end closed"],
            "severity": "medium"
        },
        "api_rate_limit": {
            "keywords": ["429", "rate limit", "too many requests", "quota exceeded", "throttled"],
            "severity": "medium"
        },
        "api_error": {
            "keywords": ["500", "502", "503", "504", "Internal Server Error", "Bad Gateway",
                        "Service Unavailable", "API error"],
            "severity": "high"
        },
        "parse_error": {
            "keywords": ["JSON", "parse", "Unterminated", "Expecting", "Invalid",
                        "XML", "HTML", "decode", "encoding"],
            "severity": "medium"
        },
        "type_error": {
            "keywords": ["TypeError", "IndexError", "KeyError", "AttributeError",
                        "NoneType", "indices must be integers", "string indices"],
            "severity": "high"
        },
        "permission": {
            "keywords": ["401", "403", "permission", "unauthorized", "forbidden",
                        "authentication", "credential", "token"],
            "severity": "high"
        },
        "config": {
            "keywords": ["config", "configuration", "missing", "required", "environment",
                        "variable", "setting", "not found"],
            "severity": "low"
        },
        "resource": {
            "keywords": ["Memory", "Disk", "resource", "out of", "insufficient", "quota"],
            "severity": "high"
        },
        "build_failure": {
            "keywords": ["build", "compilation", "syntax error", "yaml", "frontmatter",
                        "InvalidContentEntryDataError", "does not match collection schema",
                        "bad indentation", "mapping entry", "Node.js", "not supported",
                        "Astro", "astro build"],
            "severity": "critical"
        },
        "deploy_failure": {
            "keywords": ["deploy", "deployment", "publish", "Cloudflare Pages",
                        "GitHub Pages", "HttpError", "Not Found", "pages.dev",
                        "404", "not found", "unreachable"],
            "severity": "critical"
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.knowledge_base_file = f"{trendradar_path}/evolution/exception_knowledge.json"
        self.knowledge_base = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> Dict:
        """加载异常知识库"""
        if os.path.exists(self.knowledge_base_file):
            try:
                with open(self.knowledge_base_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "exceptions": [],
            "patterns": {},
            "statistics": {}
        }
    
    def _save_knowledge_base(self):
        """保存异常知识库"""
        with open(self.knowledge_base_file, 'w') as f:
            json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
    
    def _classify_exception(self, exc_type: str, exc_msg: str, stack_trace: str) -> str:
        """分类异常"""
        combined = f"{exc_type} {exc_msg} {stack_trace}".lower()
        
        for category, info in self.EXCEPTION_PATTERNS.items():
            for keyword in info["keywords"]:
                if keyword.lower() in combined:
                    return category
        
        return "unknown"
    
    def _generate_exception_hash(self, exc_type: str, exc_msg: str, stack_trace: str) -> str:
        """生成异常指纹（用于去重）"""
        # 提取关键信息生成指纹
        # 简化堆栈跟踪，只保留文件名和行号
        simplified = f"{exc_type}:{exc_msg[:100]}"
        return hashlib.md5(simplified.encode()).hexdigest()[:16]
    
    def record_exception(self, exc_type: str, exc_msg: str, stack_trace: str,
                        context: str = "", module: str = "") -> Dict:
        """记录异常到知识库"""
        
        category = self._classify_exception(exc_type, exc_msg, stack_trace)
        fingerprint = self._generate_exception_hash(exc_type, exc_msg, stack_trace)
        
        exception_record = {
            "timestamp": datetime.now().isoformat(),
            "fingerprint": fingerprint,
            "type": exc_type,
            "message": exc_msg[:500],  # 截断长消息
            "category": category,
            "severity": self.EXCEPTION_PATTERNS.get(category, {}).get("severity", "unknown"),
            "context": context,
            "module": module,
            "stack_trace": stack_trace[:1000]  # 截断长堆栈
        }
        
        # 添加到知识库
        self.knowledge_base["exceptions"].append(exception_record)
        
        # 只保留最近100条
        self.knowledge_base["exceptions"] = self.knowledge_base["exceptions"][-100:]
        
        # 更新模式统计
        if fingerprint not in self.knowledge_base["patterns"]:
            self.knowledge_base["patterns"][fingerprint] = {
                "type": exc_type,
                "category": category,
                "first_seen": exception_record["timestamp"],
                "count": 0,
                "message_pattern": exc_msg[:200]
            }
        
        self.knowledge_base["patterns"][fingerprint]["count"] += 1
        self.knowledge_base["patterns"][fingerprint]["last_seen"] = exception_record["timestamp"]
        
        # 写入统一数据管道（低成本、不阻塞）
        try:
            from evolution.data_pipeline import write_record
            write_record("exception", exception_record, trendradar_path=self.trendradar_path)
        except Exception:
            pass

        # 保存到本地知识库
        self._save_knowledge_base()

        return exception_record
    
    def monitor(self, context: str = "", module: str = "") -> Callable:
        """异常监控装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    exc_type = type(e).__name__
                    exc_msg = str(e)
                    stack_trace = traceback.format_exc()
                    
                    # 记录异常
                    self.record_exception(
                        exc_type=exc_type,
                        exc_msg=exc_msg,
                        stack_trace=stack_trace,
                        context=context or func.__name__,
                        module=module or func.__module__
                    )
                    
                    # 重新抛出，不影响原有流程
                    raise
            
            return wrapper
        return decorator
    
    def get_exception_statistics(self, hours: int = 24) -> Dict:
        """获取异常统计"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        recent_exceptions = [e for e in self.knowledge_base["exceptions"]
                           if e["timestamp"] > cutoff]
        
        if not recent_exceptions:
            return {"message": "No exceptions in the specified period"}
        
        # 按类别统计
        category_counts = Counter(e["category"] for e in recent_exceptions)
        
        # 按严重程度统计
        severity_counts = Counter(e["severity"] for e in recent_exceptions)
        
        # 高频异常模式
        pattern_counts = Counter(e["fingerprint"] for e in recent_exceptions)
        top_patterns = []
        for fingerprint, count in pattern_counts.most_common(5):
            pattern_info = self.knowledge_base["patterns"].get(fingerprint, {})
            top_patterns.append({
                "fingerprint": fingerprint,
                "count": count,
                "type": pattern_info.get("type", "unknown"),
                "category": pattern_info.get("category", "unknown"),
                "message": pattern_info.get("message_pattern", "")[:100]
            })
        
        return {
            "period_hours": hours,
            "total_exceptions": len(recent_exceptions),
            "category_distribution": dict(category_counts),
            "severity_distribution": dict(severity_counts),
            "top_patterns": top_patterns,
            "trend": "increasing" if len(recent_exceptions) > 10 else "stable"
        }
    
    def get_high_frequency_exceptions(self, threshold: int = 3) -> List[Dict]:
        """获取高频异常（需要优先修复）"""
        high_freq = []
        
        for fingerprint, pattern in self.knowledge_base["patterns"].items():
            if pattern["count"] >= threshold:
                high_freq.append({
                    "fingerprint": fingerprint,
                    "count": pattern["count"],
                    "type": pattern["type"],
                    "category": pattern["category"],
                    "message": pattern["message_pattern"],
                    "first_seen": pattern.get("first_seen", ""),
                    "last_seen": pattern.get("last_seen", "")
                })
        
        # 按频率排序
        high_freq.sort(key=lambda x: -x["count"])
        
        return high_freq
    
    def generate_monitor_report(self) -> str:
        """生成监控报告"""
        stats = self.get_exception_statistics(hours=24)
        high_freq = self.get_high_frequency_exceptions(threshold=2)
        
        lines = ["\n### 🚨 异常监控报告\n"]
        
        if "message" in stats:
            lines.append("**过去24小时无异常记录** ✅\n")
            return "\n".join(lines)
        
        lines.append(f"**过去24小时异常统计**:")
        lines.append(f"- 总异常数: {stats['total_exceptions']}")
        lines.append(f"- 趋势: {stats['trend']}")
        lines.append("")
        
        # 分类分布
        if stats.get("category_distribution"):
            lines.append("**异常分类分布**:")
            for cat, count in sorted(stats["category_distribution"].items(), key=lambda x: -x[1]):
                emoji = {"network": "🌐", "api_rate_limit": "⏳", "api_error": "❌",
                        "parse_error": "🔍", "type_error": "💥", "permission": "🔒",
                        "config": "⚙️", "resource": "💾", "unknown": "❓"}.get(cat, "❓")
                lines.append(f"- {emoji} {cat}: {count}次")
            lines.append("")
        
        # 高频异常
        if high_freq:
            lines.append("**高频异常（需优先修复）**:")
            for exc in high_freq[:5]:
                lines.append(f"- 🔥 [{exc['count']}次] {exc['type']}: {exc['message'][:80]}...")
            lines.append("")
        
        lines.append("**建议**: 关注高频异常，及时修复以避免影响系统稳定性。\n")
        
        return "\n".join(lines)


# 便捷函数
_monitor_instance = None

def get_monitor(trendradar_path: str = ".") -> ExceptionMonitor:
    """获取异常监控器实例（单例）"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ExceptionMonitor(trendradar_path)
    return _monitor_instance


def get_exception_monitor_report(trendradar_path: str = ".") -> str:
    """获取异常监控报告"""
    monitor = get_monitor(trendradar_path)
    return monitor.generate_monitor_report()


def monitor_exceptions(context: str = "", module: str = "") -> Callable:
    """异常监控装饰器"""
    monitor = get_monitor()
    return monitor.monitor(context=context, module=module)


if __name__ == "__main__":
    # 测试
    monitor = ExceptionMonitor()
    
    # 模拟一个类型错误
    try:
        s = "hello"
        _ = s["key"]  # 这会引发TypeError
    except Exception as e:
        monitor.record_exception(
            type(e).__name__,
            str(e),
            traceback.format_exc(),
            "test_context"
        )
    
    print(monitor.generate_monitor_report())
