#!/usr/bin/env python3
"""
ResearchMind安装验证脚本
验证uv环境和依赖是否正确安装
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    version = sys.version_info
    print(f"   Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 9:
        print("   ✅ Python版本符合要求 (>=3.9)")
        return True
    else:
        print("   ❌ Python版本不符合要求，需要Python 3.9+")
        return False

def check_uv_installation():
    """检查uv是否安装"""
    print("\n📦 检查uv安装...")
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ uv已安装: {result.stdout.strip()}")
            return True
        else:
            print("   ❌ uv未正确安装")
            return False
    except FileNotFoundError:
        print("   ❌ uv未安装，请先安装uv")
        print("   安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False

def check_project_files():
    """检查项目文件"""
    print("\n📁 检查项目文件...")
    required_files = [
        'pyproject.toml',
        'main_mcp.py',
        'test_agents.py',
        '.env.example',
        'Makefile'
    ]
    
    missing_files = []
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} 缺失")
            missing_files.append(file)
    
    return len(missing_files) == 0

def check_core_dependencies():
    """检查核心依赖"""
    print("\n🔧 检查核心依赖...")
    core_deps = [
        'google.adk',
        'mcp',
        'pydantic',
        'fastapi',
        'numpy',
        'pandas'
    ]
    
    failed_imports = []
    for dep in core_deps:
        try:
            importlib.import_module(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} 导入失败")
            failed_imports.append(dep)
    
    return len(failed_imports) == 0

def check_agents_import():
    """检查智能体导入"""
    print("\n🤖 检查智能体模块...")
    try:
        from agents import (
            root_agent,
            literature_agent,
            database_agent,
            simulation_agent,
            experiment_agent
        )
        print("   ✅ 智能体模块导入成功")
        return True
    except ImportError as e:
        print(f"   ❌ 智能体模块导入失败: {e}")
        return False

def check_mcp_servers():
    """检查MCP服务器文件"""
    print("\n🔌 检查MCP服务器...")
    mcp_servers = [
        'mcp_servers/literature',
        'mcp_servers/materials',
        'mcp_servers/simulation',
        'mcp_servers/experiment'
    ]
    
    missing_servers = []
    for server in mcp_servers:
        server_path = Path(server)
        if server_path.exists() and (server_path / 'server.py').exists():
            print(f"   ✅ {server}")
        else:
            print(f"   ❌ {server} 缺失或不完整")
            missing_servers.append(server)
    
    return len(missing_servers) == 0

def check_environment_file():
    """检查环境配置"""
    print("\n🔐 检查环境配置...")
    
    if Path('.env.example').exists():
        print("   ✅ .env.example 存在")
        
        if Path('.env').exists():
            print("   ✅ .env 文件已创建")
            print("   💡 请确保已填入必要的API密钥")
        else:
            print("   ⚠️  .env 文件未创建")
            print("   建议: cp .env.example .env")
        
        return True
    else:
        print("   ❌ .env.example 缺失")
        return False

def run_quick_test():
    """运行快速测试"""
    print("\n🧪 运行快速测试...")
    try:
        # 尝试导入主要模块
        import main_mcp
        print("   ✅ main_mcp.py 可以导入")
        
        # 检查CLI设置
        parser = main_mcp.setup_cli()
        if parser:
            print("   ✅ CLI设置正常")
        
        return True
    except Exception as e:
        print(f"   ❌ 快速测试失败: {e}")
        return False

def main():
    """主验证函数"""
    print("🚀 ResearchMind安装验证")
    print("=" * 50)
    
    checks = [
        ("Python版本", check_python_version),
        ("uv安装", check_uv_installation),
        ("项目文件", check_project_files),
        ("核心依赖", check_core_dependencies),
        ("智能体模块", check_agents_import),
        ("MCP服务器", check_mcp_servers),
        ("环境配置", check_environment_file),
        ("快速测试", run_quick_test),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print(f"   ❌ {check_name} 检查异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 验证结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有检查通过！ResearchMind已正确安装！")
        print("\n🚀 下一步:")
        print("   1. 配置API密钥: cp .env.example .env && 编辑 .env")
        print("   2. 运行测试: make test 或 uv run python test_agents.py")
        print("   3. 开始使用: make run 或 uv run python main_mcp.py --interactive")
        return True
    else:
        print("⚠️  部分检查失败，请解决上述问题后重新验证")
        print("\n🔧 常见解决方案:")
        print("   1. 安装uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("   2. 安装依赖: uv sync")
        print("   3. 创建环境文件: cp .env.example .env")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
