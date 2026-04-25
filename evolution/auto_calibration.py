# -*- coding: utf-8 -*-
"""
Lv47: 自动校准系统

核心理念：系统不仅生成内容，还要自己检查质量，自动调整参数优化输出。

校准维度：
1. Temperature: 输出太随机→降低，太死板→提高
2. Max Tokens: 内容截断→增加，浪费→减少
3. Prompt: 根据质量反馈自动优化权重
4. Provider: 根据成功率和质量自动切换

校准策略：
- 每次AI调用后，记录输出质量指标
- 定期分析历史数据，找出最优参数组合
- 自动应用最优参数，无需人工干预
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class AutoCalibration:
    """自动校准系统 - 根据输出质量调整参数"""
    
    # 参数推荐范围
    PARAM_RANGES = {
        "temperature": {"min": 0.1, "max": 1.0, "default": 0.7},
        "max_tokens": {"min": 500, "max": 8000, "default": 4000},
        "top_p": {"min": 0.1, "max": 1.0, "default": 0.9}
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.calibration_file = f"{trendradar_path}/evolution/auto_calibration.json"
        self.quality_file = f"{trendradar_path}/evolution/output_quality_log.json"
        self.load_data()
    
    def load_data(self):
        """加载校准数据"""
        self.calibration = {}
        if os.path.exists(self.calibration_file):
            try:
                with open(self.calibration_file, 'r') as f:
                    self.calibration = json.load(f)
            except Exception:
                pass
        
        self.quality_records = []
        if os.path.exists(self.quality_file):
            try:
                with open(self.quality_file, 'r') as f:
                    self.quality_records = json.load(f)
            except Exception:
                pass
    
    def save_calibration(self):
        """保存校准数据"""
        try:
            os.makedirs(os.path.dirname(self.calibration_file), exist_ok=True)
            with open(self.calibration_file, 'w') as f:
                json.dump(self.calibration, f, indent=2)
        except Exception:
            pass
    
    def record_quality(self, task_type: str, provider: str,
                      parameters: Dict, quality_metrics: Dict):
        """
        记录输出质量
        
        quality_metrics: {
            "completeness": 0-1,  # 内容完整性
            "coherence": 0-1,     # 连贯性
            "relevance": 0-1,     # 相关性
            "length_ok": bool,    # 长度是否合适
            "has_errors": bool    # 是否有明显错误
        }
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "provider": provider,
            "parameters": parameters,
            "quality": quality_metrics,
            "overall_score": self._calc_overall_score(quality_metrics)
        }
        
        self.quality_records.append(record)
        
        # 只保留最近100条
        if len(self.quality_records) > 100:
            self.quality_records = self.quality_records[-100:]
        
        try:
            os.makedirs(os.path.dirname(self.quality_file), exist_ok=True)
            with open(self.quality_file, 'w') as f:
                json.dump(self.quality_records, f, indent=2)
        except Exception:
            pass
        
        # 触发校准分析
        self._analyze_and_calibrate(task_type)
    
    def _calc_overall_score(self, metrics: Dict) -> float:
        """计算综合质量分"""
        score = 0.0
        weights = {
            "completeness": 0.3,
            "coherence": 0.25,
            "relevance": 0.25,
            "length_ok": 0.1,
            "has_errors": 0.1
        }
        
        for key, weight in weights.items():
            if key in metrics:
                if key == "has_errors":
                    score += (0.0 if metrics[key] else 1.0) * weight
                else:
                    score += metrics[key] * weight
        
        return min(1.0, max(0.0, score))
    
    def _analyze_and_calibrate(self, task_type: str):
        """分析历史数据并校准参数"""
        # 筛选该任务类型的记录
        task_records = [r for r in self.quality_records 
                       if r.get("task_type") == task_type]
        
        if len(task_records) < 5:
            return  # 数据不足，暂不校准
        
        # 分析不同参数的效果
        param_effectiveness = {}
        
        for record in task_records:
            params = record.get("parameters", {})
            score = record.get("overall_score", 0.5)
            
            for param_name, param_value in params.items():
                if param_name not in param_effectiveness:
                    param_effectiveness[param_name] = []
                param_effectiveness[param_name].append({
                    "value": param_value,
                    "score": score
                })
        
        # 找出每个参数的最优值
        recommendations = {}
        
        for param_name, values in param_effectiveness.items():
            if len(values) < 3:
                continue
            
            # 按参数值分组计算平均分
            value_groups = {}
            for v in values:
                val = v["value"]
                # 数值参数分桶
                if isinstance(val, (int, float)):
                    bucket = round(val * 2) / 2  # 0.5为间隔
                else:
                    bucket = str(val)
                
                if bucket not in value_groups:
                    value_groups[bucket] = []
                value_groups[bucket].append(v["score"])
            
            # 找出平均分最高的桶
            best_bucket = None
            best_score = 0
            for bucket, scores in value_groups.items():
                avg_score = sum(scores) / len(scores)
                if avg_score > best_score:
                    best_score = avg_score
                    best_bucket = bucket
            
            if best_bucket is not None:
                recommendations[param_name] = {
                    "recommended_value": best_bucket,
                    "expected_score": best_score,
                    "confidence": min(1.0, len(values) / 20)  # 数据越多越可信
                }
        
        # 保存校准结果
        if task_type not in self.calibration:
            self.calibration[task_type] = {}
        
        self.calibration[task_type] = {
            "recommendations": recommendations,
            "last_calibrated": datetime.now().isoformat(),
            "sample_size": len(task_records)
        }
        
        self.save_calibration()
    
    def get_optimal_params(self, task_type: str, 
                          base_params: Optional[Dict] = None) -> Dict:
        """
        获取任务的最优参数
        返回推荐参数字典，可与基础参数合并使用
        """
        params = base_params or {}
        
        calibration = self.calibration.get(task_type, {})
        recommendations = calibration.get("recommendations", {})
        
        for param_name, rec in recommendations.items():
            if rec.get("confidence", 0) > 0.3:  # 置信度足够才应用
                recommended = rec["recommended_value"]
                current = params.get(param_name)
                
                if current != recommended:
                    print(f"[自动校准] {task_type}.{param_name}: "
                          f"{current} → {recommended} "
                          f"(置信度: {rec['confidence']*100:.0f}%)")
                    params[param_name] = recommended
        
        return params
    
    def auto_calibrate_from_issues(self, owner: str, repo: str, token: str):
        """
        从最近生成的Issues自动提取质量数据并校准
        这是自动校准的核心入口！
        """
        print("[自动校准] 分析最近输出质量...")
        
        try:
            import requests
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            headers = {"Authorization": f"token {token}"}
            
            since = (datetime.now() - timedelta(days=3)).isoformat()
            response = requests.get(url, headers=headers,
                                  params={"labels": "memory,article-history",
                                         "since": since, "state": "all",
                                         "per_page": 5},
                                  timeout=10)
            
            if response.status_code != 200:
                return
            
            from evolution.output_quality_validator import check_issue_quality
            
            for issue in response.json():
                body = issue.get("body", "")
                quality = check_issue_quality(body)
                
                # 转换为质量指标
                metrics = {
                    "completeness": 1.0 if not quality.get("issues") else 0.7,
                    "coherence": 1.0,
                    "relevance": 1.0,
                    "length_ok": True,
                    "has_errors": not quality.get("valid", True)
                }
                
                # 记录质量
                self.record_quality(
                    task_type="article_generation",
                    provider="github_models",
                    parameters={"temperature": 0.7, "max_tokens": 4000},
                    quality_metrics=metrics
                )
            
            print(f"[自动校准] 已分析 {len(response.json())} 个Issue，参数已更新")
            
        except Exception as e:
            print(f"[自动校准] 分析失败: {e}")
    
    def generate_calibration_report(self) -> str:
        """生成校准报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("🔧 自动校准报告")
        lines.append("=" * 60)
        
        for task_type, cal in self.calibration.items():
            lines.append(f"\n📋 任务类型: {task_type}")
            lines.append(f"  样本数: {cal.get('sample_size', 0)}")
            lines.append(f"  上次校准: {cal.get('last_calibrated', 'N/A')[:10]}")
            
            recs = cal.get("recommendations", {})
            if recs:
                lines.append("  推荐参数:")
                for param, info in recs.items():
                    conf = info.get("confidence", 0) * 100
                    lines.append(f"    {param}: {info['recommended_value']} "
                               f"(置信度: {conf:.0f}%)")
            else:
                lines.append("  暂无足够数据生成推荐")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


# 便捷函数
def calibrate_and_report() -> str:
    """执行校准并返回报告"""
    calibrator = AutoCalibration()
    return calibrator.generate_calibration_report()


def auto_calibrate(owner: str = None, repo: str = None, token: str = None):
    """自动校准入口"""
    calibrator = AutoCalibration()
    
    if owner and repo and token:
        calibrator.auto_calibrate_from_issues(owner, repo, token)
    
    print(calibrator.generate_calibration_report())


if __name__ == "__main__":
    print(calibrate_and_report())
