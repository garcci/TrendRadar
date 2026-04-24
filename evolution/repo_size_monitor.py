# -*- coding: utf-8 -*-
"""
仓库体积监控 - Lv36

核心理念：
1. 持续监控仓库体积，防止无限制增长
2. 识别大文件和增长趋势
3. 设定体积阈值，超标时预警
4. 为Lv37归档和Lv38清理提供数据基础

监控维度：
- 总仓库大小
- .git目录大小（历史记录）
- 大文件扫描（>100KB）
- 文件类型分布
- 增长趋势（对比上次记录）

阈值设定：
- 警告: 50MB
- 严重: 100MB
- GitHub免费限制: 1GB（软限制）

输出：
- 体积报告
- 大文件清单
- 增长预警
"""

import json
import os
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class RepoSizeMonitor:
    """仓库体积监控器"""
    
    # 体积阈值（MB）
    SIZE_THRESHOLDS = {
        "healthy": 20,
        "warning": 50,
        "critical": 100,
        "github_limit": 1024  # 1GB
    }
    
    # 大文件阈值（KB）
    BIG_FILE_THRESHOLD = 100  # 100KB
    
    # 需要监控的文件类型
    TRACKED_EXTENSIONS = {
        ".db": "SQLite数据库",
        ".sqlite": "SQLite数据库",
        ".png": "PNG图片",
        ".jpg": "JPG图片",
        ".jpeg": "JPG图片",
        ".gif": "GIF图片",
        ".mp4": "视频",
        ".mp3": "音频",
        ".zip": "压缩包",
        ".tar": "压缩包",
        ".gz": "压缩包",
        ".lock": "锁定文件",
        ".json": "JSON数据",
        ".log": "日志文件"
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.history_file = f"{trendradar_path}/evolution/repo_size_history.json"
        self.report_file = f"{trendradar_path}/evolution/repo_size_report.json"
    
    def _run_command(self, cmd: List[str]) -> str:
        """运行shell命令"""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=self.trendradar_path, timeout=30
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    def get_total_size(self) -> int:
        """获取仓库总大小（字节）"""
        output = self._run_command(["du", "-sb", "."])
        try:
            return int(output.split()[0])
        except Exception:
            return 0
    
    def get_git_size(self) -> int:
        """获取.git目录大小（字节）"""
        git_dir = f"{self.trendradar_path}/.git"
        if not os.path.exists(git_dir):
            return 0
        
        output = self._run_command(["du", "-sb", ".git"])
        try:
            return int(output.split()[0])
        except Exception:
            return 0
    
    def scan_big_files(self, threshold_kb: int = 100) -> List[Dict]:
        """扫描大文件"""
        big_files = []
        
        for root, dirs, files in os.walk(self.trendradar_path):
            # 跳过.git目录
            if ".git" in root:
                continue
            
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    size = os.path.getsize(filepath)
                    size_kb = size / 1024
                    
                    if size_kb >= threshold_kb:
                        rel_path = os.path.relpath(filepath, self.trendradar_path)
                        ext = os.path.splitext(filename)[1].lower()
                        
                        big_files.append({
                            "path": rel_path,
                            "size_kb": round(size_kb, 1),
                            "size_mb": round(size_kb / 1024, 2),
                            "type": self.TRACKED_EXTENSIONS.get(ext, "其他"),
                            "extension": ext
                        })
                except Exception:
                    continue
        
        # 按大小排序
        big_files.sort(key=lambda x: -x["size_kb"])
        return big_files
    
    def analyze_file_distribution(self) -> Dict:
        """分析文件类型分布"""
        type_sizes = defaultdict(lambda: {"count": 0, "total_kb": 0})
        
        for root, dirs, files in os.walk(self.trendradar_path):
            if ".git" in root:
                continue
            
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    size_kb = os.path.getsize(filepath) / 1024
                    ext = os.path.splitext(filename)[1].lower()
                    file_type = self.TRACKED_EXTENSIONS.get(ext, "其他")
                    
                    type_sizes[file_type]["count"] += 1
                    type_sizes[file_type]["total_kb"] += size_kb
                except Exception:
                    continue
        
        # 转换为列表并排序
        distribution = []
        for file_type, data in sorted(type_sizes.items(), key=lambda x: -x[1]["total_kb"]):
            distribution.append({
                "type": file_type,
                "count": data["count"],
                "total_kb": round(data["total_kb"], 1),
                "total_mb": round(data["total_kb"] / 1024, 2),
                "percentage": 0  # 稍后计算
            })
        
        # 计算百分比
        total_kb = sum(d["total_kb"] for d in distribution)
        for d in distribution:
            d["percentage"] = round(d["total_kb"] / total_kb * 100, 1) if total_kb > 0 else 0
        
        return {
            "total_kb": round(total_kb, 1),
            "types": distribution[:10]  # 只返回前10
        }
    
    def check_growth_trend(self, current_size_mb: float) -> Dict:
        """检查增长趋势"""
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            except Exception:
                pass
        
        # 添加当前记录
        record = {
            "timestamp": datetime.now().isoformat(),
            "size_mb": round(current_size_mb, 2)
        }
        history.append(record)
        history = history[-30:]  # 保留最近30条
        
        # 保存
        with open(self.history_file, 'w') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        if len(history) < 2:
            return {"trend": "first_record", "growth_rate": 0}
        
        # 计算增长趋势
        first = history[0]["size_mb"]
        last = history[-1]["size_mb"]
        growth = last - first
        
        # 计算日均增长
        try:
            first_dt = datetime.fromisoformat(history[0]["timestamp"])
            last_dt = datetime.fromisoformat(history[-1]["timestamp"])
            days = max(1, (last_dt - first_dt).days)
            daily_growth = growth / days
        except Exception:
            daily_growth = 0
        
        trend = "increasing" if growth > 1 else "decreasing" if growth < -1 else "stable"
        
        return {
            "trend": trend,
            "growth_mb": round(growth, 2),
            "daily_growth_mb": round(daily_growth, 2),
            "records_count": len(history),
            "days_tracked": days if 'days' in dir() else 0
        }
    
    def generate_size_report(self) -> Dict:
        """生成体积报告"""
        total_size = self.get_total_size()
        git_size = self.get_git_size()
        total_mb = total_size / (1024 * 1024)
        git_mb = git_size / (1024 * 1024)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_size_mb": round(total_mb, 2),
            "git_size_mb": round(git_mb, 2),
            "git_percentage": round(git_mb / total_mb * 100, 1) if total_mb > 0 else 0,
            "threshold": self.SIZE_THRESHOLDS
        }
        
        # 大文件扫描
        big_files = self.scan_big_files(self.BIG_FILE_THRESHOLD)
        report["big_files"] = big_files[:20]  # 只返回前20
        report["big_files_count"] = len(big_files)
        
        # 文件分布
        distribution = self.analyze_file_distribution()
        report["file_distribution"] = distribution
        
        # 增长趋势
        growth = self.check_growth_trend(total_mb)
        report["growth_trend"] = growth
        
        # 状态评估
        if total_mb >= self.SIZE_THRESHOLDS["critical"]:
            report["status"] = "critical"
            report["status_text"] = "严重超标"
        elif total_mb >= self.SIZE_THRESHOLDS["warning"]:
            report["status"] = "warning"
            report["status_text"] = "警告"
        elif total_mb >= self.SIZE_THRESHOLDS["healthy"]:
            report["status"] = "caution"
            report["status_text"] = "偏大"
        else:
            report["status"] = "healthy"
            report["status_text"] = "健康"
        
        # 保存报告
        reports = []
        if os.path.exists(self.report_file):
            try:
                with open(self.report_file, 'r') as f:
                    reports = json.load(f)
            except Exception:
                pass
        reports.append(report)
        reports = reports[-10:]
        
        with open(self.report_file, 'w') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        
        return report
    
    def generate_size_insight(self) -> str:
        """生成体积洞察（用于Prompt注入）"""
        report = self.generate_size_report()
        
        lines = ["\n### 📦 仓库体积监控\n"]
        
        status_emoji = {"critical": "🔴", "warning": "🟡", "caution": "🟠", "healthy": "🟢"}
        emoji = status_emoji.get(report["status"], "⚪")
        lines.append(f"**仓库状态**: {emoji} {report['status_text']} ({report['total_size_mb']}MB)")
        lines.append(f"**.git占比**: {report['git_percentage']}% ({report['git_size_mb']}MB)")
        lines.append("")
        
        # 大文件
        big_files = report.get("big_files", [])
        if big_files:
            lines.append(f"**大文件** ({report['big_files_count']}个):")
            for f in big_files[:5]:
                lines.append(f"- 📄 {f['path']}: {f['size_kb']}KB ({f['type']})")
            lines.append("")
        
        # 增长趋势
        growth = report.get("growth_trend", {})
        if growth.get("trend") == "increasing":
            lines.append(f"⚠️ **体积增长**: +{growth['growth_mb']}MB (日均+{growth['daily_growth_mb']}MB)")
            lines.append("")
        
        # 建议
        if report["status"] in ["warning", "critical"]:
            lines.append("**建议**: 仓库体积偏大，建议执行数据归档和清理。")
        elif big_files:
            lines.append("**建议**: 关注大文件，考虑将数据库/图片移出Git仓库。")
        else:
            lines.append("**建议**: 仓库体积健康，继续保持。")
        lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def get_repo_size_report(trendradar_path: str = ".") -> Dict:
    """获取仓库体积报告"""
    monitor = RepoSizeMonitor(trendradar_path)
    return monitor.generate_size_report()


def get_repo_size_insight(trendradar_path: str = ".") -> str:
    """获取仓库体积洞察"""
    monitor = RepoSizeMonitor(trendradar_path)
    return monitor.generate_size_insight()


if __name__ == "__main__":
    monitor = RepoSizeMonitor()
    report = monitor.generate_size_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
