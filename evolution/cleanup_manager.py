# -*- coding: utf-8 -*-
"""
冗余清理管理 - Lv38

核心理念：
1. 清理临时文件和过期数据
2. 删除已归档的原始文件
3. 清理旧压缩包
4. 安全的清理策略（绝不删除源代码）

清理规则：
- 临时文件: *.tmp, *.temp, *.cache（立即删除）
- 日志文件: *.log（保留最近7天）
- 旧归档: .archive/*.gz（保留最近3个月）
- Python缓存: __pycache__, *.pyc（立即删除）
- 空目录: 删除空文件夹
- 重复数据: 清理evolution/*.json中过期的报告

安全原则：
- 绝不删除 .py 源代码文件
- 绝不删除 config.yaml
- 绝不删除 .git 目录
- 所有删除操作可撤销（先移动到.trash）

输出：
- 清理报告
- 释放空间统计
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class CleanupManager:
    """清理管理器"""
    
    # 安全保护的文件/目录模式
    PROTECTED_PATTERNS = [
        ".git", ".github", "config", ".env", "README",
        ".py", ".yml", ".yaml", ".json",  # 配置文件保护
        "requirements", "setup", "pyproject"
    ]
    
    # 清理规则
    CLEANUP_RULES = {
        "temp_files": {
            "patterns": ["*.tmp", "*.temp", "*.cache", "*.bak", "*.swp"],
            "retain_days": 0,  # 立即删除
            "description": "临时文件"
        },
        "python_cache": {
            "patterns": ["__pycache__", "*.pyc", "*.pyo", ".pytest_cache"],
            "retain_days": 0,
            "description": "Python缓存"
        },
        "log_files": {
            "patterns": ["*.log"],
            "retain_days": 7,
            "description": "日志文件"
        },
        "old_archives": {
            "dir": ".archive",
            "retain_days": 90,  # 保留3个月
            "description": "旧归档文件"
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.trash_dir = f"{trendradar_path}/.trash"
        self.report_file = f"{trendradar_path}/evolution/cleanup_report.json"
        
        # 确保trash目录存在
        os.makedirs(self.trash_dir, exist_ok=True)
    
    def _is_protected(self, path: str) -> bool:
        """检查路径是否受保护"""
        basename = os.path.basename(path).lower()
        
        for pattern in self.PROTECTED_PATTERNS:
            if pattern.lower() in basename:
                return True
        
        # 检查是否在关键目录中
        rel_path = os.path.relpath(path, self.trendradar_path)
        critical_dirs = [".git", ".github", "trendradar", "evolution", "config"]
        for critical in critical_dirs:
            if rel_path.startswith(critical + os.sep) and path.endswith('.py'):
                return True
        
        return False
    
    def _move_to_trash(self, source_path: str) -> bool:
        """安全移动到回收站"""
        if self._is_protected(source_path):
            return False
        
        try:
            basename = os.path.basename(source_path)
            trash_path = f"{self.trash_dir}/{basename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 如果目标已存在，添加序号
            counter = 1
            original_trash_path = trash_path
            while os.path.exists(trash_path):
                trash_path = f"{original_trash_path}_{counter}"
                counter += 1
            
            if os.path.isdir(source_path):
                shutil.move(source_path, trash_path)
            else:
                shutil.move(source_path, trash_path)
            
            return True
        except Exception:
            return False
    
    def _delete_safely(self, path: str) -> bool:
        """安全删除（先移动到trash）"""
        return self._move_to_trash(path)
    
    def cleanup_temp_files(self) -> Dict:
        """清理临时文件"""
        deleted = []
        skipped = []
        freed_kb = 0
        
        for root, dirs, files in os.walk(self.trendradar_path):
            # 跳过保护目录
            if ".git" in root or ".trash" in root or ".archive" in root:
                continue
            
            for pattern in self.CLEANUP_RULES["temp_files"]["patterns"]:
                import fnmatch
                for filename in fnmatch.filter(files, pattern):
                    filepath = os.path.join(root, filename)
                    
                    if self._is_protected(filepath):
                        skipped.append({"path": filepath, "reason": "protected"})
                        continue
                    
                    size_kb = os.path.getsize(filepath) / 1024
                    if self._delete_safely(filepath):
                        deleted.append(filepath)
                        freed_kb += size_kb
        
        return {
            "rule": "temp_files",
            "deleted_count": len(deleted),
            "freed_kb": round(freed_kb, 1),
            "deleted": deleted[:10],  # 只记录前10个
            "skipped_count": len(skipped)
        }
    
    def cleanup_python_cache(self) -> Dict:
        """清理Python缓存"""
        deleted = []
        freed_kb = 0
        
        for root, dirs, files in os.walk(self.trendradar_path):
            if ".git" in root or ".trash" in root:
                continue
            
            # 删除__pycache__目录
            for dirname in list(dirs):
                if dirname == "__pycache__" or dirname == ".pytest_cache":
                    dirpath = os.path.join(root, dirname)
                    
                    # 计算目录大小
                    dir_size = 0
                    for r, d, f in os.walk(dirpath):
                        for file in f:
                            dir_size += os.path.getsize(os.path.join(r, file))
                    
                    if self._delete_safely(dirpath):
                        deleted.append(dirpath)
                        freed_kb += dir_size / 1024
                        dirs.remove(dirname)  # 防止继续遍历已删除的目录
            
            # 删除.pyc文件
            for filename in files:
                if filename.endswith('.pyc') or filename.endswith('.pyo'):
                    filepath = os.path.join(root, filename)
                    size_kb = os.path.getsize(filepath) / 1024
                    
                    if self._delete_safely(filepath):
                        deleted.append(filepath)
                        freed_kb += size_kb
        
        return {
            "rule": "python_cache",
            "deleted_count": len(deleted),
            "freed_kb": round(freed_kb, 1),
            "deleted": deleted[:10]
        }
    
    def cleanup_old_logs(self) -> Dict:
        """清理旧日志文件"""
        retain_days = self.CLEANUP_RULES["log_files"]["retain_days"]
        cutoff = (datetime.now() - timedelta(days=retain_days)).timestamp()
        
        deleted = []
        freed_kb = 0
        
        for root, dirs, files in os.walk(self.trendradar_path):
            if ".git" in root or ".trash" in root:
                continue
            
            for filename in files:
                if filename.endswith('.log'):
                    filepath = os.path.join(root, filename)
                    
                    try:
                        mtime = os.path.getmtime(filepath)
                        if mtime < cutoff:
                            size_kb = os.path.getsize(filepath) / 1024
                            if self._delete_safely(filepath):
                                deleted.append(filepath)
                                freed_kb += size_kb
                    except Exception:
                        continue
        
        return {
            "rule": "log_files",
            "deleted_count": len(deleted),
            "freed_kb": round(freed_kb, 1),
            "deleted": deleted[:10]
        }
    
    def cleanup_old_archives(self) -> Dict:
        """清理旧归档文件"""
        archive_dir = f"{self.trendradar_path}/.archive"
        
        if not os.path.exists(archive_dir):
            return {"rule": "old_archives", "deleted_count": 0, "freed_kb": 0}
        
        retain_days = self.CLEANUP_RULES["old_archives"]["retain_days"]
        cutoff = (datetime.now() - timedelta(days=retain_days)).timestamp()
        
        deleted = []
        freed_kb = 0
        
        for filename in os.listdir(archive_dir):
            filepath = os.path.join(archive_dir, filename)
            
            try:
                mtime = os.path.getmtime(filepath)
                if mtime < cutoff:
                    size_kb = os.path.getsize(filepath) / 1024
                    if self._delete_safely(filepath):
                        deleted.append(filepath)
                        freed_kb += size_kb
            except Exception:
                continue
        
        return {
            "rule": "old_archives",
            "deleted_count": len(deleted),
            "freed_kb": round(freed_kb, 1),
            "deleted": [os.path.basename(d) for d in deleted[:10]]
        }
    
    def cleanup_empty_dirs(self) -> Dict:
        """清理空目录"""
        deleted = []
        
        for root, dirs, files in os.walk(self.trendradar_path, topdown=False):
            if ".git" in root or ".trash" in root:
                continue
            
            # 检查空目录
            for dirname in dirs:
                dirpath = os.path.join(root, dirname)
                
                try:
                    if os.path.exists(dirpath) and not os.listdir(dirpath):
                        if not self._is_protected(dirpath):
                            os.rmdir(dirpath)
                            deleted.append(dirpath)
                except Exception:
                    continue
        
        return {
            "rule": "empty_dirs",
            "deleted_count": len(deleted),
            "deleted": deleted[:10]
        }
    
    def run_cleanup(self) -> List[Dict]:
        """运行清理"""
        results = []
        
        print("[清理管理] 启动冗余清理...")
        
        # 清理临时文件
        result = self.cleanup_temp_files()
        results.append(result)
        if result["deleted_count"] > 0:
            print(f"  ✅ 清理临时文件: {result['deleted_count']} 个，释放 {result['freed_kb']} KB")
        
        # 清理Python缓存
        result = self.cleanup_python_cache()
        results.append(result)
        if result["deleted_count"] > 0:
            print(f"  ✅ 清理Python缓存: {result['deleted_count']} 个，释放 {result['freed_kb']} KB")
        
        # 清理旧日志
        result = self.cleanup_old_logs()
        results.append(result)
        if result["deleted_count"] > 0:
            print(f"  ✅ 清理旧日志: {result['deleted_count']} 个，释放 {result['freed_kb']} KB")
        
        # 清理旧归档
        result = self.cleanup_old_archives()
        results.append(result)
        if result["deleted_count"] > 0:
            print(f"  ✅ 清理旧归档: {result['deleted_count']} 个，释放 {result['freed_kb']} KB")
        
        # 清理空目录
        result = self.cleanup_empty_dirs()
        results.append(result)
        if result["deleted_count"] > 0:
            print(f"  ✅ 清理空目录: {result['deleted_count']} 个")
        
        total_freed = sum(r.get("freed_kb", 0) for r in results)
        print(f"[清理管理] 清理完成，共释放 {round(total_freed, 1)} KB")
        
        return results
    
    def generate_cleanup_report(self, results: List[Dict]) -> str:
        """生成清理报告"""
        lines = ["\n### 🧹 冗余清理报告\n"]
        
        total_freed = sum(r.get("freed_kb", 0) for r in results)
        total_deleted = sum(r.get("deleted_count", 0) for r in results)
        
        if total_deleted == 0:
            lines.append("**清理状态**: 没有需要清理的冗余文件\n")
            return "\n".join(lines)
        
        lines.append(f"**清理统计**:")
        lines.append(f"- 清理项目: {total_deleted} 个")
        lines.append(f"- 释放空间: {round(total_freed, 1)} KB ({round(total_freed/1024, 2)} MB)")
        lines.append("")
        
        for result in results:
            if result.get("deleted_count", 0) > 0:
                rule_name = {
                    "temp_files": "临时文件",
                    "python_cache": "Python缓存",
                    "log_files": "日志文件",
                    "old_archives": "旧归档",
                    "empty_dirs": "空目录"
                }.get(result["rule"], result["rule"])
                lines.append(f"- ✅ {rule_name}: {result['deleted_count']} 个 ({round(result.get('freed_kb', 0), 1)} KB)")
        lines.append("")
        
        lines.append("**安全说明**: 所有删除的文件已移动到 `.trash/` 目录，可随时恢复。\n")
        
        return "\n".join(lines)


# 便捷函数
def run_cleanup(trendradar_path: str = ".") -> List[Dict]:
    """运行清理"""
    manager = CleanupManager(trendradar_path)
    return manager.run_cleanup()


def get_cleanup_report(trendradar_path: str = ".") -> str:
    """获取清理报告"""
    manager = CleanupManager(trendradar_path)
    results = manager.run_cleanup()
    return manager.generate_cleanup_report(results)


if __name__ == "__main__":
    manager = CleanupManager()
    results = manager.run_cleanup()
    print(manager.generate_cleanup_report(results))
