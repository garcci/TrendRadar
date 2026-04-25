"""
GitHub Storage Backend for TrendRadar
Pushes articles directly to Astro repository via GitHub API
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List
from pathlib import Path

from .base import StorageBackend, NewsData

logger = logging.getLogger(__name__)


class GitHubStorageBackend(StorageBackend):
    """
    Storage backend that pushes articles to Astro repository via GitHub API.
    
    This backend:
    1. Generates Markdown files for each news item
    2. Pushes them to the Astro repository using GitHub REST API
    3. Triggers Cloudflare Pages auto-deployment via Git integration
    """
    
    def __init__(self):
        # GitHub configuration
        self.token = os.getenv("ASTRO_GITHUB_TOKEN")
        self.owner = os.getenv("ASTRO_REPO_OWNER", "garcci")
        self.repo = os.getenv("ASTRO_REPO_NAME", "Astro")
        self.branch = os.getenv("ASTRO_BRANCH", "main")
        
        if not self.token:
            raise ValueError("ASTRO_GITHUB_TOKEN environment variable is required")
        
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TrendRadar/2.0"
        }
        
        logger.info(f"GitHub Storage initialized: {self.owner}/{self.repo}@{self.branch}")
    
    @property
    def backend_name(self) -> str:
        return "github"
    
    def initialize(self) -> None:
        """Initialize storage (no-op for GitHub backend)"""
        pass
    
    def cleanup(self) -> None:
        """Cleanup resources (no-op for GitHub backend)"""
        pass
    
    def supports_txt(self) -> bool:
        """GitHub backend doesn't support TXT format"""
        return False
    
    def is_first_crawl_today(self, date: Optional[str] = None) -> bool:
        """Check if this is the first crawl today (always False for GitHub)"""
        return False
    
    def get_today_all_data(self, date: Optional[str] = None) -> Optional[NewsData]:
        """Get all data for today (not supported for GitHub backend)"""
        return None
    
    def get_latest_crawl_data(self, date: Optional[str] = None) -> Optional[NewsData]:
        """Get latest crawl data (not supported for GitHub backend)"""
        return None
    
    def detect_new_titles(self, current_data: NewsData) -> Dict[str, Dict]:
        """Detect new titles (not supported for GitHub backend)"""
        return {}
    
    def save_news_data(self, data: NewsData) -> bool:
        """
        Save news data by pushing Markdown files to Astro repository.
        Uses AI to generate professional article content.
        Also saves to local SQLite for TrendRadar's own analysis.
        
        Args:
            data: NewsData object containing crawled news items
            
        Returns:
            True if successfully pushed to GitHub
        """
        if not data.items:
            logger.warning("No news items to save")
            return False
        
        # First, save to local SQLite for TrendRadar's analysis
        try:
            from .local import LocalStorageBackend
            local_backend = LocalStorageBackend()
            local_backend.save_news_data(data)
            logger.info("Data saved to local SQLite for analysis")
        except Exception as e:
            logger.warning(f"Failed to save to local SQLite: {e}")
        
        timestamp = int(datetime.now(timezone.utc).timestamp())
        date_str = data.date or datetime.now().strftime("%Y-%m-%d")
        
        # ═══════════════════════════════════════════════════════════
        # 🧠 智能调度决策 - Lv17 进化
        # ═══════════════════════════════════════════════════════════
        try:
            from evolution.smart_scheduler import SmartScheduler
            
            # 统计热点数据
            total_items = sum(len(items) for items in data.items.values())
            
            # 简单统计科技热点（基于标题关键词）
            tech_keywords = ['AI', '人工智能', '芯片', '开源', 'GitHub', '模型', '训练', '算法', 
                           '框架', '云', '数据', '安全', '区块链', '量子', '机器人', '自动驾驶',
                           '半导体', 'GPU', '大模型', 'LLM', 'Transformer', '神经网络']
            tech_count = 0
            for items in data.items.values():
                for item in items:
                    title = getattr(item, 'title', '') or ''
                    if any(kw in title for kw in tech_keywords):
                        tech_count += 1
            
            scheduler = SmartScheduler()
            decision = scheduler.make_decision(
                news_items_count=total_items,
                tech_items_count=tech_count,
                rss_success_rate=0.8
            )
            
            logger.info(f"[智能调度] 决策={decision['action'].upper()} 评分={decision['score']}/10 原因={decision['reason']}")
            if decision['issues']:
                logger.info(f"[智能调度] 问题: {'; '.join(decision['issues'])}")
            
            if decision['action'] == 'skip':
                logger.warning(f"[智能调度] 跳过今日生成: {decision['reason']}")
                return False
            elif decision['action'] == 'draft':
                logger.info(f"[智能调度] 生成草稿模式: {decision['reason']}")
                is_draft = True
            else:
                is_draft = False
                
        except Exception as e:
            logger.warning(f"[智能调度] 决策失败，使用默认策略: {e}")
            is_draft = False
        
        # 🔍 语义去重检查 — Lv60 进化
        try:
            from evolution.semantic_deduplicator import check_content_duplication
            
            topics = []
            for source_id, items in data.items.items():
                for item in items[:5]:
                    if hasattr(item, 'title'):
                        topics.append(item.title)
            
            dup_result = check_content_duplication(
                topics,
                github_owner=self.owner,
                github_repo=self.repo,
                github_token=self.token,
                threshold=0.65,
            )
            
            if dup_result.get("is_duplicate"):
                logger.warning(f"[语义去重] {dup_result['recommendation']}")
                for sim in dup_result.get("similar_articles", [])[:3]:
                    logger.warning(f"  - {sim['title']} ({sim['date']}, 相似度: {sim['similarity']})")
                # 高相似度时跳过生成
                if dup_result.get("max_similarity", 0) >= 0.85:
                    logger.error("[语义去重] 话题高度重复，跳过今日生成")
                    return False
            else:
                logger.info(f"[语义去重] {dup_result['recommendation']}")
        except Exception as e:
            logger.warning(f"[语义去重] 检查失败: {e}，继续生成")
        
        # Generate article title and filename
        article_title = f"TrendRadar Report - {date_str}"
        filename = f"{date_str}-trendradar-{timestamp}.md"
        filepath = f"src/content/posts/news/{filename}"
        
        # Generate Markdown content using AI
        try:
            markdown_content = self._generate_ai_article(data, article_title)
            logger.info("AI-generated article created successfully")
        except Exception as e:
            logger.warning(f"AI generation failed, falling back to template: {e}")
            markdown_content = self._generate_markdown(data, article_title)
        
        # 🔬 科技内容检测 — Lv62 进化
        tech_check_result = None
        try:
            from evolution.tech_content_guard import check_tech_content
            passed, message = check_tech_content(markdown_content, min_ratio=0.7)
            tech_check_result = {"passed": passed, "message": message[:200]}
            if passed:
                logger.info(f"[科技检测] ✅ {message}")
            else:
                logger.warning(f"[科技检测] ⚠️ 科技占比不足:\n{message}")
                # 记录到异常知识库但不阻止发布（避免消耗额外额度重写）
                try:
                    from evolution.exception_monitor import ExceptionMonitor
                    monitor = ExceptionMonitor('.')
                    monitor.record_exception(
                        'TechContentGuardWarning',
                        '文章科技占比不足',
                        message,
                        context=f'file:{filepath}',
                        module='github.py'
                    )
                    monitor._save_knowledge_base()
                except Exception as e:
                    logger.debug(f"[异常监控] 保存失败: {e}")
            
            # 📦 记录检测结果到数据管道 — Round 2
            try:
                from evolution.data_pipeline import write_record
                write_record("metric", {
                    "name": "tech_content_ratio",
                    "value": 1 if passed else 0,
                    "unit": "boolean",
                    "module": "tech_content_guard",
                })
            except Exception as e:
                logger.debug(f"[数据管道] 写入失败: {e}")
        except Exception as e:
            logger.warning(f"[科技检测] 检查失败: {e}")
        
        # 📝 草稿模式处理 - 将draft设为true
        if is_draft:
            if "draft: false" in markdown_content:
                markdown_content = markdown_content.replace("draft: false", "draft: true")
                logger.info("[智能调度] 文章已标记为草稿 (draft: true)")
            elif "---" in markdown_content:
                # 在frontmatter中添加draft字段
                parts = markdown_content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    if "draft:" not in frontmatter:
                        frontmatter += "\ndraft: true"
                        markdown_content = f"---{frontmatter}---{parts[2]}"
                        logger.info("[智能调度] 文章已标记为草稿 (draft: true)")
        
        # 📝 智能摘要 - 自动生成TL;DR（Lv19进化）
        try:
            from evolution.smart_summary import add_smart_summary
            original_length = len(markdown_content)
            markdown_content = add_smart_summary(markdown_content)
            if len(markdown_content) > original_length:
                logger.info("[智能摘要] 已自动生成文章摘要块")
        except Exception as e:
            logger.warning(f"[智能摘要] 生成失败: {e}")
        
        # 📝 标题优化 - 自动生成最佳标题（Lv22进化）
        try:
            from evolution.title_optimizer import optimize_article_title, replace_article_title
            new_title = optimize_article_title(markdown_content)
            if new_title and "TrendRadar Report" not in new_title:
                markdown_content = replace_article_title(markdown_content, new_title)
                logger.info(f"[标题优化] 已优化标题为: {new_title}")
        except Exception as e:
            logger.warning(f"[标题优化] 失败: {e}")
        
        # 🧹 Frontmatter 清理 - 修复 YAML 引号嵌套等问题
        markdown_content = self._sanitize_frontmatter(markdown_content, data.date, article_title)
        
        # ✅ Frontmatter 预验证 — 防止格式错误导致 Astro 构建失败
        try:
            from evolution.frontmatter_validator import validate_article
            valid, errors, fixed_content = validate_article(markdown_content, filepath)
            if not valid:
                logger.warning(f"[Frontmatter验证] 发现 {len(errors)} 个问题:")
                for err in errors:
                    logger.warning(f"  - {err}")
                # 使用修复后的内容
                if fixed_content != markdown_content:
                    markdown_content = fixed_content
                    logger.info("[Frontmatter验证] 已自动修复问题")
                    # 再次验证
                    valid2, errors2, _ = validate_article(markdown_content, filepath)
                    if not valid2:
                        logger.error(f"[Frontmatter验证] 自动修复后仍有 {len(errors2)} 个问题:")
                        for err in errors2:
                            logger.error(f"  - {err}")
                        # 记录到异常知识库
                        try:
                            from evolution.exception_monitor import ExceptionMonitor
                            monitor = ExceptionMonitor('.')
                            monitor.record_exception(
                                'FrontmatterValidationError',
                                f'Frontmatter 验证失败: {"; ".join(errors2)}',
                                '',
                                context=f'file:{filepath}',
                                module='github.py'
                            )
                            monitor._save_knowledge_base()
                        except Exception as e:
                            logger.debug(f"[异常监控] 保存失败: {e}")
                        # 阻止推送，避免破坏 Astro 构建
                        logger.error("[Frontmatter验证] 阻止推送：frontmatter 格式严重错误")
                        return False
                else:
                    logger.error("[Frontmatter验证] 无法自动修复，阻止推送")
                    return False
            else:
                logger.info("[Frontmatter验证] ✅ 通过")
        except Exception as e:
            logger.warning(f"[Frontmatter验证] 验证过程出错: {e}，跳过验证继续推送")
        
        # 🛡️ Astro 构建预检 — 推送前模拟验证
        try:
            from evolution.astro_preflight import preflight_check
            passed, report = preflight_check(markdown_content, filepath)
            if not passed:
                logger.error(f"[构建预检] ❌ 未通过:\n{report}")
                # 记录到异常知识库
                try:
                    from evolution.exception_monitor import ExceptionMonitor
                    monitor = ExceptionMonitor('.')
                    monitor.record_exception(
                        'AstroPreflightError',
                        f'构建预检失败: {filepath}',
                        report,
                        context=f'file:{filepath}',
                        module='github.py'
                    )
                    monitor._save_knowledge_base()
                except Exception as e:
                    logger.debug(f"[异常监控] 保存失败: {e}")
                return False
            logger.info("[构建预检] ✅ 通过")
        except Exception as e:
            logger.warning(f"[构建预检] 检查过程出错: {e}，跳过继续推送")
        
        # Push to GitHub
        try:
            self._push_to_github(filepath, markdown_content, f"feat: add TrendRadar report - {article_title}")
            logger.info(f"Successfully pushed article to GitHub: {filepath}")
            
            # 🚀 部署后验证 — 确保文章成功上线
            try:
                from trendradar.storage.deploy_verifier import verify_after_push
                import os
                
                slug = os.path.basename(filepath).replace('.md', '')
                date_str = data.date.strftime('%Y-%m-%d') if hasattr(data, 'date') else ''
                
                # 验证并支持自动回滚（Lv58）
                verify_after_push(
                    slug, date_str, logger,
                    filepath=filepath,
                    github_token=self.token,
                    github_owner=self.owner,
                    github_repo=self.repo,
                    github_branch=self.branch,
                    rollback_on_failure=True,
                )
            except Exception as e:
                logger.warning(f"[部署验证] 验证过程出错: {e}")
            
            # 📦 记录文章数据到统一管道 — Round 2 数据流调优
            try:
                from evolution.data_pipeline import write_record
                write_record("article", {
                    "id": filepath.split('/')[-1].replace('.md', ''),
                    "title": article_title,
                    "date": data.date.strftime('%Y-%m-%d') if hasattr(data, 'date') else '',
                    "source_count": len(data.items),
                    "total_items": sum(len(items) for items in data.items.values()),
                    "length": len(markdown_content),
                    "is_draft": is_draft,
                })
                logger.info("[数据管道] 文章记录已写入")
            except Exception as e:
                logger.warning(f"[数据管道] 写入失败: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to push to GitHub: {e}")
            return False
    
    def _check_existing_articles(self, date_str: str) -> list:
        """
        检查今天是否已经生成过文章
        
        Returns:
            已有文章列表，每篇文章包含标题和摘要
        """
        try:
            # 通过 GitHub API 检查今天已推送的文件
            import requests
            check_url = f"{self.base_url}/contents/src/content/posts/news"
            response = requests.get(check_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            files = response.json()
            existing = []
            
            for file_info in files:
                if file_info.get('type') == 'file' and file_info.get('name', '').startswith(date_str):
                    # 获取文件内容
                    content_url = file_info.get('download_url')
                    if content_url:
                        try:
                            content_resp = requests.get(content_url, timeout=10)
                            if content_resp.status_code == 200:
                                content = content_resp.text
                                # 提取标题和描述
                                title_match = content.split('title: "')[1].split('"')[0] if 'title: "' in content else ""
                                desc_match = content.split('description: "')[1].split('"')[0] if 'description: "' in content else ""
                                existing.append({
                                    'title': title_match,
                                    'description': desc_match,
                                    'filename': file_info.get('name')
                                })
                        except Exception as e:
                            logger.debug(f"[已有文章] 获取内容失败: {e}")
            
            return existing
        except Exception as e:
            logger.warning(f"Error checking existing articles: {e}")
            return []
    
    def _has_significant_changes(self, data: NewsData, existing_articles: list) -> bool:
        """
        检查当前新闻与已有文章是否有显著差异
        
        判断标准：
        - 如果有超过 30% 的新话题（不在已有文章标题/描述中），则认为有显著变化
        
        Returns:
            True 如果有显著变化，False 如果太相似
        """
        if not existing_articles:
            return True
        
        # 提取当前所有热点的标题关键词
        current_topics = set()
        for source_id, items in data.items.items():
            for item in items:
                # 提取标题中的关键词（简单分词）
                title = item.title
                # 取前 10 个字符作为话题标识
                if len(title) > 10:
                    current_topics.add(title[:10])
                else:
                    current_topics.add(title)
        
        # 提取已有文章的话题
        existing_topics = set()
        for article in existing_articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            # 简单分词（取前 10 个字符）
            words = text.split()
            for word in words:
                if len(word) > 2:
                    existing_topics.add(word[:10])
        
        if not current_topics or not existing_topics:
            return True
        
        # 计算新话题比例
        new_topics = current_topics - existing_topics
        new_ratio = len(new_topics) / len(current_topics) if current_topics else 0
        
        logger.warning(f"Topic analysis: {len(current_topics)} current topics, {len(new_topics)} new topics, ratio: {new_ratio:.2%}")
        
        # 如果新话题比例超过 30%，认为有显著变化
        return new_ratio > 0.30
    
    def _generate_markdown(self, data: NewsData, title: str) -> str:
        """
        Generate professional Markdown content for the article with Astro features.
        Fallback method when AI generation fails.
        
        Args:
            data: NewsData object
            title: Article title
            
        Returns:
            Markdown formatted string with Astro components
        """
        # Generate date-based metadata
        date_obj = datetime.strptime(data.date, "%Y-%m-%d") if data.date else datetime.now()
        weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][date_obj.weekday()]
        
        # 安全处理 title 中的双引号
        if '"' in title and "'" not in title:
            safe_title_line = f"title: '{title}'"
        else:
            safe_title = title.replace('"', '\\"')
            safe_title_line = f'title: "{safe_title}"'
                
        lines = [
            "---",
            safe_title_line,
            f"published: {data.date}T08:00:00+08:00",
            "tags: [news, trendradar, hot, daily-digest]",
            "category: news",
            "draft: false",
            "cover: /images/trendradar-cover.jpg",
            "excerpt: \"每日热点聚合 | TrendRadar 智能监控 11+ 平台，AI 筛选高价值资讯\"",
            "---",
            "",
            f"# 📊 {title}",
            "",
            f"> **{data.date} {weekday_cn}** | TrendRadar 智能监控系统自动聚合",
            "> ",
            "> ✨ 覆盖今日头条、百度、微博、知乎、抖音等 11+ 主流平台",
            "> ",
            "> 🤖 AI 智能筛选 · 实时热点追踪 · 深度趋势分析",
            "",
            "---",
            "",
            "## 🎯 今日热点概览",
            "",
        ]
        
        # Add summary statistics
        total_items = sum(len(items) for items in data.items.values())
        platform_count = len(data.items)
        lines.append(f"**统计信息：** 共监测 {platform_count} 个平台，{total_items} 条热点内容")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Add news items by platform with enhanced formatting
        platform_icons = {
            "toutiao": "📰",
            "baidu": "🔍",
            "weibo": "🌐",
            "zhihu": "💡",
            "douyin": "🎵",
            "bilibili-hot-search": "📺",
            "thepaper": "📝",
            "wallstreetcn-hot": "💹",
            "cls-hot": "📈",
            "ifeng": "🦅",
            "tieba": "💬",
        }
        
        for source_id, items_list in data.items.items():
            source_name = data.id_to_name.get(source_id, source_id)
            icon = platform_icons.get(source_id, "📌")
            
            lines.append(f"## {icon} {source_name}")
            lines.append("")
            
            # Show top 10 items with better formatting
            display_items = items_list[:10]
            for i, item in enumerate(display_items, 1):
                rank_emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1] if i <= 10 else f"{i}."
                lines.append(f"{rank_emoji} **[{item.title}]({item.url})**")
            
            if len(items_list) > 10:
                lines.append(f"")
                lines.append(f"*... 还有 {len(items_list) - 10} 条热点，[查看完整榜单]({items_list[10].url if items_list[10].url else '#' })*")
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Add AI Analysis section (placeholder for now)
        lines.append("## 🤖 AI 智能分析")
        lines.append("")
        lines.append("> 💡 *AI 分析功能已启用，正在优化集成方式*")
        lines.append(">")
        lines.append("> 即将推出：")
        lines.append("> - 📊 核心热点与舆情态势")
        lines.append("> - 💭 舆论风向与争议焦点")
        lines.append("> - 🔍 异动信号与弱信号检测")
        lines.append("> - 📰 RSS 深度洞察")
        lines.append("> - 🎯 趋势研判与策略建议")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Add footer
        lines.append("## 📌 关于 TrendRadar")
        lines.append("")
        lines.append("TrendRadar 是一个智能热点监控系统，每小时自动抓取并分析全网热点资讯。")
        lines.append("")
        lines.append("**特性：**")
        lines.append("- ✅ 覆盖 11+ 主流平台")
        lines.append("- ✅ AI 智能筛选与分类")
        lines.append("- ✅ 实时热点追踪")
        lines.append("- ✅ 自动生成专业报告")
        lines.append("")
        lines.append(f"*本报告由 TrendRadar v6.6.1 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_ai_article(self, data: NewsData, title: str) -> str:
        """
        Use AI to generate a professional, beautiful, and valuable article.
        Integrates history context for better continuity.
        Includes cost optimization strategies.
        
        Args:
            data: NewsData object
            title: Article title
            
        Returns:
            AI-generated Markdown formatted string
        """
        from ..ai.smart_client import SmartAIClient
        from ..core.loader import load_config
        from .history_manager import ArticleHistoryManager
        from .cost_optimizer import AICostOptimizer
        import os
        
        # Initialize cost optimizer
        cost_optimizer = AICostOptimizer()
        
        # Check daily budget
        within_budget, budget_stats = cost_optimizer.check_daily_budget()
        if not within_budget:
            logger.warning(f"Daily token budget exceeded: {budget_stats}")
            raise RuntimeError("AI daily budget exceeded, falling back to template")
        
        # Load AI configuration
        try:
            config = load_config()
            ai_config = config.get("ai", {})
            ai_client = SmartAIClient(ai_config)
            
            # Validate AI configuration
            is_valid, error_msg = ai_client.validate_config()
            if not is_valid:
                raise ValueError(f"AI configuration invalid: {error_msg}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize AI client: {e}")
        
        # Prepare news data for AI - provide structured summary with video URLs
        news_summary = []
        total_count = 0
        video_platforms = ["bilibili", "douyin", "youtube"]  # Platforms that may have videos
        
        for source_id, items_list in data.items.items():
            source_name = data.id_to_name.get(source_id, source_id)
            has_video_potential = any(vp in source_id.lower() for vp in video_platforms)
            
            if has_video_potential:
                news_summary.append(f"\n**{source_name}** (Top 8) 🎥 含视频链接:")
                for i, item in enumerate(items_list[:8], 1):
                    # Include URL for video platforms
                    url_info = f" [URL: {item.url}]" if hasattr(item, 'url') and item.url else ""
                    news_summary.append(f"  {i}. {item.title}{url_info}")
            else:
                news_summary.append(f"\n**{source_name}** (Top 8):")
                for i, item in enumerate(items_list[:8], 1):
                    news_summary.append(f"  {i}. {item.title}")
            total_count += len(items_list)
        
        news_text = "\n".join(news_summary)
        
        # ═══════════════════════════════════════════════════════════
        # 🔗 跨源关联分析 - Lv18 进化
        # ═══════════════════════════════════════════════════════════
        cross_source_insights = ""
        try:
            from evolution.cross_source_analyzer import CrossSourceAnalyzer
            
            # 构建平台items数据
            platform_items = {}
            for source_id, items_list in data.items.items():
                source_name = data.id_to_name.get(source_id, source_id)
                platform_items[source_name] = []
                for item in items_list[:10]:  # 每个平台取前10条
                    platform_items[source_name].append({
                        "title": getattr(item, 'title', ''),
                        "excerpt": getattr(item, 'excerpt', '') or getattr(item, 'title', ''),
                        "url": getattr(item, 'url', '')
                    })
            
            analyzer = CrossSourceAnalyzer()
            clusters = analyzer.find_topic_clusters(platform_items)
            
            if clusters:
                cross_source_insights = analyzer.generate_cross_source_insights(clusters)
                logger.info(f"[跨源关联] 发现 {len(clusters)} 个跨平台话题簇")
                for c in clusters[:3]:
                    logger.info(f"  - {c['representative_title'][:40]}... ({c['size']}条, 平台: {', '.join(c['platforms'])})")
            else:
                logger.info("[跨源关联] 未发现跨平台关联话题")
                
        except Exception as e:
            logger.warning(f"[跨源关联] 分析失败: {e}")
        
        # Get historical context for continuity
        try:
            # Try GitHub Issues Memory first (persistent)
            gh_token = os.environ.get("GH_MEMORY_TOKEN")
            astro_owner = os.environ.get("ASTRO_REPO_OWNER", "garcci")
            astro_repo = os.environ.get("ASTRO_REPO_NAME", "Astro")
            
            logger.warning(f"Checking memory system: GH_TOKEN={'present' if gh_token else 'missing'}, Owner={astro_owner}, Repo={astro_repo}")
            
            if gh_token:
                from .github_issues_memory import GitHubIssuesMemory
                memory_backend = GitHubIssuesMemory(astro_owner, astro_repo, gh_token)
                context_summary = memory_backend.generate_context_summary(days=3)
                logger.warning("Using GitHub Issues Memory backend")
            else:
                # Fallback to local history manager
                history_mgr = ArticleHistoryManager()
                context_summary = history_mgr.generate_context_summary(days=3)
                logger.warning("Using local history manager (non-persistent)")
            
            # Get trending topics
            if gh_token and 'memory_backend' in locals():
                # TODO: Implement trending topics in GitHubIssuesMemory
                trending_topics = []
            else:
                history_mgr = ArticleHistoryManager()
                trending_topics = history_mgr.get_trending_topics(window_days=7, min_mentions=2)
            
            if trending_topics:
                trending_info = f"\n\n### 🔥 当前 Trending 话题（连续多日关注）\n"
                trending_info += "\n".join([f"- {topic}" for topic in trending_topics[:5]])
                context_summary += trending_info
        except Exception as e:
            logger.warning(f"Failed to load history context: {e}")
            context_summary = "（无历史记录）"
        
        # 🧬 获取进化反馈上下文（自适应进化系统 v3.0）
        evolution_context = ""
        try:
            if gh_token:
                import sys
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                from evolution import get_evolution_summary
                # 获取基于长期趋势分析的进化反馈
                evolution_context = get_evolution_summary(
                    astro_owner, astro_repo, gh_token,
                    current_prompt="",  # 当前prompt的哈希或版本标识
                    days=7
                )
                if evolution_context:
                    logger.warning(f"[自适应进化] 加载趋势分析: {len(evolution_context)} 字符")
                else:
                    logger.warning("[自适应进化] 数据不足，暂无趋势分析")
        except Exception as e:
            logger.warning(f"[自适应进化] 加载失败: {e}")
            # 降级到旧版进化系统
            try:
                from evolution.evolution_system import AIEvolutionSystem
                evolution_system = AIEvolutionSystem(astro_owner, astro_repo, gh_token)
                evolution_context = evolution_system.get_evolution_context()
                if evolution_context:
                    logger.warning(f"[进化系统] 降级加载改进建议: {len(evolution_context)} 字符")
            except Exception as e2:
                logger.warning(f"[进化系统] 降级加载也失败: {e2}")
        
        # 🎲 文章结构多样化引擎
        diversity_instructions = ""
        try:
            if gh_token:
                from evolution import get_diversity_instructions, PerspectiveRotator
                # 提取热点关键词用于模板匹配
                topics = []
                for source_id, items in data.items.items():
                    for item in items[:3]:
                        if hasattr(item, 'title'):
                            topics.append(item.title)
                        elif isinstance(item, dict):
                            topics.append(item.get('title', ''))
                
                diversity_instructions = get_diversity_instructions(".", topics)
                if diversity_instructions:
                    logger.warning(f"[多样化引擎] 加载结构模板: {len(diversity_instructions)} 字符")
                
                # 添加角度轮换
                perspective = PerspectiveRotator.get_rotated_perspectives(2)
                diversity_instructions += perspective
        except Exception as e:
            logger.warning(f"[多样化引擎] 加载失败: {e}")
        
        # 将进化反馈和多样化指导合并到 context_summary 中
        if evolution_context:
            context_summary += evolution_context
        if diversity_instructions:
            context_summary += diversity_instructions
        
        # 🔮 热点预测注入 — Lv67 进化
        try:
            from evolution.trend_forecast import get_trend_predictions
            trend_prediction = get_trend_predictions('.')
            if trend_prediction:
                context_summary += trend_prediction
                logger.info("[热点预测] Lv67 已注入预测内容")
            else:
                logger.info("[热点预测] Lv67 暂无即将到来的热点")
        except Exception as e:
            logger.warning(f"[热点预测] Lv67 加载失败: {e}")
        
        # 🎯 Prompt 膨胀控制 — 验证/调优阶段添加
        MAX_CONTEXT_LENGTH = 3000
        context_len = len(context_summary)
        if context_len > MAX_CONTEXT_LENGTH:
            logger.warning(f"[Prompt调优] context_summary 过长 ({context_len} 字符)，截断到 {MAX_CONTEXT_LENGTH}")
            context_summary = context_summary[:MAX_CONTEXT_LENGTH] + "\n\n...（上下文已截断以控制成本）"
        else:
            logger.info(f"[Prompt调优] context_summary 长度: {context_len} 字符")
        
        # Check cache before generating
        cache_key = cost_optimizer.generate_cache_key(news_text, context_summary)
        cached_response = cost_optimizer.get_cached_response(cache_key)
        
        if cached_response:
            logger.info("Using cached AI response (cost saved!)")
            return cached_response
        
        # Assess content importance and get optimized parameters
        importance_level = cost_optimizer.assess_content_importance(data)
        optimized_params = cost_optimizer.get_optimized_params(importance_level)
        logger.info(f"Content importance: {importance_level}, using params: {optimized_params}")
        
        # Compress input data to save tokens
        compressed_news_text = cost_optimizer.compress_input_data(data, max_items_per_source=5)
        
        # Create AI prompt
        date_obj = datetime.strptime(data.date, "%Y-%m-%d") if data.date else datetime.now()
        weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][date_obj.weekday()]
        
        # ═══════════════════════════════════════════════════════════
        # 🔥 关键：输出格式要求必须前置，防止 Prompt 过长被截断
        # ═══════════════════════════════════════════════════════════
        system_prompt = f"""你是一位资深科技媒体主编。你的任务是将热点数据转化为一篇**有深度、有洞察**的专业文章。

## ⚠️ 输出格式（必须严格遵守，否则文章无效）

1. **首先输出 Frontmatter**（以 `---` 开始和结束）：
```yaml
---
title: "有吸引力的标题"  # 禁止纯日期标题
published: {data.date}T08:00:00+08:00
tags: [科技, AI, 相关标签]  # 3-6个中文标签，科技类≥50%
category: news
draft: false
image: https://picsum.photos/seed/英文关键词/1600/900
description: "一句话概括文章核心价值"
---
```
2. **封面图后不要添加图片**
3. **每个深度分析板块配1张图**，seed 必须与内容相关（英文关键词）
4. **使用中文标签**，禁止英文标签
5. **提到GitHub项目时用** `::github{{repo="owner/repo"}}`

## 文章结构

### 开篇引言（200-300字）
提炼核心特征，设置悬念，**禁止罗列热点**。

### 深度分析（2-3个板块，每段400-600字）
- 小标题概括核心观点
- 解释技术原理，引用具体数据
- 预测3-6个月趋势
- 每板块至少1个表格 + 1个 `:::note[💡 关键洞察]`
- 跨领域关联

### 平台热点精选（5-8个）
格式：`**平台名**：[标题](链接) - 一句话锐评`

### 趋势观察（3-4条，有序列表）

### 结语（200-300字）
呼应开篇，形成闭环。

## 内容策略
- 优先：AI技术 > 开源生态 > 科技商业 > 产品创新
- 避免：政治流水账、娱乐八卦、与科技无关的国际冲突
- 科技内容占比 ≥ 70%
- 没有重磅科技新闻时，写技术趋势分析/开源推荐/AI工具评测

## 禁忌
- ❌ 把输入的热点问题直接复制到核心观点中
- ❌ 把输入数据原样输出（你不是复读机）
- ❌ 流水账、模糊表述（"据悉""据报道"）
- ❌ 关键词使用无意义的词（如"有了更多的了""了解"）
- ❌ 超过2000字

记住：你是**主编**，你有决策权。选择最有价值的科技话题，用你最擅长的角度深入分析。提供**经过筛选、分析、提炼的高价值内容**！"""
        
        # 🧬 动态Prompt优化 - 根据历史评分自动调整
        try:
            from evolution.prompt_optimizer import get_optimized_prompt_params
            _, optimized_temp, optimized_tokens = get_optimized_prompt_params(
                system_prompt, 
                base_temp=optimized_params['temperature'],
                base_tokens=optimized_params['max_tokens']
            )
            optimized_params['temperature'] = optimized_temp
            optimized_params['max_tokens'] = optimized_tokens
        except Exception as e:
            logger.warning(f"Prompt优化失败，使用默认参数: {e}")
        
        user_prompt = f"""请为以下日期生成一篇专业的热点聚合文章：

**日期**：{data.date} ({weekday_cn})
**标题**：{title}
**监测平台数**：{len(data.items)} 个
**热点总数**：{total_count} 条

**热点数据（精选 Top 5/平台）**：
{compressed_news_text}

{context_summary}
"""
        
        # 📊 数据增强 - 从RSS中提取数据点
        try:
            from evolution.data_enhancer import get_data_enhancement
            data_enhancement = get_data_enhancement(compressed_news_text)
            if data_enhancement:
                user_prompt += data_enhancement
                logger.info("[数据增强] 已注入数据点提示")
        except Exception as e:
            logger.warning(f"[数据增强] 失败: {e}")
        
        # 🔗 注入跨源关联洞察
        if cross_source_insights:
            user_prompt += cross_source_insights
            logger.info("[跨源关联] 已注入跨平台话题分析")
        
        # 🔮 注入趋势预测洞察
        try:
            from evolution.trend_predictor import get_trend_insight
            trend_insight = get_trend_insight()
            if trend_insight:
                user_prompt += trend_insight
                logger.info("[趋势预测] 已注入预测洞察")
        except Exception as e:
            logger.warning(f"[趋势预测] 失败: {e}")
        
        # 😊😠 注入情感分析洞察
        try:
            from evolution.emotion_analyzer import get_emotion_insight
            # 收集所有热点标题
            all_titles = []
            for items_list in data.items.values():
                for item in items_list:
                    title = getattr(item, 'title', '')
                    if title:
                        all_titles.append(title)
            
            if all_titles:
                emotion_insight = get_emotion_insight(all_titles)
                if emotion_insight:
                    user_prompt += emotion_insight
                    logger.info("[情感分析] 已注入情感洞察")
        except Exception as e:
            logger.warning(f"[情感分析] 失败: {e}")
        
        # 🕸️ 注入知识图谱洞察（Lv23）
        try:
            from evolution.knowledge_graph import get_knowledge_graph_insight
            # 从热点标题构建临时内容用于实体识别
            temp_content = "\n".join([
                getattr(item, 'title', '') 
                for items_list in data.items.values() 
                for item in items_list
            ])
            if temp_content:
                kg_insight = get_knowledge_graph_insight(temp_content)
                if kg_insight:
                    user_prompt += kg_insight
                    logger.info("[知识图谱] 已注入实体关系洞察")
        except Exception as e:
            logger.warning(f"[知识图谱] 失败: {e}")
        
        # 👤 注入读者画像洞察（Lv24）
        try:
            from evolution.reader_analytics import get_reader_insight
            reader_insight = get_reader_insight()
            if reader_insight:
                user_prompt += reader_insight
                logger.info("[读者画像] 已注入读者偏好洞察")
        except Exception as e:
            logger.warning(f"[读者画像] 失败: {e}")
        
        # ⚡ 注入实时热点追踪洞察（Lv25）
        try:
            from evolution.retime_tracker import get_urgency_insight
            if all_titles:
                urgency_insight = get_urgency_insight(all_titles)
                if urgency_insight:
                    user_prompt += urgency_insight
                    logger.info("[实时追踪] 已注入紧急度洞察")
        except Exception as e:
            logger.warning(f"[实时追踪] 失败: {e}")
        
        # 📊 注入进化效果评估洞察（Lv31）
        try:
            from evolution.evolution_effect_evaluator import get_evolution_effect_insight
            effect_insight = get_evolution_effect_insight()
            if effect_insight:
                user_prompt += effect_insight
                logger.info("[进化效果] 已注入效果评估洞察")
        except Exception as e:
            logger.warning(f"[进化效果] 失败: {e}")
        
        # 📡 注入RSS源推荐洞察（Lv32）
        try:
            from evolution.rss_recommender import get_rss_recommendation_insight
            rss_rec_insight = get_rss_recommendation_insight()
            if rss_rec_insight:
                user_prompt += rss_rec_insight
                logger.info("[RSS推荐] 已注入源推荐洞察")
        except Exception as e:
            logger.warning(f"[RSS推荐] 失败: {e}")
        
        # 🔮 注入异常预测洞察（Lv35）
        try:
            from evolution.exception_predictor import get_exception_prediction
            prediction_insight = get_exception_prediction()
            if prediction_insight:
                user_prompt += prediction_insight
                logger.info("[异常预测] 已注入预防建议")
        except Exception as e:
            logger.warning(f"[异常预测] 失败: {e}")
        
        # 🚨 注入异常监控洞察（Lv33）
        try:
            from evolution.exception_monitor import get_exception_monitor_report
            monitor_report = get_exception_monitor_report()
            if monitor_report:
                user_prompt += monitor_report
                logger.info("[异常监控] 已注入监控报告")
        except Exception as e:
            logger.warning(f"[异常监控] 失败: {e}")
        
        # 🔧 注入异常修复洞察（Lv34）
        try:
            from evolution.exception_healer import get_heal_report
            heal_report = get_heal_report()
            if heal_report:
                user_prompt += heal_report
                logger.info("[异常修复] 已注入修复报告")
        except Exception as e:
            logger.warning(f"[异常修复] 失败: {e}")
        
        # 📦 注入仓库体积监控洞察（Lv36）
        try:
            from evolution.repo_size_monitor import get_repo_size_insight
            size_insight = get_repo_size_insight()
            if size_insight:
                user_prompt += size_insight
                logger.info("[体积监控] 已注入体积报告")
        except Exception as e:
            logger.warning(f"[体积监控] 失败: {e}")
        
        # 🔭 注入跨项目学习洞察（Lv42）
        try:
            from evolution.cross_project_learner import learn_cross_project
            cross_project_insight = learn_cross_project()
            if cross_project_insight:
                user_prompt += cross_project_insight
                logger.info("[跨项目学习] 已注入GitHub Trending/HN洞察")
        except Exception as e:
            logger.warning(f"[跨项目学习] 失败: {e}")
        
        # 🎯 注入Prompt效果追踪洞察（Lv39）
        try:
            from evolution.prompt_tracker import get_prompt_effectiveness_report
            prompt_effect_report = get_prompt_effectiveness_report()
            if prompt_effect_report:
                user_prompt += prompt_effect_report
                logger.info("[Prompt追踪] 已注入效果报告")
        except Exception as e:
            logger.warning(f"[Prompt追踪] 失败: {e}")
        
        # 🎯 注入Prompt优化建议（Lv40）
        try:
            from evolution.prompt_optimizer import get_prompt_optimization_report
            prompt_opt_report = get_prompt_optimization_report()
            if prompt_opt_report:
                user_prompt += prompt_opt_report
                logger.info("[Prompt优化] 已注入优化建议")
        except Exception as e:
            logger.warning(f"[Prompt优化] 失败: {e}")
        
        # 🧬 Lv71: 注入结构化Prompt版本反馈 — 替代文本追加
        try:
            from evolution.prompt_versioning import PromptVersionManager
            pvm = PromptVersionManager('.')
            from evolution.data_pipeline import DataPipeline
            dp = DataPipeline('.')
            metrics = dp.query_records("metric", hours=168)  # 最近7天指标
            structured_feedback = pvm.generate_structured_feedback(metrics)
            if structured_feedback:
                user_prompt += f"\n\n{structured_feedback}"
                logger.info("[Lv71] PromptVersionManager 结构化反馈已注入")
        except Exception as e:
            logger.debug(f"[Lv71] PromptVersionManager 反馈注入失败: {e}")
        
        # 🧬 注入Prompt进化引擎报告（Lv41）
        try:
            from evolution.prompt_evolution import get_prompt_evolution_report
            prompt_evo_report = get_prompt_evolution_report()
            if prompt_evo_report:
                user_prompt += prompt_evo_report
                logger.info("[Prompt进化] 已注入进化报告")
        except Exception as e:
            logger.warning(f"[Prompt进化] 失败: {e}")
        
        # 🎯 Prompt片段追踪记录（Lv39）
        try:
            from evolution.prompt_tracker import record_prompt_fragments
            fragments_used = []
            fragment_markers = {
                "quality_feedback": "历史文章质量反馈",
                "data_enhancement": "### 📊 数据增强",
                "cross_source": "### 🔗 跨源关联",
                "trend_forecast": "### 🔮 趋势预测",
                "emotion_analysis": "### 😊😠 情感分析",
                "knowledge_graph": "### 🕸️ 知识图谱",
                "reader_profile": "### 👤 读者画像",
                "realtime_tracking": "### ⚡ 实时热点",
                "self_design": "### 🎨 自主功能设计",
                "evolution_effect": "### 📊 进化效果评估",
                "rss_recommend": "### 📡 RSS源智能推荐",
                "exception_prediction": "### 🔮 异常预测与预防",
                "exception_monitor": "### 🚨 异常监控报告",
                "exception_heal": "### 🔧 异常修复报告",
                "repo_size": "### 📦 仓库体积监控",
                "cross_project": "### 🔭 跨项目技术趋势洞察",
            }
            for fragment_id, marker in fragment_markers.items():
                if marker in user_prompt:
                    fragments_used.append(fragment_id)
            article_id = f"{data.date}_{hash(title) % 10000}"
            record_prompt_fragments(article_id, fragments_used)
            logger.info(f"[Prompt追踪] 记录{len(fragments_used)}个片段: {fragments_used}")
        except Exception as e:
            logger.warning(f"[Prompt追踪] 记录失败: {e}")
        
        # 🔥 Prompt 长度控制 — 防止输出要求被截断
        MAX_USER_PROMPT_LEN = 8000
        prompt_len = len(user_prompt)
        if prompt_len > MAX_USER_PROMPT_LEN:
            logger.warning(f"[Prompt控制] user_prompt 过长 ({prompt_len} 字符)，截断辅助上下文")
            # 保留核心数据（前面部分），截断后面的辅助注入
            # 找到 "热点数据" 部分结束的位置，从那里截断
            core_end = user_prompt.find("\n\n**⚠️ 输出")
            if core_end == -1:
                core_end = user_prompt.find("\n\n**⚠️ 重要")
            if core_end == -1:
                core_end = len(user_prompt) // 2
            user_prompt = user_prompt[:core_end] + f"""

（辅助上下文因长度限制已截断，共 {prompt_len} 字符）

**⚠️ 提醒**：你是主编。基于以上热点数据，创作一篇深度科技分析文章。
- 先输出 Frontmatter（格式要求见系统提示）
- 然后写正文：引言 → 2-3个深度分析板块（每板块有表格+Admonition） → 平台热点精选 → 趋势观察 → 结语
- 不要复制输入的热点问题作为核心观点
- 关键词必须是中文，3-6个，科技类≥50%
"""
        
        user_prompt += f"""

请立即输出完整 Markdown 文章（控制字数在 {optimized_params['max_tokens']//4} 字以内）！"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call AI API with optimized parameters
        logger.info("Calling AI API to generate article...")
        ai_content = ai_client.chat(
            messages, 
            temperature=optimized_params['temperature'],
            max_tokens=optimized_params['max_tokens']
        )
        
        if not ai_content or len(ai_content.strip()) < 100:
            raise ValueError("AI generated content is too short or empty")
        
        # Estimate token usage (rough estimate: 1 Chinese char ≈ 1.5 tokens)
        estimated_tokens = int(len(ai_content) * 1.5 + len(str(messages)) * 0.5)
        logger.info(f"AI generated {len(ai_content)} characters (~{estimated_tokens} tokens)")
        
        # 🔬 科技内容检测
        try:
            from evolution.tech_content_guard import check_tech_content
            is_pass, tech_message = check_tech_content(ai_content, min_ratio=0.7)
            if is_pass:
                logger.info(f"[科技检测] {tech_message}")
            else:
                logger.warning(f"[科技检测] {tech_message[:100]}...")
                # 将科技内容不足的信息记录到metrics中，供Prompt优化器使用
                # 不强制重写以避免额外API成本
        except Exception as e:
            logger.warning(f"[科技检测] 检测失败: {e}")
        
        # 🔍 强制输出格式验证
        is_valid, validation_msg = self._validate_article_format(ai_content, data.date)
        if not is_valid:
            logger.warning(f"[格式验证] 文章格式不合格: {validation_msg}")
            # 记录到异常监控供后续分析
            try:
                from evolution.exception_monitor import record_exception
                record_exception("ARTICLE_FORMAT_INVALID", validation_msg, {"title": title, "date": data.date})
            except Exception:
                pass
        else:
            logger.info(f"[格式验证] 文章格式检查通过: {validation_msg}")
        
        # Cache the response
        cost_optimizer.cache_response(cache_key, ai_content, estimated_tokens)
        
        # Save article metadata to history for future context
        try:
            gh_token = os.environ.get("GH_MEMORY_TOKEN")
            astro_owner = os.environ.get("ASTRO_REPO_OWNER", "garcci")
            astro_repo = os.environ.get("ASTRO_REPO_NAME", "Astro")
            
            # Extract keywords from title and content (simple extraction)
            import re
            
            # 提取纯文本内容（去掉frontmatter）用于生成excerpt
            # AI返回的内容包含frontmatter(---...---)，需要跳过
            content_for_excerpt = ai_content
            if '---' in ai_content:
                # 跳过frontmatter，取第一个---之后的内容
                parts = ai_content.split('---', 2)
                if len(parts) >= 3:
                    content_for_excerpt = parts[2]
            
            # 去掉markdown标记，取纯文本前300字符作为excerpt
            clean_text = re.sub(r'[#*>`\[\]\(\)!\n\r]', '', content_for_excerpt)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            excerpt = clean_text[:300] if len(clean_text) > 300 else clean_text
            
            keywords = re.findall(r'[\u4e00-\u9fa5]{2,6}', ai_content[:500])  # First 500 chars
            # Filter common words
            stop_words = {'今日', '热点', '分析', '深度', '平台', '趋势'}
            keywords = list(set([kw for kw in keywords if kw not in stop_words]))[:10]
            
            # Extract hot topics from content (hashtags or bold text)
            hot_topics_match = re.findall(r'\*\*(.+?)\*\*', ai_content[:1000])
            hot_topics = [t for t in hot_topics_match if len(t) > 2][:5]
            
            metadata = {
                'date': data.date,
                'title': title,
                'excerpt': excerpt,
                'keywords': keywords,
                'hot_topics': hot_topics,
                'platforms': list(data.id_to_name.values()),
                'timestamp': datetime.now().isoformat()
            }
            
            # Save to GitHub Issues Memory (persistent)
            if gh_token:
                from .github_issues_memory import GitHubIssuesMemory
                memory_backend = GitHubIssuesMemory(astro_owner, astro_repo, gh_token)
                success = memory_backend.save_article_metadata(metadata)
                logger.warning(f"Save to GitHub Issues result: {success}")
                if success:
                    logger.warning("Article metadata saved to GitHub Issues (persistent)")
                else:
                    logger.warning("Failed to save to GitHub Issues - check API response")
            else:
                # Fallback to local history manager (non-persistent)
                history_mgr = ArticleHistoryManager()
                history_mgr.save_article_metadata(metadata)
                logger.warning("Article metadata saved to local history (will be lost)")
        except Exception as e:
            logger.warning(f"Failed to save article metadata: {e}")
        
        # 🧬 AI 进化系统 - 评估文章质量并记录改进建议
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from evolution.evolution_system import evaluate_and_evolve
            from evolution import record_article_metrics
            gh_token = os.environ.get("GH_MEMORY_TOKEN")
            astro_owner = os.environ.get("ASTRO_REPO_OWNER", "garcci")
            astro_repo = os.environ.get("ASTRO_REPO_NAME", "Astro")
            if gh_token:
                # 先进行评估
                improvement_prompt = evaluate_and_evolve(
                    ai_content, title, astro_owner, astro_repo, gh_token
                )
                if improvement_prompt:
                    logger.warning(f"[进化系统] 文章评估完成，生成改进建议: {len(improvement_prompt)} 字符")
                else:
                    logger.warning("[进化系统] 文章评估完成，无需改进")
                
                # 然后记录到自适应进化系统的指标数据库
                # 注意：evaluate_and_evolve 内部已经保存了评估结果
                # 这里我们额外记录到新的结构化数据库
                try:
                    # 重新获取评估结果用于记录
                    from evolution.evolution_system import AIEvolutionSystem
                    evo = AIEvolutionSystem(astro_owner, astro_repo, gh_token)
                    evaluation = evo.evaluate_article(ai_content, title)
                    record_article_metrics(astro_owner, astro_repo, gh_token, evaluation, prompt_version="v2")
                    logger.warning("[自适应进化] 已记录文章指标到趋势数据库")
                    
                    # 🗄️ 同时记录到D1数据库（解决Issues截断问题）
                    try:
                        from evolution.storage_d1 import get_evolution_data_store
                        d1_store = get_evolution_data_store()
                        d1_store.save_article_metric({
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'title': title,
                            'overall_score': evaluation.get('overall_score', 0),
                            'tech_content_ratio': evaluation.get('dimensions', {}).get('tech_content_ratio', {}).get('score', 0),
                            'analysis_depth': evaluation.get('dimensions', {}).get('analysis_depth', {}).get('score', 0),
                            'style_diversity': evaluation.get('dimensions', {}).get('style_diversity', {}).get('score', 0),
                            'insightfulness': evaluation.get('dimensions', {}).get('insightfulness', {}).get('score', 0),
                            'readability': evaluation.get('dimensions', {}).get('readability', {}).get('score', 0),
                            'model_used': 'deepseek-reasoner',
                            'cost': 0.02
                        })
                        logger.warning("[D1存储] 文章指标已保存到D1数据库")
                    except Exception as d1e:
                        logger.warning(f"[D1存储] 保存到D1失败（降级到文件）: {d1e}")
                except Exception as e2:
                    logger.warning(f"[自适应进化] 记录指标失败: {e2}")
            else:
                logger.warning("[进化系统] 跳过评估：未配置 GH_MEMORY_TOKEN")
        except Exception as e:
            logger.warning(f"[进化系统] 评估失败: {e}")
        
        return ai_content
    
    def _sanitize_frontmatter(self, content: str, date_str: str, fallback_title: str) -> str:
        """
        修复 frontmatter 中的 YAML 格式问题，确保 Astro 能正确解析。

        处理的问题：
        1. title/description 中的双引号嵌套（导致 YAML 解析失败）
        2. title/description 没有用引号包裹（含有特殊字符时 YAML 解析失败）
        3. 中文引号污染（AI 可能输出中文引号）
        4. 缺少 frontmatter（AI 未输出或后续处理破坏）
        5. 缺少必要字段
        """
        import re

        # 检查是否有 frontmatter
        has_frontmatter = content.startswith("---")

        if has_frontmatter:
            m = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
            if not m:
                # frontmatter 格式异常，重新生成
                has_frontmatter = False

        if not has_frontmatter:
            # 缺少 frontmatter，添加默认的
            safe_title = fallback_title.replace('"', '\\"')
            default_fm = f"""---
title: "{safe_title}"
published: {date_str}T08:00:00+08:00
tags: [新闻, 热点]
category: news
draft: false
image: https://picsum.photos/seed/trendradar-{int(datetime.now().timestamp())}/1600/900
description: "TrendRadar 自动生成的热点聚合报告"
---

"""
            return default_fm + content

        # 提取并修复 frontmatter
        m = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        fm = m.group(1)
        body = content[m.end():]

        # ═══════════════════════════════════════════════════════════
        # 逐行处理 frontmatter，强制修复关键字段
        # ═══════════════════════════════════════════════════════════
        lines = fm.split('\n')
        fixed_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                fixed_lines.append(line)
                continue

            # 只处理 key: value 格式的行
            if ':' not in line_stripped:
                fixed_lines.append(line)
                continue

            key = line_stripped.split(':', 1)[0].strip()
            val_part = line_stripped.split(':', 1)[1].strip()

            # 只处理需要强制引号的字符串字段
            if key not in ('title', 'description', 'excerpt', 'image'):
                fixed_lines.append(line)
                continue

            # 如果值已经被引号包裹，修复嵌套引号
            if (val_part.startswith('"') and val_part.endswith('"')) or \
               (val_part.startswith("'") and val_part.endswith("'")):
                quote_char = val_part[0]
                inner = val_part[1:-1]

                # 中文引号 → 英文引号
                inner = inner.replace('"', '"').replace('"', '"')

                if quote_char == '"' and '"' in inner:
                    # 双引号嵌套
                    if "'" not in inner:
                        line = f'{key}: \'{inner}\''
                    else:
                        safe = inner.replace('"', '\\"')
                        line = f'{key}: "{safe}"'
                else:
                    line = f'{key}: {quote_char}{inner}{quote_char}'
            else:
                # 值没有被引号包裹 —— 这是最常见的问题！
                # 先清理中文引号
                val_part = val_part.replace('"', '"').replace('"', '"')

                # 如果值包含英文双引号，用单引号包裹；否则用双引号
                if '"' in val_part:
                    if "'" not in val_part:
                        line = f"{key}: '{val_part}'"
                    else:
                        safe = val_part.replace('"', '\\"')
                        line = f'{key}: "{safe}"'
                else:
                    line = f'{key}: "{val_part}"'

            fixed_lines.append(line)

        fm = '\n'.join(fixed_lines)

        # 确保必要字段存在
        required_fields = {
            'title': f'title: "{fallback_title.replace(chr(34), chr(92)+chr(34))}"',
            'published': f'published: {date_str}T08:00:00+08:00',
            'category': 'category: news',
            'draft': 'draft: false',
        }
        for field, default_value in required_fields.items():
            if not re.search(rf'^{field}:', fm, re.MULTILINE):
                fm += f"\n{default_value}"

        return f"---\n{fm}\n---\n{body}"
    
    def _validate_article_format(self, content: str, date_str: str) -> tuple:
        """
        验证AI生成文章的输出格式是否符合要求。
        检查 frontmatter、核心观点、关键词质量等。
        
        Returns:
            (is_valid: bool, message: str)
        """
        import re
        
        issues = []
        
        # 1. 检查 Frontmatter 存在性
        if not content.startswith('---'):
            issues.append("缺少 Frontmatter 开头标记")
        
        # 2. 提取 Frontmatter
        fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            issues.append("Frontmatter 格式错误（未找到 ---...---）")
        else:
            fm = fm_match.group(1)
            
            # 3. 检查必要字段
            required = ['title:', 'published:', 'tags:', 'category:', 'draft:', 'image:', 'description:']
            for field in required:
                if field not in fm:
                    issues.append(f"Frontmatter 缺少字段: {field}")
            
            # 4. 检查 title 是否为纯日期格式
            title_match = re.search(r'title:\s*["\']?([^"\'\n]+)', fm)
            if title_match:
                title_val = title_match.group(1).strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}', title_val) or '每日热点' in title_val:
                    issues.append(f"标题机械无吸引力: {title_val[:30]}")
            else:
                issues.append("无法解析 title 字段")
            
            # 5. 检查 tags 质量
            tags_match = re.search(r'tags:\s*\[(.*?)\]', fm)
            if tags_match:
                tags_str = tags_match.group(1)
                tags = [t.strip().strip('"').strip("'") for t in tags_str.split(',')]
                # 检查是否有无意义标签
                meaningless = {'了解', '的', '了', '和', '与', '或', '是', '有了', '有了更多的了'}
                bad_tags = [t for t in tags if t in meaningless or len(t) < 2]
                if bad_tags:
                    issues.append(f"标签质量差: {bad_tags}")
                # 允许常见英文科技缩写
                tech_abbreviations = {'AI', 'API', 'GPU', 'LLM', 'GPT', 'CPU', 'NLP', 'CV', 'ML', 'DL', 'IoT', '5G', 'AR', 'VR', 'XR', 'OS', 'UI', 'UX', 'SaaS', 'PaaS', 'IaaS'}
                has_chinese = any(len(t) >= 2 and '\\u4e00' <= t[0] <= '\\u9fa5' for t in tags)
                has_tech_abbr = any(t.upper() in tech_abbreviations for t in tags)
                if not has_chinese and not has_tech_abbr:
                    issues.append("标签非中文且无科技含义")
            else:
                issues.append("无法解析 tags 字段")
            
            # 6. 检查 description
            desc_match = re.search(r'description:\s*["\']?([^"\'\n]+)', fm)
            if desc_match:
                desc = desc_match.group(1).strip()
                if len(desc) < 10 or desc.startswith('====') or desc.startswith('---'):
                    issues.append(f"description 无效: {desc[:30]}")
            else:
                issues.append("缺少 description")
        
        # 7. 检查正文是否复制了输入数据（知乎问题列表等）
        body = content.split('---', 2)[-1] if '---' in content else content
        # 检测常见的问题列表模式
        question_patterns = [
            r'具体是怎么回事\?',
            r'如何看待这一事件\?',
            r'背后有什么科学原理\?',
            r'我们为何要研究',
            r'这种相处模式为什么',
        ]
        for pattern in question_patterns:
            if re.search(pattern, body):
                issues.append("正文包含未加工的热搜问题（复制输入数据）")
                break
        
        # 8. 检查核心观点是否变成问题列表
        if '核心观点' in body:
            # 提取核心观点部分
            kp_match = re.search(r'核心观点[:：]\s*\n(.*?)(?:\n##|\n###|</aside>|$)', body, re.DOTALL)
            if kp_match:
                kp_section = kp_match.group(1)
                # 如果核心观点中有太多问号，说明是问题列表
                question_count = kp_section.count('？') + kp_section.count('?')
                line_count = kp_section.count('\\n')
                if question_count > 2 and question_count > line_count * 0.3:
                    issues.append("核心观点被替换为问题列表（AI未正确理解任务）")
        
        # 9. 检查文章长度（frontmatter 约 200 字符，正文至少 300 字符）
        body_only = content.split('---', 2)[-1] if '---' in content else content
        if len(body_only.strip()) < 200:
            issues.append(f"正文过短: {len(body_only)} 字符")
        
        if issues:
            return False, "; ".join(issues[:3])  # 最多返回3个问题
        return True, "格式检查通过"
    
    def _push_to_github(self, filepath: str, content: str, commit_message: str) -> None:
        """
        Push file to GitHub repository using Git Data API.
        
        Steps:
        1. Get the latest commit SHA of the branch
        2. Create a blob with the file content
        3. Get the tree SHA from the latest commit
        4. Create a new tree with the new file
        5. Create a new commit
        6. Update the branch reference
        
        Args:
            filepath: Path in the repository
            content: File content
            commit_message: Commit message
        """
        import requests
        
        # Step 1: Get latest commit SHA
        ref_url = f"{self.base_url}/git/refs/heads/{self.branch}"
        response = requests.get(ref_url, headers=self.headers)
        response.raise_for_status()
        latest_commit_sha = response.json()["object"]["sha"]
        logger.debug(f"Latest commit SHA: {latest_commit_sha}")
        
        # Step 2: Create blob
        blob_url = f"{self.base_url}/git/blobs"
        blob_data = {
            "content": content,
            "encoding": "utf-8"
        }
        response = requests.post(blob_url, headers=self.headers, json=blob_data)
        response.raise_for_status()
        blob_sha = response.json()["sha"]
        logger.debug(f"Created blob: {blob_sha}")
        
        # Step 3: Get tree SHA from latest commit
        commit_url = f"{self.base_url}/git/commits/{latest_commit_sha}"
        response = requests.get(commit_url, headers=self.headers)
        response.raise_for_status()
        tree_sha = response.json()["tree"]["sha"]
        logger.debug(f"Tree SHA: {tree_sha}")
        
        # Step 4: Create new tree with the file
        tree_url = f"{self.base_url}/git/trees"
        tree_data = {
            "base_tree": tree_sha,
            "tree": [
                {
                    "path": filepath,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha
                }
            ]
        }
        response = requests.post(tree_url, headers=self.headers, json=tree_data)
        response.raise_for_status()
        new_tree_sha = response.json()["sha"]
        logger.debug(f"New tree SHA: {new_tree_sha}")
        
        # Step 5: Create new commit
        commit_url = f"{self.base_url}/git/commits"
        commit_data = {
            "message": commit_message,
            "tree": new_tree_sha,
            "parents": [latest_commit_sha]
        }
        response = requests.post(commit_url, headers=self.headers, json=commit_data)
        response.raise_for_status()
        new_commit_sha = response.json()["sha"]
        logger.debug(f"New commit SHA: {new_commit_sha}")
        
        # Step 6: Update branch reference
        update_ref_url = f"{self.base_url}/git/refs/heads/{self.branch}"
        update_data = {
            "sha": new_commit_sha,
            "force": False
        }
        response = requests.patch(update_ref_url, headers=self.headers, json=update_data)
        response.raise_for_status()
        logger.info(f"Branch updated: {self.branch} -> {new_commit_sha}")
    
    def cleanup_old_data(self, retention_days: int) -> int:
        """Cleanup old data (not applicable for GitHub backend)"""
        return 0
    
    def save_html_report(self, html_content: str, filename: str) -> None:
        """Save HTML report (not supported for GitHub backend)"""
        logger.warning("HTML reports are not supported by GitHub storage backend")
        pass
    
    def save_txt_snapshot(self, data) -> bool:
        """Save TXT snapshot (not supported for GitHub backend)"""
        logger.warning("TXT snapshots are not supported by GitHub storage backend")
        return False
    
    def detect_new_rss_items(self, current_data) -> dict:
        """Detect new RSS items (not supported for GitHub backend)"""
        logger.warning("RSS detection is not supported by GitHub storage backend")
        return {}
    
    def get_latest_rss_data(self, date=None):
        """Get latest RSS data (not supported for GitHub backend)"""
        logger.warning("RSS data retrieval is not supported by GitHub storage backend")
        return None
    
    def get_rss_data(self, date=None):
        """Get RSS data (not supported for GitHub backend)"""
        logger.warning("RSS data retrieval is not supported by GitHub storage backend")
        return None
    
    def save_rss_data(self, data) -> bool:
        """Save RSS data (not supported for GitHub backend)"""
        logger.warning("RSS data saving is not supported by GitHub storage backend")
        return False
    
    # Delegate read operations to local storage
    def get_today_all_data(self, date=None):
        """Get today's data by delegating to local storage"""
        try:
            from .local import LocalStorageBackend
            local_backend = LocalStorageBackend()
            return local_backend.get_today_all_data(date)
        except Exception as e:
            logger.warning(f"Failed to get today's data from local storage: {e}")
            return None
    
    def get_latest_crawl_data(self, date=None):
        """Get latest crawl data by delegating to local storage"""
        try:
            from .local import LocalStorageBackend
            local_backend = LocalStorageBackend()
            return local_backend.get_latest_crawl_data(date)
        except Exception as e:
            logger.warning(f"Failed to get latest crawl data from local storage: {e}")
            return None
    
    def detect_new_titles(self, current_data):
        """Detect new titles by delegating to local storage"""
        try:
            from .local import LocalStorageBackend
            local_backend = LocalStorageBackend()
            return local_backend.detect_new_titles(current_data)
        except Exception as e:
            logger.warning(f"Failed to detect new titles from local storage: {e}")
            return {}
