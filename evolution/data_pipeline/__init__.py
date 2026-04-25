# -*- coding: utf-8 -*-
"""
evolution/data_pipeline/ 数据存储目录的入口

注意：实际的数据管道逻辑在 evolution/data_pipeline.py 中定义，
但导入路径 `from evolution.data_pipeline import write_record` 会优先匹配本目录。
因此在此重新导出 data_pipeline.py 的符号。
"""

import os
import importlib.util

# 使用完整文件路径加载 data_pipeline.py，避免与包名冲突
_dp_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dp_path = os.path.join(_dp_dir, "data_pipeline.py")

_spec = importlib.util.spec_from_file_location("_evolution_data_pipeline", _dp_path)
_dp_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dp_module)

DataPipeline = _dp_module.DataPipeline
write_record = _dp_module.write_record
read_records = _dp_module.read_records
query_records = _dp_module.query_records
get_pipeline = _dp_module.get_pipeline

__all__ = ["DataPipeline", "write_record", "read_records", "query_records", "get_pipeline"]
