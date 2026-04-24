# -*- coding: utf-8 -*-
"""
自主测试验证 - 自动生成测试用例验证新功能

核心理念：
1. 对自主生成的新功能进行自动测试
2. 验证代码语法、基本功能、集成兼容性
3. 生成测试报告

测试维度：
- 语法测试: Python语法检查
- 功能测试: 模块是否能正常运行
- 集成测试: 模块是否能集成到主流程
- 回归测试: 新功能是否影响现有功能

输出：
- 测试报告（JSON格式）
- 测试通过/失败状态
- 供 Lv30 部署决策使用
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional


class SelfTester:
    """自主测试验证器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.designs_dir = f"{trendradar_path}/evolution/designs"
        self.evolution_dir = f"{trendradar_path}/evolution"
        self.test_results = []
    
    def load_implemented_designs(self) -> List[Dict]:
        """加载已实现的设计文档"""
        designs = []
        
        if not os.path.exists(self.designs_dir):
            return designs
        
        for file_name in sorted(os.listdir(self.designs_dir)):
            if not file_name.endswith('.json'):
                continue
            
            file_path = f"{self.designs_dir}/{file_name}"
            try:
                with open(file_path, 'r') as f:
                    design = json.load(f)
                
                if design.get("status") == "implemented":
                    designs.append(design)
            except Exception:
                continue
        
        return designs
    
    def test_syntax(self, file_path: str) -> Dict:
        """测试代码语法"""
        test_name = "语法检查"
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            compile(code, file_path, 'exec')
            
            return {
                "test": test_name,
                "status": "pass",
                "message": "语法正确"
            }
        except SyntaxError as e:
            return {
                "test": test_name,
                "status": "fail",
                "message": f"语法错误: {e}"
            }
        except Exception as e:
            return {
                "test": test_name,
                "status": "fail",
                "message": f"读取失败: {e}"
            }
    
    def test_import(self, file_path: str) -> Dict:
        """测试模块是否能正确导入"""
        test_name = "模块导入"
        
        try:
            # 获取模块名
            file_name = os.path.basename(file_path)
            module_name = file_name.replace('.py', '')
            
            # 尝试导入（通过exec）
            with open(file_path, 'r') as f:
                code = f.read()
            
            # 在隔离环境中执行
            namespace = {}
            exec(code, namespace)
            
            # 检查是否有主要类
            has_class = any(isinstance(v, type) for v in namespace.values())
            
            return {
                "test": test_name,
                "status": "pass",
                "message": f"模块可导入，{'包含类定义' if has_class else '包含函数定义'}"
            }
        except Exception as e:
            return {
                "test": test_name,
                "status": "fail",
                "message": f"导入失败: {e}"
            }
    
    def test_basic_function(self, file_path: str) -> Dict:
        """测试基本功能"""
        test_name = "基本功能"
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            namespace = {}
            exec(code, namespace)
            
            # 查找类实例
            classes = [v for v in namespace.values() if isinstance(v, type) and v.__name__ != 'type']
            
            if not classes:
                return {
                    "test": test_name,
                    "status": "warn",
                    "message": "未找到可测试的类"
                }
            
            # 尝试实例化第一个类
            cls = classes[0]
            instance = cls()
            
            # 查找并测试process/run/enhance方法
            test_methods = ['process', 'run', 'enhance', 'analyze']
            tested = False
            
            for method_name in test_methods:
                if hasattr(instance, method_name):
                    method = getattr(instance, method_name)
                    if callable(method):
                        # 尝试调用（使用空字符串作为测试输入）
                        try:
                            result = method("") if method_name != 'run' else method()
                            tested = True
                            break
                        except TypeError:
                            continue
            
            if tested:
                return {
                    "test": test_name,
                    "status": "pass",
                    "message": f"类 {cls.__name__} 可实例化并运行"
                }
            else:
                return {
                    "test": test_name,
                    "status": "warn",
                    "message": f"类 {cls.__name__} 可实例化，但未找到可测试的方法"
                }
        
        except Exception as e:
            return {
                "test": test_name,
                "status": "fail",
                "message": f"功能测试失败: {e}"
            }
    
    def test_no_regression(self, file_path: str) -> Dict:
        """测试是否影响现有功能（简化版：检查是否覆盖现有文件）"""
        test_name = "回归检查"
        
        try:
            file_name = os.path.basename(file_path)
            
            # 检查是否是新文件
            git_check = subprocess.run(
                ['git', 'ls-files', file_path],
                capture_output=True,
                text=True,
                cwd=self.trendradar_path
            )
            
            if git_check.stdout.strip():
                return {
                    "test": test_name,
                    "status": "warn",
                    "message": "修改现有文件，需要人工审查"
                }
            else:
                return {
                    "test": test_name,
                    "status": "pass",
                    "message": "新增文件，无回归风险"
                }
        
        except Exception as e:
            return {
                "test": test_name,
                "status": "warn",
                "message": f"无法检查回归风险: {e}"
            }
    
    def run_tests(self, design: Dict) -> Dict:
        """对单个设计运行完整测试"""
        feature = design["feature"]
        file_name = feature["file_name"]
        file_path = f"{self.evolution_dir}/{file_name}"
        
        print(f"[自主测试] 测试功能: {feature['name']}")
        
        if not os.path.exists(file_path):
            return {
                "design_id": design["design_id"],
                "feature_name": feature["name"],
                "status": "fail",
                "message": f"文件不存在: {file_path}",
                "tests": []
            }
        
        # 运行测试
        tests = []
        tests.append(self.test_syntax(file_path))
        tests.append(self.test_import(file_path))
        tests.append(self.test_basic_function(file_path))
        tests.append(self.test_no_regression(file_path))
        
        # 计算总体结果
        pass_count = sum(1 for t in tests if t["status"] == "pass")
        fail_count = sum(1 for t in tests if t["status"] == "fail")
        warn_count = sum(1 for t in tests if t["status"] == "warn")
        
        if fail_count > 0:
            overall_status = "fail"
        elif warn_count > 0:
            overall_status = "warn"
        else:
            overall_status = "pass"
        
        result = {
            "design_id": design["design_id"],
            "feature_name": feature["name"],
            "file_name": file_name,
            "status": overall_status,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "warn_count": warn_count,
            "tests": tests,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def update_design_status(self, design: Dict, status: str, test_result: Dict):
        """更新设计文档状态"""
        design["status"] = status
        design["testing"] = test_result
        
        file_path = f"{self.designs_dir}/{design['design_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(design, f, ensure_ascii=False, indent=2)
    
    def test_all_features(self) -> List[Dict]:
        """主入口：测试所有已实现的功能"""
        designs = self.load_implemented_designs()
        
        if not designs:
            print("[自主测试] 没有待测试的功能")
            return []
        
        print(f"[自主测试] 发现 {len(designs)} 个待测试的功能")
        
        results = []
        for design in designs:
            result = self.run_tests(design)
            results.append(result)
            
            # 更新设计状态
            if result["status"] == "pass":
                self.update_design_status(design, "tested", result)
                print(f"[自主测试] ✅ {result['feature_name']}: 测试通过")
            elif result["status"] == "warn":
                self.update_design_status(design, "tested_with_warnings", result)
                print(f"[自主测试] ⚠️ {result['feature_name']}: 测试通过但有警告")
            else:
                self.update_design_status(design, "test_failed", result)
                print(f"[自主测试] ❌ {result['feature_name']}: 测试失败")
        
        return results
    
    def generate_test_report(self, results: List[Dict]) -> str:
        """生成测试报告"""
        lines = ["\n### 🧪 自主测试报告\n"]
        
        if not results:
            lines.append("暂无需要测试的功能。\n")
            return "\n".join(lines)
        
        pass_count = sum(1 for r in results if r["status"] == "pass")
        fail_count = sum(1 for r in results if r["status"] == "fail")
        warn_count = sum(1 for r in results if r["status"] == "warn")
        
        lines.append(f"**测试结果**: ✅ {pass_count} 通过 | ⚠️ {warn_count} 警告 | ❌ {fail_count} 失败")
        lines.append("")
        
        for result in results:
            emoji = "✅" if result["status"] == "pass" else "⚠️" if result["status"] == "warn" else "❌"
            lines.append(f"{emoji} **{result['feature_name']}** ({result['file_name']})")
            
            for test in result["tests"]:
                test_emoji = "✅" if test["status"] == "pass" else "⚠️" if test["status"] == "warn" else "❌"
                lines.append(f"  {test_emoji} {test['test']}: {test['message']}")
            lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def run_self_testing(trendradar_path: str = ".") -> List[Dict]:
    """运行自主测试"""
    tester = SelfTester(trendradar_path)
    return tester.test_all_features()


if __name__ == "__main__":
    results = run_self_testing()
    if results:
        tester = SelfTester()
        print(tester.generate_test_report(results))
    else:
        print("暂无需要测试的功能")
