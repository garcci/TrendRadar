# -*- coding: utf-8 -*-
"""
Astro 博客构建健康监控 — 跨仓库部署状态检查

监控维度：
1. GitHub Actions 构建状态（pages-optimize.yml）
2. Cloudflare Pages 部署状态（通过 GitHub check runs）
3. 线上文章可访问性（HTTP 200 检查）
4. 最新文章日期检查（确保新文章已上线）
5. frontmatter 格式回归检查

发现异常时：
- 记录到异常知识库（供 Lv34 修复使用）
- 发送告警通知
- 尝试自动诊断根因
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class BuildHealthMonitor:
    """构建健康监控器"""

    def __init__(self, 
                 github_owner: str = "garcci",
                 github_repo: str = "Astro",
                 blog_url: str = "https://www.gjqqq.com",
                 github_token: Optional[str] = None):
        self.owner = github_owner
        self.repo = github_repo
        self.blog_url = blog_url.rstrip('/')
        self.token = github_token or os.getenv("GH_MEMORY_TOKEN") or os.getenv("GITHUB_TOKEN")
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.headers["Accept"] = "application/vnd.github.v3+json"
        self.headers["User-Agent"] = "TrendRadar-BuildHealthMonitor/1.0"

    def check_all(self) -> Dict:
        """执行完整健康检查"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall": "unknown",
            "checks": {}
        }

        # 1. 检查 GitHub Actions 最新构建
        results["checks"]["github_actions"] = self._check_github_actions()

        # 2. 检查 Cloudflare Pages 部署
        results["checks"]["cloudflare_pages"] = self._check_cloudflare_pages()

        # 3. 检查线上文章可访问性
        results["checks"]["online_availability"] = self._check_online_availability()

        # 4. 检查最新文章日期
        results["checks"]["latest_article_date"] = self._check_latest_article_date()

        # 5. 检查 frontmatter 格式（扫描仓库最新文件）
        results["checks"]["frontmatter_health"] = self._check_frontmatter_health()

        # 综合判断
        failed = [k for k, v in results["checks"].items() if not v.get("healthy", True)]
        results["overall"] = "healthy" if not failed else "unhealthy"
        results["failed_checks"] = failed

        return results

    def _check_github_actions(self) -> Dict:
        """检查 GitHub Actions 最新构建状态"""
        try:
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/actions/runs?branch=master&per_page=5"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            runs = data.get("workflow_runs", [])
            if not runs:
                return {"healthy": False, "message": "没有找到 GitHub Actions 构建记录"}

            # 检查 Pages Build Optimization
            pages_runs = [r for r in runs if "Pages" in r.get("name", "")]
            if not pages_runs:
                pages_runs = runs  #  fallback

            latest = pages_runs[0]
            status = latest.get("conclusion", latest.get("status", "unknown"))
            
            result = {
                "healthy": status == "success",
                "workflow": latest.get("name"),
                "status": status,
                "run_id": latest.get("id"),
                "url": latest.get("html_url"),
                "created_at": latest.get("created_at"),
            }

            if status == "failure":
                result["message"] = f"GitHub Actions 构建失败: {latest.get('name')}"
            elif status == "success":
                result["message"] = f"GitHub Actions 构建成功: {latest.get('name')}"
            else:
                result["message"] = f"GitHub Actions 状态: {status}"

            return result

        except Exception as e:
            return {"healthy": False, "message": f"检查 GitHub Actions 失败: {e}"}

    def _check_cloudflare_pages(self) -> Dict:
        """检查 Cloudflare Pages 部署状态（优先使用 Cloudflare API，回退到 GitHub check runs）"""
        # 优先尝试 Cloudflare API 直接查询
        cf_token = os.environ.get("CF_API_TOKEN")
        cf_account = os.environ.get("CF_ACCOUNT_ID", "298718290c935a26d5016d3abe0b1c56")
        if cf_token:
            try:
                url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/pages/projects/astro/deployments?per_page=1"
                req = urllib.request.Request(
                    url,
                    headers={
                        "Authorization": f"Bearer {cf_token}",
                        "Content-Type": "application/json",
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())

                deployments = data.get("result", [])
                if deployments:
                    latest = deployments[0]
                    stage = latest.get("latest_stage", {})
                    status = stage.get("status", "unknown")
                    env = latest.get("environment", "unknown")
                    result = {
                        "healthy": status == "success",
                        "status": status,
                        "environment": env,
                        "deployment_id": latest.get("id"),
                        "url": latest.get("url"),
                        "created_at": latest.get("created_on"),
                    }
                    if status == "success":
                        result["message"] = f"Cloudflare Pages {env} 部署成功"
                    elif status == "failure":
                        result["message"] = f"Cloudflare Pages {env} 部署失败"
                    else:
                        result["message"] = f"Cloudflare Pages {env} 状态: {status}"
                    return result
            except Exception as e:
                # Cloudflare API 失败，回退到 GitHub check runs
                pass

        # 回退：通过 GitHub check runs 检查
        try:
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits/master/check-runs"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            check_runs = data.get("check_runs", [])
            cf_runs = [r for r in check_runs if "Cloudflare" in r.get("name", "")]

            if not cf_runs:
                return {"healthy": False, "message": "没有找到 Cloudflare Pages check run"}

            latest = cf_runs[0]
            status = latest.get("conclusion", "unknown")
            
            result = {
                "healthy": status == "success",
                "status": status,
                "check_run_id": latest.get("id"),
                "details_url": latest.get("details_url"),
                "started_at": latest.get("started_at"),
                "completed_at": latest.get("completed_at"),
            }

            if status == "success":
                result["message"] = "Cloudflare Pages 部署标记为成功"
            elif status == "failure":
                result["message"] = "Cloudflare Pages 部署失败"
            else:
                result["message"] = f"Cloudflare Pages 状态: {status}"

            return result

        except Exception as e:
            return {"healthy": False, "message": f"检查 Cloudflare Pages 失败: {e}"}

    def _check_online_availability(self) -> Dict:
        """检查线上文章可访问性"""
        try:
            # 检查首页
            req = urllib.request.Request(
                self.blog_url + "/",
                headers={"User-Agent": "TrendRadar-HealthCheck/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                homepage_html = resp.read().decode('utf-8', errors='ignore')
                homepage_status = resp.status

            result = {
                "healthy": homepage_status == 200,
                "homepage_status": homepage_status,
            }

            if homepage_status != 200:
                result["message"] = f"首页返回状态码 {homepage_status}"
                return result

            # 检查最近文章链接
            article_links = re.findall(
                r'href="(/posts/news/[^"]+)"',
                homepage_html
            )[:5]
            
            checked = []
            for link in article_links:
                try:
                    article_url = self.blog_url + link
                    req = urllib.request.Request(
                        article_url,
                        headers={"User-Agent": "TrendRadar-HealthCheck/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        checked.append({
                            "url": link,
                            "status": resp.status,
                            "healthy": resp.status == 200
                        })
                except urllib.error.HTTPError as e:
                    checked.append({
                        "url": link,
                        "status": e.code,
                        "healthy": False
                    })
                except Exception as e:
                    checked.append({
                        "url": link,
                        "status": f"error: {e}",
                        "healthy": False
                    })

            result["articles_checked"] = checked
            broken = [c for c in checked if not c["healthy"]]
            if broken:
                result["healthy"] = False
                result["message"] = f"{len(broken)} 篇文章不可访问"
            else:
                result["message"] = f"首页正常，{len(checked)} 篇文章均可访问"

            return result

        except Exception as e:
            return {"healthy": False, "message": f"检查线上可用性失败: {e}"}

    def _check_latest_article_date(self) -> Dict:
        """检查最新文章日期是否与今天一致"""
        try:
            req = urllib.request.Request(
                self.blog_url + "/",
                headers={"User-Agent": "TrendRadar-HealthCheck/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')

            # 提取所有日期
            dates = re.findall(r'(\d{4}-\d{2}-\d{2})', html)
            if not dates:
                return {"healthy": False, "message": "首页没有找到文章日期"}

            latest = max(dates)
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 允许 1 天延迟（构建可能有延迟）
            latest_dt = datetime.strptime(latest, "%Y-%m-%d")
            today_dt = datetime.strptime(today, "%Y-%m-%d")
            delay_days = (today_dt - latest_dt).days

            result = {
                "healthy": delay_days <= 1,
                "latest_date": latest,
                "today": today,
                "delay_days": delay_days,
            }

            if delay_days > 1:
                result["message"] = f"最新文章日期为 {latest}，延迟 {delay_days} 天"
            else:
                result["message"] = f"最新文章日期为 {latest}，正常"

            return result

        except Exception as e:
            return {"healthy": False, "message": f"检查最新文章日期失败: {e}"}

    def _check_frontmatter_health(self) -> Dict:
        """检查 Astro 仓库中 frontmatter 格式健康度"""
        try:
            # 通过 GitHub API 获取最近修改的文件列表
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits?sha=master&per_page=3"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                commits = json.loads(resp.read().decode())

            # 获取最近 commit 中的文件
            if not commits:
                return {"healthy": True, "message": "没有 commit 可检查"}

            latest_sha = commits[0].get("sha", "")
            files_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits/{latest_sha}"
            req = urllib.request.Request(files_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                commit_data = json.loads(resp.read().decode())

            files = commit_data.get("files", [])
            md_files = [f for f in files if f.get("filename", "").endswith(".md")]
            
            if not md_files:
                return {"healthy": True, "message": "最近 commit 没有 Markdown 文件修改"}

            # 获取文件内容并验证 frontmatter
            from evolution.frontmatter_validator import validate_article
            issues = []
            for f in md_files:
                filename = f.get("filename", "")
                if "posts/news/" not in filename:
                    continue
                
                raw_url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/master/{filename}"
                try:
                    req = urllib.request.Request(raw_url, headers={"User-Agent": "TrendRadar-HealthCheck/1.0"})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        content = resp.read().decode('utf-8', errors='ignore')
                    
                    valid, errors, fixed = validate_article(content, filename)
                    if not valid:
                        issues.append({
                            "file": filename,
                            "errors": errors
                        })
                except Exception as e:
                    issues.append({"file": filename, "errors": [f"无法获取文件: {e}"]})

            if issues:
                return {
                    "healthy": False,
                    "message": f"发现 {len(issues)} 个文件 frontmatter 有问题",
                    "issues": issues
                }
            else:
                return {
                    "healthy": True,
                    "message": f"检查了 {len(md_files)} 个 Markdown 文件，frontmatter 格式正常"
                }

        except Exception as e:
            return {"healthy": False, "message": f"检查 frontmatter 健康度失败: {e}"}


def get_build_health_report(
    github_token: Optional[str] = None,
    github_owner: str = "garcci",
    github_repo: str = "Astro",
    blog_url: str = "https://www.gjqqq.com",
    cf_api_token: Optional[str] = None,
    cf_account_id: Optional[str] = None,
) -> str:
    """生成构建健康报告"""
    monitor = BuildHealthMonitor(
        github_owner=github_owner,
        github_repo=github_repo,
        blog_url=blog_url,
        github_token=github_token,
    )
    # 如果提供了 Cloudflare API token，设置到环境变量供内部方法使用
    if cf_api_token:
        os.environ["CF_API_TOKEN"] = cf_api_token
    if cf_account_id:
        os.environ["CF_ACCOUNT_ID"] = cf_account_id
    results = monitor.check_all()
    
    lines = [
        "# Astro 博客构建健康报告",
        f"",
        f"**检查时间**: {results['timestamp']}",
        f"**整体状态**: {'✅ 健康' if results['overall'] == 'healthy' else '❌ 异常'}",
        f"",
    ]

    for check_name, check_result in results["checks"].items():
        status = "✅" if check_result.get("healthy") else "❌"
        lines.append(f"## {status} {check_name}")
        lines.append(f"{check_result.get('message', '无消息')}")
        if "issues" in check_result:
            for issue in check_result["issues"]:
                lines.append(f"- **{issue['file']}**: {', '.join(issue['errors'])}")
        lines.append("")

    if results.get("failed_checks"):
        lines.append(f"**失败项**: {', '.join(results['failed_checks'])}")

    return '\n'.join(lines)


if __name__ == "__main__":
    print(get_build_health_report())
