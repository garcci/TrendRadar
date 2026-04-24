# -*- coding: utf-8 -*-
"""
自主部署决策 - 根据测试结果决定是否部署新功能

核心理念：
1. 读取测试报告，评估新功能质量
2. 根据质量阈值决定是否提交到版本控制
3. 自动提交通过的代码，回滚失败的代码
4. 生成部署决策报告

部署策略：
- 全部通过: 自动提交
- 有警告但无失败: 提交但标记为实验性功能
- 有失败: 回滚，不提交

输出：
- 部署决策报告
- Git提交记录（如果部署）
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional


class SelfDeployer:
    """自主部署决策器"""
    
    # 部署策略配置
    DEPLOY_POLICY = {
        "auto_deploy_threshold": {
            "pass": 1.0,    # 全部通过才自动部署
            "warn": 0.3,    # 警告比例不超过30%
            "fail": 0       # 不能有失败
        },
        "commit_message_template": """feat: 自主进化 - {feature_name}

自主进化系统自动生成的新功能：
- 功能: {feature_description}
- 目标: {issue}
- 状态: {test_status}

生成时间: {timestamp}
设计ID: {design_id}"""
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.designs_dir = f"{trendradar_path}/evolution/designs"
        self.evolution_dir = f"{trendradar_path}/evolution"
    
    def load_tested_designs(self) -> List[Dict]:
        """加载已测试的设计文档"""
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
                
                if design.get("status") in ["tested", "tested_with_warnings"]:
                    designs.append(design)
            except Exception:
                continue
        
        return designs
    
    def evaluate_deploy_decision(self, design: Dict) -> Dict:
        """评估是否部署"""
        test_result = design.get("testing", {})
        feature = design["feature"]
        
        status = test_result.get("status", "unknown")
        pass_count = test_result.get("pass_count", 0)
        fail_count = test_result.get("fail_count", 0)
        warn_count = test_result.get("warn_count", 0)
        total = pass_count + fail_count + warn_count
        
        # 决策逻辑
        if fail_count > 0:
            decision = "rollback"
            reason = f"有{fail_count}个测试失败"
        elif warn_count > 0 and total > 0 and warn_count / total > self.DEPLOY_POLICY["auto_deploy_threshold"]["warn"]:
            decision = "manual_review"
            reason = f"警告比例过高({warn_count}/{total})"
        elif status == "pass":
            decision = "deploy"
            reason = "所有测试通过"
        elif status == "warn":
            decision = "deploy_with_caution"
            reason = "测试通过但有警告"
        else:
            decision = "manual_review"
            reason = "无法确定测试状态"
        
        return {
            "design_id": design["design_id"],
            "feature_name": feature["name"],
            "file_name": feature["file_name"],
            "decision": decision,
            "reason": reason,
            "test_summary": {
                "pass": pass_count,
                "warn": warn_count,
                "fail": fail_count
            }
        }
    
    def deploy_feature(self, design: Dict, decision: Dict) -> bool:
        """部署功能（Git提交）"""
        feature = design["feature"]
        file_name = feature["file_name"]
        file_path = f"{self.evolution_dir}/{file_name}"
        
        if not os.path.exists(file_path):
            print(f"[自主部署] ❌ 文件不存在: {file_path}")
            return False
        
        try:
            # 生成提交信息
            commit_msg = self.DEPLOY_POLICY["commit_message_template"].format(
                feature_name=feature["name"],
                feature_description=feature["description"],
                issue=design["origin"]["issue"],
                test_status=decision["decision"],
                timestamp=datetime.now().isoformat(),
                design_id=design["design_id"]
            )
            
            # Git添加文件
            subprocess.run(
                ['git', 'add', file_path],
                cwd=self.trendradar_path,
                check=True,
                capture_output=True
            )
            
            # Git提交
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=self.trendradar_path,
                check=True,
                capture_output=True
            )
            
            print(f"[自主部署] ✅ 已提交: {feature['name']}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"[自主部署] ❌ Git操作失败: {e}")
            return False
        except Exception as e:
            print(f"[自主部署] ❌ 部署失败: {e}")
            return False
    
    def rollback_feature(self, design: Dict) -> bool:
        """回滚功能（删除生成的文件，恢复备份）"""
        feature = design["feature"]
        file_name = feature["file_name"]
        file_path = f"{self.evolution_dir}/{file_name}"
        
        try:
            # 删除生成的文件
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[自主部署] 🗑️ 已删除: {file_name}")
            
            # 查找并恢复备份
            backup_files = [
                f for f in os.listdir(self.evolution_dir)
                if f.startswith(file_name + '.bak.')
            ]
            
            if backup_files:
                # 恢复最新的备份
                latest_backup = sorted(backup_files)[-1]
                backup_path = f"{self.evolution_dir}/{latest_backup}"
                os.rename(backup_path, file_path)
                print(f"[自主部署] 🔄 已恢复备份: {latest_backup}")
            
            return True
            
        except Exception as e:
            print(f"[自主部署] ❌ 回滚失败: {e}")
            return False
    
    def update_design_status(self, design: Dict, status: str, deploy_info: Dict):
        """更新设计文档状态"""
        design["status"] = status
        design["deployment"] = deploy_info
        
        file_path = f"{self.designs_dir}/{design['design_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(design, f, ensure_ascii=False, indent=2)
    
    def make_deploy_decisions(self) -> List[Dict]:
        """主入口：对所有已测试功能做出部署决策"""
        designs = self.load_tested_designs()
        
        if not designs:
            print("[自主部署] 没有待部署的功能")
            return []
        
        print(f"[自主部署] 发现 {len(designs)} 个待部署的功能")
        
        decisions = []
        for design in designs:
            feature = design["feature"]
            
            # 评估部署决策
            decision = self.evaluate_deploy_decision(design)
            decisions.append(decision)
            
            print(f"[自主部署] {feature['name']}: {decision['decision']} - {decision['reason']}")
            
            # 执行决策
            deploy_info = {
                "timestamp": datetime.now().isoformat(),
                "decision": decision["decision"],
                "reason": decision["reason"]
            }
            
            if decision["decision"] in ["deploy", "deploy_with_caution"]:
                success = self.deploy_feature(design, decision)
                deploy_info["deployed"] = success
                self.update_design_status(design, "deployed" if success else "deploy_failed", deploy_info)
            
            elif decision["decision"] == "rollback":
                success = self.rollback_feature(design)
                deploy_info["rolled_back"] = success
                self.update_design_status(design, "rolled_back" if success else "rollback_failed", deploy_info)
            
            else:
                # manual_review
                self.update_design_status(design, "pending_review", deploy_info)
        
        return decisions
    
    def generate_deploy_report(self, decisions: List[Dict]) -> str:
        """生成部署决策报告"""
        lines = ["\n### 🚀 自主部署决策报告\n"]
        
        if not decisions:
            lines.append("暂无需要部署的功能。\n")
            return "\n".join(lines)
        
        deploy_count = sum(1 for d in decisions if d["decision"] in ["deploy", "deploy_with_caution"])
        rollback_count = sum(1 for d in decisions if d["decision"] == "rollback")
        review_count = sum(1 for d in decisions if d["decision"] == "manual_review")
        
        lines.append(f"**部署统计**: 🚀 {deploy_count} 部署 | 🔄 {rollback_count} 回滚 | 👀 {review_count} 待审查")
        lines.append("")
        
        for decision in decisions:
            emoji = {
                "deploy": "🚀",
                "deploy_with_caution": "⚠️",
                "rollback": "🔄",
                "manual_review": "👀"
            }.get(decision["decision"], "❓")
            
            lines.append(f"{emoji} **{decision['feature_name']}** ({decision['file_name']})")
            lines.append(f"   决策: {decision['decision']}")
            lines.append(f"   原因: {decision['reason']}")
            lines.append(f"   测试: ✅{decision['test_summary']['pass']} ⚠️{decision['test_summary']['warn']} ❌{decision['test_summary']['fail']}")
            lines.append("")
        
        return "\n".join(lines)


# 便捷函数
def run_self_deploy(trendradar_path: str = ".") -> List[Dict]:
    """运行自主部署决策"""
    deployer = SelfDeployer(trendradar_path)
    return deployer.make_deploy_decisions()


if __name__ == "__main__":
    decisions = run_self_deploy()
    if decisions:
        deployer = SelfDeployer()
        print(deployer.generate_deploy_report(decisions))
    else:
        print("暂无需要部署的功能")

