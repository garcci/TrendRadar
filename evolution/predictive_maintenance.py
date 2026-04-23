# -*- coding: utf-8 -*-
"""
预测性维护系统 - 提前发现问题，防患于未然

核心理念：
1. 基于历史数据预测未来趋势
2. 在问题发生前自动修复
3. 自适应阈值调整
4. 异常行为检测

预测模型：
- RSS源衰减预测：基于成功率趋势预测何时失效
- AI质量趋势预测：基于评分趋势预测质量下降
- 成本激增预测：基于使用量趋势预测额度耗尽时间
- 系统负载预测：基于运行时间预测性能瓶颈
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class PredictiveModel:
    """基础预测模型"""
    
    @staticmethod
    def linear_trend(values: List[float]) -> Tuple[float, float]:
        """
        简单线性趋势预测
        
        返回: (斜率, 预测下一个值)
        """
        if len(values) < 2:
            return 0.0, values[-1] if values else 0.0
        
        n = len(values)
        x = list(range(n))
        
        # 计算斜率
        avg_x = sum(x) / n
        avg_y = sum(values) / n
        
        numerator = sum((x[i] - avg_x) * (values[i] - avg_y) for i in range(n))
        denominator = sum((x[i] - avg_x) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        next_value = values[-1] + slope
        
        return slope, next_value
    
    @staticmethod
    def predict_time_to_threshold(values: List[float], threshold: float) -> Optional[int]:
        """
        预测达到阈值还需要多少步
        
        返回: 预测步数，None表示不会达到
        """
        if len(values) < 2:
            return None
        
        slope, next_val = PredictiveModel.linear_trend(values)
        current = values[-1]
        
        # 如果趋势不朝向阈值，返回None
        if slope == 0:
            return None
        if threshold > current and slope <= 0:
            return None
        if threshold < current and slope >= 0:
            return None
        
        # 计算达到阈值需要的步数
        steps = (threshold - current) / slope
        
        if steps > 0:
            return int(steps)
        return None


class PredictiveMaintenance:
    """预测性维护引擎"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.model = PredictiveModel()
        self.predictions = []
        self.actions = []
    
    def run_predictive_analysis(self) -> Dict:
        """运行预测性分析"""
        print("🔮 启动预测性维护分析...")
        
        # 1. 预测RSS源失效
        self._predict_rss_failure()
        
        # 2. 预测AI质量下降
        self._predict_quality_degradation()
        
        # 3. 预测成本激增
        self._predict_cost_spike()
        
        # 4. 预测系统瓶颈
        self._predict_system_bottleneck()
        
        # 5. 执行预防性维护
        self._execute_preventive_actions()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "predictions": self.predictions,
            "actions_taken": self.actions,
            "risk_level": self._calculate_risk_level()
        }
    
    def _predict_rss_failure(self):
        """预测RSS源即将失效"""
        rss_file = f"{self.trendradar_path}/evolution/rss_health.json"
        if not os.path.exists(rss_file):
            return
        
        with open(rss_file, 'r') as f:
            records = json.load(f)
        
        # 按源分组，按时间排序
        source_history = {}
        for r in records:
            sid = r.get("source_id", "unknown")
            if sid not in source_history:
                source_history[sid] = []
            source_history[sid].append(1 if r.get("success") else 0)
        
        for sid, history in source_history.items():
            if len(history) < 5:
                continue
            
            # 使用最近10次记录
            recent = history[-10:]
            
            # 计算成功率趋势
            window_size = 3
            success_rates = []
            for i in range(len(recent) - window_size + 1):
                window = recent[i:i+window_size]
                rate = sum(window) / len(window)
                success_rates.append(rate)
            
            if len(success_rates) < 2:
                continue
            
            slope, predicted_rate = self.model.linear_trend(success_rates)
            
            # 预测何时失效（成功率<0.3）
            steps_to_failure = self.model.predict_time_to_threshold(success_rates, 0.3)
            
            if steps_to_failure and steps_to_failure <= 3:
                self.predictions.append({
                    "type": "rss_failure",
                    "component": sid,
                    "severity": "high" if steps_to_failure <= 1 else "medium",
                    "current_rate": success_rates[-1],
                    "predicted_rate": predicted_rate,
                    "steps_to_failure": steps_to_failure,
                    "message": f"RSS源 {sid} 预计 {steps_to_failure} 次运行后失效（当前成功率: {success_rates[-1]:.0%}）",
                    "action": "提前禁用并寻找替代源"
                })
                
                # 如果即将失效，提前禁用
                if steps_to_failure <= 1:
                    self.actions.append({
                        "type": "disable_rss",
                        "target": sid,
                        "reason": f"预测即将失效（成功率趋势下降）"
                    })
    
    def _predict_quality_degradation(self):
        """预测AI质量下降"""
        metrics_file = f"{self.trendradar_path}/evolution/article_metrics.json"
        if not os.path.exists(metrics_file):
            return
        
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)
        
        if len(metrics) < 5:
            return
        
        # 提取评分序列
        scores = [m.get("overall_score", 0) for m in metrics]
        tech_ratios = [m.get("tech_content_ratio", 0) for m in metrics]
        
        # 预测评分趋势
        score_slope, predicted_score = self.model.linear_trend(scores)
        tech_slope, predicted_tech = self.model.linear_trend(tech_ratios)
        
        # 预测何时低于阈值
        score_steps = self.model.predict_time_to_threshold(scores, 6.0)
        tech_steps = self.model.predict_time_to_threshold(tech_ratios, 5.0)
        
        if score_steps and score_steps <= 3:
            self.predictions.append({
                "type": "quality_degradation",
                "component": "article_generator",
                "severity": "high" if score_steps <= 1 else "medium",
                "current_score": scores[-1],
                "predicted_score": predicted_score,
                "steps_to_threshold": score_steps,
                "message": f"文章评分预计 {score_steps} 次后降至6.0以下（当前: {scores[-1]:.1f}）",
                "action": "启用高质量模式或优化Prompt"
            })
            
            if score_steps <= 1:
                self.actions.append({
                    "type": "enable_high_quality",
                    "target": "article_generator",
                    "reason": "预测质量即将下降"
                })
        
        if tech_steps and tech_steps <= 3:
            self.predictions.append({
                "type": "tech_content_degradation",
                "component": "article_generator",
                "severity": "medium",
                "current_ratio": tech_ratios[-1],
                "predicted_ratio": predicted_tech,
                "steps_to_threshold": tech_steps,
                "message": f"科技内容占比预计 {tech_steps} 次后降至50%以下（当前: {tech_ratios[-1]:.1f}）",
                "action": "强化科技内容Prompt要求"
            })
    
    def _predict_cost_spike(self):
        """预测成本激增"""
        usage_file = f"{self.trendradar_path}/evolution/ai_provider_usage.json"
        if not os.path.exists(usage_file):
            return
        
        with open(usage_file, 'r') as f:
            usage = json.load(f)
        
        # 按天统计成本
        daily_costs = {}
        for u in usage:
            date = u.get("timestamp", "")[:10]
            cost = u.get("cost", 0)
            daily_costs[date] = daily_costs.get(date, 0) + cost
        
        if len(daily_costs) < 3:
            return
        
        dates = sorted(daily_costs.keys())
        costs = [daily_costs[d] for d in dates]
        
        slope, predicted_cost = self.model.linear_trend(costs)
        
        # 预测何时超过预算（假设预算0.05/天）
        budget = 0.05
        steps_to_budget = self.model.predict_time_to_threshold(costs, budget)
        
        if steps_to_budget and steps_to_budget <= 3:
            self.predictions.append({
                "type": "cost_spike",
                "component": "ai_router",
                "severity": "medium",
                "current_cost": costs[-1],
                "predicted_cost": predicted_cost,
                "steps_to_budget": steps_to_budget,
                "message": f"AI成本预计 {steps_to_budget} 天后超过预算 ¥{budget}（当前: ¥{costs[-1]:.3f}）",
                "action": "增加免费API使用比例"
            })
    
    def _predict_system_bottleneck(self):
        """预测系统瓶颈"""
        # 基于运行时间预测
        # 如果运行时间持续增加，可能预示性能问题
        metrics_file = f"{self.trendradar_path}/evolution/article_metrics.json"
        if not os.path.exists(metrics_file):
            return
        
        # 这里可以添加基于Workflow运行时间的预测
        # 暂时跳过，需要GitHub Actions API获取运行时间
        pass
    
    def _execute_preventive_actions(self):
        """执行预防性维护动作"""
        for action in self.actions:
            try:
                if action["type"] == "disable_rss":
                    self._disable_rss_source(action["target"])
                    print(f"   ✅ 预防性禁用RSS源: {action['target']}")
                    
                elif action["type"] == "enable_high_quality":
                    self._enable_high_quality_mode()
                    print(f"   ✅ 预防性启用高质量模式")
                    
            except Exception as e:
                print(f"   ❌ 预防性维护失败: {e}")
    
    def _disable_rss_source(self, source_id: str):
        """禁用RSS源"""
        config_path = f"{self.trendradar_path}/config/config.yaml"
        with open(config_path, 'r') as f:
            content = f.read()
        
        # 添加enabled: false
        pattern = f'- id: "{source_id}"\\n(\\s+)name:'
        replacement = f'- id: "{source_id}"\\n\\1enabled: false  # [PREDICTIVE] 预测即将失效\\n\\1name:'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(config_path, 'w') as f:
                f.write(new_content)
    
    def _enable_high_quality_mode(self):
        """启用高质量模式"""
        flag_file = f"{self.trendradar_path}/.predictive_high_quality"
        with open(flag_file, 'w') as f:
            f.write(f"# 预测性维护: 启用高质量模式\n# 时间: {datetime.now().isoformat()}\n")
    
    def _calculate_risk_level(self) -> str:
        """计算风险等级"""
        high_risk = len([p for p in self.predictions if p["severity"] == "high"])
        medium_risk = len([p for p in self.predictions if p["severity"] == "medium"])
        
        if high_risk > 0:
            return "high"
        elif medium_risk > 2:
            return "medium"
        elif medium_risk > 0:
            return "low"
        return "safe"


# 便捷函数
def run_predictive_maintenance(trendradar_path: str = ".") -> str:
    """运行预测性维护"""
    engine = PredictiveMaintenance(trendradar_path)
    result = engine.run_predictive_analysis()
    
    # 格式化输出
    report = []
    report.append("\n" + "=" * 70)
    report.append("🔮 预测性维护报告")
    report.append("=" * 70)
    report.append(f"\n📊 风险等级: {result['risk_level'].upper()}")
    report.append(f"🔮 预测数量: {len(result['predictions'])}")
    report.append(f"🔧 预防动作: {len(result['actions_taken'])}")
    
    if result['predictions']:
        report.append("\n⚠️ 预测到的问题:")
        for pred in result['predictions']:
            icon = "🔴" if pred['severity'] == 'high' else "🟡"
            report.append(f"   {icon} {pred['message']}")
            report.append(f"      建议: {pred['action']}")
    
    if result['actions_taken']:
        report.append("\n✅ 已执行的预防动作:")
        for action in result['actions_taken']:
            report.append(f"   • {action['target']}: {action['reason']}")
    
    report.append("=" * 70)
    
    return "\n".join(report)


if __name__ == "__main__":
    print(run_predictive_maintenance())
