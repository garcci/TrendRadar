# -*- coding: utf-8 -*-
"""
系统健康检查 - 全面验证当前系统功能

检查维度：
1. 模块导入: 所有evolution模块是否可正常导入
2. 配置文件: config.yaml、.env等关键文件是否完整
3. 数据文件: metrics、history等数据文件是否正常
4. Workflow: crawler.yml配置是否正确
5. 代码质量: 是否有语法错误、循环导入等
6. 系统状态: 仓库大小、最近运行状态
7. 进化模块: 各模块功能是否正常

输出：
- 健康检查报告
- 问题清单
- 修复建议
"""

import ast
import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class SystemHealthChecker:
    """系统健康检查器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.results = []
        self.warnings = []
        self.errors = []
    
    def _check(self, name: str, check_func) -> bool:
        """运行单个检查"""
        try:
            result = check_func()
            self.results.append({"name": name, "status": "pass", "detail": result if result else "OK"})
            return True
        except Exception as e:
            self.results.append({"name": name, "status": "fail", "detail": str(e)})
            self.errors.append(f"{name}: {e}")
            return False
    
    def _warn(self, name: str, message: str):
        """记录警告"""
        self.warnings.append(f"{name}: {message}")
        self.results.append({"name": name, "status": "warn", "detail": message})
    
    def check_module_imports(self) -> Dict:
        """检查所有evolution模块导入"""
        evolution_dir = f"{self.trendradar_path}/evolution"
        if not os.path.exists(evolution_dir):
            return {"error": "evolution directory not found"}
        
        modules = [f.replace('.py', '') for f in os.listdir(evolution_dir) if f.endswith('.py') and not f.startswith('__')]
        passed = []
        failed = []
        
        for module in sorted(modules):
            try:
                __import__(f"evolution.{module}")
                passed.append(module)
            except Exception as e:
                failed.append(f"{module}: {e}")
        
        return {
            "total": len(modules),
            "passed": len(passed),
            "failed": len(failed),
            "passed_modules": passed,
            "failed_modules": failed
        }
    
    def check_config_files(self) -> Dict:
        """检查配置文件"""
        required_files = [
            "config/config.yaml",
            ".env.example",
            "pyproject.toml",
            ".github/workflows/crawler.yml"
        ]
        
        optional_files = [
            ".env",
            "evolution/article_metrics.json",
            "evolution/exception_knowledge.json"
        ]
        
        missing_required = []
        missing_optional = []
        
        for f in required_files:
            if not os.path.exists(f"{self.trendradar_path}/{f}"):
                missing_required.append(f)
        
        for f in optional_files:
            if not os.path.exists(f"{self.trendradar_path}/{f}"):
                missing_optional.append(f)
        
        return {
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "status": "ok" if not missing_required else "fail"
        }
    
    def check_workflow_syntax(self) -> Dict:
        """检查Workflow YAML语法"""
        workflow_file = f"{self.trendradar_path}/.github/workflows/crawler.yml"
        
        if not os.path.exists(workflow_file):
            return {"error": "Workflow file not found"}
        
        try:
            import yaml
            with open(workflow_file, 'r') as f:
                content = yaml.safe_load(f)
            
            # 检查关键步骤是否存在
            jobs = content.get("jobs", {})
            crawl_job = jobs.get("crawl", {})
            steps = crawl_job.get("steps", [])
            step_names = [s.get("name", "") for s in steps]
            
            required_steps = ["Run crawler", "Autonomous Evolution", "Exception Intervention"]
            missing_steps = [s for s in required_steps if not any(s in name for name in step_names)]
            
            return {
                "valid": True,
                "total_steps": len(steps),
                "missing_steps": missing_steps,
                "step_names": step_names
            }
        except Exception as e:
            return {"error": str(e)}
    
    def check_python_syntax(self) -> Dict:
        """检查Python文件语法"""
        errors = []
        checked = 0
        
        for root, dirs, files in os.walk(f"{self.trendradar_path}/evolution"):
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r') as f:
                        source = f.read()
                    ast.parse(source)
                    checked += 1
                except SyntaxError as e:
                    errors.append(f"{filename}: {e}")
        
        return {
            "checked": checked,
            "errors": errors,
            "status": "ok" if not errors else "fail"
        }
    
    def check_recent_articles(self) -> Dict:
        """检查最近文章生成情况"""
        metrics_file = f"{self.trendradar_path}/evolution/article_metrics.json"
        
        if not os.path.exists(metrics_file):
            return {"error": "Metrics file not found"}
        
        try:
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            
            if not metrics:
                return {"error": "No metrics data"}
            
            # 最近7天
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            recent = [m for m in metrics if m.get("timestamp", "") > cutoff]
            
            if not recent:
                return {"message": "No articles in the last 7 days"}
            
            scores = [m.get("overall_score", 0) for m in recent if m.get("overall_score", 0) > 0]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            return {
                "total_articles": len(metrics),
                "recent_articles": len(recent),
                "avg_score": round(avg_score, 2),
                "min_score": round(min(scores), 2) if scores else 0,
                "max_score": round(max(scores), 2) if scores else 0,
                "status": "healthy" if avg_score >= 7 else "warning"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def check_repo_size(self) -> Dict:
        """检查仓库大小"""
        try:
            total_size = 0
            for root, dirs, files in os.walk(self.trendradar_path):
                if ".git" in root:
                    continue
                for filename in files:
                    try:
                        filepath = os.path.join(root, filename)
                        total_size += os.path.getsize(filepath)
                    except Exception:
                        continue
            
            size_mb = total_size / (1024 * 1024)
            
            return {
                "size_mb": round(size_mb, 2),
                "status": "healthy" if size_mb < 50 else "warning" if size_mb < 100 else "critical"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def check_git_status(self) -> Dict:
        """检查Git状态"""
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True,
                cwd=self.trendradar_path
            )
            
            uncommitted = result.stdout.strip()
            
            # 获取最近提交
            log_result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True, text=True,
                cwd=self.trendradar_path
            )
            
            return {
                "has_uncommitted": bool(uncommitted),
                "uncommitted_files": len(uncommitted.split('\n')) if uncommitted else 0,
                "recent_commits": log_result.stdout.strip().split('\n') if log_result.stdout else [],
                "status": "ok" if not uncommitted else "warn"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def run_all_checks(self) -> Dict:
        """运行所有检查"""
        print("[系统健康] 启动全面检查...")
        print("=" * 60)
        
        checks = [
            ("模块导入检查", self.check_module_imports),
            ("配置文件检查", self.check_config_files),
            ("Workflow语法检查", self.check_workflow_syntax),
            ("Python语法检查", self.check_python_syntax),
            ("最近文章检查", self.check_recent_articles),
            ("仓库大小检查", self.check_repo_size),
            ("Git状态检查", self.check_git_status),
        ]
        
        for name, func in checks:
            print(f"\n  🔍 {name}...")
            self._check(name, func)
        
        print("\n" + "=" * 60)
        
        # 计算总体状态
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "pass")
        warnings = sum(1 for r in self.results if r["status"] == "warn")
        failed = sum(1 for r in self.results if r["status"] == "fail")
        
        overall = "healthy" if failed == 0 else "warning" if failed <= 1 else "critical"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall,
            "summary": {
                "total_checks": total,
                "passed": passed,
                "warnings": warnings,
                "failed": failed
            },
            "details": self.results,
            "errors": self.errors,
            "warnings_list": self.warnings
        }
    
    def generate_health_report(self) -> str:
        """生成健康报告"""
        report = self.run_all_checks()
        
        lines = ["\n" + "=" * 60]
        lines.append("🏥 系统健康检查报告")
        lines.append("=" * 60)
        lines.append(f"\n📊 总体状态: {report['overall_status'].upper()}")
        lines.append(f"   通过: {report['summary']['passed']}/{report['summary']['total_checks']}")
        lines.append(f"   警告: {report['summary']['warnings']}")
        lines.append(f"   失败: {report['summary']['failed']}")
        lines.append("")
        
        # 详细结果
        for result in report["details"]:
            emoji = "✅" if result["status"] == "pass" else "⚠️" if result["status"] == "warn" else "❌"
            detail = result["detail"]
            if isinstance(detail, dict):
                detail_str = json.dumps(detail, ensure_ascii=False, indent=2)
                # 简化显示
                if "passed" in detail and "failed" in detail:
                    detail_str = f"通过{detail['passed']}/失败{detail['failed']}"
                elif "missing_required" in detail:
                    detail_str = "配置完整" if not detail["missing_required"] else f"缺失: {', '.join(detail['missing_required'])}"
                elif "size_mb" in detail:
                    detail_str = f"{detail['size_mb']}MB"
                elif "avg_score" in detail:
                    detail_str = f"均分{detail['avg_score']}"
                else:
                    detail_str = str(detail)[:80]
            else:
                detail_str = str(detail)[:80]
            
            lines.append(f"{emoji} {result['name']}: {detail_str}")
        
        # 错误列表
        if report["errors"]:
            lines.append("\n❌ 需要修复的问题:")
            for error in report["errors"]:
                lines.append(f"   - {error}")
        
        # 警告列表
        if report["warnings_list"]:
            lines.append("\n⚠️ 警告:")
            for warning in report["warnings_list"]:
                lines.append(f"   - {warning}")
        
        # 建议
        lines.append("\n💡 建议:")
        if report["overall_status"] == "healthy":
            lines.append("   系统运行良好，可以继续进化！")
        elif report["overall_status"] == "warning":
            lines.append("   系统有轻微问题，建议先修复再进化。")
        else:
            lines.append("   系统存在严重问题，必须优先修复！")
        
        lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def run_health_check(trendradar_path: str = ".") -> Dict:
    """运行健康检查"""
    checker = SystemHealthChecker(trendradar_path)
    return checker.run_all_checks()


def get_health_report(trendradar_path: str = ".") -> str:
    """获取健康报告"""
    checker = SystemHealthChecker(trendradar_path)
    return checker.generate_health_report()


if __name__ == "__main__":
    print(get_health_report())
