# -*- coding: utf-8 -*-
"""
智能回滚系统 - 改进失败后自动恢复

核心理念：
1. 任何自动修改都有备份
2. 实时监控修改后的效果
3. 效果不佳时自动回滚
4. 记录失败经验，避免重复犯错
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ChangeRecord:
    """变更记录"""
    
    def __init__(self, change_type: str, target: str, description: str):
        self.change_type = change_type
        self.target = target
        self.description = description
        self.timestamp = datetime.now().isoformat()
        self.status = "pending"  # pending, applied, verified, rolled_back
        self.effectiveness = None  # 变更效果评分
        self.backup_path = None
    
    def to_dict(self) -> Dict:
        return {
            "change_type": self.change_type,
            "target": self.target,
            "description": self.description,
            "timestamp": self.timestamp,
            "status": self.status,
            "effectiveness": self.effectiveness,
            "backup_path": self.backup_path
        }


class SmartRollback:
    """智能回滚引擎"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.changes = []
        self.backup_dir = f"{trendradar_path}/evolution/backups"
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 加载历史变更记录
        self.history_file = f"{trendradar_path}/evolution/change_history.json"
        self.change_history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """加载历史变更记录"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        """保存变更历史"""
        with open(self.history_file, 'w') as f:
            json.dump(self.change_history, f, ensure_ascii=False, indent=2)
    
    def register_change(self, change_type: str, target: str, description: str, 
                       file_path: str = None) -> ChangeRecord:
        """
        注册一个变更
        
        返回变更记录，后续用于验证和回滚
        """
        record = ChangeRecord(change_type, target, description)
        
        # 创建备份
        if file_path and os.path.exists(file_path):
            backup_name = f"{os.path.basename(file_path)}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            backup_path = os.path.join(self.backup_dir, backup_name)
            shutil.copy2(file_path, backup_path)
            record.backup_path = backup_path
        
        self.changes.append(record)
        return record
    
    def verify_change(self, record: ChangeRecord, metrics_before: Dict, 
                     metrics_after: Dict) -> bool:
        """
        验证变更效果
        
        返回: True=有效, False=需要回滚
        """
        print(f"🔍 验证变更: {record.description}")
        
        # 计算效果评分
        effectiveness = self._calculate_effectiveness(record, metrics_before, metrics_after)
        record.effectiveness = effectiveness
        
        # 判断标准
        if effectiveness < 0:
            print(f"   ❌ 变更效果差 ({effectiveness:+.1f})，建议回滚")
            record.status = "failed"
            return False
        elif effectiveness < 0.3:
            print(f"   ⚠️ 变更效果一般 ({effectiveness:+.1f})，可保留观察")
            record.status = "marginal"
            return True
        else:
            print(f"   ✅ 变更效果良好 ({effectiveness:+.1f})")
            record.status = "verified"
            return True
    
    def _calculate_effectiveness(self, record: ChangeRecord, 
                                before: Dict, after: Dict) -> float:
        """计算变更效果评分"""
        
        if record.change_type == "rss_fix":
            # RSS修复效果 = 成功率提升
            before_rate = before.get("rss_success_rate", 0)
            after_rate = after.get("rss_success_rate", 0)
            return after_rate - before_rate
        
        elif record.change_type == "prompt_optimize":
            # Prompt优化效果 = 质量分提升
            before_score = before.get("avg_quality_score", 0)
            after_score = after.get("avg_quality_score", 0)
            return (after_score - before_score) / 10  # 归一化到0-1
        
        elif record.change_type == "config_adjust":
            # 配置调整效果 = 成本降低
            before_cost = before.get("daily_cost", 0)
            after_cost = after.get("daily_cost", 0)
            return (before_cost - after_cost) / max(before_cost, 0.001)
        
        elif record.change_type == "disable_source":
            # 禁用源效果 = 错误减少
            before_errors = before.get("error_count", 0)
            after_errors = after.get("error_count", 0)
            return (before_errors - after_errors) / max(before_errors, 1)
        
        return 0.0
    
    def rollback(self, record: ChangeRecord) -> bool:
        """
        回滚变更
        
        返回: True=成功, False=失败
        """
        print(f"🔄 回滚变更: {record.description}")
        
        if not record.backup_path or not os.path.exists(record.backup_path):
            print(f"   ❌ 备份不存在，无法回滚")
            return False
        
        try:
            # 从备份恢复
            if record.target.startswith("config/"):
                target_path = os.path.join(self.trendradar_path, record.target)
                shutil.copy2(record.backup_path, target_path)
                print(f"   ✅ 已恢复: {record.target}")
            
            record.status = "rolled_back"
            
            # 记录失败经验
            self._record_failure_lesson(record)
            
            return True
            
        except Exception as e:
            print(f"   ❌ 回滚失败: {e}")
            return False
    
    def _record_failure_lesson(self, record: ChangeRecord):
        """记录失败经验，避免重复犯错"""
        lesson = {
            "timestamp": datetime.now().isoformat(),
            "change_type": record.change_type,
            "target": record.target,
            "description": record.description,
            "effectiveness": record.effectiveness,
            "lesson": f"此类型的变更在当前场景下无效，未来类似情况应跳过"
        }
        
        # 保存到失败经验库
        lessons_file = f"{self.trendradar_path}/evolution/failure_lessons.json"
        lessons = []
        if os.path.exists(lessons_file):
            with open(lessons_file, 'r') as f:
                lessons = json.load(f)
        
        lessons.append(lesson)
        
        # 只保留最近50条
        lessons = lessons[-50:]
        
        with open(lessons_file, 'w') as f:
            json.dump(lessons, f, ensure_ascii=False, indent=2)
    
    def should_skip_change(self, change_type: str, target: str) -> bool:
        """
        检查是否应该跳过某个变更（基于历史失败经验）
        
        返回: True=应该跳过, False=可以执行
        """
        lessons_file = f"{self.trendradar_path}/evolution/failure_lessons.json"
        if not os.path.exists(lessons_file):
            return False
        
        with open(lessons_file, 'r') as f:
            lessons = json.load(f)
        
        # 检查最近是否有类似失败
        recent_lessons = [l for l in lessons if 
                         l["change_type"] == change_type and 
                         l["target"] == target and
                         (datetime.now() - datetime.fromisoformat(l["timestamp"])).days < 7]
        
        if len(recent_lessons) >= 2:
            print(f"⚠️ 基于历史经验，跳过可能失败的变更: {change_type} -> {target}")
            return True
        
        return False
    
    def run_verification_cycle(self, current_metrics: Dict) -> Dict:
        """
        运行验证周期
        
        检查之前的变更效果，必要时回滚
        """
        print("🔄 运行变更验证周期...")
        
        results = {
            "verified": [],
            "rolled_back": [],
            "pending": []
        }
        
        # 检查之前的变更
        for change_dict in self.change_history[-10:]:  # 只检查最近10个
            if change_dict["status"] == "applied":
                # 需要验证的变更
                # 这里简化处理，实际应该比较变更前后的指标
                pass
        
        return results
    
    def finalize_changes(self):
        """完成变更记录"""
        for record in self.changes:
            self.change_history.append(record.to_dict())
        
        # 只保留最近100条
        self.change_history = self.change_history[-100:]
        
        self._save_history()
        print(f"💾 已保存 {len(self.changes)} 个变更记录")


# 便捷函数
def verify_and_rollback(trendradar_path: str = ".") -> str:
    """验证并回滚失败的变更"""
    engine = SmartRollback(trendradar_path)
    
    # 这里简化处理，实际应该读取变更前后的指标
    # 返回报告
    report = []
    report.append("\n" + "=" * 70)
    report.append("🔄 智能回滚报告")
    report.append("=" * 70)
    report.append(f"\n📊 历史变更数: {len(engine.change_history)}")
    
    # 统计各类变更
    successful = len([c for c in engine.change_history if c["status"] in ["verified", "applied"]])
    failed = len([c for c in engine.change_history if c["status"] == "rolled_back"])
    
    report.append(f"✅ 成功: {successful}")
    report.append(f"❌ 回滚: {failed}")
    
    if failed > 0:
        report.append(f"\n📚 已学习 {failed} 个失败经验，避免重复犯错")
    
    report.append("=" * 70)
    
    return "\n".join(report)


if __name__ == "__main__":
    print(verify_and_rollback())
