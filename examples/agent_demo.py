"""
ResearchMind智能体演示脚本
展示不同智能体和工作流的使用方法
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import (
    root_agent, 
    literature_agent, 
    database_agent, 
    simulation_agent, 
    experiment_agent,
    sequential_workflow_agent,
    parallel_workflow_agent,
    hybrid_workflow_agent,
    agent_manager
)

async def demo_literature_research():
    """演示文献调研智能体"""
    print("🔍 === 文献调研智能体演示 ===")
    
    # 创建文献调研任务
    task_id = agent_manager.create_task(
        task_type="文献调研",
        description="搜索钙钛矿太阳能电池相关文献",
        parameters={
            "query": "perovskite solar cell efficiency",
            "max_results": 10,
            "analysis_type": "methodology"
        },
        preferred_agent="literature_agent"
    )
    
    print(f"📋 创建任务: {task_id}")
    
    # 执行任务
    try:
        result = await agent_manager.execute_task(task_id)
        print(f"✅ 任务完成: {result}")
    except Exception as e:
        print(f"❌ 任务失败: {e}")
    
    # 查看任务状态
    status = agent_manager.get_task_status(task_id)
    print(f"📊 任务状态: {status}")

async def demo_materials_discovery():
    """演示材料发现工作流"""
    print("\n🔬 === 材料发现工作流演示 ===")
    
    task_id = agent_manager.create_task(
        task_type="材料搜索",
        description="搜索高效钙钛矿材料结构",
        parameters={
            "formula": "CsPbI3",
            "crystal_system": "cubic",
            "target_properties": ["bandgap", "stability"]
        },
        preferred_agent="database_agent"
    )
    
    print(f"📋 创建任务: {task_id}")
    
    try:
        result = await agent_manager.execute_task(task_id)
        print(f"✅ 任务完成: {result}")
    except Exception as e:
        print(f"❌ 任务失败: {e}")

async def demo_simulation_workflow():
    """演示仿真计算工作流"""
    print("\n⚛️ === 仿真计算工作流演示 ===")
    
    task_id = agent_manager.create_task(
        task_type="仿真计算",
        description="计算钙钛矿材料的电子性质",
        parameters={
            "structure": "CsPbI3_cubic.cif",
            "calculation_type": "electronic_properties",
            "accuracy": "high"
        },
        preferred_agent="simulation_agent"
    )
    
    print(f"📋 创建任务: {task_id}")
    
    try:
        result = await agent_manager.execute_task(task_id)
        print(f"✅ 任务完成: {result}")
    except Exception as e:
        print(f"❌ 任务失败: {e}")

async def demo_experiment_design():
    """演示实验设计工作流"""
    print("\n🧪 === 实验设计工作流演示 ===")
    
    task_id = agent_manager.create_task(
        task_type="实验设计",
        description="设计钙钛矿太阳能电池制备实验",
        parameters={
            "research_objective": "提高钙钛矿太阳能电池效率",
            "target_material": "CsPbI3",
            "synthesis_method": "sol_gel",
            "budget_constraint": 50.0
        },
        preferred_agent="experiment_agent"
    )
    
    print(f"📋 创建任务: {task_id}")
    
    try:
        result = await agent_manager.execute_task(task_id)
        print(f"✅ 任务完成: {result}")
    except Exception as e:
        print(f"❌ 任务失败: {e}")

async def demo_sequential_workflow():
    """演示顺序工作流"""
    print("\n🔄 === 顺序工作流演示 ===")
    
    # 创建一系列相关任务
    tasks = []
    
    # 1. 文献调研
    task1 = agent_manager.create_task(
        task_type="文献调研",
        description="调研钙钛矿材料最新进展",
        parameters={"query": "perovskite material recent advances"},
        priority=3
    )
    tasks.append(task1)
    
    # 2. 数据库检索
    task2 = agent_manager.create_task(
        task_type="材料搜索", 
        description="搜索高性能钙钛矿结构",
        parameters={"formula": "CsPbI3", "properties": ["efficiency"]},
        priority=2
    )
    tasks.append(task2)
    
    # 3. 仿真验证
    task3 = agent_manager.create_task(
        task_type="仿真计算",
        description="验证材料性质",
        parameters={"calculation_type": "property_prediction"},
        priority=1
    )
    tasks.append(task3)
    
    print(f"📋 创建了 {len(tasks)} 个顺序任务")
    
    # 顺序执行任务
    for i, task_id in enumerate(tasks, 1):
        print(f"\n🔄 执行第 {i} 个任务: {task_id}")
        try:
            result = await agent_manager.execute_task(task_id)
            print(f"✅ 第 {i} 个任务完成")
        except Exception as e:
            print(f"❌ 第 {i} 个任务失败: {e}")

async def demo_parallel_workflow():
    """演示并行工作流"""
    print("\n⚡ === 并行工作流演示 ===")
    
    # 创建可以并行执行的任务
    parallel_tasks = []
    
    # 并行任务1: 文献调研
    task1 = agent_manager.create_task(
        task_type="文献调研",
        description="并行文献调研",
        parameters={"query": "perovskite synthesis methods"}
    )
    parallel_tasks.append(task1)
    
    # 并行任务2: 数据库检索
    task2 = agent_manager.create_task(
        task_type="材料搜索",
        description="并行材料搜索", 
        parameters={"formula": "MAPbI3"}
    )
    parallel_tasks.append(task2)
    
    # 并行任务3: 仿真计算
    task3 = agent_manager.create_task(
        task_type="仿真计算",
        description="并行仿真计算",
        parameters={"calculation_type": "structure_optimization"}
    )
    parallel_tasks.append(task3)
    
    print(f"📋 创建了 {len(parallel_tasks)} 个并行任务")
    
    # 并行执行所有任务
    print("⚡ 开始并行执行...")
    tasks_coroutines = [
        agent_manager.execute_task(task_id) 
        for task_id in parallel_tasks
    ]
    
    try:
        results = await asyncio.gather(*tasks_coroutines, return_exceptions=True)
        
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                print(f"❌ 并行任务 {i} 失败: {result}")
            else:
                print(f"✅ 并行任务 {i} 完成")
                
    except Exception as e:
        print(f"❌ 并行执行失败: {e}")

async def demo_system_monitoring():
    """演示系统监控功能"""
    print("\n📊 === 系统监控演示 ===")
    
    # 获取系统统计信息
    stats = agent_manager.get_system_stats()
    print("📈 系统统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 获取智能体状态
    print("\n🤖 智能体状态:")
    agent_statuses = agent_manager.get_agent_status()
    for agent_status in agent_statuses[:5]:  # 只显示前5个
        if agent_status:
            print(f"  {agent_status['name']}: {agent_status['status']} "
                  f"(成功率: {agent_status['success_rate']:.2%})")

async def main():
    """主演示函数"""
    print("🚀 ResearchMind智能体系统演示")
    print("=" * 50)
    
    try:
        # 演示各种智能体和工作流
        await demo_literature_research()
        await demo_materials_discovery()
        await demo_simulation_workflow()
        await demo_experiment_design()
        
        print("\n" + "=" * 50)
        print("🔄 工作流演示")
        
        await demo_sequential_workflow()
        await demo_parallel_workflow()
        
        print("\n" + "=" * 50)
        await demo_system_monitoring()
        
    except KeyboardInterrupt:
        print("\n⏹️ 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
    
    print("\n🎉 演示完成!")

if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
