"""
计算设置工具
提供仿真计算参数设置和任务管理功能
"""

import asyncio
import json
import uuid
import random
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CalculationSetupTool:
    """计算设置工具类"""
    
    def __init__(self):
        self.calculation_registry = {}
        self.default_parameters = {
            "energy": {
                "convergence_threshold": 1e-6,
                "max_scf_cycles": 100,
                "mixing_parameter": 0.7
            },
            "optimization": {
                "force_tolerance": 0.01,
                "max_iterations": 200,
                "optimization_method": "bfgs"
            },
            "md": {
                "time_step": 1.0,
                "total_time": 1000.0,
                "thermostat": "nose_hoover",
                "barostat": "parrinello_rahman"
            },
            "phonon": {
                "displacement": 0.01,
                "supercell_size": [2, 2, 2],
                "q_point_mesh": [4, 4, 4]
            },
            "elastic": {
                "strain_magnitude": 0.01,
                "strain_states": 6
            }
        }
    
    async def setup_calculation(
        self,
        structure: str,
        calculation_type: str = "energy",
        accuracy: str = "medium",
        temperature: float = 300.0,
        pressure: float = 0.0
    ) -> Dict[str, Any]:
        """
        设置计算参数
        
        Args:
            structure: 结构数据 (CIF格式或结构ID)
            calculation_type: 计算类型
            accuracy: 计算精度
            temperature: 温度 (K)
            pressure: 压力 (GPa)
        
        Returns:
            包含计算设置的字典
        """
        try:
            logger.info(f"设置计算参数: {calculation_type}, 精度: {accuracy}")
            
            # 生成唯一的计算ID
            calculation_id = str(uuid.uuid4())
            
            # 获取基础参数
            base_params = self.default_parameters.get(calculation_type, {}).copy()
            
            # 根据精度调整参数
            accuracy_params = self._get_accuracy_parameters(accuracy, calculation_type)
            base_params.update(accuracy_params)
            
            # 设置环境条件
            environmental_params = {
                "temperature": temperature,
                "pressure": pressure
            }
            
            # 分析结构并设置相关参数
            structure_params = await self._analyze_structure_and_set_params(structure)
            
            # 组装完整的计算设置
            calculation_setup = {
                "calculation_id": calculation_id,
                "structure": structure,
                "calculation_type": calculation_type,
                "accuracy": accuracy,
                "parameters": base_params,
                "environmental_conditions": environmental_params,
                "structure_parameters": structure_params,
                "computational_resources": self._estimate_resources(calculation_type, accuracy),
                "estimated_time": self._estimate_computation_time(calculation_type, accuracy),
                "status": "configured",
                "created_at": "模拟创建时间"
            }
            
            # 注册计算任务
            self.calculation_registry[calculation_id] = calculation_setup
            
            # 如果有MatterSim工具，也注册到那里
            try:
                from .mattersim_wrapper import MatterSimTool
                mattersim_tool = MatterSimTool()
                mattersim_tool.register_calculation(calculation_id, calculation_setup)
            except ImportError:
                logger.warning("MatterSim工具不可用")
            
            return {
                "status": "success",
                "calculation_setup": calculation_setup,
                "next_steps": [
                    f"使用 run_mattersim 工具执行计算，calculation_id: {calculation_id}",
                    "计算完成后使用 analyze_results 工具分析结果"
                ],
                "note": "计算参数设置完成，可以开始执行计算"
            }
            
        except Exception as e:
            error_msg = f"设置计算参数时发生错误: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    def _get_accuracy_parameters(self, accuracy: str, calculation_type: str) -> Dict[str, Any]:
        """根据精度级别获取参数"""
        accuracy_settings = {
            "low": {
                "energy_cutoff": 300,
                "k_point_density": 0.1,
                "convergence_threshold": 1e-4,
                "scf_mixing": 0.8
            },
            "medium": {
                "energy_cutoff": 500,
                "k_point_density": 0.2,
                "convergence_threshold": 1e-6,
                "scf_mixing": 0.7
            },
            "high": {
                "energy_cutoff": 700,
                "k_point_density": 0.3,
                "convergence_threshold": 1e-8,
                "scf_mixing": 0.5
            },
            "ultra": {
                "energy_cutoff": 1000,
                "k_point_density": 0.4,
                "convergence_threshold": 1e-10,
                "scf_mixing": 0.3
            }
        }
        
        return accuracy_settings.get(accuracy, accuracy_settings["medium"])
    
    async def _analyze_structure_and_set_params(self, structure: str) -> Dict[str, Any]:
        """分析结构并设置相关参数"""
        # 模拟结构分析
        await asyncio.sleep(0.1)
        
        # 模拟结构信息
        structure_info = {
            "num_atoms": random.randint(10, 200),
            "num_elements": random.randint(1, 5),
            "cell_volume": random.uniform(100, 2000),
            "density": random.uniform(1.0, 10.0),
            "has_magnetic_elements": random.choice([True, False]),
            "is_metallic": random.choice([True, False]),
            "space_group": random.randint(1, 230)
        }
        
        # 根据结构特征调整参数
        structure_params = {
            "structure_info": structure_info,
            "recommended_k_points": self._calculate_k_points(structure_info),
            "spin_polarized": structure_info["has_magnetic_elements"],
            "smearing_method": "gaussian" if structure_info["is_metallic"] else "fixed",
            "smearing_width": 0.1 if structure_info["is_metallic"] else 0.0
        }
        
        return structure_params
    
    def _calculate_k_points(self, structure_info: Dict[str, Any]) -> List[int]:
        """计算推荐的k点网格"""
        # 简化的k点计算
        base_k = 8
        volume = structure_info["cell_volume"]
        
        # 根据体积调整k点密度
        if volume < 200:
            k_factor = 1.5
        elif volume < 500:
            k_factor = 1.2
        elif volume < 1000:
            k_factor = 1.0
        else:
            k_factor = 0.8
        
        k_points = [int(base_k * k_factor)] * 3
        return k_points
    
    def _estimate_resources(self, calculation_type: str, accuracy: str) -> Dict[str, Any]:
        """估算计算资源需求"""
        base_resources = {
            "energy": {"cpu_cores": 4, "memory_gb": 8, "gpu_required": False},
            "optimization": {"cpu_cores": 8, "memory_gb": 16, "gpu_required": True},
            "md": {"cpu_cores": 16, "memory_gb": 32, "gpu_required": True},
            "phonon": {"cpu_cores": 32, "memory_gb": 64, "gpu_required": True},
            "elastic": {"cpu_cores": 8, "memory_gb": 16, "gpu_required": False}
        }
        
        resources = base_resources.get(calculation_type, base_resources["energy"]).copy()
        
        # 根据精度调整资源需求
        accuracy_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 2.0,
            "ultra": 4.0
        }
        
        multiplier = accuracy_multipliers.get(accuracy, 1.0)
        resources["cpu_cores"] = int(resources["cpu_cores"] * multiplier)
        resources["memory_gb"] = int(resources["memory_gb"] * multiplier)
        
        return resources
    
    def _estimate_computation_time(self, calculation_type: str, accuracy: str) -> Dict[str, Any]:
        """估算计算时间"""
        base_times = {
            "energy": {"min": 5, "max": 30},
            "optimization": {"min": 30, "max": 300},
            "md": {"min": 60, "max": 1800},
            "phonon": {"min": 120, "max": 3600},
            "elastic": {"min": 60, "max": 600}
        }
        
        time_range = base_times.get(calculation_type, base_times["energy"])
        
        # 根据精度调整时间
        accuracy_multipliers = {
            "low": 0.3,
            "medium": 1.0,
            "high": 3.0,
            "ultra": 10.0
        }
        
        multiplier = accuracy_multipliers.get(accuracy, 1.0)
        
        return {
            "estimated_min_minutes": int(time_range["min"] * multiplier),
            "estimated_max_minutes": int(time_range["max"] * multiplier),
            "note": "实际计算时间取决于系统复杂度和硬件性能"
        }
    
    async def get_calculation_info(self, calculation_id: str) -> Dict[str, Any]:
        """获取计算信息"""
        if calculation_id in self.calculation_registry:
            return {
                "status": "success",
                "calculation_info": self.calculation_registry[calculation_id]
            }
        else:
            return {
                "status": "error",
                "message": f"计算任务 {calculation_id} 不存在"
            }
    
    async def list_calculations(self) -> Dict[str, Any]:
        """列出所有计算任务"""
        calculations = []
        for calc_id, calc_info in self.calculation_registry.items():
            calculations.append({
                "calculation_id": calc_id,
                "calculation_type": calc_info["calculation_type"],
                "status": calc_info["status"],
                "created_at": calc_info["created_at"]
            })
        
        return {
            "status": "success",
            "total_calculations": len(calculations),
            "calculations": calculations
        }
    
    async def update_calculation_status(self, calculation_id: str, status: str) -> Dict[str, Any]:
        """更新计算状态"""
        if calculation_id in self.calculation_registry:
            self.calculation_registry[calculation_id]["status"] = status
            return {
                "status": "success",
                "message": f"计算 {calculation_id} 状态更新为 {status}"
            }
        else:
            return {
                "status": "error",
                "message": f"计算任务 {calculation_id} 不存在"
            }
