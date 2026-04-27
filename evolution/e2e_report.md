# 🔬 端到端测试报告

**状态**: ✅ 全部通过
**通过**: 339 项
**失败**: 0 项

## memory_backend (3.75s)
- ✅ **读写一致性**: 保存后成功读取，数据一致（1 条记录）
- ✅ **state过滤参数**: state 过滤参数正确（all/open）
- ✅ **标题唯一性**: 标题包含文章标识，可区分不同记忆
- ✅ **记忆数据集成**: trending_topics 从记忆数据提取

## frontmatter_pipeline (0.2s)
- ✅ **正常 frontmatter**: 验证通过
- ✅ **引号嵌套修复**: 检测到引号嵌套并自动修复为单引号包裹
- ✅ **缺少字段补全**: 检测到缺少字段并自动补全默认值
- ✅ **空行开头兼容**: 空行开头的 frontmatter 验证通过
- ✅ **重复 image 键**: 检测到重复 image 键并清理为 1 个
- ✅ **YAML 语法错误**: 未检测到 YAML 错误，验证器未崩溃

## data_pipeline (0.11s)
- ✅ **写入读取一致性**: 写入后成功读取，id=test-001
- ✅ **必填字段校验**: 缺少必填字段时 write() 通过（未崩溃）
- ✅ **多次写入读取**: 写入 3 条记录，读出 3 条
- ✅ **JSONL 格式合法**: 所有 jsonl 文件格式正确
- ✅ **数据类型初始化**: 6 种数据类型文件全部初始化

## github_pipeline (3.74s)
- ✅ **引号嵌套修复**: 双引号嵌套已修复为单引号包裹
- ✅ **重复键去重**: 重复 image 键已清理为 1 个
- ✅ **缺少 frontmatter**: 缺少 frontmatter 时已自动添加默认
- ✅ **空行开头兼容**: 空行开头的 frontmatter 正确解析
- ✅ **文章格式验证**: 正常文章格式验证通过
- ✅ **缺少字段检测**: 缺少必要字段时验证正确失败
- ✅ **title 强制引号**: 未用引号包裹的 title 已强制加引号

## exception_monitor (0.17s)
- ✅ **记录读取一致性**: 异常已记录，指纹=1f954f7f...
- ✅ **异常分类**: 网络/超时/逻辑异常分类正确
- ✅ **指纹计数**: 相同异常指纹计数正确递增
- ✅ **装饰器捕获**: monitor 装饰器正确捕获并记录异常
- ✅ **异常统计**: 统计功能正常返回数据

## model_router (0.05s)
- ✅ **文章生成路由**: 选择推理模型: deepseek/deepseek-reasoner
- ✅ **RSS分析路由**: 选择轻量模型: deepseek/deepseek-chat
- ✅ **降级链配置**: 降级模型: ['deepseek/deepseek-chat']
- ✅ **成本估算**: 预估成本: ¥12.00
- ✅ **翻译任务成本**: 选择低价模型: deepseek/deepseek-chat (¥1.0/M)
- ✅ **使用记录报告**: 成本报告生成成功，总成本: ¥0.0000

## tech_content_guard (0.01s)
- ✅ **高科技内容通过**: 科技占比 80%，深度 6/10
- ✅ **低科技内容拦截**: 正确拦截，占比 10%
- ✅ **非科技检测**: 检测到非科技内容，占比 100%
- ✅ **frontmatter 清理**: 清理后正确检测，占比 70%
- ✅ **技术深度评分**: 深度评分 6/10
- ✅ **强制 Prompt**: 低质量内容正确生成强化 Prompt
- ✅ **空内容处理**: 空内容正确标记为不通过

## free_ai_router (0.04s)
- ✅ **轻量任务免费**: 选择 Cloudflare Workers AI，成本 ¥0
- ✅ **高质量兜底**: 高质量任务选择 DeepSeek
- ✅ **额度耗尽降级**: Cloudflare 耗尽后选择 Google Gemini
- ✅ **额度状态**: Cloudflare 剩余 10000 
- ✅ **成本报告**: 总成本 ¥0.6300, 节省 ¥-0.6294
- ✅ **翻译任务路由**: 翻译任务选择 Google Gemini（免费）

## tag_optimizer (0.02s)
- ✅ **标题提取标签**: 提取到标签: ['AI', '投资']
- ✅ **默认标签**: 无匹配时返回默认 '科技'
- ✅ **标签分布**: 分析到 5 个标签
- ✅ **过度使用检测**: 检测到 1 个过度使用标签
- ✅ **缺失标签检测**: 检测到缺失具体标签的文章
- ✅ **低质量标签**: 检测到 1 个低质量标签
- ✅ **生成建议**: 生成 2 条建议
- ✅ **报告生成**: 报告生成成功

## trend_forecast (0.03s)
- ✅ **已知模式**: 加载了 7 个模式: Apple发布会周期, Google I/O, CES消费电子展...
- ✅ **未来事件预测**: 预测到 6 个事件
- ✅ **预测结构**: topic=Google I/O (2026-05), confidence=1.0
- ✅ **季节性预测**: 6月=1, 9月=1, 12月=1
- ✅ **新兴趋势**: 检测到新趋势: ['GPT-5', 'Claude 4', '量子计算突破']
- ✅ **无新趋势**: 相同话题正确返回空
- ✅ **内容建议**: 生成 1 条建议
- ✅ **置信度排序**: 置信度降序: [1.0, 0.95, 0.95]

## semantic_deduplicator (0.76s)
- ✅ **高相似度**: 相似度 0.78
- ✅ **低相似度**: 相似度 0.00
- ✅ **空文本**: 空文本相似度为0
- ✅ **相同文本**: 相同文本相似度为1.0
- ✅ **领域增强**: 检测到领域权重: ['__domain_ai']
- ✅ **阈值判断**: 相似度 0.89 >= 0.65，判定重复
- ✅ **建议分级**: 无历史文章: 无历史文章，可以生成

## auto_calibration (0.6s)
- ✅ **test_record_quality_and_persist**: 质量记录与持久化一致
- ✅ **test_overall_score_calculation**: 综合分数计算权重正确
- ✅ **test_optimal_params_recommendation**: 参数推荐系统工作正常
- ✅ **test_recommendation_confidence_threshold**: 置信度阈值过滤正确
- ✅ **test_quality_records_limit**: 记录上限100条正确
- ✅ **test_calibration_report_format**: 校准报告格式正确

## self_observer (0.17s)
- ✅ **test_diagnosis_report_structure**: 诊断报告结构完整
- ✅ **test_content_quality_analysis**: 内容质量分析正确 (score=7.0, trend=declining)
- ✅ **test_system_stability_analysis**: 系统稳定性分析正确
- ✅ **test_feature_coverage_scan**: 功能覆盖扫描正确 (active=3)
- ✅ **test_report_persistence**: 报告持久化保留10份正确
- ✅ **test_capability_gap_report**: 能力缺口报告格式正确
- ✅ **test_empty_metrics_handling**: 空指标数据处理正确

## smart_summary (0.01s)
- ✅ **test_extract_tldr_from_description**: 从description提取TL;DR正确
- ✅ **test_extract_tldr_from_content**: 从正文提取TL;DR正确: '谷歌量子计算团队宣布实现了新的量子纠错里程碑。...'
- ✅ **test_extract_key_insights**: 提取4条核心观点
- ✅ **test_extract_keywords_from_tags**: 从tags提取关键词: ['科技', 'AI芯片', '半导体', '英伟达']
- ✅ **test_extract_keywords_fallback**: 无tags时关键词: ['和人工智能正', '在改变软件开', '发的方式', '机器学习模型', '越来越强大']
- ✅ **test_estimate_reading_time**: 阅读时间估算: 1分钟
- ✅ **test_generate_summary_block**: 摘要块格式正确
- ✅ **test_inject_summary_position**: 摘要注入位置正确
- ✅ **test_inject_summary_no_frontmatter**: 无frontmatter注入正确
- ✅ **test_get_article_summary_dict**: 便捷函数返回结构正确

## title_optimizer (0.01s)
- ✅ **test_extract_topics**: 提取到10个话题: ['Intel', '英伟达', 'AMD']
- ✅ **test_generate_candidates**: 生成3个候选标题
- ✅ **test_score_title_length**: 长度评分: 最佳=45, 短=25, 长=45
- ✅ **test_score_title_with_number**: 含数字=47, 不含=45
- ✅ **test_score_title_question**: 疑问句=45, 陈述句=25
- ✅ **test_select_best_title**: 最佳标题: '3个数据揭示AI芯片真相' (评分: 47)
- ✅ **test_optimize_title**: 优化后标题: 'Intel你看懂了吗？...'
- ✅ **test_replace_title_simple**: 简单标题替换正确
- ✅ **test_replace_title_with_double_quotes**: 双引号标题安全替换正确
- ✅ **test_replace_title_no_frontmatter**: 无frontmatter处理正确
- ✅ **test_convenience_optimize_article_title**: 便捷函数返回: 'Intel意味着什么？...'
- ✅ **test_detect_garbage_title_number_secret**: 垃圾标题检测正确
- ✅ **test_detect_garbage_title_version**: 版本号垃圾标题检测正确
- ✅ **test_safe_fallback_no_garbage_output**: 安全回退生效: 'DeepSeek：真相...'
- ✅ **test_meaningful_number_scoring**: 有意义=50, 短数字=42

## regression_guard (0.55s)
- ✅ **test_article_quality_regression_detected**: 检测到退化: severity=critical, drop=0.38
- ✅ **test_article_quality_stable**: 质量稳定，未检测到退化
- ✅ **test_insufficient_data**: 数据不足处理正确
- ✅ **test_pause_evolution**: 暂停标记创建正确
- ✅ **test_is_evolution_paused**: 暂停状态检测正确
- ✅ **test_resume_evolution**: 恢复进化功能正确
- ✅ **test_regression_log_persistence**: 日志持久化正确: 2条记录
- ✅ **test_run_full_check_healthy**: 文章质量健康, full_check结构正确 (status=critical)
- ✅ **test_run_full_check_critical**: 严重退化检测正确: 2项退化, 1项干预

## output_quality_validator (0.33s)
- ✅ **test_validate_issue_frontmatter_leak**: 检测到4个frontmatter泄漏
- ✅ **test_validate_issue_truncation_marker**: 截断标记检测正确
- ✅ **test_validate_issue_empty_excerpt**: 空excerpt检测正确
- ✅ **test_validate_issue_short_excerpt**: excerpt过短检测正确
- ✅ **test_validate_issue_markdown_in_excerpt**: markdown混入检测正确: 1个
- ✅ **test_validate_issue_clean**: 干净Issue验证通过
- ✅ **test_validate_article_frontmatter_complete**: 完整frontmatter验证通过
- ✅ **test_validate_article_frontmatter_missing**: 缺少frontmatter检测正确
- ✅ **test_validate_article_frontmatter_missing_field**: 检测到2个缺少字段
- ✅ **test_validate_article_frontmatter_too_few_tags**: 标签过少检测正确
- ✅ **test_check_issue_quality_convenience**: 便捷函数工作正常
- ✅ **test_body_too_long**: body过长检测正确

## frontmatter_validator (0.01s)
- ✅ **test_validate_complete_frontmatter**: 完整 frontmatter 验证通过
- ✅ **test_validate_missing_frontmatter**: 缺少 frontmatter 自动添加正确
- ✅ **test_validate_title_quote_nesting**: title 引号嵌套检测和修复正确
- ✅ **test_validate_description_quote_nesting**: description 引号嵌套检测正确
- ✅ **test_validate_published_format**: published 格式检测正确
- ✅ **test_validate_tags_not_list**: tags 格式检测正确
- ✅ **test_validate_duplicate_keys**: 重复键检测和清理正确
- ✅ **test_validate_missing_required_fields**: 缺少字段自动补全正确
- ✅ **test_validate_yaml_syntax_error**: YAML 语法处理正确
- ✅ **test_validate_leading_whitespace**: 开头空行兼容正确
- ✅ **test_convenience_validate_article**: 便捷函数工作正常
- ✅ **test_batch_validate_files**: 批量验证正确

## health_check (0.52s)
- ✅ **test_check_decorator_pass**: _check 通过情况正确
- ✅ **test_check_decorator_fail**: _check 失败情况正确
- ✅ **test_warn**: _warn 记录警告正确
- ✅ **test_check_python_syntax_valid**: Python 语法检查通过正确
- ✅ **test_check_python_syntax_invalid**: Python 语法检查失败正确
- ✅ **test_check_repo_size**: 仓库大小检查正确: 0.19MB
- ✅ **test_run_all_checks_structure**: run_all_checks 结构正确, status=healthy
- ✅ **test_generate_health_report**: 健康报告格式正确
- ✅ **test_convenience_run_health_check**: 便捷函数返回结构正确

## article_quality_db (0.06s)
- ✅ **test_record_and_query**: 记录查询一致: 3 条
- ✅ **test_query_by_date_range**: 日期范围查询正确
- ✅ **test_query_by_score**: 评分查询正确: 2 条
- ✅ **test_query_by_tag**: 标签查询正确: 2 条
- ✅ **test_query_limit**: 查询数量限制正确
- ✅ **test_get_quality_trend**: 趋势: stable, 均分: 6.83
- ✅ **test_get_module_contribution**: 模块贡献度: 2.75, 样本: 2
- ✅ **test_generate_quality_report**: 质量报告格式正确
- ✅ **test_empty_db_query**: 空数据库处理正确

## diversity_engine (0.02s)
- ✅ **test_init_has_templates**: 通过
- ✅ **test_select_template_match_topic**: 通过
- ✅ **test_select_template_no_match_fallback**: 通过
- ✅ **test_select_template_avoids_recent**: 通过
- ✅ **test_generate_instructions_format**: 通过
- ✅ **test_generate_instructions_required_marker**: 通过
- ✅ **test_record_and_get_recent_templates**: 通过
- ✅ **test_get_recent_templates_empty**: 通过
- ✅ **test_perspective_rotator_count**: 通过
- ✅ **test_perspective_rotator_format**: 通过
- ✅ **test_get_diversity_instructions**: 通过

## knowledge_graph (0.02s)
- ✅ **test_extract_entities_company**: 通过
- ✅ **test_extract_entities_technology**: 通过
- ✅ **test_extract_entities_multiple_types**: 通过
- ✅ **test_extract_entities_empty**: 通过
- ✅ **test_find_relations_compete**: 通过
- ✅ **test_find_relations_cooperate**: 通过
- ✅ **test_build_graph_structure**: 通过
- ✅ **test_generate_insight_with_entities**: 通过
- ✅ **test_generate_insight_empty**: 通过
- ✅ **test_save_and_load_graph**: 通过
- ✅ **test_get_entity_history**: 通过
- ✅ **test_get_knowledge_graph_insight**: 通过

## cleanup_manager (0.14s)
- ✅ **test_init_creates_trash**: 通过
- ✅ **test_is_protected_py**: 通过
- ✅ **test_is_protected_config**: 通过
- ✅ **test_is_protected_git**: 通过
- ✅ **test_is_not_protected_tmp**: 通过
- ✅ **test_cleanup_temp_files**: 通过
- ✅ **test_cleanup_python_cache**: 通过
- ✅ **test_cleanup_old_logs**: 通过
- ✅ **test_cleanup_empty_dirs**: 通过
- ✅ **test_run_cleanup_returns_list**: 通过
- ✅ **test_generate_report**: 通过

## emotion_analyzer (0.0s)
- ✅ **test_analyze_positive**: 通过
- ✅ **test_analyze_negative**: 通过
- ✅ **test_analyze_neutral**: 通过
- ✅ **test_analyze_empty**: 通过
- ✅ **test_analyze_controversial**: 通过
- ✅ **test_analyze_not_controversial**: 通过
- ✅ **test_analyze_intensity**: 通过
- ✅ **test_analyze_batch**: 通过
- ✅ **test_analyze_batch_empty**: 通过
- ✅ **test_generate_insight**: 通过
- ✅ **test_convenience_analyze_emotion**: 通过

## unified_logger (0.05s)
- ✅ **test_set_get_article_id**: 通过
- ✅ **test_log_info_writes_file**: 通过
- ✅ **test_log_warn_level**: 通过
- ✅ **test_log_error_level**: 通过
- ✅ **test_log_debug_no_console**: 通过
- ✅ **test_log_with_article_id**: 通过
- ✅ **test_get_run_summary**: 通过
- ✅ **test_step_timer_success**: 通过
- ✅ **test_step_timer_exception**: 通过

## module_value_assessor (0.01s)
- ✅ **test_calculate_complexity_optimal**: 通过
- ✅ **test_calculate_complexity_small**: 通过
- ✅ **test_calculate_functional_value**: 通过
- ✅ **test_calculate_integration_difficulty**: 通过
- ✅ **test_calculate_integration_easy**: 通过
- ✅ **test_calculate_maturity**: 通过
- ✅ **test_get_recommendation_high**: 通过
- ✅ **test_get_recommendation_low**: 通过
- ✅ **test_assess_module**: 通过
- ✅ **test_generate_report**: 通过

## data_archiver (0.04s)
- ✅ **test_compress_file**: 通过
- ✅ **test_compress_file_not_found**: 通过
- ✅ **test_archive_json_by_age**: 通过
- ✅ **test_archive_json_by_age_no_old_data**: 通过
- ✅ **test_archive_json_by_count**: 通过
- ✅ **test_archive_json_by_count_under_limit**: 通过
- ✅ **test_archive_old_databases**: 通过
- ✅ **test_generate_archive_report**: 通过
- ✅ **test_generate_archive_report_empty**: 通过
- ✅ **test_run_auto_archive_skips_missing**: 通过

## reader_behavior_analyzer (0.02s)
- ✅ **test_analyze_tag_popularity**: 通过
- ✅ **test_analyze_tag_popularity_empty**: 通过
- ✅ **test_analyze_quality_trends**: 通过
- ✅ **test_analyze_quality_trends_stable**: 通过
- ✅ **test_analyze_source_quality**: 通过
- ✅ **test_analyze_source_quality_list_format**: 通过
- ✅ **test_identify_content_gaps**: 通过
- ✅ **test_generate_content_strategy**: 通过
- ✅ **test_generate_content_strategy_empty**: 通过
- ✅ **test_generate_report**: 通过
- ✅ **test_save_outputs**: 通过
- ✅ **test_extract_keywords**: 通过
- ✅ **test_extract_keywords_empty**: 通过

## ab_testing (0.13s)
- ✅ **test_create_test**: 通过
- ✅ **test_assign_variant**: 通过
- ✅ **test_assign_variant_inactive**: 通过
- ✅ **test_record_result**: 通过
- ✅ **test_get_test_summary**: 通过
- ✅ **test_auto_select_winner**: 通过
- ✅ **test_calculate_significance**: 通过
- ✅ **test_get_recommendations**: 通过
- ✅ **test_auto_create_tests**: 通过
- ✅ **test_run_ab_test_decision**: 通过
- ✅ **test_run_ab_test_decision_invalid_dimension**: 通过

## prompt_optimizer (0.02s)
- ✅ **test_calculate_weights_high_effect**: 通过
- ✅ **test_calculate_weights_low_effect**: 通过
- ✅ **test_generate_plan_boost**: 通过
- ✅ **test_generate_plan_remove**: 通过
- ✅ **test_generate_plan_new_suggestions**: 通过
- ✅ **test_save_load_optimization**: 通过
- ✅ **test_optimized_params_long_prompt**: 通过
- ✅ **test_optimized_params_short_prompt**: 通过
- ✅ **test_optimized_params_with_history**: 通过
- ✅ **test_empty_fragment_data**: 通过
- ✅ **test_reorder_sorted_by_weight**: 通过

## prompt_tracker (0.04s)
- ✅ **test_record_usage**: 通过
- ✅ **test_analyze_effectiveness**: 通过
- ✅ **test_assess_effect_significant**: 通过
- ✅ **test_assess_effect_none**: 通过
- ✅ **test_get_top_fragments**: 通过
- ✅ **test_get_weak_fragments**: 通过
- ✅ **test_top_fragments_min_uses_filter**: 通过
- ✅ **test_empty_tracks**: 通过
- ✅ **test_single_track_insufficient**: 通过
- ✅ **test_save_load_tracks**: 通过

## smart_scheduler (0.06s)
- ✅ **test_evaluate_high_quality**: 通过
- ✅ **test_evaluate_low_quality**: 通过
- ✅ **test_make_decision_publish**: 通过
- ✅ **test_make_decision_skip**: 通过
- ✅ **test_make_decision_draft**: 通过
- ✅ **test_history_trend_no_data**: 通过
- ✅ **test_history_trend_good**: 通过
- ✅ **test_schedule_stats**: 通过
- ✅ **test_should_publish_today**: 通过
- ✅ **test_log_decision_retention**: 通过
- ✅ **test_metrics_in_decision**: 通过

## trend_predictor (0.03s)
- ✅ **test_analyze_topic_frequency**: 通过
- ✅ **test_analyze_topic_frequency_empty**: 通过
- ✅ **test_generate_prompt_insight**: 通过
- ✅ **test_generate_prompt_insight_empty**: 通过
- ✅ **test_generate_suggestion**: 通过
- ✅ **test_get_seasonal_trends**: 通过
- ✅ **test_hot_topics_rising**: 通过
- ✅ **test_predict_trends**: 通过
- ✅ **test_predict_trends_empty**: 通过
- ✅ **test_recurring_topics**: 通过

## quota_monitor (0.04s)
- ✅ **test_check_alerts**: 通过
- ✅ **test_check_alerts_normal**: 通过
- ✅ **test_generate_report**: 通过
- ✅ **test_get_daily_cost**: 通过
- ✅ **test_get_quota_status**: 通过
- ✅ **test_get_usage_today**: 通过
- ✅ **test_get_usage_today_empty**: 通过
- ✅ **test_quota_status_critical**: 通过
- ✅ **test_quota_status_warning**: 通过
- ✅ **test_record_usage**: 通过

## dynamic_scheduler (0.02s)
- ✅ **test_generate_schedule_always_run**: 通过
- ✅ **test_generate_schedule_report**: 通过
- ✅ **test_generate_schedule_run**: 通过
- ✅ **test_generate_schedule_skip**: 通过
- ✅ **test_generate_schedule_skip_repo_cleanup**: 通过
- ✅ **test_get_step_decision_run**: 通过
- ✅ **test_get_step_decision_skip**: 通过
- ✅ **test_get_step_decision_unknown**: 通过
- ✅ **test_load_jsonl**: 通过
- ✅ **test_load_jsonl_empty**: 通过
- ✅ **test_load_jsonl_invalid**: 通过

## repo_size_monitor (0.11s)
- ✅ **test_get_total_size**: 总大小: 3000 字节 (2.9 KB)
- ✅ **test_get_total_size_empty**: 空目录大小: 0 字节
- ✅ **test_scan_big_files**: 发现 1 个大文件
- ✅ **test_scan_big_files_empty**: 无大文件，返回空列表
- ✅ **test_analyze_file_distribution**: 检测到 3 种文件类型
- ✅ **test_analyze_file_distribution_empty**: 空目录分布正确
- ✅ **test_size_thresholds**: 阈值定义正确
- ✅ **test_git_size_no_git**: 无.git目录返回0
- ✅ **test_big_file_info_fields**: 字段完整: path, size_kb, size_mb, type, extension
- ✅ **test_distribution_percentage_calculation**: 百分比计算正确

## system_final_check (30.24s)
- ✅ **test_init_paths**: 路径初始化正确
- ✅ **test_check_module_imports**: 模块导入: 76/76 成功
- ✅ **test_check_critical_files**: 关键文件: 7/7 存在
- ✅ **test_check_workflow_syntax**: evolution.yml 语法: ✅ (25 个步骤)
- ✅ **test_check_title_quality**: 拦截=True, 过滤=True, 验证=True
- ✅ **test_generate_report_structure**: 报告结构完整
- ✅ **test_empty_directory**: 空目录产生 7 个缺失错误
- ✅ **test_error_tracking**: 结果=5, 警告=0, 错误=0
- ✅ **test_status_healthy**: 无错误状态=healthy
- ✅ **test_status_issues_found**: 有错误状态=issues_found
