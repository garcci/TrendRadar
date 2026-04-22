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

### 3. 文章结构（必须包含）

#### 开篇引言（150-200字）
- 今日热点的整体态势
- 最值得关注的3-5个核心事件
- 一句话总结今日舆情特点

#### 文章标题要求
- **禁止**使用 "TrendRadar Report - 日期" 这种机械标题
- 标题要有**吸引力、悬念感、观点性**
- 可以是对今日热点的精准概括、金句提炼、或引发思考的反问
- 示例好标题：
  - "俄乌冲突500天：世界学到了什么？"
  - "当'报复性消费'变成'报复性存钱'"
  - "ChatGPT抢不走的工作，正在被另一种AI取代"
  - "一场颁奖典礼，照出了中国电影的体面与尴尬"

#### 深度分析板块（重点！800-1000字）
选择3-5个最有价值的热点，每个进行深度分析：
- 事件背景简述
- 关键信息提炼
- 多方观点对比
- 潜在影响分析
- 个人独到见解
- **🎥 必须嵌入相关视频**：如果该热点在 Bilibili/YouTube/抖音有相关内容，嵌入 1 个高质量视频
- **🖼️ 建议配图**：如果有相关新闻图片或示意图，可以嵌入增强视觉效果

#### 平台热点精选（简洁有力）
每个平台只选Top 5，用一句话点评：
- 格式：**[标题](链接)** - 点评（20-30字）
- 点评要有态度、有角度，不是复述标题

#### 趋势观察（200-300字）
- 今日热点反映的社会趋势
- 值得持续关注的信号
- 可能的后续发展

#### 结语思考（100-150字）
- 今日热点的共性特征
- 给读者的思考题或建议

### 4. 写作风格
- **专业但不枯燥**：用生动的语言，避免官话套话
- **客观但有立场**：基于事实，但可以有独到观点
- **简洁但有深度**：每句话都要有价值，不废话
- **善用修辞**：比喻、对比、排比等手法增强可读性

### 5. Markdown 格式规范
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
  - **开篇必须有一张主题相关的封面图**，紧跟在 Frontmatter 之后
  - 使用 Picsum Photos 免费图库，**必须使用与内容相关的英文关键词作为 seed**：
    - **格式**：`https://picsum.photos/seed/英文关键词/1200/600`
    - **要求**：seed 必须是与图片内容相关的英文单词或短语（2-4个词），用连字符连接
    - **示例**：
      ```markdown
      ![美伊谈判紧张局势](https://picsum.photos/seed/us-iran-negotiation/1200/600)
      ![中国制造业供应链](https://picsum.photos/seed/china-factory-supply/1200/600)
      ![芯片科技股上涨](https://picsum.photos/seed/tech-stock-chip/1200/600)
      ![英雄烈士归国仪式](https://picsum.photos/seed/hero-memorial-ceremony/1200/600)
      ```
  - **封面图 seed 规则**：使用文章核心主题的英文关键词，如 `diplomacy-tension`、`china-economy`、`tech-innovation`
  - **分析配图 seed 规则**：每个深度分析板块的图片 seed 必须与该板块内容直接相关
  - **禁止使用通用 seed**：如 `news`、`image`、`photo` 等，必须使用具体内容相关的 seed
  
- **🎥 视频嵌入（重点！）**
  - 每个深度分析板块**必须**嵌入至少 1 个相关视频
  - **优先使用 Bilibili 热榜中的真实视频 URL**：
    - 从提供的热点数据中提取 Bilibili 相关条目的 URL
    - 如果热点数据中有 Bilibili 条目，直接使用其 URL
    - 示例：如果数据中有 `{"title": "xxx", "url": "https://www.bilibili.com/video/BV1xx411c7mD"}`
    - 则提取 bvid 并生成 iframe：
      ```html
      <div class="video-container">
        <iframe src="//player.bilibili.com/player.html?bvid=BV1xx411c7mD&p=1&high_quality=1&danmaku=0" 
                scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true">
        </iframe>
      </div>
      ```
  - **如果没有合适的 Bilibili 视频 URL，使用以下方案**：
    1. **推荐搜索链接**（最实用）：
       ```markdown
       📺 [在B站搜索相关视频](https://search.bilibili.com/all?keyword=美伊谈判)
       ```
    2. **使用占位符并说明**：
       ```html
       <!-- 此处可嵌入相关视频，建议搜索关键词：美伊谈判 -->
       <div class="video-container">
         <iframe src="//player.bilibili.com/player.html?bvid=BV1xx411c7mD&p=1&high_quality=1&danmaku=0" 
                 scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true">
         </iframe>
       </div>
       *注：请替换为实际相关的视频ID*
       ```
  
- 使用 Emoji 增强视觉效果（但不要滥用）
- 合理使用引用块 `>` 突出金句
- 用加粗 `**text**` 强调重点
- 列表清晰，层级分明

### 6. 禁忌
- ❌ 不要重复同一事件多次
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

**⚠️ 输出要求（必须遵守）：**
1. **首先输出完整的 Frontmatter**，以 `---` 开始和结束
2. **使用中文标签**：tags 必须是中文，如 `[新闻, 热点, 国际局势]`
3. **开篇配图**：Frontmatter 后立即添加一张主题相关的封面图
4. **🖼️ 图片 seed 必须与内容相关**：
   - 封面图：使用文章核心主题的英文关键词（如 `diplomacy-tension`、`china-economy`）
   - 分析配图：每个板块的图片 seed 必须与该板块内容直接相关
   - 禁止使用通用 seed（如 `news`、`image`），必须使用具体内容关键词
5. 然后才是文章内容
6. 严格按照系统提示中的结构和要求创作
7. 不要简单罗列，要提供深度分析和独到见解
8. **🎥 视频嵌入**：
   - **优先使用 Bilibili 热榜中的真实视频 URL**（从提供的数据中提取）
   - 如果数据中有 Bilibili 条目，提取其 bvid 并生成 iframe
   - 如果没有合适的视频，使用搜索链接或占位符
9. **🖼️ 图片增强**：每个深度分析板块配 1 张相关图片（Picsum Photos，seed 与内容相关）
10. 如果无法确定具体视频 ID，可以推荐搜索关键词或使用占位符
11. **📚 利用历史上下文**：如果有持续关注的热点，请在文章中体现其演变和延续性
12. **💰 成本控制**：文章精炼有力，控制在 {optimized_params['max_tokens']//4} 字以内

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
