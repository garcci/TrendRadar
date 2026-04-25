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
) -> bool:
    """
    推送文章后执行部署验证（便捷函数）

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

    return result["success"]
