"""
智能体管理器
负责智能体的动态调度、资源管理和性能监控
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from . import AGENT_REGISTRY, AGENT_CAPABILITIES, get_agent, recommend_agent

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentStatus(Enum):
    """智能体状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class Task:
    """任务数据类"""
    task_id: str
    task_type: str
    description: str
    parameters: Dict[str, Any]
    priority: int = 1
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str = None
    result: Any = None
    error: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

@dataclass
class AgentInfo:
    """智能体信息数据类"""
    name: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: str = None
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_execution_time: float = 0.0
    last_activity: float = None
    capabilities: List[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = AGENT_CAPABILITIES.get(self.name, [])
        if self.last_activity is None:
            self.last_activity = time.time()

class AgentManager:
    """智能体管理器"""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []
        self.running_tasks: Dict[str, str] = {}  # task_id -> agent_name
        self.task_counter = 0
        
        # 初始化智能体信息
        self._initialize_agents()
    
    def _initialize_agents(self):
        """初始化所有智能体的信息"""
        for agent_name in AGENT_REGISTRY.keys():
            self.agents[agent_name] = AgentInfo(name=agent_name)
        logger.info(f"初始化了 {len(self.agents)} 个智能体")
    
    def create_task(
        self,
        task_type: str,
        description: str,
        parameters: Dict[str, Any],
        priority: int = 1,
        preferred_agent: str = None
    ) -> str:
        """创建新任务"""
        self.task_counter += 1
        task_id = f"task_{self.task_counter:06d}"
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            description=description,
            parameters=parameters,
            priority=priority
        )
        
        # 如果指定了首选智能体，验证其可用性
        if preferred_agent and preferred_agent in self.agents:
            task.assigned_agent = preferred_agent
        else:
            # 自动推荐合适的智能体
            recommended_agents = recommend_agent(task_type)
            if recommended_agents:
                task.assigned_agent = recommended_agents[0]
        
        self.tasks[task_id] = task
        self.task_queue.append(task_id)
        
        logger.info(f"创建任务 {task_id}: {description}")
        return task_id
    
    def get_available_agent(self, task: Task) -> Optional[str]:
        """获取可用的智能体"""
        # 如果任务指定了智能体，检查其可用性
        if task.assigned_agent:
            agent_info = self.agents.get(task.assigned_agent)
            if agent_info and agent_info.status == AgentStatus.IDLE:
                return task.assigned_agent
        
        # 寻找空闲的智能体
        for agent_name, agent_info in self.agents.items():
            if agent_info.status == AgentStatus.IDLE:
                # 检查智能体是否具备所需能力
                if self._agent_can_handle_task(agent_name, task):
                    return agent_name
        
        return None
    
    def _agent_can_handle_task(self, agent_name: str, task: Task) -> bool:
        """检查智能体是否能处理指定任务"""
        agent_capabilities = AGENT_CAPABILITIES.get(agent_name, [])
        
        # 简单的能力匹配逻辑
        task_keywords = task.task_type.lower().split()
        for keyword in task_keywords:
            for capability in agent_capabilities:
                if keyword in capability.lower():
                    return True
        
        # 协调器智能体可以处理所有任务
        if 'coordinator' in agent_name.lower():
            return True
        
        return False
    
    async def execute_task(self, task_id: str) -> Any:
        """执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
        
        # 获取可用智能体
        agent_name = self.get_available_agent(task)
        if not agent_name:
            raise RuntimeError(f"没有可用的智能体执行任务 {task_id}")
        
        # 更新任务和智能体状态
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        task.assigned_agent = agent_name
        
        agent_info = self.agents[agent_name]
        agent_info.status = AgentStatus.BUSY
        agent_info.current_task = task_id
        agent_info.last_activity = time.time()
        
        self.running_tasks[task_id] = agent_name
        
        logger.info(f"智能体 {agent_name} 开始执行任务 {task_id}")
        
        try:
            # 获取智能体实例并执行任务
            agent = get_agent(agent_name)
            if not agent:
                raise RuntimeError(f"无法获取智能体 {agent_name}")
            
            # 这里应该调用智能体的具体方法
            # 由于ADK的具体API可能不同，这里使用模拟执行
            result = await self._simulate_agent_execution(agent, task)
            
            # 更新任务状态
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = result
            
            # 更新智能体统计信息
            agent_info.successful_tasks += 1
            execution_time = task.completed_at - task.started_at
            agent_info.average_execution_time = (
                (agent_info.average_execution_time * (agent_info.total_tasks - 1) + execution_time) 
                / agent_info.total_tasks
            ) if agent_info.total_tasks > 0 else execution_time
            
            logger.info(f"任务 {task_id} 执行成功，耗时 {execution_time:.2f} 秒")
            
        except Exception as e:
            # 处理执行错误
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            task.error = str(e)
            
            agent_info.failed_tasks += 1
            agent_info.status = AgentStatus.ERROR
            
            logger.error(f"任务 {task_id} 执行失败: {e}")
            raise
        
        finally:
            # 清理状态
            agent_info.status = AgentStatus.IDLE
            agent_info.current_task = None
            agent_info.total_tasks += 1
            agent_info.last_activity = time.time()
            
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
        
        return task.result
    
    async def _simulate_agent_execution(self, agent, task: Task) -> Any:
        """模拟智能体执行（实际实现中应该调用真实的智能体方法）"""
        # 模拟执行时间
        await asyncio.sleep(1.0)
        
        return {
            "task_id": task.task_id,
            "agent": task.assigned_agent,
            "result": f"模拟执行结果 for {task.description}",
            "execution_time": 1.0,
            "status": "success"
        }
    
    async def process_task_queue(self):
        """处理任务队列"""
        while self.task_queue:
            # 按优先级排序
            self.task_queue.sort(key=lambda tid: self.tasks[tid].priority, reverse=True)
            
            task_id = self.task_queue[0]
            task = self.tasks[task_id]
            
            # 检查是否有可用智能体
            if self.get_available_agent(task):
                self.task_queue.pop(0)
                try:
                    await self.execute_task(task_id)
                except Exception as e:
                    logger.error(f"任务 {task_id} 执行失败: {e}")
            else:
                # 没有可用智能体，等待
                await asyncio.sleep(0.1)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "description": task.description,
            "assigned_agent": task.assigned_agent,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": task.error
        }
    
    def get_agent_status(self, agent_name: str = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """获取智能体状态"""
        if agent_name:
            agent_info = self.agents.get(agent_name)
            if not agent_info:
                return None
            
            return {
                "name": agent_info.name,
                "status": agent_info.status.value,
                "current_task": agent_info.current_task,
                "total_tasks": agent_info.total_tasks,
                "successful_tasks": agent_info.successful_tasks,
                "failed_tasks": agent_info.failed_tasks,
                "success_rate": agent_info.successful_tasks / agent_info.total_tasks if agent_info.total_tasks > 0 else 0,
                "average_execution_time": agent_info.average_execution_time,
                "capabilities": agent_info.capabilities
            }
        else:
            return [self.get_agent_status(name) for name in self.agents.keys()]
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        running_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)
        pending_tasks = len(self.task_queue)
        
        idle_agents = sum(1 for agent in self.agents.values() if agent.status == AgentStatus.IDLE)
        busy_agents = sum(1 for agent in self.agents.values() if agent.status == AgentStatus.BUSY)
        error_agents = sum(1 for agent in self.agents.values() if agent.status == AgentStatus.ERROR)
        
        return {
            "total_agents": len(self.agents),
            "idle_agents": idle_agents,
            "busy_agents": busy_agents,
            "error_agents": error_agents,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "running_tasks": running_tasks,
            "pending_tasks": pending_tasks,
            "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
        }

# 全局智能体管理器实例
agent_manager = AgentManager()
