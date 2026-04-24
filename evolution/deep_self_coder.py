# -*- coding: utf-8 -*-
"""
Lv44: 深度自主编码

升级self_coder，使用AI（Cloudflare Workers AI）生成真正可用的核心逻辑代码，
而不仅仅是骨架代码。

特性：
1. 使用Cloudflare Workers AI生成代码（零成本）
2. 生成的代码包含完整的业务逻辑
3. 自动语法验证和简单测试
4. 渐进式增强 - 从简单功能开始

与Lv28的区别：
- Lv28: 生成骨架代码（类定义、空方法）
- Lv44: 生成完整逻辑代码（包含具体实现）
"""

import ast
import json
import os
import re
import textwrap
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import urllib.request
from urllib.error import HTTPError, URLError


class DeepSelfCoder:
    """深度自主编码器"""
    
    def __init__(self, trendradar_path: str = "."):
        self.trendradar_path = trendradar_path
        self.output_dir = f"{trendradar_path}/evolution/auto_code_deep"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Cloudflare AI配置
        self.cf_account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        self.cf_api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self.cf_enabled = bool(self.cf_account_id and self.cf_api_token)
    
    def _call_cloudflare_ai(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """调用Cloudflare Workers AI生成代码"""
        if not self.cf_enabled:
            return None
        
        try:
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
            
            payload = json.dumps({
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert Python developer. Generate clean, well-documented Python code. Only output the code, no explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens
            }).encode('utf-8')
            
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.cf_api_token}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if data.get("success") and "result" in data:
                    response_text = data["result"].get("response", "")
                    return response_text
                return None
        except Exception as e:
            print(f"  [深度编码] Cloudflare AI调用失败: {e}")
            return None
    
    def _extract_code(self, text: str) -> str:
        """从AI响应中提取代码"""
        if not text:
            return ""
        
        # 尝试提取代码块
        code_blocks = re.findall(r'```python\n(.*?)\n```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        code_blocks = re.findall(r'```\n(.*?)\n```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        # 如果没有代码块，假设整个输出是代码
        # 移除常见的解释性文本
        lines = text.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from ') or stripped.startswith('class ') or stripped.startswith('def '):
                in_code = True
            if in_code:
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines)
        
        return text.strip()
    
    def _validate_code(self, code: str) -> Tuple[bool, str]:
        """验证代码语法"""
        try:
            ast.parse(code)
            return True, "语法正确"
        except SyntaxError as e:
            return False, f"语法错误: {e}"
    
    def _generate_prompt(self, design_doc: Dict) -> str:
        """生成代码生成Prompt"""
        name = design_doc.get("name", "AutoModule")
        purpose = design_doc.get("purpose", "")
        methods = design_doc.get("methods", [])
        inputs = design_doc.get("inputs", "")
        outputs = design_doc.get("outputs", "")
        
        prompt = f"""Generate a complete, production-ready Python module named '{name}'.

Purpose: {purpose}

Required methods:
"""
        for method in methods:
            prompt += f"- {method}\n"
        
        prompt += f"""
Inputs: {inputs}
Outputs: {outputs}

Requirements:
1. Include all necessary imports
2. Implement complete logic for each method (not just stubs)
3. Add docstrings for the class and methods
4. Include error handling with try/except
5. Add type hints where appropriate
6. Include a '__main__' block with example usage

Generate only the Python code, no explanations outside the code."""
        
        return prompt
    
    def generate_code(self, design_doc: Dict) -> Dict:
        """生成完整代码"""
        module_name = design_doc.get("name", "auto_module")
        print(f"[深度编码] 开始生成模块: {module_name}")
        
        result = {
            "module_name": module_name,
            "generated_at": datetime.now().isoformat(),
            "code": "",
            "valid": False,
            "error": "",
            "fallback": False
        }
        
        # 尝试使用AI生成
        if self.cf_enabled:
            prompt = self._generate_prompt(design_doc)
            ai_response = self._call_cloudflare_ai(prompt)
            
            if ai_response:
                code = self._extract_code(ai_response)
                
                if code:
                    # 验证语法
                    valid, error = self._validate_code(code)
                    
                    if valid:
                        result["code"] = code
                        result["valid"] = True
                        print(f"  [深度编码] ✅ AI生成成功，语法验证通过")
                    else:
                        print(f"  [深度编码] ⚠️ AI生成代码语法错误: {error}")
                        # 使用fallback
                        result["code"] = self._generate_fallback(design_doc)
                        result["valid"] = True
                        result["fallback"] = True
                else:
                    print(f"  [深度编码] ⚠️ 无法从AI响应提取代码")
                    result["code"] = self._generate_fallback(design_doc)
                    result["valid"] = True
                    result["fallback"] = True
            else:
                print(f"  [深度编码] ⚠️ AI未返回响应，使用fallback")
                result["code"] = self._generate_fallback(design_doc)
                result["valid"] = True
                result["fallback"] = True
        else:
            print(f"  [深度编码] ℹ️ Cloudflare AI未配置，使用fallback生成骨架代码")
            result["code"] = self._generate_fallback(design_doc)
            result["valid"] = True
            result["fallback"] = True
        
        # 保存代码
        if result["code"]:
            filepath = f"{self.output_dir}/{module_name}.py"
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result["code"])
                result["filepath"] = filepath
            except Exception as e:
                result["error"] = str(e)
        
        return result
    
    def _generate_fallback(self, design_doc: Dict) -> str:
        """生成fallback代码（比Lv28更完整的骨架）"""
        name = design_doc.get("name", "AutoModule")
        purpose = design_doc.get("purpose", "")
        methods = design_doc.get("methods", [])
        inputs = design_doc.get("inputs", "")
        outputs = design_doc.get("outputs", "")
        
        code_lines = [
            '# -*- coding: utf-8 -*-',
            f'"""',
            f'Auto-generated module: {name}',
            f'',
            f'Purpose: {purpose}',
            f'Generated at: {datetime.now().isoformat()}',
            f'"""',
            '',
            'from typing import Dict, List, Optional, Any',
            'import json',
            'import os',
            '',
            f'class {name}:',
            f'    """{purpose}"""',
            '',
            '    def __init__(self):',
            '        """初始化"""',
            '        pass',
            ''
        ]
        
        for method in methods:
            method_name = method.replace(" ", "_").replace("(", "").replace(")", "").lower()
            code_lines.extend([
                f'    def {method_name}(self, data: Dict) -> Dict:',
                f'        """',
                f'        {method}',
                f'        ',
                f'        Args:',
                f'            data: 输入数据',
                f'        ',
                f'        Returns:',
                f'            处理结果',
                f'        """',
                '        try:',
                '            # TODO: 实现具体逻辑',
                '            result = {}',
                '            return result',
                '        except Exception as e:',
                '            return {"error": str(e)}',
                ''
            ])
        
        code_lines.extend([
            '',
            'if __name__ == "__main__":',
            f'    instance = {name}()',
            '    # TODO: 添加示例用法',
            '    pass'
        ])
        
        return '\n'.join(code_lines)
    
    def run_tests(self, module_path: str) -> Dict:
        """对生成的模块运行简单测试"""
        result = {
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }
        
        try:
            # 尝试导入
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_module", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查类是否存在
            module_name = os.path.basename(module_path).replace('.py', '')
            classes = [name for name in dir(module) if not name.startswith('_') and isinstance(getattr(module, name), type)]
            
            if classes:
                result["tests_passed"] += 1
                
                # 尝试实例化
                cls = getattr(module, classes[0])
                try:
                    instance = cls()
                    result["tests_passed"] += 1
                except Exception as e:
                    result["tests_failed"] += 1
                    result["errors"].append(f"实例化失败: {e}")
            else:
                result["tests_failed"] += 1
                result["errors"].append("未找到类定义")
                
        except Exception as e:
            result["tests_failed"] += 1
            result["errors"].append(f"导入失败: {e}")
        
        return result
    
    def generate_and_test(self, design_doc: Dict) -> Dict:
        """生成代码并运行测试"""
        result = self.generate_code(design_doc)
        
        if result.get("valid") and result.get("filepath"):
            test_result = self.run_tests(result["filepath"])
            result["test_result"] = test_result
            
            if test_result["tests_failed"] == 0:
                print(f"  [深度编码] ✅ 所有测试通过")
            else:
                print(f"  [深度编码] ⚠️ {test_result['tests_failed']}个测试失败")
        
        return result


# 便捷函数
def generate_module_with_ai(design_doc: Dict, trendradar_path: str = ".") -> Dict:
    """使用AI生成完整模块"""
    try:
        coder = DeepSelfCoder(trendradar_path)
        return coder.generate_and_test(design_doc)
    except Exception as e:
        return {"error": str(e), "valid": False}


def generate_simple_module(name: str, purpose: str, methods: List[str],
                           trendradar_path: str = ".") -> Dict:
    """生成简单模块"""
    design_doc = {
        "name": name,
        "purpose": purpose,
        "methods": methods,
        "inputs": "Dict",
        "outputs": "Dict"
    }
    return generate_module_with_ai(design_doc, trendradar_path)


if __name__ == "__main__":
    # 测试
    design = {
        "name": "TestAnalyzer",
        "purpose": "分析测试数据并生成报告",
        "methods": ["analyze data", "generate report", "export results"],
        "inputs": "JSON数据文件路径",
        "outputs": "分析报告Dict"
    }
    
    result = generate_module_with_ai(design)
    print(f"生成结果: valid={result.get('valid')}, fallback={result.get('fallback')}")
    if result.get('code'):
        print(f"代码长度: {len(result['code'])}字符")
