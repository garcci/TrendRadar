# -*- coding: utf-8 -*-
"""
Astro 部署后验证器 — 推送文章后自动验证是否成功上线

功能：
1. 轮询 Cloudflare Pages 部署状态
2. 部署成功后验证文章 URL 可访问性
3. 失败时记录异常并告警
"""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class DeployVerifier:
    """部署验证器"""

    def __init__(
        self,
        blog_url: str = "https://www.gjqqq.com",
        cf_api_token: Optional[str] = None,
        cf_account_id: Optional[str] = None,
        cf_project_name: str = "astro",
        max_wait_seconds: int = 300,
        poll_interval: int = 15,
    ):
        self.blog_url = blog_url.rstrip("/")
        self.cf_token = cf_api_token or os.environ.get("CF_API_TOKEN")
        self.cf_account = cf_account_id or os.environ.get("CF_ACCOUNT_ID", "298718290c935a26d5016d3abe0b1c56")
        self.cf_project = cf_project_name
        self.max_wait = max_wait_seconds
        self.poll_interval = poll_interval

    def verify_article_online(
        self,
        article_slug: str,
        expected_date: Optional[str] = None,
    ) -> Dict:
        """
        验证指定文章是否成功上线

        Args:
            article_slug: 文章 slug，如 "2026-04-25-trendradar-1777059076"
            expected_date: 期望的文章日期，用于检查首页是否有该日期

        Returns:
            {"success": bool, "message": str, "details": dict}
        """
        article_url = f"{self.blog_url}/posts/news/{article_slug}/"
        start_time = datetime.now()

        # Step 1: 等待 Cloudflare Pages 部署成功
        deploy_result = self._wait_for_deploy()
        if not deploy_result["success"]:
            return {
                "success": False,
                "message": f"部署未成功: {deploy_result['message']}",
                "details": deploy_result,
            }

        # Step 2: 验证文章 URL 可访问
        url_result = self._check_url(article_url)
        if not url_result["success"]:
            return {
                "success": False,
                "message": f"文章 URL 不可访问: {url_result['message']}",
                "details": url_result,
            }

        # Step 3: 验证首页包含期望日期（可选）
        if expected_date:
            date_result = self._check_homepage_date(expected_date)
            if not date_result["success"]:
                return {
                    "success": False,
                    "message": f"首页未找到文章日期: {date_result['message']}",
                    "details": date_result,
                }

        elapsed = (datetime.now() - start_time).total_seconds()
        return {
            "success": True,
            "message": f"文章已成功上线 ({elapsed:.0f}s)",
            "details": {
                "article_url": article_url,
                "deploy_status": deploy_result.get("status"),
                "elapsed_seconds": elapsed,
            },
        }

    def _wait_for_deploy(self) -> Dict:
        """轮询等待 Cloudflare Pages 部署成功"""
        if not self.cf_token:
            return {
                "success": False,
                "message": "未配置 CF_API_TOKEN，无法检查部署状态",
            }

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account}/pages/projects/{self.cf_project}/deployments?per_page=1"
        headers = {
            "Authorization": f"Bearer {self.cf_token}",
            "Content-Type": "application/json",
        }

        start_time = time.time()
        attempts = 0

        while time.time() - start_time < self.max_wait:
            attempts += 1
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())

                deployments = data.get("result", [])
                if deployments:
                    latest = deployments[0]
                    stage = latest.get("latest_stage", {})
                    status = stage.get("status", "unknown")

                    if status == "success":
                        return {
                            "success": True,
                            "message": "部署成功",
                            "status": status,
                            "deployment_id": latest.get("id"),
                            "attempts": attempts,
                        }
                    elif status == "failure":
                        return {
                            "success": False,
                            "message": "部署失败",
                            "status": status,
                            "deployment_id": latest.get("id"),
                            "attempts": attempts,
                        }
                    # else: 仍在构建中，继续等待

            except urllib.error.HTTPError as e:
                if e.code == 403:
                    return {
                        "success": False,
                        "message": (
                            f"Cloudflare API 403 Forbidden: CF_API_TOKEN 缺少权限或 Account ID 错误。"
                            f"请检查: 1) Token 是否有 'Cloudflare Pages:Read' 权限"
                            f" 2) Account ID ({self.cf_account}) 是否正确"
                        ),
                        "attempts": attempts,
                    }
                return {
                    "success": False,
                    "message": f"HTTP {e.code}: {e.reason}",
                    "attempts": attempts,
                }
            except Exception as e:
                return {"success": False, "message": f"查询部署状态失败: {e}", "attempts": attempts}

            time.sleep(self.poll_interval)

        return {
            "success": False,
            "message": f"等待部署超时 ({self.max_wait}s)",
            "attempts": attempts,
        }

    def _check_url(self, url: str) -> Dict:
        """检查 URL 是否可访问"""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "TrendRadar-DeployVerifier/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {
                    "success": resp.status == 200,
                    "message": f"HTTP {resp.status}",
                    "status": resp.status,
                }
        except urllib.error.HTTPError as e:
            return {"success": False, "message": f"HTTP {e.code}", "status": e.code}
        except Exception as e:
            return {"success": False, "message": f"请求失败: {e}", "status": None}

    def _check_homepage_date(self, expected_date: str) -> Dict:
        """检查首页是否包含期望的文章日期"""
        try:
            req = urllib.request.Request(
                self.blog_url + "/",
                headers={"User-Agent": "TrendRadar-DeployVerifier/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            if expected_date in html:
                return {"success": True, "message": f"首页包含日期 {expected_date}"}
            else:
                return {"success": False, "message": f"首页未找到日期 {expected_date}"}
        except Exception as e:
            return {"success": False, "message": f"检查首页失败: {e}"}


def verify_after_push(
    article_slug: str,
    expected_date: Optional[str] = None,
    logger=None,
    filepath: Optional[str] = None,
    github_token: Optional[str] = None,
    github_owner: str = "garcci",
    github_repo: str = "Astro",
    github_branch: str = "master",
    rollback_on_failure: bool = True,
) -> bool:
    """
    推送文章后执行部署验证（便捷函数）

    Args:
        article_slug: 文章 slug
        expected_date: 期望日期
        logger: 日志对象
        filepath: 文件路径（用于回滚）
        github_token: GitHub Token（用于回滚）
        github_owner: 仓库所有者
        github_repo: 仓库名
        github_branch: 分支名
        rollback_on_failure: 验证失败时是否自动回滚

    Returns:
        True if verification passed, False otherwise
    """
    verifier = DeployVerifier()
    result = verifier.verify_article_online(article_slug, expected_date)

    if logger:
        if result["success"]:
            logger.info(f"[部署验证] ✅ {result['message']}")
        else:
            logger.error(f"[部署验证] ❌ {result['message']}")

    if not result["success"]:
        # 记录到异常知识库
        try:
            import os
            import sys

            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from evolution.exception_monitor import ExceptionMonitor

            monitor = ExceptionMonitor(".")
            monitor.record_exception(
                "DeployVerificationError",
                f"文章部署验证失败: {article_slug}",
                result.get("details", {}),
                context=f"article:{article_slug}",
                module="deploy_verifier",
            )
            monitor._save_knowledge_base()
        except Exception:
            pass

        # 🔄 自动回滚 — 删除有问题的文章文件
        if rollback_on_failure and filepath and github_token:
            try:
                rollback_success = _rollback_article(
                    filepath, github_token, github_owner, github_repo, github_branch, logger
                )
                if rollback_success:
                    logger.info(f"[自动回滚] ✅ 已删除有问题的文章: {filepath}")
                else:
                    logger.error(f"[自动回滚] ❌ 回滚失败: {filepath}")
            except Exception as e:
                logger.error(f"[自动回滚] 回滚过程出错: {e}")

    return result["success"]


def _rollback_article(
    filepath: str,
    token: str,
    owner: str = "garcci",
    repo: str = "Astro",
    branch: str = "master",
    logger=None,
) -> bool:
    """
    通过 GitHub API 删除文章文件（回滚）

    Args:
        filepath: 文件路径，如 src/content/posts/news/2026-04-25-xxx.md
        token: GitHub Token
        owner: 仓库所有者
        repo: 仓库名
        branch: 分支名
        logger: 日志对象

    Returns:
        True if rollback succeeded
    """
    import json
    import urllib.request

    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "TrendRadar-DeployVerifier/1.0",
    }

    try:
        # Step 1: 获取文件当前 SHA
        get_url = f"{base_url}/contents/{filepath}?ref={branch}"
        req = urllib.request.Request(get_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            file_data = json.loads(resp.read().decode())
        file_sha = file_data.get("sha")

        if not file_sha:
            if logger:
                logger.warning(f"[回滚] 无法获取文件 SHA: {filepath}")
            return False

        # Step 2: 删除文件
        delete_url = f"{base_url}/contents/{filepath}"
        delete_data = json.dumps({
            "message": f"rollback: remove failed article - {filepath.split('/')[-1]}",
            "sha": file_sha,
            "branch": branch,
        }).encode()

        req = urllib.request.Request(
            delete_url,
            data=delete_data,
            headers={**headers, "Content-Type": "application/json"},
            method="DELETE",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()

        if logger:
            logger.info(f"[回滚] 已删除文件: {filepath}")
        return True

    except urllib.error.HTTPError as e:
        if e.code == 404:
            if logger:
                logger.warning(f"[回滚] 文件不存在（可能已被删除）: {filepath}")
            return True  # 文件已不存在，视为回滚成功
        if logger:
            logger.error(f"[回滚] HTTP {e.code}: {e.reason}")
        return False
    except Exception as e:
        if logger:
            logger.error(f"[回滚] 失败: {e}")
        return False
