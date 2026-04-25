# -*- coding: utf-8 -*-
"""
智能异常修复 - Lv34

核心理念：
1. 读取Lv33的异常知识库
2. 匹配预设的修复方案
3. 自动应用修复
4. 记录修复结果，更新知识库

修复策略库：
- RSS SSL错误: 禁用该源，记录为失效源
- API 429: 增加重试间隔，切换备用API
- JSON解析错误: 尝试修复截断JSON，回退到简单解析
- 类型错误: 添加类型检查和防御性代码
- 连接超时: 增加超时时间，添加指数退避
- 权限错误: 检查环境变量和Token配置

修复方式：
- 配置修复: 修改config.yaml（禁用失效源、调整参数）
- 代码修复: 生成防御性代码补丁
- 路由修复: 切换API路由或数据源
- 重试修复: 调整重试策略

输出：
- 修复报告
- 更新的知识库
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional


class ExceptionHealer:
    """异常修复器"""
    
    # 修复策略库
    HEAL_STRATEGIES = {
        "network_ssl": {
            "name": "SSL证书修复",
            "category": "network",
            "pattern_keywords": ["SSL", "certificate", "verify", "TLS"],
            "actions": [
                "disable_source",
                "log_broken_source"
            ],
            "description": "SSL证书验证失败，禁用该RSS源并寻找替代"
        },
        "network_timeout": {
            "name": "连接超时修复",
            "category": "network",
            "pattern_keywords": ["Timeout", "timed out", "Connection refused"],
            "actions": [
                "increase_timeout",
                "add_retry_backoff"
            ],
            "description": "连接超时，增加超时时间和重试退避"
        },
        "api_rate_limit": {
            "name": "API限流修复",
            "category": "api_rate_limit",
            "pattern_keywords": ["429", "rate limit", "too many requests"],
            "actions": [
                "increase_interval",
                "switch_backup_api"
            ],
            "description": "API限流，增加调用间隔或切换到备用API"
        },
        "parse_json": {
            "name": "JSON解析修复",
            "category": "parse_error",
            "pattern_keywords": ["JSON", "parse", "Unterminated", "Expecting"],
            "actions": [
                "add_json_fix",
                "fallback_parser"
            ],
            "description": "JSON解析错误，添加截断修复和回退解析"
        },
        "type_error": {
            "name": "类型错误修复",
            "category": "type_error",
            "pattern_keywords": ["TypeError", "indices", "NoneType", "KeyError"],
            "actions": [
                "add_type_check",
                "add_null_guard"
            ],
            "description": "类型错误，添加类型检查和空值保护"
        },
        "permission_error": {
            "name": "权限修复",
            "category": "permission",
            "pattern_keywords": ["401", "403", "permission", "unauthorized"],
            "actions": [
                "check_env_vars",
                "check_permissions"
            ],
            "description": "权限错误，检查环境变量和权限配置"
        },
        "build_frontmatter": {
            "name": "Frontmatter格式修复",
            "category": "build_failure",
            "pattern_keywords": ["frontmatter", "yaml", "bad indentation", "mapping entry",
                               "InvalidContentEntryDataError", "schema", "title: Required"],
            "actions": [
                "fix_frontmatter_quotes",
                "add_missing_fields",
                "validate_before_push"
            ],
            "description": "Astro frontmatter YAML格式错误，修复引号嵌套和缺少字段"
        },
        "build_node_version": {
            "name": "Node.js版本修复",
            "category": "build_failure",
            "pattern_keywords": ["Node.js", "not supported", ">=22", ">=20",
                               "astro build", "compilation"],
            "actions": [
                "update_node_version",
                "update_workflow_config"
            ],
            "description": "Node.js版本不兼容Astro要求，升级workflow和package.json"
        },
        "deploy_cloudflare": {
            "name": "Cloudflare部署修复",
            "category": "deploy_failure",
            "pattern_keywords": ["Cloudflare Pages", "pages.dev", "404",
                               "Not Found", "deployment", "unreachable"],
            "actions": [
                "check_cf_pages_settings",
                "verify_build_output",
                "trigger_redeploy"
            ],
            "description": "Cloudflare Pages部署异常，检查构建设置和触发重新部署"
        }
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.knowledge_base_file = f"{trendradar_path}/evolution/exception_knowledge.json"
        self.heal_log_file = f"{trendradar_path}/evolution/heal_log.json"
        self.config_file = f"{trendradar_path}/config/config.yaml"
    
    def _load_knowledge_base(self) -> Dict:
        """加载异常知识库"""
        if os.path.exists(self.knowledge_base_file):
            try:
                with open(self.knowledge_base_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"exceptions": [], "patterns": {}}
    
    def _save_heal_log(self, log_entry: Dict):
        """保存修复日志"""
        logs = []
        if os.path.exists(self.heal_log_file):
            try:
                with open(self.heal_log_file, 'r') as f:
                    logs = json.load(f)
            except Exception:
                pass
        
        logs.append(log_entry)
        logs = logs[-50:]  # 保留最近50条
        
        with open(self.heal_log_file, 'w') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def _match_strategy(self, exception: Dict) -> Optional[Dict]:
        """为异常匹配合适的修复策略"""
        exc_type = exception.get("type", "").lower()
        exc_msg = exception.get("message", "").lower()
        category = exception.get("category", "")
        
        for strategy_id, strategy in self.HEAL_STRATEGIES.items():
            # 优先按类别匹配
            if strategy["category"] == category:
                return {**strategy, "strategy_id": strategy_id}
            
            # 按关键词匹配
            for keyword in strategy["pattern_keywords"]:
                if keyword.lower() in exc_msg or keyword.lower() in exc_type:
                    return {**strategy, "strategy_id": strategy_id}
        
        return None
    
    def _apply_action(self, action: str, exception: Dict) -> Dict:
        """应用修复动作"""
        result = {"action": action, "status": "skipped", "detail": ""}
        
        if action == "disable_source":
            # 从异常信息中提取源名称，尝试禁用
            result = self._heal_disable_source(exception)
        
        elif action == "increase_timeout":
            result = {"action": action, "status": "info", "detail": "建议增加请求超时时间到30秒"}
        
        elif action == "increase_interval":
            result = {"action": action, "status": "info", "detail": "建议增加API调用间隔到5秒"}
        
        elif action == "add_json_fix":
            result = {"action": action, "status": "info", "detail": "已在AI筛选模块添加JSON截断修复"}
        
        elif action == "add_type_check":
            result = {"action": action, "status": "info", "detail": "建议添加类型检查和防御性编程"}
        
        elif action == "check_env_vars":
            result = {"action": action, "status": "info", "detail": "请检查环境变量和Token配置"}
        
        return result
    
    def _heal_disable_source(self, exception: Dict) -> Dict:
        """修复：禁用失效的RSS源"""
        exc_msg = exception.get("message", "")
        
        # 尝试从错误信息中提取URL或源名称
        url_match = re.search(r'https?://[^\s\'"]+', exc_msg)
        if not url_match:
            return {"action": "disable_source", "status": "skipped", "detail": "无法从错误信息中提取源URL"}
        
        url = url_match.group(0)
        
        # 尝试在config.yaml中找到并禁用该源
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    content = f.read()
                
                # 检查是否包含该URL
                if url in content:
                    # 找到对应的源配置块，添加enabled: false
                    # 简化处理：如果源还没有enabled字段，添加一个
                    lines = content.split('\n')
                    modified = False
                    
                    for i, line in enumerate(lines):
                        if url in line:
                            # 在url行后面添加enabled: false
                            indent = len(line) - len(line.lstrip())
                            lines.insert(i + 1, ' ' * indent + 'enabled: false  # [AUTO-DISABLED] 异常自动禁用')
                            modified = True
                            break
                    
                    if modified:
                        with open(self.config_file, 'w') as f:
                            f.write('\n'.join(lines))
                        
                        return {
                            "action": "disable_source",
                            "status": "success",
                            "detail": f"已自动禁用失效源: {url}"
                        }
            except Exception as e:
                return {"action": "disable_source", "status": "failed", "detail": f"禁用源失败: {e}"}
        
        return {"action": "disable_source", "status": "skipped", "detail": f"未找到配置文件中匹配的源: {url}"}
    
    def heal_exception(self, exception: Dict) -> Dict:
        """修复单个异常"""
        strategy = self._match_strategy(exception)
        
        if not strategy:
            return {
                "status": "no_strategy",
                "message": f"未找到匹配的修复策略: {exception.get('type', '')}"
            }
        
        # 应用所有修复动作
        action_results = []
        for action in strategy["actions"]:
            result = self._apply_action(action, exception)
            action_results.append(result)
        
        heal_result = {
            "timestamp": datetime.now().isoformat(),
            "exception_fingerprint": exception.get("fingerprint", ""),
            "strategy": strategy["name"],
            "description": strategy["description"],
            "actions": action_results,
            "status": "healed" if any(a["status"] == "success" for a in action_results) else "info"
        }
        
        # 保存修复日志
        self._save_heal_log(heal_result)
        
        return heal_result
    
    def heal_all_exceptions(self, min_count: int = 2) -> List[Dict]:
        """修复所有高频异常"""
        kb = self._load_knowledge_base()
        
        # 获取高频异常模式
        high_freq = []
        for fingerprint, pattern in kb.get("patterns", {}).items():
            if pattern.get("count", 0) >= min_count:
                # 获取最新的一条异常记录
                latest = None
                for exc in kb.get("exceptions", []):
                    if exc.get("fingerprint") == fingerprint:
                        latest = exc
                        break
                
                if latest:
                    high_freq.append(latest)
        
        if not high_freq:
            print("[异常修复] 没有需要修复的高频异常")
            return []
        
        print(f"[异常修复] 发现 {len(high_freq)} 个高频异常，开始修复...")
        
        results = []
        for exception in high_freq:
            print(f"[异常修复] 修复: {exception.get('type', '')} - {exception.get('message', '')[:50]}...")
            result = self.heal_exception(exception)
            results.append(result)
            
            if result["status"] == "healed":
                print(f"  ✅ 修复成功")
            else:
                print(f"  ℹ️ {result.get('message', '已记录修复建议')}")
        
        return results
    
    def generate_heal_report(self, results: List[Dict]) -> str:
        """生成修复报告"""
        lines = ["\n### 🔧 异常修复报告\n"]
        
        if not results:
            lines.append("暂无需要修复的异常。\n")
            return "\n".join(lines)
        
        success_count = sum(1 for r in results if r["status"] == "healed")
        info_count = sum(1 for r in results if r["status"] == "info")
        
        lines.append(f"**修复统计**: ✅ {success_count} 成功 | ℹ️ {info_count} 建议")
        lines.append("")
        
        for result in results:
            emoji = "✅" if result["status"] == "healed" else "ℹ️"
            lines.append(f"{emoji} **{result['strategy']}**")
            lines.append(f"   描述: {result['description']}")
            
            for action in result.get("actions", []):
                action_emoji = "✅" if action["status"] == "success" else "⏭️"
                lines.append(f"   {action_emoji} {action['action']}: {action['detail']}")
            lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def run_exception_healing(trendradar_path: str = ".", min_count: int = 2) -> List[Dict]:
    """运行异常修复"""
    healer = ExceptionHealer(trendradar_path)
    return healer.heal_all_exceptions(min_count=min_count)


def get_heal_report(trendradar_path: str = ".") -> str:
    """获取修复报告"""
    healer = ExceptionHealer(trendradar_path)
    results = healer.heal_all_exceptions(min_count=2)
    return healer.generate_heal_report(results)


if __name__ == "__main__":
    results = run_exception_healing()
    healer = ExceptionHealer()
    print(healer.generate_heal_report(results))
