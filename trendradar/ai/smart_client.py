# coding=utf-8
"""
智能AI客户端 - 自动选择免费API降低成本

集成策略：
1. 任务分类 → 选择最优Provider
2. 免费API优先 → 降低成本
3. 失败自动降级 → 保证可用性
4. 使用情况记录 → 额度监控
"""

import os
import time
from typing import Any, Dict, List

from .client import AIClient


class SmartAIClient:
    """智能AI客户端 - 多Provider路由"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.task_type = config.get("TASK_TYPE", "article_generation")
        
        # 保持与AIClient兼容的属性
        self.api_key = config.get("API_KEY") or os.environ.get("AI_API_KEY", "")
        self.model = config.get("MODEL", "deepseek/deepseek-chat")
        self.api_base = config.get("API_BASE", "")
        self.temperature = config.get("TEMPERATURE", 0.7)
        self.max_tokens = config.get("MAX_TOKENS", 4000)
        
        # 🛡️ 额度保护阈值（严格控制在免费额度内）
        self.quota_limits = {
            "cloudflare_workers_ai": {
                "daily_limit": 10000,
                "safety_threshold": 0.85,  # 用到85%就停用
                "unit": "neurons"
            },
            "google_gemini": {
                "daily_limit": 1500,
                "safety_threshold": 0.85,
                "unit": "requests"
            },
            "modelscope": {
                "daily_limit": 2000,
                "safety_threshold": 0.85,
                "unit": "requests"
            }
        }
        
        # ⏱️ 频率控制（避免429）
        self.last_gemini_call = 0
        self.min_interval = 2  # Gemini最小调用间隔2秒
        
        self._init_providers()
    
    def _check_quota(self, provider: str) -> bool:
        """
        检查Provider额度是否充足
        返回: True=可用, False=已超限或接近阈值
        """
        try:
            from evolution.quota_monitor import QuotaMonitor
            monitor = QuotaMonitor()
            usage = monitor.get_usage_today()
            
            limit_config = self.quota_limits.get(provider)
            if not limit_config:
                return True  # 没有限制（如DeepSeek）
            
            used = usage.get(provider, 0)
            limit = limit_config["daily_limit"]
            threshold = limit_config["safety_threshold"]
            
            # 检查是否超过安全阈值
            if used >= limit * threshold:
                print(f"[额度保护] {provider} 额度即将耗尽: {used}/{limit} ({used/limit*100:.0f}%)，切换到DeepSeek")
                return False
            
            return True
        except Exception:
            # 额度检查失败时，保守起见不使用免费API
            return False
    
    def _init_providers(self):
        """初始化各Provider客户端"""
        # DeepSeek（兜底）
        self.deepseek_client = AIClient({
            "MODEL": self.config.get("MODEL", "deepseek/deepseek-chat"),
            "API_KEY": self.config.get("API_KEY") or os.environ.get("AI_API_KEY", ""),
            "API_BASE": self.config.get("API_BASE", ""),
            "TEMPERATURE": self.config.get("TEMPERATURE", 0.7),
            "MAX_TOKENS": self.config.get("MAX_TOKENS", 4000),
        })
        
        # Cloudflare Workers AI
        cf_account = os.environ.get("CF_ACCOUNT_ID", "")
        cf_token = os.environ.get("CF_API_TOKEN", "")
        self.cf_enabled = bool(cf_account and cf_token)
        
        # Google Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        self.gemini_enabled = bool(gemini_key)
    
    def validate_config(self) -> tuple[bool, str]:
        """验证配置（代理到DeepSeek客户端）"""
        return self.deepseek_client.validate_config()
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        智能路由调用
        
        策略：
        1. 根据任务类型和配置选择Provider
        2. 免费API优先
        3. 失败时自动降级
        """
        start_time = time.time()
        
        # 确定任务类型
        task_type = kwargs.get("task_type", self.task_type)
        require_high_quality = kwargs.get("require_high_quality", False)
        
        # 路由决策
        provider = self._select_provider(task_type, require_high_quality)
        
        try:
            if provider == "cloudflare" and self.cf_enabled:
                return self._call_cloudflare(messages, kwargs, start_time, task_type)
            elif provider == "gemini" and self.gemini_enabled:
                return self._call_gemini(messages, kwargs, start_time, task_type)
            else:
                return self._call_deepseek(messages, kwargs, start_time, task_type)
        except Exception as e:
            print(f"[SmartAI] {provider} 调用失败: {e}，降级到DeepSeek")
            return self._call_deepseek(messages, kwargs, start_time, task_type)
    
    def _select_provider(self, task_type: str, require_high_quality: bool) -> str:
        """
        选择Provider（带额度保护）
        绝不超过免费额度！
        """
        # 高质量要求 → DeepSeek
        if require_high_quality:
            return "deepseek"
        
        # 检查各免费API额度（有额度才用）
        cf_available = self.cf_enabled and self._check_quota("cloudflare_workers_ai")
        gemini_available = self.gemini_enabled and self._check_quota("google_gemini")
        
        # 任务路由（只使用有额度的Provider）
        if task_type in ["summarization", "content_dedup", "rss_analysis"]:
            if cf_available:
                return "cloudflare"
            elif gemini_available:
                return "gemini"
        
        elif task_type in ["translation", "quality_evaluation"]:
            if gemini_available:
                return "gemini"
            elif cf_available:
                return "cloudflare"
        
        elif task_type == "article_generation":
            # 文章生成默认用DeepSeek，但可尝试Gemini（如果有额度）
            if gemini_available:
                return "gemini"
        
        # 默认兜底：DeepSeek（付费但稳定）
        return "deepseek"
    
    def _call_cloudflare(self, messages, kwargs, start_time, task_type):
        """调用Cloudflare Workers AI"""
        import requests
        
        account_id = os.environ.get("CF_ACCOUNT_ID", "")
        api_token = os.environ.get("CF_API_TOKEN", "")
        model = "@cf/meta/llama-3.1-8b-instruct"
        
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, 
                                json={"messages": messages}, 
                                timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("success"):
            content = result.get("result", {}).get("response", "")
            latency = time.time() - start_time
            self._record_usage("cloudflare_workers_ai", task_type, 0, 0, latency, True)
            return content
        else:
            raise Exception(f"Cloudflare API错误: {result.get('errors', [])}")
    
    def _call_gemini(self, messages, kwargs, start_time, task_type):
        """调用Google Gemini（带频率控制和重试）"""
        import requests
        import time as time_module
        
        api_key = os.environ.get("GEMINI_API_KEY", "")
        model = kwargs.get("model", "gemini-2.0-flash")
        
        # 频率控制：确保最小间隔
        elapsed = time_module.time() - self.last_gemini_call
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            print(f"[SmartAI] Gemini频率控制：等待 {wait_time:.1f} 秒")
            time_module.sleep(wait_time)
        
        # 转换消息格式
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        # 重试机制（最多3次，遇到429时等待）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, 
                                        json={"contents": gemini_messages},
                                        timeout=30)
                
                # 遇到429时等待后重试
                if response.status_code == 429:
                    wait = 2 ** attempt  # 指数退避：1, 2, 4秒
                    print(f"[SmartAI] Gemini 429，等待 {wait} 秒后重试 ({attempt+1}/{max_retries})")
                    time_module.sleep(wait)
                    continue
                
                response.raise_for_status()
                result = response.json()
                
                if "candidates" in result and result["candidates"]:
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    latency = time_module.time() - start_time
                    self.last_gemini_call = time_module.time()
                    self._record_usage("google_gemini", task_type, 0, 0, latency, True)
                    return content
                else:
                    raise Exception(f"Gemini API错误: {result}")
                    
            except requests.exceptions.HTTPError as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"[SmartAI] Gemini请求失败，等待 {wait} 秒后重试: {e}")
                    time_module.sleep(wait)
                else:
                    raise
        
        raise Exception("Gemini在最大重试次数后仍然失败")
    
    def _call_deepseek(self, messages, kwargs, start_time, task_type):
        """调用DeepSeek（兜底）"""
        result = self.deepseek_client.chat(messages, **kwargs)
        latency = time.time() - start_time
        
        # 估算tokens
        input_tokens = sum(len(m["content"]) for m in messages) // 4
        output_tokens = len(result) // 4
        
        self._record_usage("deepseek", task_type, input_tokens, output_tokens, latency, True)
        return result
    
    def _record_usage(self, provider: str, task_type: str, 
                     input_tokens: int, output_tokens: int, 
                     latency: float, success: bool):
        """记录使用情况"""
        try:
            from evolution.quota_monitor import QuotaMonitor
            monitor = QuotaMonitor()
            
            # 计算成本
            cost = 0.0
            if provider == "deepseek":
                cost = (input_tokens / 1_000_000) * 1.0 + (output_tokens / 1_000_000) * 2.0
            
            monitor.record_usage(provider, task_type, input_tokens + output_tokens, cost, latency, success)
        except Exception:
            pass  # 记录失败不影响主流程
