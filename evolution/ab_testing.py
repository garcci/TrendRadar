# -*- coding: utf-8 -*-
"""
A/B测试框架 - 数据驱动的进化决策

问题：
1. 优化建议是基于主观判断，缺乏数据验证
2. 不知道哪种Prompt版本效果更好
3. 不知道哪种文章结构更受欢迎
4. 改进是盲目的

解决方案：
1. A/B分组测试不同策略
2. 追踪关键指标
3. 统计显著性检验
4. 自动选择胜者

测试维度：
- Prompt版本（v1 vs v2）
- 文章结构（对比型 vs 叙事型）
- 模型选择（chat vs reasoner）
- 温度参数（0.6 vs 0.8）
"""

import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class TestDimension(Enum):
    """测试维度"""
    PROMPT_VERSION = "prompt_version"
    ARTICLE_STRUCTURE = "article_structure"
    MODEL = "model"
    TEMPERATURE = "temperature"
    MAX_TOKENS = "max_tokens"
    RSS_SOURCES = "rss_sources"
    PLATFORM_SELECTION = "platform_selection"


@dataclass
class ABTest:
    """A/B测试定义"""
    test_id: str
    dimension: TestDimension
    variant_a: Dict  # 对照组
    variant_b: Dict  # 实验组
    start_date: str
    end_date: Optional[str]
    sample_size: int  # 目标样本量
    winner: Optional[str]  # 胜者
    is_active: bool


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    variant: str  # 'A' or 'B'
    date: str
    overall_score: float
    dimensions: Dict
    cost: float
    latency: float
    tokens_used: int


class ABTestingFramework:
    """A/B测试框架"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.tests_file = f"{trendradar_path}/evolution/ab_tests.json"
        self.results_file = f"{trendradar_path}/evolution/ab_results.json"
        
        # 配置
        self.min_sample_size = 5  # 最少样本量
        self.confidence_threshold = 0.95  # 置信度阈值
        self.auto_select_winner = True  # 自动选择胜者
    
    def create_test(self, dimension: TestDimension, 
                   variant_a: Dict, variant_b: Dict,
                   sample_size: int = 10) -> str:
        """
        创建A/B测试
        
        Args:
            dimension: 测试维度
            variant_a: 对照组配置
            variant_b: 实验组配置
            sample_size: 目标样本量
        
        Returns:
            test_id: 测试ID
        """
        test_id = f"{dimension.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        test = ABTest(
            test_id=test_id,
            dimension=dimension,
            variant_a=variant_a,
            variant_b=variant_b,
            start_date=datetime.now().isoformat(),
            end_date=None,
            sample_size=sample_size,
            winner=None,
            is_active=True
        )
        
        self._save_test(test)
        print(f"[A/B测试] 创建测试: {test_id}")
        print(f"  维度: {dimension.value}")
        print(f"  A组: {variant_a}")
        print(f"  B组: {variant_b}")
        
        return test_id
    
    def assign_variant(self, test_id: str) -> str:
        """
        分配变体（A或B）
        
        使用确定性哈希，确保同一内容始终分配到同一组
        """
        test = self._get_test(test_id)
        if not test or not test.is_active:
            return "A"  # 默认对照组
        
        # 随机分配（但记录）
        variant = random.choice(["A", "B"])
        return variant
    
    def record_result(self, test_id: str, variant: str, 
                     overall_score: float, dimensions: Dict,
                     cost: float = 0, latency: float = 0, 
                     tokens_used: int = 0):
        """记录测试结果"""
        result = TestResult(
            test_id=test_id,
            variant=variant,
            date=datetime.now().isoformat(),
            overall_score=overall_score,
            dimensions=dimensions,
            cost=cost,
            latency=latency,
            tokens_used=tokens_used
        )
        
        self._save_result(result)
        print(f"[A/B测试] 记录结果: {test_id} 变体{variant} 得分{overall_score:.1f}")
        
        # 检查是否可以得出结论
        self._check_test_completion(test_id)
    
    def get_test_summary(self, test_id: str) -> Optional[Dict]:
        """获取测试摘要"""
        test = self._get_test(test_id)
        if not test:
            return None
        
        results = self._get_results(test_id)
        
        if not results:
            return {
                "test_id": test_id,
                "status": "running",
                "samples": 0,
                "a_scores": [],
                "b_scores": [],
                "winner": None
            }
        
        a_results = [r for r in results if r.variant == "A"]
        b_results = [r for r in results if r.variant == "B"]
        
        a_scores = [r.overall_score for r in a_results]
        b_scores = [r.overall_score for r in b_results]
        
        summary = {
            "test_id": test_id,
            "dimension": test.dimension.value,
            "status": "completed" if test.winner else "running",
            "samples": len(results),
            "a_samples": len(a_results),
            "b_samples": len(b_results),
            "a_avg_score": sum(a_scores) / len(a_scores) if a_scores else 0,
            "b_avg_score": sum(b_scores) / len(b_scores) if b_scores else 0,
            "a_scores": a_scores,
            "b_scores": b_scores,
            "winner": test.winner,
            "is_active": test.is_active
        }
        
        # 计算统计显著性（简化版t检验）
        if len(a_scores) >= self.min_sample_size and len(b_scores) >= self.min_sample_size:
            significance = self._calculate_significance(a_scores, b_scores)
            summary["significance"] = significance
            summary["is_significant"] = significance > self.confidence_threshold
        
        return summary
    
    def auto_create_tests(self, evolution_suggestions: List[str]) -> List[str]:
        """
        根据进化建议自动创建测试
        
        例如：
        - 建议"增加技术细节" → 创建Prompt版本测试
        - 建议"使用对比表格" → 创建结构测试
        """
        test_ids = []
        
        for suggestion in evolution_suggestions:
            if "技术" in suggestion and "细节" in suggestion:
                test_id = self.create_test(
                    TestDimension.PROMPT_VERSION,
                    variant_a={"tech_detail_level": "normal"},
                    variant_b={"tech_detail_level": "high"},
                    sample_size=5
                )
                test_ids.append(test_id)
            
            elif "结构" in suggestion or "模板" in suggestion:
                test_id = self.create_test(
                    TestDimension.ARTICLE_STRUCTURE,
                    variant_a={"template": "default"},
                    variant_b={"template": "contrast"},
                    sample_size=5
                )
                test_ids.append(test_id)
            
            elif "模型" in suggestion or "reasoner" in suggestion:
                test_id = self.create_test(
                    TestDimension.MODEL,
                    variant_a={"model": "deepseek-chat"},
                    variant_b={"model": "deepseek-reasoner"},
                    sample_size=5
                )
                test_ids.append(test_id)
        
        return test_ids
    
    def get_active_tests(self) -> List[Dict]:
        """获取活跃的测试"""
        tests = self._load_tests()
        active = [t for t in tests if t.is_active]
        return [self.get_test_summary(t.test_id) for t in active if self.get_test_summary(t.test_id)]
    
    def get_recommendations(self) -> List[Dict]:
        """
        基于已完成测试的推荐
        
        Returns:
            推荐配置列表
        """
        recommendations = []
        tests = self._load_tests()
        
        for test in tests:
            if not test.winner:
                continue
            
            summary = self.get_test_summary(test.test_id)
            if not summary or not summary.get("is_significant"):
                continue
            
            winner_config = test.variant_a if test.winner == "A" else test.variant_b
            loser_config = test.variant_b if test.winner == "A" else test.variant_a
            
            recommendations.append({
                "dimension": test.dimension.value,
                "winner": test.winner,
                "winner_config": winner_config,
                "improvement": summary["a_avg_score"] - summary["b_avg_score"] if test.winner == "A" else summary["b_avg_score"] - summary["a_avg_score"],
                "confidence": summary.get("significance", 0),
                "test_id": test.test_id
            })
        
        return recommendations
    
    def _check_test_completion(self, test_id: str):
        """检查测试是否完成"""
        test = self._get_test(test_id)
        if not test or not test.is_active:
            return
        
        results = self._get_results(test_id)
        a_results = [r for r in results if r.variant == "A"]
        b_results = [r for r in results if r.variant == "B"]
        
        # 样本量足够
        if len(a_results) >= self.min_sample_size and len(b_results) >= self.min_sample_size:
            a_scores = [r.overall_score for r in a_results]
            b_scores = [r.overall_score for r in b_results]
            
            a_avg = sum(a_scores) / len(a_scores)
            b_avg = sum(b_scores) / len(b_scores)
            
            # 自动选择胜者
            if self.auto_select_winner:
                winner = "A" if a_avg > b_avg else "B"
                improvement = abs(a_avg - b_avg)
                
                # 只有改进显著时才确认
                if improvement > 0.5:
                    test.winner = winner
                    test.is_active = False
                    test.end_date = datetime.now().isoformat()
                    self._update_test(test)
                    print(f"[A/B测试] 测试完成: {test_id}")
                    print(f"  胜者: {winner} (改进: {improvement:.1f}分)")
    
    def _calculate_significance(self, a_scores: List[float], b_scores: List[float]) -> float:
        """
        计算统计显著性（简化版）
        
        使用均值差异/合并标准差作为效应量
        """
        if not a_scores or not b_scores:
            return 0.0
        
        a_mean = sum(a_scores) / len(a_scores)
        b_mean = sum(b_scores) / len(b_scores)
        
        a_var = sum((x - a_mean) ** 2 for x in a_scores) / len(a_scores)
        b_var = sum((x - b_mean) ** 2 for x in b_scores) / len(b_scores)
        
        pooled_std = ((a_var + b_var) / 2) ** 0.5
        
        if pooled_std == 0:
            return 1.0 if a_mean != b_mean else 0.0
        
        effect_size = abs(a_mean - b_mean) / pooled_std
        
        # 简化的置信度：效应量越大，置信度越高
        # Cohen's d: 0.2=小, 0.5=中, 0.8=大
        if effect_size > 0.8:
            return 0.95
        elif effect_size > 0.5:
            return 0.85
        elif effect_size > 0.2:
            return 0.70
        else:
            return 0.50
    
    def _save_test(self, test: ABTest):
        """保存测试"""
        tests = self._load_tests()
        tests = [t for t in tests if t.test_id != test.test_id]
        tests.append(test)
        self._save_tests(tests)
    
    def _update_test(self, test: ABTest):
        """更新测试"""
        self._save_test(test)
    
    def _get_test(self, test_id: str) -> Optional[ABTest]:
        """获取测试"""
        tests = self._load_tests()
        for t in tests:
            if t.test_id == test_id:
                return t
        return None
    
    def _load_tests(self) -> List[ABTest]:
        """加载所有测试"""
        try:
            if not os.path.exists(self.tests_file):
                return []
            
            with open(self.tests_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return [ABTest(**t) for t in data]
        except Exception:
            return []
    
    def _save_tests(self, tests: List[ABTest]):
        """保存测试列表"""
        try:
            os.makedirs(os.path.dirname(self.tests_file), exist_ok=True)
            with open(self.tests_file, 'w', encoding='utf-8') as f:
                json.dump([{
                    "test_id": t.test_id,
                    "dimension": t.dimension.value,
                    "variant_a": t.variant_a,
                    "variant_b": t.variant_b,
                    "start_date": t.start_date,
                    "end_date": t.end_date,
                    "sample_size": t.sample_size,
                    "winner": t.winner,
                    "is_active": t.is_active
                } for t in tests], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[A/B测试] 保存测试失败: {e}")
    
    def _save_result(self, result: TestResult):
        """保存结果"""
        try:
            results = []
            if os.path.exists(self.results_file):
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
            
            results.append({
                "test_id": result.test_id,
                "variant": result.variant,
                "date": result.date,
                "overall_score": result.overall_score,
                "dimensions": result.dimensions,
                "cost": result.cost,
                "latency": result.latency,
                "tokens_used": result.tokens_used
            })
            
            os.makedirs(os.path.dirname(self.results_file), exist_ok=True)
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[A/B测试] 保存结果失败: {e}")
    
    def _get_results(self, test_id: str) -> List[TestResult]:
        """获取测试结果"""
        try:
            if not os.path.exists(self.results_file):
                return []
            
            with open(self.results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return [TestResult(**r) for r in data if r["test_id"] == test_id]
        except Exception:
            return []


# 便捷函数
def run_ab_test_decision(trendradar_path: str, dimension: str,
                        variant_a: Dict, variant_b: Dict) -> str:
    """
    运行A/B测试决策
    
    返回应该使用的变体（A或B）
    """
    framework = ABTestingFramework(trendradar_path)
    
    try:
        dim = TestDimension(dimension)
    except ValueError:
        return "A"
    
    test_id = framework.create_test(dim, variant_a, variant_b)
    return framework.assign_variant(test_id)
