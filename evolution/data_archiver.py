# -*- coding: utf-8 -*-
"""
历史数据归档 - Lv37

核心理念：
1. 自动归档旧的历史数据文件
2. 压缩大数据以节省空间
3. 管理归档生命周期（保留策略）
4. 支持按需恢复归档数据

归档策略：
- metrics数据: 保留最近60天，旧数据压缩归档
- 异常知识库: 保留最近100条，旧数据归档
- 体积报告: 保留最近30份，旧数据归档
- 数据库文件: 保留最近7天，旧数据归档
- 图片文件: 超过500KB的图片压缩或移出仓库

归档格式：
- JSON数据 → 压缩为 .json.gz
- 数据库 → 压缩为 .db.gz
- 图片 → 压缩质量或移出仓库

输出：
- 归档报告
- 节省空间统计
"""

import gzip
import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class DataArchiver:
    """数据归档器"""
    
    # 归档配置
    ARCHIVE_CONFIG = {
        "article_metrics": {
            "file": "evolution/article_metrics.json",
            "retain_days": 60,
            "compress": True
        },
        "exception_knowledge": {
            "file": "evolution/exception_knowledge.json",
            "retain_count": 100,
            "compress": True
        },
        "repo_size_history": {
            "file": "evolution/repo_size_history.json",
            "retain_count": 30,
            "compress": True
        },
        "evolution_reports": {
            "file": "evolution/evolution_effect_report.json",
            "retain_count": 10,
            "compress": True
        },
        "heal_logs": {
            "file": "evolution/heal_log.json",
            "retain_count": 50,
            "compress": True
        },
        "output_db": {
            "dir": "output/news",
            "retain_days": 7,
            "compress": True
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.archive_dir = f"{trendradar_path}/.archive"
        self.report_file = f"{trendradar_path}/evolution/archive_report.json"
        
        # 确保归档目录存在
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def _ensure_dir(self, path: str):
        """确保目录存在"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
    
    def compress_file(self, source_path: str, remove_original: bool = False) -> Dict:
        """压缩单个文件"""
        if not os.path.exists(source_path):
            return {"status": "skipped", "reason": "file_not_found"}
        
        original_size = os.path.getsize(source_path)
        archive_path = f"{self.archive_dir}/{os.path.basename(source_path)}.{datetime.now().strftime('%Y%m%d')}.gz"
        
        try:
            with open(source_path, 'rb') as f_in:
                with gzip.open(archive_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            compressed_size = os.path.getsize(archive_path)
            savings = original_size - compressed_size
            
            if remove_original:
                os.remove(source_path)
            
            return {
                "status": "success",
                "original_path": source_path,
                "archive_path": archive_path,
                "original_size_kb": round(original_size / 1024, 1),
                "compressed_size_kb": round(compressed_size / 1024, 1),
                "savings_kb": round(savings / 1024, 1),
                "savings_pct": round(savings / original_size * 100, 1) if original_size > 0 else 0
            }
        except Exception as e:
            return {"status": "failed", "reason": str(e)}
    
    def archive_json_by_age(self, file_path: str, retain_days: int = 60) -> Dict:
        """按时间归档JSON文件中的旧数据"""
        full_path = f"{self.trendradar_path}/{file_path}"
        
        if not os.path.exists(full_path):
            return {"status": "skipped", "reason": "file_not_found"}
        
        try:
            with open(full_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return {"status": "failed", "reason": f"parse_error: {e}"}
        
        # 如果数据是列表，按时间过滤
        if isinstance(data, list):
            cutoff = (datetime.now() - timedelta(days=retain_days)).isoformat()
            
            recent_data = []
            old_data = []
            
            for item in data:
                timestamp = item.get("timestamp", "") if isinstance(item, dict) else ""
                if timestamp and timestamp < cutoff:
                    old_data.append(item)
                else:
                    recent_data.append(item)
            
            if not old_data:
                return {"status": "skipped", "reason": "no_old_data"}
            
            # 保存最近数据回原文件
            with open(full_path, 'w') as f:
                json.dump(recent_data, f, ensure_ascii=False, indent=2)
            
            # 归档旧数据
            archive_name = f"{os.path.basename(file_path)}.{datetime.now().strftime('%Y%m')}.json"
            archive_path = f"{self.archive_dir}/{archive_name}"
            
            # 如果归档文件已存在，合并数据
            existing_old = []
            if os.path.exists(archive_path):
                try:
                    with open(archive_path, 'r') as f:
                        existing_old = json.load(f)
                except Exception:
                    pass
            
            combined = existing_old + old_data
            with open(archive_path, 'w') as f:
                json.dump(combined, f, ensure_ascii=False, indent=2)
            
            # 压缩归档
            compress_result = self.compress_file(archive_path, remove_original=True)
            
            return {
                "status": "success",
                "file": file_path,
                "retained_count": len(recent_data),
                "archived_count": len(old_data),
                "compress_result": compress_result
            }
        
        return {"status": "skipped", "reason": "not_a_list"}
    
    def archive_json_by_count(self, file_path: str, retain_count: int = 100) -> Dict:
        """按数量归档JSON文件中的旧数据"""
        full_path = f"{self.trendradar_path}/{file_path}"
        
        if not os.path.exists(full_path):
            return {"status": "skipped", "reason": "file_not_found"}
        
        try:
            with open(full_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return {"status": "failed", "reason": f"parse_error: {e}"}
        
        if isinstance(data, list) and len(data) > retain_count:
            recent_data = data[-retain_count:]
            old_data = data[:-retain_count]
            
            # 保存最近数据
            with open(full_path, 'w') as f:
                json.dump(recent_data, f, ensure_ascii=False, indent=2)
            
            # 归档旧数据
            archive_name = f"{os.path.basename(file_path)}.{datetime.now().strftime('%Y%m')}.json"
            archive_path = f"{self.archive_dir}/{archive_name}"
            
            with open(archive_path, 'w') as f:
                json.dump(old_data, f, ensure_ascii=False, indent=2)
            
            # 压缩归档
            compress_result = self.compress_file(archive_path, remove_original=True)
            
            return {
                "status": "success",
                "file": file_path,
                "retained_count": len(recent_data),
                "archived_count": len(old_data),
                "compress_result": compress_result
            }
        
        return {"status": "skipped", "reason": "under_limit"}
    
    def archive_old_databases(self, dir_path: str, retain_days: int = 7) -> Dict:
        """归档旧的数据库文件"""
        full_dir = f"{self.trendradar_path}/{dir_path}"
        
        if not os.path.exists(full_dir):
            return {"status": "skipped", "reason": "dir_not_found"}
        
        cutoff = (datetime.now() - timedelta(days=retain_days)).timestamp()
        archived = []
        
        for filename in os.listdir(full_dir):
            if not filename.endswith('.db'):
                continue
            
            filepath = os.path.join(full_dir, filename)
            try:
                mtime = os.path.getmtime(filepath)
                if mtime < cutoff:
                    result = self.compress_file(filepath, remove_original=True)
                    archived.append(result)
            except Exception as e:
                archived.append({"status": "failed", "file": filename, "reason": str(e)})
        
        total_savings = sum(a.get("savings_kb", 0) for a in archived if a.get("status") == "success")
        
        return {
            "status": "success",
            "dir": dir_path,
            "archived_count": len([a for a in archived if a.get("status") == "success"]),
            "total_savings_kb": round(total_savings, 1),
            "details": archived
        }
    
    def run_auto_archive(self) -> List[Dict]:
        """运行自动归档"""
        results = []
        
        print("[数据归档] 启动自动归档...")
        
        # 按时间归档metrics
        if "article_metrics" in self.ARCHIVE_CONFIG:
            cfg = self.ARCHIVE_CONFIG["article_metrics"]
            result = self.archive_json_by_age(cfg["file"], cfg["retain_days"])
            results.append(result)
            if result["status"] == "success":
                print(f"  ✅ 归档 {cfg['file']}: {result.get('archived_count', 0)} 条记录")
        
        # 按数量归档异常知识库
        if "exception_knowledge" in self.ARCHIVE_CONFIG:
            cfg = self.ARCHIVE_CONFIG["exception_knowledge"]
            result = self.archive_json_by_count(cfg["file"], cfg["retain_count"])
            results.append(result)
            if result["status"] == "success":
                print(f"  ✅ 归档 {cfg['file']}: {result.get('archived_count', 0)} 条记录")
        
        # 按数量归档体积历史
        if "repo_size_history" in self.ARCHIVE_CONFIG:
            cfg = self.ARCHIVE_CONFIG["repo_size_history"]
            result = self.archive_json_by_count(cfg["file"], cfg["retain_count"])
            results.append(result)
            if result["status"] == "success":
                print(f"  ✅ 归档 {cfg['file']}: {result.get('archived_count', 0)} 条记录")
        
        # 按数量归档进化报告
        if "evolution_reports" in self.ARCHIVE_CONFIG:
            cfg = self.ARCHIVE_CONFIG["evolution_reports"]
            result = self.archive_json_by_count(cfg["file"], cfg["retain_count"])
            results.append(result)
            if result["status"] == "success":
                print(f"  ✅ 归档 {cfg['file']}: {result.get('archived_count', 0)} 条记录")
        
        # 按数量归档修复日志
        if "heal_logs" in self.ARCHIVE_CONFIG:
            cfg = self.ARCHIVE_CONFIG["heal_logs"]
            result = self.archive_json_by_count(cfg["file"], cfg["retain_count"])
            results.append(result)
            if result["status"] == "success":
                print(f"  ✅ 归档 {cfg['file']}: {result.get('archived_count', 0)} 条记录")
        
        # 归档旧数据库
        if "output_db" in self.ARCHIVE_CONFIG:
            cfg = self.ARCHIVE_CONFIG["output_db"]
            result = self.archive_old_databases(cfg["dir"], cfg["retain_days"])
            results.append(result)
            if result["status"] == "success":
                print(f"  ✅ 归档 {cfg['dir']}: {result.get('archived_count', 0)} 个文件")
        
        print("[数据归档] 自动归档完成")
        return results
    
    def generate_archive_report(self, results: List[Dict]) -> str:
        """生成归档报告"""
        lines = ["\n### 📦 数据归档报告\n"]
        
        successful = [r for r in results if r.get("status") == "success"]
        skipped = [r for r in results if r.get("status") == "skipped"]
        
        if not successful:
            lines.append("**归档状态**: 没有需要归档的数据\n")
            return "\n".join(lines)
        
        total_archived = sum(r.get("archived_count", 0) for r in successful)
        total_savings = sum(
            r.get("compress_result", {}).get("savings_kb", 0) 
            for r in successful 
            if isinstance(r.get("compress_result"), dict)
        )
        
        lines.append(f"**归档统计**:")
        lines.append(f"- 成功归档: {len(successful)} 个文件")
        lines.append(f"- 归档数据量: {total_archived} 条记录/文件")
        lines.append(f"- 节省空间: {round(total_savings, 1)} KB")
        lines.append("")
        
        for result in successful:
            file_name = result.get("file", result.get("dir", "unknown"))
            lines.append(f"- ✅ {file_name}: {result.get('archived_count', 0)} 条归档")
        lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def run_auto_archive(trendradar_path: str = ".") -> List[Dict]:
    """运行自动归档"""
    archiver = DataArchiver(trendradar_path)
    return archiver.run_auto_archive()


def get_archive_report(trendradar_path: str = ".") -> str:
    """获取归档报告"""
    archiver = DataArchiver(trendradar_path)
    results = archiver.run_auto_archive()
    return archiver.generate_archive_report(results)


if __name__ == "__main__":
    archiver = DataArchiver()
    results = archiver.run_auto_archive()
    print(archiver.generate_archive_report(results))
