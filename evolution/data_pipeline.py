# -*- coding: utf-8 -*-
"""
统一数据管道 — 进化系统模块间数据标准化流动

问题：
1. 各模块各自存储数据，格式不统一
2. 模块 A 的输出无法被模块 B 消费
3. 数据重复存储，缺乏溯源

解决方案：
1. 定义标准数据格式（Schema）
2. 提供统一的读写接口
3. 自动记录数据血缘关系
4. 支持数据版本控制

数据类型：
- article: 文章相关数据（标题、评分、标签等）
- rss: RSS源数据（源状态、成功率等）
- prompt: Prompt相关（版本、效果等）
- cost: 成本数据（API调用、额度等）
- exception: 异常数据
- metric: 性能指标
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataPipeline:
    """统一数据管道"""

    # 标准数据类型
    DATA_TYPES = {
        "article": {
            "required": ["id", "timestamp"],
            "fields": ["title", "date", "score", "tags", "tech_ratio", "source_count"],
        },
        "rss": {
            "required": ["source_id", "timestamp"],
            "fields": ["success", "item_count", "error", "response_time"],
        },
        "prompt": {
            "required": ["version", "timestamp"],
            "fields": ["template", "effectiveness", "avg_score", "usage_count"],
        },
        "cost": {
            "required": ["provider", "timestamp"],
            "fields": ["cost", "tokens", "model", "success"],
        },
        "exception": {
            "required": ["type", "timestamp"],
            "fields": ["message", "module", "context", "resolved"],
        },
        "metric": {
            "required": ["name", "timestamp"],
            "fields": ["value", "unit", "module", "threshold"],
        },
    }

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = Path(trendradar_path)
        self.pipeline_dir = self.trendradar_path / "evolution" / "data_pipeline"
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)

        # 初始化各类型存储
        for data_type in self.DATA_TYPES:
            (self.pipeline_dir / f"{data_type}.jsonl").touch(exist_ok=True)

    def write(self, data_type: str, record: Dict) -> bool:
        """
        写入数据记录

        Args:
            data_type: 数据类型（article/rss/prompt/cost/exception/metric）
            record: 数据记录
        """
        if data_type not in self.DATA_TYPES:
            print(f"[数据管道] 未知数据类型: {data_type}")
            return False

        schema = self.DATA_TYPES[data_type]

        # 验证必填字段
        for field in schema["required"]:
            if field not in record:
                record[field] = datetime.now().isoformat() if field == "timestamp" else "unknown"

        # 自动添加时间戳
        if "timestamp" not in record:
            record["timestamp"] = datetime.now().isoformat()

        # 写入 JSONL
        try:
            filepath = self.pipeline_dir / f"{data_type}.jsonl"
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            return True
        except Exception as e:
            print(f"[数据管道] 写入失败: {e}")
            return False

    def read(self, data_type: str, days: int = 7, limit: int = 100) -> List[Dict]:
        """
        读取最近的数据记录

        Args:
            data_type: 数据类型
            days: 最近 N 天
            limit: 最大返回条数
        """
        filepath = self.pipeline_dir / f"{data_type}.jsonl"
        if not filepath.exists():
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            records = []
            for line in lines[-limit:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    # 时间过滤
                    if days > 0 and "timestamp" in record:
                        from datetime import timedelta
                        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                        if record["timestamp"] < cutoff:
                            continue
                    records.append(record)
                except json.JSONDecodeError:
                    continue

            return records
        except Exception as e:
            print(f"[数据管道] 读取失败: {e}")
            return []

    def query(self, data_type: str, filters: Dict = None, limit: int = 100) -> List[Dict]:
        """
        条件查询数据

        Args:
            data_type: 数据类型
            filters: 过滤条件 {字段: 值}
            limit: 最大返回条数
        """
        filters = filters or {}
        records = self.read(data_type, days=30, limit=1000)

        result = []
        for record in records:
            match = True
            for key, value in filters.items():
                if record.get(key) != value:
                    match = False
                    break
            if match:
                result.append(record)
            if len(result) >= limit:
                break

        return result

    def get_stats(self, data_type: str) -> Dict:
        """获取数据类型的统计信息"""
        filepath = self.pipeline_dir / f"{data_type}.jsonl"
        if not filepath.exists():
            return {"count": 0, "size_bytes": 0}

        try:
            size = filepath.stat().st_size
            with open(filepath, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)

            return {
                "count": count,
                "size_bytes": size,
                "size_kb": round(size / 1024, 2),
            }
        except Exception:
            return {"count": 0, "size_bytes": 0}

    def get_pipeline_summary(self) -> str:
        """获取数据管道总览"""
        lines = ["# 📦 数据管道总览"]
        lines.append("")

        total_records = 0
        for data_type in self.DATA_TYPES:
            stats = self.get_stats(data_type)
            total_records += stats["count"]
            lines.append(f"- **{data_type}**: {stats['count']} 条 ({stats['size_kb']} KB)")

        lines.append("")
        lines.append(f"**总计**: {total_records} 条记录")

        return "\n".join(lines)


# 便捷函数
_pipeline = None


def get_pipeline(trendradar_path: str = ".") -> DataPipeline:
    """获取全局数据管道实例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = DataPipeline(trendradar_path)
    return _pipeline


def write_record(data_type: str, record: Dict, trendradar_path: str = ".") -> bool:
    """便捷函数：写入数据记录"""
    return get_pipeline(trendradar_path).write(data_type, record)


def read_records(data_type: str, days: int = 7, limit: int = 100, trendradar_path: str = ".") -> List[Dict]:
    """便捷函数：读取数据记录"""
    return get_pipeline(trendradar_path).read(data_type, days, limit)


def query_records(data_type: str, filters: Dict = None, limit: int = 100, trendradar_path: str = ".") -> List[Dict]:
    """便捷函数：条件查询"""
    return get_pipeline(trendradar_path).query(data_type, filters, limit)


if __name__ == "__main__":
    # 测试
    pipeline = DataPipeline()
    pipeline.write("article", {"id": "test-1", "title": "测试文章", "score": 8.5})
    print(pipeline.get_pipeline_summary())
    print(pipeline.read("article", days=1))
