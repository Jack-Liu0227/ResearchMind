#!/usr/bin/env python3
"""
ResearchMind智能体系统快速测试脚本
验证智能体架构和MCP工具集成
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_agent_imports():
    """测试智能体导入"""
    print("🧪 测试智能体导入...")
    
    try:
        from agents import (
            root_agent,
            literature_agent,
            database_agent,
            simulation_agent,
            experiment_agent,
            AGENT_REGISTRY,
            get_agent,
            list_agents,
            recommend_agent
        )
        print("✅ 智能体导入成功")
        return True
    except Exception as e:
        print(f"❌ 智能体导入失败: {e}")
        return False

def test_agent_registry():
    """测试智能体注册表"""
    print("\n🧪 测试智能体注册表...")
    
    try:
        from agents import AGENT_REGISTRY, list_agents, get_agent
        
        # 列出所有智能体
        all_agents = list_agents()
        print(f"📋 注册的智能体数量: {len(all_agents)}")
        print(f"📋 智能体列表: {all_agents[:5]}...")  # 只显示前5个
        
        # 测试获取特定智能体
        root = get_agent('root_agent')
        if root:
            print("✅ 成功获取root_agent")
        else:
            print("❌ 无法获取root_agent")
            return False
        
        # 测试智能体推荐
        from agents import recommend_agent
        recommendations = recommend_agent('文献调研')
        print(f"📚 文献调研推荐智能体: {recommendations}")
        
        return True
    except Exception as e:
        print(f"❌ 智能体注册表测试失败: {e}")
        return False

def test_agent_manager():
    """测试智能体管理器"""
    print("\n🧪 测试智能体管理器...")
    
    try:
        from agents.agent_manager import agent_manager
        
        # 获取系统统计
        stats = agent_manager.get_system_stats()
        print(f"📊 系统统计: {stats}")
        
        # 创建测试任务
        task_id = agent_manager.create_task(
            task_type="测试任务",
            description="这是一个测试任务",
            parameters={"test": True}
        )
        print(f"📋 创建测试任务: {task_id}")
        
        # 获取任务状态
        task_status = agent_manager.get_task_status(task_id)
        print(f"📊 任务状态: {task_status['status']}")
        
        return True
    except Exception as e:
        print(f"❌ 智能体管理器测试失败: {e}")
        return False

def test_mcp_servers():
    """测试MCP服务器文件存在性"""
    print("\n🧪 测试MCP服务器文件...")
    
    mcp_servers = [
        'mcp_servers/literature/server.py',
        'mcp_servers/materials/server.py', 
        'mcp_servers/simulation/server.py',
        'mcp_servers/experiment/server.py'
    ]
    
    all_exist = True
    for server_path in mcp_servers:
        if os.path.exists(server_path):
            print(f"✅ {server_path} 存在")
        else:
            print(f"❌ {server_path} 不存在")
            all_exist = False
    
    return all_exist

def test_config_files():
    """测试配置文件"""
    print("\n🧪 测试配置文件...")
    
    config_files = [
        'config/agent_config.yaml',
        'config/mcp_config.yaml'
    ]
    
    all_exist = True
    for config_path in config_files:
        if os.path.exists(config_path):
            print(f"✅ {config_path} 存在")
        else:
            print(f"❌ {config_path} 不存在")
            all_exist = False
    
    return all_exist

def test_workflow_agents():
    """测试工作流智能体"""
    print("\n🧪 测试工作流智能体...")
    
    try:
        from agents.workflow_agent import (
            sequential_workflow_agent,
            parallel_workflow_agent,
            hybrid_workflow_agent,
            specialized_workflow_agent
        )
        
        workflows = [
            ('sequential_workflow_agent', sequential_workflow_agent),
            ('parallel_workflow_agent', parallel_workflow_agent),
            ('hybrid_workflow_agent', hybrid_workflow_agent),
            ('specialized_workflow_agent', specialized_workflow_agent)
        ]
        
        for name, agent in workflows:
            if agent:
                print(f"✅ {name} 创建成功")
            else:
                print(f"❌ {name} 创建失败")
                return False
        
        return True
    except Exception as e:
        print(f"❌ 工作流智能体测试失败: {e}")
        return False

def test_main_integration():
    """测试主程序集成"""
    print("\n🧪 测试主程序集成...")
    
    try:
        # 测试main_mcp.py中的函数
        import main_mcp
        
        # 测试CLI设置
        parser = main_mcp.setup_cli()
        if parser:
            print("✅ CLI设置成功")
        else:
            print("❌ CLI设置失败")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 主程序集成测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🚀 ResearchMind智能体系统测试")
    print("=" * 50)
    
    tests = [
        ("智能体导入", test_agent_imports),
        ("智能体注册表", test_agent_registry),
        ("智能体管理器", test_agent_manager),
        ("MCP服务器文件", test_mcp_servers),
        ("配置文件", test_config_files),
        ("工作流智能体", test_workflow_agents),
        ("主程序集成", test_main_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！ResearchMind智能体系统就绪！")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关组件")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
