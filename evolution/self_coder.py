# -*- coding: utf-8 -*-
"""
自主代码生成 - 基于设计文档自动生成新功能代码

核心理念：
1. 读取Lv27的设计文档
2. 使用代码模板自动生成Python模块
3. 零API成本（基于规则的代码生成）
4. 生成的代码包含：类、方法、测试、日志

代码模板：
- 标准模块模板：文件头、导入、类、方法、便捷函数
- 分析器模板：输入处理、分析逻辑、结果格式化
- 增强器模板：内容处理、增强逻辑、输出生成

生成策略：
- 根据设计文档的category选择模板
- 自动填充类名、方法名、描述
- 生成符合项目规范的代码格式
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional


class SelfCoder:
    """自主代码生成器"""
    
    # 代码模板库
    CODE_TEMPLATES = {
        "分析器": """# -*- coding: utf-8 -*-
\"\"\"
{feature_description}

核心理念：
{core_logic}

输入: {input_spec}
输出: {output_spec}
\"\"\"

from typing import Dict, List, Optional


class {class_name}:
    \"\"\"{feature_name}\"\"\"
    
    def __init__(self):
        pass
    
    def process(self, content: str) -> Dict:
        \"\"\"
        处理输入内容
        
        Args:
            content: 输入内容
            
        Returns:
            处理结果字典
        \"\"\"
        try:
            result = self._analyze(content)
            return result
        except Exception as e:
            print(f"[{class_name}] 处理失败: {{e}}")
            return {{}}
    
    def _analyze(self, content: str) -> Dict:
        \"\"\"核心分析逻辑\"\"\"
        # TODO: 实现核心分析逻辑
        return {{"status": "placeholder", "content": content}}
    
    def generate_insight(self, content: str) -> str:
        \"\"\"生成洞察报告\"\"\"
        result = self.process(content)
        if not result:
            return ""
        
        lines = ["\\n### {feature_name}\\n"]
        lines.append("**分析结果**:")
        for key, value in result.items():
            lines.append(f"- {{key}}: {{value}}")
        lines.append("")
        
        return "\\n".join(lines)


# 便捷函数
def get_{utility_name}(content: str) -> str:
    \"\"\"获取分析洞察\"\"\"
    analyzer = {class_name}()
    return analyzer.generate_insight(content)


if __name__ == "__main__":
    # 测试
    analyzer = {class_name}()
    test_content = "测试内容"
    result = analyzer.process(test_content)
    print(result)
""",
        "增强器": """# -*- coding: utf-8 -*-
\"\"\"
{feature_description}

核心理念：
{core_logic}

输入: {input_spec}
输出: {output_spec}
\"\"\"

from typing import Dict, List, Optional


class {class_name}:
    \"\"\"{feature_name}\"\"\"
    
    def __init__(self):
        pass
    
    def enhance(self, content: str) -> str:
        \"\"\"
        增强输入内容
        
        Args:
            content: 原始内容
            
        Returns:
            增强后的内容
        \"\"\"
        try:
            enhanced = self._enhance_logic(content)
            return enhanced
        except Exception as e:
            print(f"[{class_name}] 增强失败: {{e}}")
            return content
    
    def _enhance_logic(self, content: str) -> str:
        \"\"\"核心增强逻辑\"\"\"
        # TODO: 实现核心增强逻辑
        return content


# 便捷函数
def get_{utility_name}(content: str) -> str:
    \"\"\"获取增强后的内容\"\"\"
    enhancer = {class_name}()
    return enhancer.enhance(content)


if __name__ == "__main__":
    # 测试
    enhancer = {class_name}()
    test_content = "测试内容"
    result = enhancer.enhance(test_content)
    print(result)
""",
        "通用": """# -*- coding: utf-8 -*-
\"\"\"
{feature_description}

核心理念：
{core_logic}

输入: {input_spec}
输出: {output_spec}
\"\"\"

import json
import os
from typing import Dict, List, Optional


class {class_name}:
    \"\"\"{feature_name}\"\"\"
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
    
    def run(self, **kwargs) -> Dict:
        \"\"\"
        运行功能
        
        Returns:
            运行结果
        \"\"\"
        try:
            result = self._process(**kwargs)
            return result
        except Exception as e:
            print(f"[{class_name}] 运行失败: {{e}}")
            return {{"error": str(e)}}
    
    def _process(self, **kwargs) -> Dict:
        \"\"\"核心处理逻辑\"\"\"
        # TODO: 实现核心逻辑
        return {{"status": "success"}}


# 便捷函数
def get_{utility_name}(trendradar_path: str = ".") -> str:
    \"\"\"获取功能输出\"\"\"
    runner = {class_name}(trendradar_path)
    result = runner.run()
    return str(result)


if __name__ == "__main__":
    # 测试
    runner = {class_name}()
    result = runner.run()
    print(result)
"""
    }
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.designs_dir = f"{trendradar_path}/evolution/designs"
        self.output_dir = f"{trendradar_path}/evolution"
    
    def load_pending_designs(self) -> List[Dict]:
        """加载待实现的设计文档"""
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
                
                if design.get("status") == "designed":
                    designs.append(design)
            except Exception:
                continue
        
        return designs
    
    def select_template(self, category: str) -> str:
        """根据功能类别选择模板"""
        if "分析" in category or "检测" in category:
            return self.CODE_TEMPLATES["分析器"]
        elif "增强" in category or "优化" in category:
            return self.CODE_TEMPLATES["增强器"]
        else:
            return self.CODE_TEMPLATES["通用"]
    
    def generate_code(self, design: Dict) -> str:
        """根据设计文档生成代码"""
        feature = design["feature"]
        guide = design["implementation_guide"]
        
        # 选择模板
        template = self.select_template(feature["category"])
        
        # 生成类名（如果设计文档没有提供）
        class_name = guide.get("class_name", self._generate_class_name(feature["file_name"]))
        utility_name = guide.get("utility_function", f"get_{feature['file_name'].replace('.py', '')}_insight")
        
        # 填充模板
        code = template.format(
            feature_description=feature["description"],
            core_logic=feature["core_logic"],
            input_spec=feature["input_spec"],
            output_spec=feature["output_spec"],
            class_name=class_name,
            feature_name=feature["name"],
            utility_name=utility_name.replace("get_", "").replace("_insight", "")
        )
        
        return code
    
    def _generate_class_name(self, file_name: str) -> str:
        """根据文件名生成类名"""
        base = file_name.replace('.py', '')
        parts = base.split('_')
        return ''.join(part.capitalize() for part in parts)
    
    def save_code(self, design: Dict, code: str) -> str:
        """保存生成的代码文件"""
        file_name = design["feature"]["file_name"]
        file_path = f"{self.output_dir}/{file_name}"
        
        # 检查文件是否已存在
        if os.path.exists(file_path):
            # 备份旧文件
            backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            os.rename(file_path, backup_path)
            print(f"[自主编码] 备份旧文件: {backup_path}")
        
        with open(file_path, 'w') as f:
            f.write(code)
        
        return file_path
    
    def update_design_status(self, design: Dict, status: str):
        """更新设计文档状态"""
        design["status"] = status
        design["implementation"] = {
            "timestamp": datetime.now().isoformat(),
            "status": status
        }
        
        file_path = f"{self.designs_dir}/{design['design_id']}.json"
        with open(file_path, 'w') as f:
            json.dump(design, f, ensure_ascii=False, indent=2)
    
    def implement_features(self) -> List[Dict]:
        """主入口：实现待实现的设计"""
        designs = self.load_pending_designs()
        
        if not designs:
            print("[自主编码] 没有待实现的设计文档")
            return []
        
        print(f"[自主编码] 发现 {len(designs)} 个待实现的设计")
        
        implemented = []
        for design in designs:
            feature = design["feature"]
            print(f"[自主编码] 开始实现: {feature['name']}")
            
            # 生成代码
            code = self.generate_code(design)
            
            # 验证代码语法
            if not self._validate_syntax(code):
                print(f"[自主编码] ⚠️ 代码语法检查未通过，跳过: {feature['file_name']}")
                continue
            
            # 保存代码
            file_path = self.save_code(design, code)
            print(f"[自主编码] ✅ 代码已生成: {file_path}")
            
            # 更新设计状态
            self.update_design_status(design, "implemented")
            
            implemented.append({
                "design_id": design["design_id"],
                "feature_name": feature["name"],
                "file_path": file_path,
                "status": "implemented"
            })
        
        return implemented
    
    def _validate_syntax(self, code: str) -> bool:
        """验证Python代码语法"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            print(f"[自主编码] 语法错误: {e}")
            return False
    
    def generate_implementation_report(self, implementations: List[Dict]) -> str:
        """生成实现报告"""
        lines = ["\n### 📝 自主代码生成报告\n"]
        
        if not implementations:
            lines.append("暂无新功能需要实现。\n")
            return "\n".join(lines)
        
        lines.append(f"**成功实现 {len(implementations)} 个新功能**:")
        for impl in implementations:
            lines.append(f"- ✅ **{impl['feature_name']}**: {impl['file_path']}")
        lines.append("")
        lines.append("**下一步**: 运行测试验证新功能。\n")
        
        return "\n".join(lines)


# 便捷函数
def run_self_coding(trendradar_path: str = ".") -> List[Dict]:
    """运行自主代码生成"""
    coder = SelfCoder(trendradar_path)
    return coder.implement_features()


if __name__ == "__main__":
    implementations = run_self_coding()
    if implementations:
        print(f"\n成功实现 {len(implementations)} 个新功能")
    else:
        print("\n暂无需要实现的新功能")
