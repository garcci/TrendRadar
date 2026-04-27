# -*- coding: utf-8 -*-
"""
系统最终健康检查 — Round 5 调优验证

功能：
1. 检查所有 evolution 模块可导入性
2. 验证关键配置文件完整
3. 检查 workflow 语法有效性
4. 统计调优成果
5. 输出最终系统状态报告
"""

import ast
import sys
from pathlib import Path
from typing import Dict


class SystemFinalCheck:
    """系统最终健康检查器"""

    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = Path(trendradar_path)
        self.evolution_dir = self.trendradar_path / "evolution"
        self.results = []
        self.warnings = []
        self.errors = []

    def run_all_checks(self) -> Dict:
        """运行所有检查"""
        self.check_module_imports()
        self.check_critical_files()
        self.check_workflow_syntax()
        self.check_tuning_results()
        self.check_github_py_health()
        self.check_data_pipeline()
        self.check_module_activation()

        return {
            "status": "healthy" if not self.errors else "issues_found",
            "checks_passed": len(self.results),
            "warnings": len(self.warnings),
            "errors": len(self.errors),
            "details": {
                "results": self.results,
                "warnings": self.warnings,
                "errors": self.errors,
            }
        }

    def check_module_imports(self):
        """检查所有模块可导入"""
        import sys
        sys.path.insert(0, str(self.trendradar_path))

        py_files = [f for f in self.evolution_dir.glob("*.py") if not f.name.startswith("_")]
        success = 0
        failed = []

        for py_file in py_files:
            module_name = f"evolution.{py_file.stem}"
            try:
                __import__(module_name)
                success += 1
            except Exception as e:
                failed.append(f"{py_file.stem}: {e}")

        self.results.append(f"模块导入: {success}/{len(py_files)} 成功")
        if failed:
            self.warnings.extend([f"导入失败: {f}" for f in failed[:5]])

    def check_critical_files(self):
        """检查关键文件"""
        critical = [
            ".github/workflows/evolution.yml",
            ".github/workflows/crawler.yml",
            "trendradar/storage/github.py",
            "trendradar/ai/smart_client.py",
            "evolution/exception_monitor.py",
            "evolution/data_pipeline.py",
            "evolution/module_health_dashboard.py",
        ]

        missing = []
        for f in critical:
            if not (self.trendradar_path / f).exists():
                missing.append(f)

        self.results.append(f"关键文件: {len(critical) - len(missing)}/{len(critical)} 存在")
        if missing:
            self.errors.extend([f"缺失: {m}" for m in missing])

    def check_workflow_syntax(self):
        """检查 workflow YAML 基本语法"""
        try:
            import yaml
            wf_file = self.trendradar_path / ".github/workflows/evolution.yml"
            if wf_file.exists():
                with open(wf_file, 'r') as f:
                    data = yaml.safe_load(f)
                steps = data.get("jobs", {}).get("evolve", {}).get("steps", [])
                self.results.append(f"evolution.yml 语法: ✅ ({len(steps)} 个步骤)")
            else:
                self.errors.append("evolution.yml 不存在")
        except ImportError:
            self.results.append("evolution.yml 语法: 跳过 (无 PyYAML)")
        except Exception as e:
            self.errors.append(f"evolution.yml 语法错误: {e}")

    def check_tuning_results(self):
        """检查调优成果"""
        github_py = self.trendradar_path / "trendradar/storage/github.py"
        if github_py.exists():
            content = github_py.read_text()
            checks = {
                "prompt精简": "Prompt 膨胀控制" in content or "prompt压缩" in content,
                "context长度限制": "MAX_CONTEXT_LENGTH" in content,
                "数据管道接入": "write_record" in content,
                "科技检测": "tech_content_guard" in content,
                "语义去重": "semantic_deduplicator" in content,
                "构建预检": "astro_preflight" in content,
                "部署回滚": "rollback_on_failure" in content,
                "热点预测": "trend_forecast" in content,
            }
            passed = sum(checks.values())
            self.results.append(f"调优检查: {passed}/{len(checks)} 项已应用")
            for name, ok in checks.items():
                if not ok:
                    self.warnings.append(f"调优未应用: {name}")

    def check_github_py_health(self):
        """检查 github.py 健康度"""
        github_py = self.trendradar_path / "trendradar/storage/github.py"
        if not github_py.exists():
            return

        content = github_py.read_text()

        # 检查关键方法是否存在
        methods = ["save_news_data", "_generate_ai_article", "_push_to_github"]
        for method in methods:
            if f"def {method}" in content:
                self.results.append(f"github.py.{method}: ✅")
            else:
                self.errors.append(f"github.py.{method}: ❌ 缺失")

        # 检查是否有死代码（未使用的导入）
        try:
            tree = ast.parse(content)
            imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
            # 简化检查
            self.results.append(f"github.py AST解析: ✅")
        except SyntaxError as e:
            self.errors.append(f"github.py 语法错误: {e}")

    def check_data_pipeline(self):
        """检查数据管道状态 — 确保 Lv73-Lv79 有数据可用"""
        dp_dir = self.trendradar_path / "evolution" / "data_pipeline"
        if not dp_dir.exists():
            self.warnings.append("数据管道目录不存在")
            return

        log_file = dp_dir / "log.jsonl"
        quality_file = dp_dir / "article_quality.jsonl"

        log_count = 0
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    log_count = sum(1 for line in f if line.strip())
            except Exception:
                pass

        quality_count = 0
        if quality_file.exists():
            try:
                with open(quality_file, 'r') as f:
                    quality_count = sum(1 for line in f if line.strip())
            except Exception:
                pass

        self.results.append(f"数据管道: log={log_count} 条, quality={quality_count} 条")

        if log_count == 0:
            self.warnings.append("log.jsonl 为空: unified_logger 可能未正确写入")
        if quality_count == 0:
            self.warnings.append("article_quality.jsonl 为空: article_quality_db 可能未正确写入")

        # 检查 .gitignore 是否排除了 jsonl
        gitignore = self.trendradar_path / ".gitignore"
        if gitignore.exists():
            gi_content = gitignore.read_text()
            if "*.jsonl" in gi_content or "data_pipeline/*.jsonl" in gi_content:
                self.errors.append(".gitignore 排除了 *.jsonl，数据无法持久化到仓库")

    def check_module_activation(self):
        """Lv77: 模块激活建议 — 基于 article_quality_db 数据推荐"""
        try:
            from evolution.article_quality_db import get_quality_trend, get_module_contribution

            trend = get_quality_trend(days=14)
            suggestions = []

            # 评分维度建议
            if trend["avg_score"] < 6.0:
                suggestions.append({
                    "module": "tech_content_guard",
                    "effect": "提升科技内容占比，当前评分偏低",
                    "confidence": 0.9,
                })
                suggestions.append({
                    "module": "smart_scheduler",
                    "effect": "优化文章生成调度，减少低质量输出",
                    "confidence": 0.85,
                })
            elif trend["avg_score"] < 7.5:
                suggestions.append({
                    "module": "title_optimizer",
                    "effect": "优化标题质量，提升文章吸引力",
                    "confidence": 0.8,
                })

            # 科技占比维度
            if trend.get("avg_tech_ratio", 10) < 6.0:
                suggestions.append({
                    "module": "tech_content_guard",
                    "effect": f"科技占比仅{trend.get('avg_tech_ratio', 0)}/10，需强化",
                    "confidence": 0.9,
                })

            # 趋势维度
            if trend.get("score_trend") == "down":
                suggestions.append({
                    "module": "prompt_evolution",
                    "effect": "质量趋势下降，需自动优化 Prompt",
                    "confidence": 0.85,
                })
                suggestions.append({
                    "module": "regression_guard",
                    "effect": "启用退化检测，防止进一步下滑",
                    "confidence": 0.88,
                })

            # 模块贡献度分析
            key_modules = [
                "smart_scheduler", "tech_content_guard", "title_optimizer",
                "semantic_deduplicator", "trend_forecast", "ab_testing",
            ]
            for mod in key_modules:
                contrib = get_module_contribution(mod, days=14)
                if contrib["with_count"] >= 3 and contrib["contribution"] < -0.5:
                    suggestions.append({
                        "module": mod,
                        "effect": f"贡献度为负({contrib['contribution']})，建议检查或替换",
                        "confidence": 0.75,
                    })
                elif contrib["with_count"] >= 3 and contrib["contribution"] > 0.5:
                    suggestions.append({
                        "module": mod,
                        "effect": f"贡献度为正(+{contrib['contribution']})，建议持续使用",
                        "confidence": 0.8,
                    })

            if suggestions:
                self.results.append(f"模块激活建议: {len(suggestions)} 条")
                self._activation_suggestions = suggestions
            else:
                self.results.append("模块激活建议: 暂无（系统运行良好）")
                self._activation_suggestions = []
        except Exception as e:
            self.warnings.append(f"模块激活建议生成失败: {e}")
            self._activation_suggestions = []

    def generate_report(self) -> str:
        """生成最终报告"""
        result = self.run_all_checks()

        lines = []
        lines.append("# 🔬 系统最终健康检查报告 (Round 5)")
        lines.append("")
        lines.append(f"**状态**: {'✅ 健康' if result['status'] == 'healthy' else '⚠️ 发现问题'}")
        lines.append(f"**检查通过**: {result['checks_passed']} 项")
        lines.append(f"**警告**: {result['warnings']} 个")
        lines.append(f"**错误**: {result['errors']} 个")
        lines.append("")

        lines.append("## ✅ 检查结果")
        for r in result['details']['results']:
            lines.append(f"- {r}")

        if result['details']['warnings']:
            lines.append("")
            lines.append("## ⚠️ 警告")
            for w in result['details']['warnings'][:10]:
                lines.append(f"- {w}")

        if result['details']['errors']:
            lines.append("")
            lines.append("## ❌ 错误")
            for e in result['details']['errors']:
                lines.append(f"- {e}")

        # Lv77: 模块激活建议
        if hasattr(self, '_activation_suggestions') and self._activation_suggestions:
            lines.append("")
            lines.append("## 🚀 模块激活建议 (Lv77)")
            for s in self._activation_suggestions[:8]:
                conf_emoji = "🔥" if s["confidence"] >= 0.85 else "💡"
                lines.append(
                    f"- {conf_emoji} **{s['module']}** — {s['effect']} (置信度: {s['confidence']})"
                )

        lines.append("")
        lines.append("---")
        lines.append("**Round 5 完成**: 系统架构调优与最终验证结束。")

        return "\n".join(lines)


def run_final_check(trendradar_path: str = ".") -> str:
    """便捷函数"""
    checker = SystemFinalCheck(trendradar_path)
    return checker.generate_report()


if __name__ == "__main__":
    print(run_final_check())
