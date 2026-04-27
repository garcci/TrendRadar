"""
GitHub Storage Backend for TrendRadar
Pushes articles directly to Astro repository via GitHub API
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, List
from pathlib import Path

from .base import StorageBackend, NewsData

logger = logging.getLogger(__name__)

# Lv73: 统一日志收集器
try:
    from evolution.unified_logger import StepTimer, log_info, log_warn, log_error, set_article_id
    HAS_UNIFIED_LOGGER = True
except ImportError:
    HAS_UNIFIED_LOGGER = False
    # 降级：创建空壳
    class StepTimer:
        def __init__(self, module, step): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
    def log_info(m, msg, **kw): print(f"[{m}] {msg}")
    def log_warn(m, msg, **kw): print(f"[{m}] ⚠️ {msg}")
    def log_error(m, msg, **kw): print(f"[{m}] ❌ {msg}")
    def set_article_id(aid): pass


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
        # Lv73: 设置文章追踪ID
        timestamp = int(datetime.now(timezone.utc).timestamp())
        date_str = data.date or datetime.now().strftime("%Y-%m-%d")
        article_id = f"{date_str}-{timestamp}"
        set_article_id(article_id)
        log_info("github", f"save_news_data 开始执行", article_id=article_id)
        
        if not data.items:
            log_warn("github", "data.items 为空，返回 False")
            return False
        total_items = sum(len(items) for items in data.items.values())
        log_info("github", f"data.items 有 {total_items} 条数据", total_items=total_items)
        
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
        with StepTimer("smart_scheduler", "调度决策"):
            try:
                from evolution.smart_scheduler import SmartScheduler
                
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
                
                log_info("smart_scheduler", f"决策={decision['action'].upper()} 评分={decision['score']}/10", reason=decision['reason'])
                
                if decision['action'] == 'skip':
                    is_draft = True
                elif decision['action'] == 'draft':
                    is_draft = True
                else:
                    is_draft = False
                    
            except Exception as e:
                log_error("smart_scheduler", f"决策失败: {e}")
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
        
        # ═══════════════════════════════════════════════════════════
        # 🛡️ 质量门槛拦截 — 低质量文章绝不上线
        # ═══════════════════════════════════════════════════════════
        MAX_QUALITY_RETRIES = 3
        QUALITY_MIN_OVERALL = 4.0
        QUALITY_MIN_TECH = 3.0
        QUALITY_MAX_DUPLICATE_PENALTY = 3.0
        
        markdown_content = None
        last_quality_reason = ""
        final_scores = None
        
        log_info("quality_gate", f"开始 {MAX_QUALITY_RETRIES} 次尝试生成文章...")
        for attempt in range(1, MAX_QUALITY_RETRIES + 1):
            # Generate Markdown content using AI
            with StepTimer("ai_generate", f"AI文章生成-第{attempt}次"):
                try:
                    markdown_content = self._generate_ai_article(data, article_title)
                    log_info("ai_generate", f"AI生成成功（第{attempt}次）", content_length=len(markdown_content) if markdown_content else 0)
                except Exception as e:
                    log_error("ai_generate", f"AI生成失败: {e}", attempt=attempt)
                    last_quality_reason = f"AI生成异常: {e}"
                    continue
            
            # 立即质量评分
            with StepTimer("quality_score", f"质量评分-第{attempt}次"):
                try:
                    scores = self._auto_score_article(markdown_content, article_title)
                    final_scores = scores
                    log_info("quality_score", f"评分完成", overall=scores['overall_score'], tech=scores['tech_content_ratio'], total_penalty=scores['penalties']['total'])
                    
                    # 硬性门槛检查
                    fail_reasons = []
                    penalties = scores['penalties']
                    
                    if scores['overall_score'] < QUALITY_MIN_OVERALL:
                        fail_reasons.append(f"综合评分过低 ({scores['overall_score']:.1f} < {QUALITY_MIN_OVERALL})")
                    if scores['tech_content_ratio'] < QUALITY_MIN_TECH:
                        fail_reasons.append(f"科技含量过低 ({scores['tech_content_ratio']:.1f} < {QUALITY_MIN_TECH})")
                    if penalties['duplicate'] >= QUALITY_MAX_DUPLICATE_PENALTY:
                        fail_reasons.append(f"重复内容过多 (惩罚={penalties['duplicate']:.1f})")
                    
                    if penalties.get('total', 0) >= 8.0:
                        fail_reasons.append(f"总惩罚过高 ({penalties['total']:.1f} >= 8.0)")
                    if penalties.get('length', 0) >= 2.0:
                        fail_reasons.append(f"内容长度过短 (惩罚={penalties['length']:.1f})")
                    if penalties.get('template', 0) >= 2.0:
                        fail_reasons.append(f"模板痕迹过重 (惩罚={penalties['template']:.1f})")
                    if penalties.get('promo', 0) >= 2.0:
                        fail_reasons.append(f"推广内容 detected (惩罚={penalties['promo']:.1f})")
                    
                    if fail_reasons:
                        last_quality_reason = "; ".join(fail_reasons)
                        log_warn("quality_gate", f"第{attempt}次未通过: {last_quality_reason}", overall=scores['overall_score'])
                        markdown_content = None
                        continue
                    else:
                        log_info("quality_gate", f"✅ 通过（overall={scores['overall_score']:.1f}）")
                        self._save_article_metrics(
                            date=data.date if isinstance(data.date, str) else (data.date.strftime('%Y-%m-%d') if hasattr(data, 'date') and data.date else ''),
                            title=article_title,
                            scores=scores
                        )
                        break
                except Exception as e:
                    log_error("quality_score", f"评分失败: {e}", attempt=attempt)
                    last_quality_reason = f"评分异常: {e}"
                    markdown_content = None
                    continue
        
        # 循环结束后检查是否成功
        if markdown_content is None:
            log_error("quality_gate", f"{MAX_QUALITY_RETRIES}次尝试均失败，当天不发布", last_reason=last_quality_reason)
            try:
                self._create_quality_alert_issue(date_str, last_quality_reason)
            except Exception:
                pass
            return False
        
        # 🔬 科技内容检测 — Lv62 进化
        tech_check_result = None
        try:
            from evolution.tech_content_guard import check_tech_content
            passed, message = check_tech_content(markdown_content, min_ratio=0.5)
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
        with StepTimer("smart_summary", "智能摘要生成"):
            try:
                from evolution.smart_summary import add_smart_summary
                original_length = len(markdown_content)
                markdown_content = add_smart_summary(markdown_content)
                if len(markdown_content) > original_length:
                    log_info("smart_summary", "已自动生成文章摘要块")
            except Exception as e:
                log_warn("smart_summary", f"生成失败: {e}")
        
        # 📝 标题优化 - 自动生成最佳标题（Lv22进化）
        with StepTimer("title_optimizer", "标题优化"):
            try:
                from evolution.title_optimizer import optimize_article_title, replace_article_title
                new_title = optimize_article_title(markdown_content)
                if new_title and "TrendRadar Report" not in new_title:
                    markdown_content = replace_article_title(markdown_content, new_title)
                    log_info("title_optimizer", f"已优化标题为: {new_title}")
            except Exception as e:
                log_warn("title_optimizer", f"失败: {e}")
        
        # 🚀 多模型协作优化 frontmatter
        with StepTimer("multi_model", "多模型 frontmatter 优化"):
            try:
                original_fm = markdown_content.split('---', 2)[1] if markdown_content.startswith('---') else ""
                markdown_content = self._enhance_frontmatter_multi_model(markdown_content)
                new_fm = markdown_content.split('---', 2)[1] if markdown_content.startswith('---') else ""
                if original_fm != new_fm:
                    log_info("multi_model", "✅ frontmatter 已被多模型优化")
                else:
                    log_info("multi_model", "ℹ️ frontmatter 未发生变化")
            except Exception as e:
                log_error("multi_model", f"优化失败: {e}")
        
        # 🧹 Frontmatter 清理
        with StepTimer("sanitize", "Frontmatter 清理"):
            try:
                markdown_content = self._sanitize_frontmatter(markdown_content, data.date, article_title)
                log_info("sanitize", "✅ sanitize 完成")
            except Exception as e:
                log_error("sanitize", f"sanitize 失败: {e}，跳过继续")
        
        # 🧹 清理重复的快速阅读区（AI有时会输出两次）
        print("[文章处理] 检查重复快速阅读区...")
        tip_blocks = markdown_content.split(':::tip[📋 快速阅读]')
        if len(tip_blocks) > 2:
            # 保留第一个，删除后面的
            first_tip_end = tip_blocks[1].find(':::')
            if first_tip_end != -1:
                first_tip = ':::tip[📋 快速阅读]' + tip_blocks[1][:first_tip_end+3]
                # 重建内容：frontmatter + 第一个tip + 正文其余部分
                body_after_tips = ''
                for i, block in enumerate(tip_blocks[2:], 2):
                    tip_end = block.find(':::')
                    if tip_end != -1:
                        body_after_tips += block[tip_end+3:]
                    else:
                        body_after_tips += block
                markdown_content = tip_blocks[0] + first_tip + body_after_tips
                print("[文章处理] ✅ 已删除重复的快速阅读区")
        else:
            print("[文章处理] 无重复快速阅读区")
        
        # 🧹 修复核心观点编号格式（AI有时会输出 `: 内容` 或 `：内容`）
        import re
        # 在快速阅读区内，将 `: 内容` 或 `：内容` 修复为正常编号
        def fix_bullet_numbers(section):
            # 修复空的编号行（如 `3. : ` 或 `4. ：`）
            section = re.sub(r'(\d+\.\s*)[:：]\s*', r'\1', section)
            return section
        
        # 只修复快速阅读区内的核心观点部分
        try:
            markdown_content = re.sub(
                r'(\*\*核心观点\*\*[:：]\s*\n)(.*?)(\n\n\*\*关键词)',
                lambda m: m.group(1) + fix_bullet_numbers(m.group(2)) + m.group(3),
                markdown_content,
                flags=re.DOTALL
            )
        except Exception as e:
            print(f"[文章处理] ⚠️ 核心观点编号格式修复失败: {e}，跳过继续")
        
        # ✅ Frontmatter 预验证
        with StepTimer("frontmatter_validator", "Frontmatter 预验证"):
            try:
                from evolution.frontmatter_validator import validate_article
                valid, errors, fixed_content = validate_article(markdown_content, filepath)
                if not valid:
                    log_warn("frontmatter_validator", f"发现 {len(errors)} 个问题", errors=errors)
                    if fixed_content != markdown_content:
                        markdown_content = fixed_content
                        log_info("frontmatter_validator", "已自动修复问题")
                        valid2, errors2, _ = validate_article(markdown_content, filepath)
                        if not valid2:
                            log_error("frontmatter_validator", f"自动修复后仍有 {len(errors2)} 个问题，阻止推送", errors=errors2)
                            return False
                    else:
                        log_error("frontmatter_validator", "无法自动修复，阻止推送")
                        return False
                else:
                    log_info("frontmatter_validator", "✅ 通过")
            except Exception as e:
                log_warn("frontmatter_validator", f"验证过程出错: {e}，跳过验证继续推送")
        
        # 🛡️ Astro 构建预检
        with StepTimer("astro_preflight", "Astro 构建预检"):
            try:
                from evolution.astro_preflight import preflight_check
                passed, report = preflight_check(markdown_content, filepath)
                if not passed:
                    log_error("astro_preflight", f"❌ 未通过", report=report[:200])
                    return False
                log_info("astro_preflight", "✅ 通过")
            except Exception as e:
                log_warn("astro_preflight", f"检查过程出错: {e}，跳过继续推送")
        
        # Push to GitHub
        with StepTimer("github_push", "GitHub 文章推送"):
            try:
                self._push_to_github(filepath, markdown_content, f"feat: add TrendRadar report - {article_title}")
                log_info("github_push", f"✅ 成功推送文章到 GitHub: {filepath}")
                
                # 🚀 部署后验证
                with StepTimer("deploy_verify", "部署后验证"):
                    try:
                        from trendradar.storage.deploy_verifier import verify_after_push
                        import os
                        
                        slug = os.path.basename(filepath).replace('.md', '')
                        date_str = data.date if isinstance(data.date, str) else (data.date.strftime('%Y-%m-%d') if hasattr(data, 'date') and data.date else '')
                        
                        verify_after_push(
                            slug, date_str, logger,
                            filepath=filepath,
                            github_token=self.token,
                            github_owner=self.owner,
                            github_repo=self.repo,
                            github_branch=self.branch,
                            rollback_on_failure=False,
                        )
                    except Exception as e:
                        log_warn("deploy_verify", f"验证过程出错: {e}")
                
                # 📦 记录文章数据到统一管道
                try:
                    from evolution.data_pipeline import write_record
                    write_record("article", {
                        "id": filepath.split('/')[-1].replace('.md', ''),
                        "title": article_title,
                        "date": data.date if isinstance(data.date, str) else (data.date.strftime('%Y-%m-%d') if hasattr(data, 'date') and data.date else ''),
                        "source_count": len(data.items),
                        "total_items": sum(len(items) for items in data.items.values()),
                        "length": len(markdown_content),
                        "is_draft": is_draft,
                    })
                    log_info("data_pipeline", "文章记录已写入")
                except Exception as e:
                    log_warn("data_pipeline", f"写入失败: {e}")
                
                # 📦 Lv75: 记录文章质量到回溯库
                try:
                    from evolution.article_quality_db import record_article_quality
                    # 从 frontmatter 提取标签
                    tags = []
                    try:
                        fm_match = markdown_content.split('---', 2)
                        if len(fm_match) >= 2:
                            import yaml
                            fm = yaml.safe_load(fm_match[1])
                            tags = fm.get('tags', []) if fm else []
                    except Exception:
                        pass
                    
                    record_article_quality(
                        article_id=filepath.split('/')[-1].replace('.md', ''),
                        title=article_title,
                        date=data.date if isinstance(data.date, str) else (data.date.strftime('%Y-%m-%d') if hasattr(data, 'date') and data.date else ''),
                        tags=tags,
                        scores=final_scores,
                        is_draft=is_draft,
                        source_count=len(data.items),
                        total_items=sum(len(items) for items in data.items.values()),
                        content_length=len(markdown_content),
                        modules_used=["smart_scheduler", "ai_generate", "quality_gate", "multi_model", "sanitize", "frontmatter_validator", "astro_preflight"],
                    )
                    log_info("article_quality_db", "文章质量已记录到回溯库")
                except Exception as e:
                    log_warn("article_quality_db", f"记录失败: {e}")
                
                return True
            except Exception as e:
                log_error("github_push", f"推送失败: {e}")
                return False
    
    def _auto_score_article(self, content: str, title: str) -> dict:
        """
        基于规则自动评估文章质量 — 校准后与历史数据分布对齐
        
        历史数据参考：overall_score 均值6.86(2.7-9.4), tech_ratio 均值4.66(0.5-8.5)
        """
        import re
        
        # 提取正文（去掉 frontmatter）
        body = content
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                body = parts[2]
        
        # 1. 科技内容占比评分（扩大关键词库，降低阈值）
        tech_keywords = [
            'AI', '人工智能', '大模型', 'LLM', '机器学习', '深度学习', '神经网络',
            '开源', 'GitHub', '代码', '算法', '芯片', 'GPU', 'CPU', 'NPU', '算力',
            '云计算', '云原生', '容器', 'Kubernetes', 'Docker', 'K8s',
            '区块链', 'Web3', '加密货币', '比特币', '以太坊', 'DeFi',
            '自动驾驶', '机器人', '具身智能', '人形机器人', '智能驾驶',
            '量子计算', '生物技术', '基因编辑', '太空', '星链', '卫星',
            '数据', '隐私', '安全', '漏洞', '攻击', '防护', '加密',
            '融资', '估值', 'IPO', '并购', '独角兽', '投资', '上市',
            'Python', 'JavaScript', 'Rust', 'Go', 'TypeScript', 'Java', 'C++',
            'ChatGPT', 'Claude', 'Gemini', 'GPT', 'Transformer', 'Diffusion',
            '生成式', '多模态', 'Agent', 'RAG', '微调', 'Fine-tuning',
            'SaaS', 'PaaS', 'IaaS', 'FaaS', 'Serverless', '微服务',
            '元宇宙', 'VR', 'AR', 'XR', 'MR', '数字孪生',
            '新能源', '电动车', '光伏', '储能', '锂电池', '固态电池',
            '脑机接口', 'Neuralink', '合成生物', 'mRNA', 'CRISPR',
            '5G', '6G', '物联网', 'IoT', '边缘计算', '联邦学习',
            '推荐算法', '搜索引擎', '社交媒体', '电商平台', '直播',
            '框架', '库', '工具链', 'IDE', '编译器', '运行时',
            '并发', '异步', '分布式', '高可用', '容错', '负载均衡',
            '监控', '日志', '链路追踪', '可观测性', 'DevOps', 'CI/CD',
        ]
        body_lower = body.lower()
        tech_count = sum(1 for kw in tech_keywords if kw.lower() in body_lower)
        # 校准：历史均值4.66，高质量文章应有5-8分
        tech_ratio = min(8.5, max(0.5, tech_count * 0.6))
        
        # 2. 分析深度评分（更宽松）
        analysis_markers = ['###', '|', '对比', '趋势', '预测', '展望', '分析', '原因', '影响', '核心观点', '关键数据', '数据显示', '研究表明', '报告指出', '调研']
        analysis_count = sum(1 for m in analysis_markers if m in body)
        analysis_depth = min(9.0, max(1.0, analysis_count * 0.8))
        
        # 3. Markdown元素多样性
        md_elements = {
            'table': len(re.findall(r'\|.*\|.*\|', body)),
            'code_block': body.count('```'),
            'list': len(re.findall(r'^\s*[-*\d+]', body, re.MULTILINE)),
            'quote': body.count('>'),
            'link': len(re.findall(r'\[.*?\]\(.*?\)', body)),
            'image': len(re.findall(r'!\[.*?\]\(.*?\)', body)),
            'tip': body.count(':::tip'),
            'heading': len(re.findall(r'^#{2,4}\s+', body, re.MULTILINE)),
        }
        element_types = sum(1 for v in md_elements.values() if v > 0)
        style_diversity = min(9.0, max(2.0, element_types * 1.2))
        
        # 4. 洞察/预测性
        insight_markers = ['预测', '未来', '趋势', '将', '可能', '预计', '展望', '信号', '拐点', '爆发', '颠覆', '变革', '值得', '关键', '核心', '深度']
        insight_count = sum(1 for m in insight_markers if m in body)
        insightfulness = min(10.0, max(0.0, insight_count * 0.7))
        
        # 5. 可读性（句子长度适中=高分）
        sentences = re.split(r'[。！？\n]', body)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if sentences:
            avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
            readability = max(4.0, min(10.0, 15 - avg_sentence_len / 6))
        else:
            readability = 5.0
        
        # 6. 内容质量惩罚项（检测重复和空洞填充）
        # 检测重复段落
        paragraphs = [p.strip() for p in re.split(r'\n\n+', body) if len(p.strip()) > 20]
        duplicate_penalty = 0
        if len(paragraphs) > 3:
            seen = set()
            for p in paragraphs:
                p_short = p[:50]
                if p_short in seen:
                    duplicate_penalty += 1.5
                seen.add(p_short)
        
        # 检测空洞填充词密度
        filler_words = ['了解', '有了', '让我们', '值得一提的是', '不得不说', '众所周知', '总而言之', '综上所述']
        filler_count = sum(body.count(w) for w in filler_words)
        filler_penalty = min(3.0, filler_count * 0.5)
        
        # 检测"平台热点精选"等重复章节（低质量文章标志）
        section_headers = re.findall(r'^#{2,3}\s+(.+)$', body, re.MULTILINE)
        unique_headers = set(section_headers)
        repeat_section_penalty = 0
        if len(section_headers) > len(unique_headers):
            repeat_section_penalty = 2.0
        
        # 6b. 新增低质量特征检测
        # 内容长度惩罚 — 正文太短=低质量
        # 计算有效文本长度（中文字符 + 英文单词 + 数字）
        meaningful_chars = len(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]', body))
        length_penalty = 0
        if meaningful_chars < 600:
            length_penalty = 3.0  # 严重不足（<600有效字符）
        elif meaningful_chars < 1200:
            length_penalty = 1.5  # 偏短
        elif meaningful_chars < 2000:
            length_penalty = 0.3  # 略短
        
        # 模板痕迹惩罚 — 检测AI模板化输出
        template_phrases = [
            '随着...的发展', '在当今时代', '在这个快速变化的时代', '在这个信息爆炸的时代',
            '引起了广泛关注', '成为了热门话题', '再次成为焦点', '备受瞩目',
            '不仅...而且', '一方面...另一方面', '首先...其次...最后',
            '值得注意的是', '需要指出的是', '不可否认的是', '毫无疑问',
            '总而言之', '综上所述', '总的来说', '一言以蔽之',
        ]
        template_count = 0
        for phrase in template_phrases:
            # 支持"随着...的发展"这种变体匹配
            if '...' in phrase:
                parts = phrase.split('...')
                pattern = re.escape(parts[0]) + r'[^，。]{1,10}' + re.escape(parts[1])
                template_count += len(re.findall(pattern, body))
            else:
                template_count += body.count(phrase)
        template_penalty = min(4.0, template_count * 0.8)
        
        # 空洞段落惩罚 — 段落中实质内容占比过低
        empty_paragraph_penalty = 0
        for p in paragraphs:
            p_len = len(p)
            if p_len > 30:
                # 计算有效字符（中文字符+数字+英文单词）
                meaningful_chars = len(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]', p))
                ratio = meaningful_chars / p_len if p_len > 0 else 1.0
                if ratio < 0.5:  # 一半以上是无意义符号/空格
                    empty_paragraph_penalty += 1.0
        empty_paragraph_penalty = min(3.0, empty_paragraph_penalty)
        
        # 广告/推广惩罚 — 移除科技语境中常见的误报词
        promo_phrases = ['点击了解', '立即下载', '免费试用', '限时优惠', '抢购', '爆款', '网红',
                         '关注我', '私信', '加微信', '扫码', '推广', ' sponsored']
        promo_count = sum(1 for p in promo_phrases if p in body)
        promo_penalty = min(3.0, promo_count * 1.5)
        
        # 7. 总分（加权）— 校准后与历史均值6.86对齐
        base_score = (
            tech_ratio * 0.30 +
            analysis_depth * 0.20 +
            style_diversity * 0.15 +
            insightfulness * 0.25 +
            readability * 0.10
        )
        # 所有惩罚项汇总
        total_penalty = (
            duplicate_penalty + filler_penalty + repeat_section_penalty +
            length_penalty + template_penalty + empty_paragraph_penalty + promo_penalty
        )
        overall = min(9.5, max(2.0, base_score * 1.15 - total_penalty))
        
        return {
            'overall_score': round(overall, 1),
            'tech_content_ratio': round(tech_ratio, 1),
            'analysis_depth': round(analysis_depth, 1),
            'style_diversity': round(style_diversity, 1),
            'insightfulness': round(insightfulness, 1),
            'readability': round(readability, 1),
            'word_count': len(body),
            'penalties': {
                'duplicate': round(duplicate_penalty, 1),
                'filler': round(filler_penalty, 1),
                'repeat_section': round(repeat_section_penalty, 1),
                'length': round(length_penalty, 1),
                'template': round(template_penalty, 1),
                'empty_paragraph': round(empty_paragraph_penalty, 1),
                'promo': round(promo_penalty, 1),
                'total': round(total_penalty, 1),
            }
        }
    
    def _save_article_metrics(self, date: str, title: str, scores: dict):
        """保存文章评分到 metrics 文件"""
        import json
        import os
        
        metrics_file = os.path.join("evolution", "article_metrics.json")
        
        # 读取现有数据
        metrics = []
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        metrics = data
            except Exception:
                metrics = []
        
        # 添加新记录
        record = {
            'date': date,
            'timestamp': datetime.now().isoformat(),
            'title': title,
            'overall_score': scores['overall_score'],
            'tech_content_ratio': scores['tech_content_ratio'],
            'analysis_depth': scores['analysis_depth'],
            'style_diversity': scores['style_diversity'],
            'insightfulness': scores['insightfulness'],
            'readability': scores['readability'],
            'word_count': scores['word_count'],
        }
        metrics.append(record)
        
        # 只保留最近100条
        metrics = metrics[-100:]
        
        # 写入文件
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
    
    def _create_quality_alert_issue(self, date_str: str, reason: str):
        """质量拦截失败时创建告警 Issue"""
        import requests
        
        issue_title = f"🚨 质量门槛拦截: {date_str} 文章未通过审核"
        issue_body = f"""## 质量拦截告警

**日期**: {date_str}
**拦截原因**: {reason}

### 说明
文章在连续3次生成尝试后，均未能达到质量门槛标准，已被自动拦截，当天不会发布低质量文章。

### 建议处理
1. 检查当天 RSS 数据源是否正常
2. 检查 AI 服务（DeepSeek/Gemini）响应质量
3. 如连续多天触发此告警，请检查 Prompt 模板是否需要优化

---
*此 Issue 由 TrendRadar 质量门槛系统自动创建*
"""
        
        try:
            url = f"https://api.github.com/repos/{self.owner}/TrendRadar/issues"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            response = requests.post(url, headers=headers, json={
                "title": issue_title,
                "body": issue_body,
                "labels": ["quality-gate", "auto-alert"]
            }, timeout=30)
            
            if response.status_code == 201:
                logger.info(f"[质量告警] 已创建 Issue: {response.json().get('html_url')}")
            else:
                logger.warning(f"[质量告警] Issue 创建失败: {response.status_code}")
        except Exception as e:
            logger.warning(f"[质量告警] Issue 创建异常: {e}")
    
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
        # 🔬 科技热点预过滤 — 只保留科技相关的热点，提高文章科技占比
        tech_keywords = ['AI', '人工智能', '芯片', '开源', 'GitHub', '模型', '训练', '算法',
                         '框架', '云计算', '数据', '安全', '区块链', '量子', '机器人', '自动驾驶',
                         '半导体', 'GPU', '大模型', 'LLM', 'Transformer', '神经网络', 'Python',
                         'JavaScript', '开发者', '编程', '代码', 'API', '系统', '硬件', '软件',
                         'iOS', 'Android', '苹果', '谷歌', '微软', '特斯拉', 'SpaceX', 'Meta',
                         '英伟达', 'NVIDIA', 'DeepSeek', 'ChatGPT', 'OpenAI', '字节跳动']
        
        news_summary = []
        total_count = 0
        tech_count = 0
        video_platforms = ["bilibili", "douyin", "youtube"]  # Platforms that may have videos
        
        for source_id, items_list in data.items.items():
            source_name = data.id_to_name.get(source_id, source_id)
            has_video_potential = any(vp in source_id.lower() for vp in video_platforms)
            
            # 过滤科技热点
            tech_items = []
            for item in items_list:
                title = getattr(item, 'title', '') or ''
                if any(kw in title for kw in tech_keywords):
                    tech_items.append(item)
            
            # 如果该平台没有科技热点，保留 Top 3 作为背景参考
            if not tech_items:
                tech_items = items_list[:3]
            
            if has_video_potential:
                news_summary.append(f"\n**{source_name}** (科技相关 Top 8) 🎥 含视频链接:")
                for i, item in enumerate(tech_items[:8], 1):
                    url_info = f" [URL: {item.url}]" if hasattr(item, 'url') and item.url else ""
                    news_summary.append(f"  {i}. {item.title}{url_info}")
            else:
                news_summary.append(f"\n**{source_name}** (科技相关 Top 8):")
                for i, item in enumerate(tech_items[:8], 1):
                    news_summary.append(f"  {i}. {item.title}")
            
            total_count += len(items_list)
            tech_count += len(tech_items)
        
        if tech_count > 0:
            logger.info(f"[热点过滤] 从 {total_count} 条热点中筛选出 {tech_count} 条科技相关热点 ({tech_count/total_count*100:.0f}%)")
        
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
        system_prompt = f"""你是科技媒体主编。根据热点数据写一篇科技分析文章。

## 输出格式（严格遵守）

第1步：输出 Frontmatter：
```yaml
---
title: "有吸引力的标题"  # 用具体事件/数字命名，如"DeepSeek V4发布：英伟达重回5万亿"
published: {data.date}T08:00:00+08:00
tags: [科技, AI, 相关标签]  # 3-6个中文标签，科技类≥50%
category: news
draft: false
image: https://picsum.photos/seed/关键词/1600/900
description: "一句话概括文章核心价值"
---
```

第2步：输出快速阅读区（紧跟frontmatter，只输出这一次）：
```
:::tip[📋 快速阅读]
**一句话总结**: 20-40字概括核心科技趋势

**阅读时间**: ⏱️ X 分钟

**核心观点**:
1. 洞察1（不要复制热点标题）
2. 洞察2
3. 洞察3
4. 洞察4
5. 洞察5

**关键词**: 技术名, 产品名, 公司名（3-6个具体中文词）

:::
```

第3步：输出正文（以下每个部分只出现一次）：

### 开篇引言（100-200字）
提炼今日科技核心特征，不要罗列热点。

### 深度分析（2-3个板块）
- 小标题概括核心观点
- 解释技术原理，引用输入热点中的真实数据（不要编造数字）
- 预测趋势
- 每板块1个表格 + 1个 `:::note[💡 关键洞察]`

### 平台热点精选（5-8个）
格式：`**平台名**：[标题](链接) - 一句话点评`

### 趋势观察（3-4条）

### 结语（100-200字）
呼应开篇，形成闭环。

## 内容要求
- 聚焦AI、开源、芯片、科技商业
- 不聊政治流水账、娱乐八卦
- 科技内容≥70%
- 全文不超过1500字
- 禁止重复输出同一章节
- 禁止复制输入的热点标题当观点
- 禁止编造虚假数据（表格数据必须来自输入热点）
- 禁止模板化废话
- 正文中不要再次出现"快速阅读区"

你是主编，筛选最有价值的科技话题，提供深度分析。"""
        
        # 📋 加载外部动态 Prompt 强化要求
        try:
            prompt_addon_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'evolution', 'prompts', 'article_prompt.md'
            )
            if os.path.exists(prompt_addon_path):
                with open(prompt_addon_path, 'r', encoding='utf-8') as f:
                    addon_content = f.read()
                # 提取 <!-- AUTO-PROMPT-SECTION --> 之间的内容
                import re
                match = re.search(
                    r'<!--\s*AUTO-PROMPT-SECTION\s*开始.*?-->(.*?)<!--\s*AUTO-PROMPT-SECTION\s*结束\s*-->',
                    addon_content, re.DOTALL
                )
                if match:
                    auto_section = match.group(1).strip()
                    if auto_section:
                        system_prompt += f"\n\n## 动态强化要求\n{auto_section}\n"
                        logger.info("[Prompt扩展] 已加载动态强化要求")
        except Exception as e:
            logger.warning(f"[Prompt扩展] 加载外部Prompt失败: {e}")
        
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

请立即输出完整 Markdown 文章（控制字数在 {optimized_params['max_tokens']//3} 字以内）！"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call AI API with optimized parameters
        logger.info("Calling AI API to generate article...")
        ai_content = ai_client.chat(
            messages, 
            temperature=optimized_params['temperature'],
            max_tokens=optimized_params['max_tokens'],
            require_high_quality=True,  # 文章生成强制使用高质量模型
            task_type="article_generation"
        )
        
        if not ai_content or len(ai_content.strip()) < 100:
            raise ValueError("AI generated content is too short or empty")
        
        # Estimate token usage (rough estimate: 1 Chinese char ≈ 1.5 tokens)
        estimated_tokens = int(len(ai_content) * 1.5 + len(str(messages)) * 0.5)
        logger.info(f"AI generated {len(ai_content)} characters (~{estimated_tokens} tokens)")
        
        # 🔬 科技内容检测
        try:
            from evolution.tech_content_guard import check_tech_content
            is_pass, tech_message = check_tech_content(ai_content, min_ratio=0.5)
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
    
    def _enhance_frontmatter_multi_model(self, content: str) -> str:
        """
        多模型协作优化文章 frontmatter — 让每个模型做它百分百擅长的事
        
        分工策略:
        - Gemini (title_optimization): 标题创意、description 提炼
        - GitHub Models (keyword_extraction): tags 结构化提取
        - 失败时保留原 frontmatter，不影响主体文章
        """
        import re
        
        if not content or not content.startswith('---'):
            return content
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            return content
        
        frontmatter = parts[1]
        body = parts[2]
        
        # 提取当前 frontmatter 字段
        current_title_match = re.search(r'^title:\s*"([^"]+)"', frontmatter, re.MULTILINE)
        current_title = current_title_match.group(1) if current_title_match else ""
        
        current_desc_match = re.search(r'^description:\s*"([^"]+)"', frontmatter, re.MULTILINE)
        current_desc = current_desc_match.group(1) if current_desc_match else ""
        
        current_tags_match = re.search(r'^tags:\s*\[([^\]]*)\]', frontmatter, re.MULTILINE)
        current_tags = current_tags_match.group(1) if current_tags_match else ""
        
        # 正文摘要（限制长度，控制成本）
        body_summary = body[:3000]
        
        # 创建 AI 客户端
        try:
            from ..ai.smart_client import SmartAIClient
            from ..core.loader import load_config
            config = load_config()
            ai_client = SmartAIClient(config.get("ai", {}))
        except Exception as e:
            logger.warning(f"[多模型增强] AI客户端创建失败: {e}")
            return content
        
        new_title = current_title
        new_desc = current_desc
        new_tags = current_tags
        
        # ═══════════════════════════════════════════════════════════
        # Step 1: Gemini — 优化 title + description（创意+提炼）
        # ═══════════════════════════════════════════════════════════
        try:
            title_desc_prompt = f"""基于以下文章正文，优化标题和描述。

当前标题: {current_title}
当前描述: {current_desc}

优化要求:
1. 标题: 15-25字，具体有料，优先包含数字/核心事件/公司名称，禁止"每日科技热点"这类泛泛标题
2. 描述: 30-50字，一句话概括文章核心科技价值，不要复制标题

正文摘要:
{body_summary}

请严格按以下格式输出，不要有任何多余解释:
TITLE: <优化后的标题>
DESCRIPTION: <优化后的描述>"""
            
            result = ai_client.chat(
                [{"role": "user", "content": title_desc_prompt}],
                task_type="title_optimization",
                temperature=0.7,
                max_tokens=200
            )
            
            # 解析结果
            title_m = re.search(r'TITLE:\s*(.+?)(?:\n|$)', result)
            desc_m = re.search(r'DESCRIPTION:\s*(.+?)(?:\n|$)', result)
            
            if title_m:
                candidate = title_m.group(1).strip().strip('"').strip("'")
                # 质量校验: 长度、非空、有变化、不是泛泛标题
                if (5 <= len(candidate) <= 35 and 
                    candidate != current_title and
                    not any(v in candidate for v in ['每日科技热点', '科技日报', '热点聚合', 'TrendRadar Report'])):
                    new_title = candidate
                    print(f"[多模型增强] 标题优化: '{current_title[:30]}...' → '{new_title[:30]}...'")
            
            if desc_m:
                candidate = desc_m.group(1).strip().strip('"').strip("'")
                if (10 <= len(candidate) <= 80 and candidate != current_desc):
                    new_desc = candidate
                    print(f"[多模型增强] 描述优化: '{current_desc[:25]}...' → '{new_desc[:25]}...'")
            
            # Fallback: 如果主路径没有优化成功，尝试更宽松的方式
            try:
                fallback_prompt = f"""请为以下文章生成一个吸引人的中文标题（15-25字）和一句话描述（30-50字）。

文章摘要: {body_summary[:1500]}

直接输出标题和描述，不要加标签前缀。"""
                fb_result = ai_client.chat(
                    [{"role": "user", "content": fallback_prompt}],
                    temperature=0.7,
                    max_tokens=150
                )
                # 宽松解析：第一行作为标题，第二行作为描述
                lines = [l.strip() for l in fb_result.split('\n') if l.strip()]
                if lines and new_title == current_title:
                    fb_title = lines[0].strip('"').strip("'")
                    if 8 <= len(fb_title) <= 35 and fb_title != current_title:
                        new_title = fb_title
                        print(f"[多模型增强] Fallback 标题: '{current_title[:30]}...' → '{new_title[:30]}...'")
                if len(lines) >= 2 and new_desc == current_desc:
                    fb_desc = lines[1].strip('"').strip("'")
                    if 10 <= len(fb_desc) <= 80 and fb_desc != current_desc:
                        new_desc = fb_desc
                        print(f"[多模型增强] Fallback 描述: '{current_desc[:25]}...' → '{new_desc[:25]}...'")
            except Exception as fb_e:
                logger.warning(f"[多模型增强] Fallback 优化失败: {fb_e}")
                    
        except Exception as e:
            logger.warning(f"[多模型增强] Gemini title/description 优化失败: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # Step 2: GitHub Models — 提取 tags（结构化输出）
        # ═══════════════════════════════════════════════════════════
        try:
            tags_prompt = f"""从以下科技文章中提取3-6个中文标签。

要求:
- 必须是中文标签
- 至少50%是科技类标签（如: AI, 芯片, 开源, 云计算, 大模型, 自动驾驶等）
- 输出格式严格为: ["标签1", "标签2", "标签3"]
- 只输出标签数组，不要任何解释

正文摘要:
{body_summary}

当前标签: [{current_tags}]"""
            
            result = ai_client.chat(
                [{"role": "user", "content": tags_prompt}],
                task_type="keyword_extraction",
                temperature=0.3,
                max_tokens=100
            )
            
            # 解析方括号中的标签
            tags_m = re.search(r'\[([^\]]+)\]', result)
            if tags_m:
                raw = tags_m.group(1).strip()
                tag_list = [t.strip().strip('"').strip("'") for t in raw.split(',')]
                # 过滤有效中文标签
                valid_tags = []
                for t in tag_list:
                    if any('\u4e00' <= c <= '\u9fff' for c in t) and len(t) >= 1 and len(t) <= 12:
                        valid_tags.append(t)
                if len(valid_tags) >= 3:
                    new_tags = ', '.join(f'"{t}"' for t in valid_tags[:6])
                    logger.info(f"[多模型增强] GitHub Models优化标签: [{current_tags}] → [{new_tags}]")
                    
        except Exception as e:
            logger.warning(f"[多模型增强] GitHub Models tags 提取失败: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # Step 3: 组装新的 frontmatter
        # ═══════════════════════════════════════════════════════════
        new_frontmatter = frontmatter
        
        if new_title != current_title:
            new_frontmatter = re.sub(
                r'^title:\s*"([^"]+)"',
                f'title: "{new_title}"',
                new_frontmatter,
                flags=re.MULTILINE
            )
        
        if new_desc != current_desc:
            new_frontmatter = re.sub(
                r'^description:\s*"([^"]+)"',
                f'description: "{new_desc}"',
                new_frontmatter,
                flags=re.MULTILINE
            )
        
        if new_tags != current_tags:
            new_frontmatter = re.sub(
                r'^tags:\s*\[([^\]]*)\]',
                f'tags: [{new_tags}]',
                new_frontmatter,
                flags=re.MULTILINE
            )
        
        enhanced = f"---{new_frontmatter}---{body}"
        logger.info(f"[多模型增强] frontmatter 优化完成")
        return enhanced
    
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
        
        # 强制覆盖 draft: true → draft: false（智能调度草稿模式在验证通过后发布）
        fm = re.sub(r'^draft:\s*true\s*$', 'draft: false', fm, flags=re.MULTILINE)

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
        # 检测常见的问题列表模式 —— 降级为警告，不阻止发布
        question_patterns = [
            r'具体是怎么回事\?',
            r'如何看待这一事件\?',
            r'背后有什么科学原理\?',
            r'我们为何要研究',
            r'这种相处模式为什么',
        ]
        for pattern in question_patterns:
            if re.search(pattern, body):
                # 降级为警告：AI可能在引用热点标题进行分析，不一定是复制
                logger.warning("[格式验证] 正文包含类似热搜问题的表述，建议检查是否复制输入数据")
                break
        
        # 8. 检查核心观点是否变成问题列表
        if '核心观点' in body:
            # 提取核心观点部分
            kp_match = re.search(r'核心观点[:：]\s*\n(.*?)(?:\n##|\n###|</aside>|$)', body, re.DOTALL)
            if kp_match:
                kp_section = kp_match.group(1)
                # 如果核心观点中有太多问号，说明是问题列表
                question_count = kp_section.count('？') + kp_section.count('?')
                line_count = kp_section.count('\n')
                if question_count > 2 and question_count > line_count * 0.3:
                    issues.append("核心观点被替换为问题列表（AI未正确理解任务）")
        
        # 9. 检查内容重复（同一章节标题出现多次是严重质量问题）
        section_headers = re.findall(r'^(#{2,3}\s+.+)$', body, re.MULTILINE)
        seen_headers = set()
        duplicates = []
        for h in section_headers:
            h_clean = h.strip()
            if h_clean in seen_headers:
                duplicates.append(h_clean)
            seen_headers.add(h_clean)
        if duplicates:
            issues.append(f"内容重复: {duplicates[:2]} 等章节出现多次")
        
        # 10. 检查关键词质量（快速阅读区的关键词列表）
        kw_match = re.search(r'\*\*关键词\*\*[:：]\s*(.+?)(?:\n\n|\n\*\*|$)', body, re.DOTALL)
        if kw_match:
            kw_text = kw_match.group(1)
            # 检测无意义词
            meaningless_kws = ['有了更多的了', '了解', '的了解', '让我们', '对国际', '了更多的了解']
            found_bad = [w for w in meaningless_kws if w in kw_text]
            if found_bad:
                issues.append(f"关键词包含无意义词汇: {found_bad}")
        
        # 11. 检查一句话总结质量
        summary_match = re.search(r'\*\*一句话总结\*\*[:：]\s*(.+?)(?:\n\n|\n\*\*|$)', body, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
            if summary.startswith('====') or summary.startswith('---') or len(summary) < 10:
                issues.append(f"一句话总结无效: {summary[:30]}")
        
        # 12. 检查文章长度（frontmatter 约 200 字符，正文至少 300 字符）
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
