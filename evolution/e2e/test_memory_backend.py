# -*- coding: utf-8 -*-
"""
记忆系统端到端测试

测试场景：
1. save_article_metadata 保存文章元数据到 GitHub Issue
2. get_recent_articles 读取最近的文章历史
3. 验证写入的数据能被正确读出（读写一致性）
4. 验证 state 过滤参数正确（防止 state=closed bug）
5. 验证标题包含唯一标识（防止去重失效）

历史教训：
- 曾出现 state=closed 但 Issue 默认 open，导致记忆永远读不到
- 曾出现 trending_topics 直接设为空列表，完全不用记忆数据
- 这些 bug 逃过了所有代码结构检查，只有端到端测试能发现
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from trendradar.storage.github_issues_memory import GitHubIssuesMemory


class TestMemoryBackendConsistency:
    """记忆系统读写一致性测试"""

    def __init__(self):
        self.test_results = []

    def _log(self, test_name: str, passed: bool, message: str):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_save_and_read_consistency(self):
        """测试1: 保存后能读到，且数据一致"""
        test_name = "读写一致性"

        # 模拟数据
        metadata = {
            "date": "2026-04-27",
            "title": "DeepSeek V4 Pro 降价分析",
            "keywords": ["AI", "DeepSeek", "降价"],
            "hot_topics": ["核心观点", "一句话总结"],
            "platforms": ["知乎", "华尔街见闻"],
            "excerpt": "DeepSeek V4 Pro 大幅降价，国产算力...",
            "timestamp": "2026-04-27T12:00:00"
        }

        memory = GitHubIssuesMemory("test_owner", "test_repo", "fake_token")

        # 模拟 save 成功（GitHub API 返回 201）
        mock_save_response = MagicMock()
        mock_save_response.status_code = 201
        mock_save_response.json.return_value = {"number": 123, "html_url": "https://github.com/test_owner/test_repo/issues/123"}

        # 模拟 get 返回刚才保存的 Issue
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200

        # 构建 Issue body（与 _format_issue_body 一致）
        issue_body = memory._format_issue_body(metadata)

        mock_get_response.json.return_value = [
            {
                "number": 123,
                "title": f"[Memory] {metadata['title'][:30]} - {metadata['date']}",
                "body": issue_body,
                "created_at": "2026-04-27T12:00:00Z",
                "labels": [{"name": "memory"}, {"name": "article-history"}]
            }
        ]

        with patch('trendradar.storage.github_issues_memory.requests.post', return_value=mock_save_response):
            save_ok = memory.save_article_metadata(metadata)

        if not save_ok:
            self._log(test_name, False, "save_article_metadata 返回失败")
            return

        with patch('trendradar.storage.github_issues_memory.requests.get', return_value=mock_get_response):
            articles = memory.get_recent_articles(days=7)

        if not articles:
            self._log(test_name, False, "get_recent_articles 返回空列表——记忆保存了但读不到！")
            return

        # 验证数据一致性
        article = articles[0]
        checks = [
            (article.get('date') == metadata['date'], f"date 不一致: {article.get('date')} != {metadata['date']}"),
            (article.get('title') == metadata['title'], f"title 不一致: {article.get('title')} != {metadata['title']}"),
            (len(article.get('keywords', [])) == len(metadata['keywords']), "keywords 数量不一致"),
        ]

        for check_passed, error_msg in checks:
            if not check_passed:
                self._log(test_name, False, f"数据不一致: {error_msg}")
                return

        self._log(test_name, True, f"保存后成功读取，数据一致（{len(articles)} 条记录）")

    def test_state_filter_correctness(self):
        """测试2: get_recent_articles 的 state 过滤参数正确

        历史 bug: state=closed 但 Issue 默认 open，导致永远读不到记忆
        """
        test_name = "state过滤参数"

        memory = GitHubIssuesMemory("test_owner", "test_repo", "fake_token")

        # 检查搜索 URL 中是否包含正确的 state 参数
        import inspect
        source = inspect.getsource(memory.get_recent_articles)

        if 'state=closed' in source:
            self._log(test_name, False, "严重bug: get_recent_articles 使用 state=closed，但 Issue 默认 open，记忆永远读不到")
            return

        if 'state=all' not in source and 'state=open' not in source:
            self._log(test_name, False, "警告: get_recent_articles 未明确指定 state 参数，可能遗漏 open 状态的 Issue")
            return

        self._log(test_name, True, "state 过滤参数正确（all/open）")

    def test_title_uniqueness(self):
        """测试3: Issue 标题包含文章唯一标识，防止所有记忆标题相同"""
        test_name = "标题唯一性"

        memory = GitHubIssuesMemory("test_owner", "test_repo", "fake_token")
        import inspect
        source = inspect.getsource(memory.save_article_metadata)

        # 检查标题是否包含 article_title 变量
        if 'article_title' not in source or '{article_title}' not in source:
            self._log(test_name, False, "Issue 标题固定，不同文章无法区分，可能导致去重失效")
            return

        self._log(test_name, True, "标题包含文章标识，可区分不同记忆")

    def test_trending_topics_from_memory(self):
        """测试4: github.py 中的 trending_topics 在有 memory_backend 时是否使用记忆数据

        历史 bug: 有 memory_backend 时 trending_topics 直接设为空列表 []
        """
        test_name = "记忆数据集成"

        github_py_path = project_root / "trendradar/storage/github.py"
        if not github_py_path.exists():
            self._log(test_name, False, "github.py 不存在")
            return

        content = github_py_path.read_text()

        # 检查是否有从 memory_backend 提取 trending topics 的代码
        has_memory_usage = "memory_backend.get_recent_articles" in content and "topic_counts" in content
        has_empty_list_bug = "if gh_token and 'memory_backend' in locals():" in content and "trending_topics = []" in content

        if has_empty_list_bug and not has_memory_usage:
            self._log(test_name, False, "严重bug: 有 memory_backend 时 trending_topics 直接设为空列表，完全不用记忆数据")
            return

        if has_memory_usage:
            self._log(test_name, True, "trending_topics 从记忆数据提取")
        else:
            self._log(test_name, False, "无法确认 trending_topics 是否使用记忆数据")

    def run_all(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("记忆系统端到端测试")
        print("=" * 60)

        self.test_save_and_read_consistency()
        self.test_state_filter_correctness()
        self.test_title_uniqueness()
        self.test_trending_topics_from_memory()

        passed = sum(1 for r in self.test_results if r["passed"])
        failed = sum(1 for r in self.test_results if not r["passed"])

        print()
        for r in self.test_results:
            emoji = "✅" if r["passed"] else "❌"
            print(f"{emoji} {r['test']}: {r['message']}")

        print()
        print(f"总计: {passed}/{len(self.test_results)} 通过, {failed} 失败")
        print("=" * 60)

        return {
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": self.test_results
        }


if __name__ == "__main__":
    tester = TestMemoryBackendConsistency()
    result = tester.run_all()
    sys.exit(0 if result["all_passed"] else 1)
