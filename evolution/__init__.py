# AI 自我进化系统
# 让 DeepSeek 持续自我改进，越来越强大、越来越聪明、越来越专业

from .evolution_system import AIEvolutionSystem, evaluate_and_evolve
from .system_evolution import SystemEvolutionEngine, evolve_system
from .auto_evolution import (
    AdaptiveEvolutionEngine,
    get_evolution_summary,
    record_article_metrics,
    update_rss_health
)

from .code_evolution import AutoCodeEvolution, run_auto_evolution
from .prompt_versioning import PromptVersionManager, get_compact_evolution_feedback
from .diversity_engine import ArticleDiversityEngine, get_diversity_instructions, PerspectiveRotator
from .smart_scheduler import SmartScheduler, get_smart_schedule_config
from .model_router import ModelRouter, get_model_for_task, TaskType
from .ab_testing import ABTestingFramework, run_ab_test_decision, TestDimension
from .auto_healing import AutoHealingSystem, handle_error, get_system_health
from .trend_forecast import TrendForecastEngine, get_trend_predictions, get_content_suggestions

__all__ = [
    'AIEvolutionSystem',
    'evaluate_and_evolve',
    'SystemEvolutionEngine',
    'evolve_system',
    'AdaptiveEvolutionEngine',
    'get_evolution_summary',
    'record_article_metrics',
    'update_rss_health',
    'AutoCodeEvolution',
    'run_auto_evolution',
    'PromptVersionManager',
    'get_compact_evolution_feedback',
    'ArticleDiversityEngine',
    'get_diversity_instructions',
    'PerspectiveRotator',
    'SmartScheduler',
    'get_smart_schedule_config',
    'ModelRouter',
    'get_model_for_task',
    'TaskType',
    'ABTestingFramework',
    'run_ab_test_decision',
    'TestDimension',
    'AutoHealingSystem',
    'handle_error',
    'get_system_health',
    'TrendForecastEngine',
    'get_trend_predictions',
    'get_content_suggestions'
]
