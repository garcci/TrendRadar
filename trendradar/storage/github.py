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
        self.branch = os.getenv("ASTRO_BRANCH", "master")
        
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
        
        # Check if we already generated an article today
        # If yes, skip to avoid duplicates (simple and reliable)
        # NOTE: Temporarily disabled for testing
        # try:
        #     existing_articles = self._check_existing_articles(date_str)
        #     if existing_articles:
        #         logger.warning(f"Found {len(existing_articles)} existing article(s) for {date_str}, skipping to avoid duplicates")
        #         return False
        # except Exception as e:
        #     logger.warning(f"Could not check existing articles: {e}, proceeding anyway")
        
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
        
        # Push to GitHub
        try:
            self._push_to_github(filepath, markdown_content, f"feat: add TrendRadar report - {article_title}")
            logger.info(f"Successfully pushed article to GitHub: {filepath}")
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
                        except Exception:
                            pass
            
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
        
        lines = [
            "---",
            f"title: \"{title}\"",
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
        from ..ai.client import AIClient
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
            ai_client = AIClient(ai_config)
            
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
        
        # 🧬 获取进化反馈上下文（基于历史文章评估的改进建议）
        evolution_context = ""
        try:
            if gh_token:
                from ..evolution.evolution_system import AIEvolutionSystem
                evolution_system = AIEvolutionSystem(astro_owner, astro_repo, gh_token)
                evolution_context = evolution_system.get_evolution_context()
                if evolution_context:
                    logger.info(f"[进化系统] 加载改进建议: {len(evolution_context)} 字符")
        except Exception as e:
            logger.warning(f"[进化系统] 加载进化上下文失败: {e}")
        
        # 将进化反馈合并到 context_summary 中
        if evolution_context:
            context_summary += evolution_context
        
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
        
        system_prompt = """你是一位资深的新闻主编和深度内容创作者，拥有10年以上的媒体经验。你的任务是将热点资讯转化为一篇**有深度、有洞察、有价值**的专业文章。

## 核心要求

### 1. 不要简单罗列！
- ❌ 错误做法：只是把标题搬过来
- ✅ 正确做法：分析热点背后的逻辑、趋势、影响

### 2. 提供独特价值
- **深度解读**：为什么这个热点重要？背后有什么深层原因？
- **横向对比**：不同平台的热点有什么关联？反映了什么社会现象？
- **纵向分析**：这个事件的发展趋势如何？未来可能怎样演变？
- **实用建议**：读者应该关注什么？如何应对？

### 3. 内容策略（由你决定）
**你是一位资深科技主编，拥有完全的内容决策权。**

- 🎯 **你的任务**：从今日热点中，挖掘出最有价值的科技/AI/开源内容，写一篇深度文章
- 🎯 **你的判断**：什么话题值得深入？什么角度最独特？什么分析最有洞察？**由你决定，而不是被规定**
- 🎯 **你的风格**：每篇文章用不同的分析框架，不要重复相同的结构
  - 可选角度：技术原理深度解析、行业影响与趋势预测、开发者实战指南、开源生态观察、投资与商业分析、产品体验评测
  - 可选结构：对比分析型、故事叙事型、问题-解答型、时间线梳理型、跨界关联型

- 💡 **内容建议**（参考，不强制）：
  - AI 模型新能力与底层原理（DeepSeek、GPT、Claude、Llama 等）
  - 开源项目与技术工具（GitHub Trending、新框架、开发工具）
  - AI 基础设施与硬件（芯片、算力、液冷、能源）
  - 前沿技术突破（量子计算、脑机接口、航天科技）
  - 科技产业动态（产品发布、财报、并购、政策）

- ⚠️ **避免**：纯社会新闻流水账、地缘政治流水账、娱乐八卦

### 4. 文章结构（必须包含）

#### 开篇引言（200-300字）
- 今日热点的整体态势
- 最值得关注的3-5个核心事件
- **不要简单罗列**，而是提炼今日舆情的核心特征
- 设置悬念或提出问题，吸引读者继续阅读

#### 文章标题要求
- **禁止**使用 "TrendRadar Report - 日期" 这种机械标题
- 标题要有**吸引力、悬念感、观点性**
- 可以是对今日热点的精准概括、金句提炼、或引发思考的反问
- 示例好标题：
  - "俄乌冲突500天：世界学到了什么？"
  - "当'报复性消费'变成'报复性存钱'"
  - "ChatGPT抢不走的工作，正在被另一种AI取代"
  - "一场颁奖典礼，照出了中国电影的体面与尴尬"

#### 深度分析板块（重点！每个 400-600字）
选择2-3个最有价值的热点，每个进行深度分析：
- **小标题要有吸引力**，能概括核心观点
- **每个板块配 1 张相关图片**（Picsum Photos，seed 不重复）
- 事件背景简述
- 关键信息提炼
- 多方观点对比
- 潜在影响分析
- 个人独到见解
- **📝 使用 Admonition 引用块**：至少使用 1 个 `:::note` 或 `:::tip` 突出关键洞察
  ```markdown
  :::note[💡 关键洞察]
  这里是重要的观点或总结，会以蓝色边框+图标的形式展示
  :::
  ```
- **跨领域关联**：将不同热点联系起来，发现隐藏的逻辑

#### 平台热点精选（简短锐评）
- 选择 5-8 个最有代表性的热点
- **格式**：`**平台名**：[标题](链接) - 一句话锐评`
- 锐评要有观点、有态度，不要中性描述
- 展现不同平台的舆论特点

#### 趋势观察（300-400字）
- 提炼 3-4 条清晰的趋势线
- **使用有序列表呈现**
- 每条趋势都要有具体的热点作为支撑
- 指出值得关注的信号或转折点

#### 结语思考（200-300字）
- **呼应开篇**，形成闭环
- 提出更深层次的思考或问题
- 给读者留下回味空间
- 可以适度展望

### 5. 写作风格
- **专业但不枯燥**：用生动的语言，避免官话套话
- **客观但有立场**：基于事实，但可以有独到观点
- **简洁但有深度**：每句话都要有价值，不废话
- **善用修辞**：比喻、对比、排比等手法增强可读性

### 6. Markdown 格式规范
- **必须且首先输出完整的 Frontmatter（YAML 格式）**
  ```yaml
  ---
  title: "你创作的有吸引力的标题"  # 不要用机械的日期标题
  published: {data.date}T08:00:00+08:00
  tags: [新闻, 热点, 趋势雷达]  # 使用中文标签，3-5个
  category: news
  draft: false
  image: https://picsum.photos/seed/diplomacy-tension/1600/900  # 使用与主题相关的英文关键词
  description: "一句话概括文章核心价值"
  ---
  ```
  **⚠️ 重要：Frontmatter 必须在文章最开头，以 `---` 开始和结束！这是 Astro 的要求！**
  
  **标签要求（本地化）：**
  - 使用**中文标签**，不要使用英文标签
  - 基础标签：`新闻`, `热点`, `趋势雷达`, `每日速览`
  - 根据内容添加相关中文标签，如：`国际局势`, `科技`, `财经`, `社会观察` 等
  - 标签数量控制在 3-6 个
  
- **🖼️ 图片增强（重点！）**
  - **Frontmatter 后不要添加任何图片**，因为封面图 `image` 字段已显示在文章顶部
  - **正文配图**：每个深度分析板块配 1 张相关图片（Picsum Photos）
  - 使用 Picsum Photos 免费图库，**必须使用与内容相关的英文关键词作为 seed**：
    - **格式**：`https://picsum.photos/seed/英文关键词/1200/600`
    - **要求**：seed 必须是与图片内容相关的英文单词或短语（2-4个词），用连字符连接
    - **示例**：
      ```markdown
      ![中国制造业供应链](https://picsum.photos/seed/china-factory-supply/1200/600)
      ![芯片科技股上涨](https://picsum.photos/seed/tech-stock-chip/1200/600)
      ![英雄烈士归国仪式](https://picsum.photos/seed/hero-memorial-ceremony/1200/600)
      ```
  - **封面图 seed 规则**：使用文章核心主题的英文关键词，如 `diplomacy-tension`、`china-economy`、`tech-innovation`
  - **分析配图 seed 规则**：每个深度分析板块的图片 seed 必须与该板块内容直接相关
  - **禁止使用通用 seed**：如 `news`、`image`、`photo` 等，必须使用具体内容相关的 seed
  - **⚠️ 重要：正文配图不能与封面图使用相同的 seed**，必须为每个板块选择不同的相关关键词
  
- **📝 Astro 博客特性利用（重点！）**
  - **Admonition 引用块**：使用 `:::note[标题]` 语法创建漂亮的提示框
    ```markdown
    :::note[💡 关键洞察]
    这里是重要的观点或总结，会以蓝色边框+图标的形式展示
    :::
    
    :::tip[🔍 深度观察]
    这里是值得注意的趋势或现象
    :::
    
    :::warning[⚠️ 风险提示]
    这里是潜在的风险或问题
    :::
    ```
  - **GitHub Card 组件**：提到 GitHub 项目时使用 `::github{repo="owner/repo"}`
    ```markdown
    ::github{repo="microsoft/TypeScript"}
    ```
  - **代码块**：使用带语言标识的代码块，支持一键复制
    ```markdown
    ```python
    # 示例代码
    print("Hello")
    ```
    ```
  - **引用块**：使用 `>` 突出金句和重要观点
  - **表格**：用于对比分析、数据展示
  - **Emoji 适度使用**：增强视觉效果但不要滥用
  - **加粗强调**：使用 `**text**` 突出重点
- 列表清晰，层级分明

### 7. 去重与连续性规则（极其重要）
- **🚫 严格去重**：检查今日已生成文章列表（见下方历史记录），如果某个热点话题今天已经写过，**绝对不要重复写**
- **📊 热点演变**：如果同一话题持续多日，请重点写"新变化"和"新进展"，而非重复已知信息
- **🔄 增量更新**：只写今日新增的内容，不写昨日已报道过的相同内容
- **✅ 首次出现**：新话题优先写；已写过的话题，除非有重大突破，否则跳过

### 8. 禁忌
- ❌ 不要重复同一事件多次（特别是同一天内）
- ❌ 不要使用"据悉""据报道"等模糊表述
- ❌ 不要写流水账
- ❌ 不要没有观点
- ❌ 不要超过2000字（精炼胜过冗长）

记住：读者时间宝贵，你要提供的是**经过筛选、分析、提炼的高价值内容**，而不是信息的简单搬运工！"""
        
        user_prompt = f"""请为以下日期生成一篇专业的热点聚合文章：

**日期**：{data.date} ({weekday_cn})
**标题**：{title}
**监测平台数**：{len(data.items)} 个
**热点总数**：{total_count} 条

**热点数据（精选 Top 5/平台）**：
{compressed_news_text}

{context_summary}

**⚠️ 重要提醒**：
1. **你是主编，你有决策权**：选择今日最有价值的科技话题，用你最擅长的角度分析
2. **风格多样化**：这篇文章用什么结构、什么角度，由你决定（不要每次都用相同的结构）
3. **深度优先**：宁可在 1-2 个话题上写得深入，也不要罗列 5-6 个话题每个都浅尝辄止
4. **利用你的知识**：调用你的专业知识做分析，不要只描述表面现象
5. **如果没有重磅科技新闻**：可以写技术趋势分析、开源项目推荐、AI 工具评测、编程语言新特性等

**⚠️ 输出要求（必须遵守）：**
1. **首先输出完整的 Frontmatter**，以 `---` 开始和结束
2. **使用中文标签**：tags 必须是中文，如 `[新闻, 热点, 国际局势]`
3. **🖼️ 图片规则（极其重要）**：
   - Frontmatter 中的 `image` 字段设置封面图 seed
   - **Frontmatter 后不要添加任何图片**，封面图会自动显示在文章顶部
   - 每个深度分析板块的图片 seed 也必须互不相同
   - **示例**：如果封面是 `iran-tension-negotiation`，深度分析板块配图必须是其他词如 `diplomacy-talks`
4. **图片 seed 必须与内容相关**：
   - 封面图：使用文章核心主题的英文关键词
   - 分析配图：每个板块的图片 seed 必须与该板块内容直接相关
   - 禁止使用通用 seed（如 `news`、`image`），必须使用具体内容关键词
5. **📝 Astro 博客特性利用**：
   - 每个深度分析板块至少使用 1 个 Admonition 引用块（`:::note[...]` 或 `:::tip[...]`，使用方括号）
   - 使用引用块 `>` 突出金句
   - 使用表格进行对比分析
6. 然后才是文章内容
7. 严格按照系统提示中的结构和要求创作
8. **不要流水账**：要提供深度分析和独到见解，跨领域关联不同热点
9. **🖼️ 图片增强**：每个深度分析板块配 1 张相关图片（Picsum Photos，所有 seed 必须唯一不重复）
10. **📚 利用历史上下文**：如果有持续关注的热点，请在文章中体现其演变和延续性
11. **💰 成本控制**：文章精炼有力，控制在 {optimized_params['max_tokens']//4} 字以内

请立即开始输出完整的 Markdown 文章！"""
        
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
        
        # Cache the response
        cost_optimizer.cache_response(cache_key, ai_content, estimated_tokens)
        
        # Save article metadata to history for future context
        try:
            gh_token = os.environ.get("GH_MEMORY_TOKEN")
            astro_owner = os.environ.get("ASTRO_REPO_OWNER", "garcci")
            astro_repo = os.environ.get("ASTRO_REPO_NAME", "Astro")
            
            # Extract keywords from title and content (simple extraction)
            import re
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
                'excerpt': ai_content[200:400] if len(ai_content) > 400 else '',
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
            from ..evolution.evolution_system import evaluate_and_evolve
            gh_token = os.environ.get("GH_MEMORY_TOKEN")
            astro_owner = os.environ.get("ASTRO_REPO_OWNER", "garcci")
            astro_repo = os.environ.get("ASTRO_REPO_NAME", "Astro")
            if gh_token:
                improvement_prompt = evaluate_and_evolve(
                    ai_content, title, astro_owner, astro_repo, gh_token
                )
                if improvement_prompt:
                    logger.info(f"[进化系统] 文章评估完成，生成改进建议: {len(improvement_prompt)} 字符")
            else:
                logger.warning("[进化系统] 跳过评估：未配置 GH_MEMORY_TOKEN")
        except Exception as e:
            logger.warning(f"[进化系统] 评估失败: {e}")
        
        return ai_content
    
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
