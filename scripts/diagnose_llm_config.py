#!/usr/bin/env python3
"""
LLM配置诊断脚本

用于检查报告生成所需的LLM配置是否正确
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

def check_env_file():
    """检查.env文件是否存在（可选）"""
    env_path = project_root / ".env"
    if env_path.exists():
        print(f"✅ .env文件存在: {env_path}")
        print("   将从.env文件加载配置")
        return True
    else:
        print(f"ℹ️  .env文件不存在: {env_path}")
        print("   将使用系统环境变量")
        return False

def check_env_variables():
    """检查必需的环境变量"""
    # 尝试加载.env文件（如果存在）
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("   已加载.env文件中的配置")
    else:
        print("   使用系统环境变量")
    
    required_vars = {
        'OPENAI_API_KEY': '用于LLM API调用的密钥',
        'OPENAI_BASE_URL': 'LLM API的基础URL',
        'MODEL_USE': '使用的模型名称（如 gemini/gemini-2.5-flash）'
    }
    
    all_ok = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # 隐藏API key的大部分内容
            if 'KEY' in var and len(value) > 8:
                display_value = value[:4] + '...' + value[-4:]
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
            print(f"   ({description})")
        else:
            print(f"❌ {var}: 未设置")
            print(f"   ({description})")
            all_ok = False
    
    return all_ok

def test_llm_connection():
    """测试LLM连接"""
    print("\n测试LLM连接...")
    
    try:
        from litellm import completion
        
        model = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')
        api_key = os.getenv('OPENAI_API_KEY')
        api_base = os.getenv('OPENAI_BASE_URL')
        
        print(f"使用模型: {model}")
        print(f"API Base: {api_base}")
        
        response = completion(
            model=model,
            messages=[{"role": "user", "content": "Hello, this is a test. Please respond with 'OK'."}],
            temperature=0.3,
            max_tokens=10,
            api_key=api_key,
            api_base=api_base
        )
        
        if response and response.choices:
            content = response.choices[0].message.content
            print(f"✅ LLM连接成功！响应: {content}")
            return True
        else:
            print("❌ LLM返回了空响应")
            return False
            
    except Exception as e:
        print(f"❌ LLM连接失败: {e}")
        print("\n可能的原因：")
        print("1. API key无效或已过期")
        print("2. API Base URL不正确")
        print("3. 模型名称不正确")
        print("4. 网络连接问题")
        print("5. API配额用尽")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("LLM配置诊断工具")
    print("=" * 60)
    print()
    
    # 检查.env文件（可选）
    print("1. 检查配置来源...")
    check_env_file()

    print()
    
    # 检查环境变量
    print("2. 检查环境变量...")
    if not check_env_variables():
        print("\n诊断失败：请配置所有必需的环境变量")
        return 1
    
    print()
    
    # 测试LLM连接
    print("3. 测试LLM连接...")
    if not test_llm_connection():
        print("\n诊断失败：LLM连接测试失败")
        return 1
    
    print()
    print("=" * 60)
    print("✅ 所有检查通过！LLM配置正确")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

