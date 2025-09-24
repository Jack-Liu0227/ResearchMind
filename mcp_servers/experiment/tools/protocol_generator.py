"""
实验协议生成工具
提供详细的实验操作协议生成功能
"""

import asyncio
import json
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProtocolGeneratorTool:
    """实验协议生成工具类"""
    
    def __init__(self):
        self.protocol_templates = self._load_protocol_templates()
        self.safety_templates = self._load_safety_templates()
    
    def _load_protocol_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载协议模板"""
        return {
            "sol_gel": {
                "title": "溶胶-凝胶法合成协议",
                "steps": [
                    "原料准备和称量",
                    "前驱体溶液配制",
                    "水解反应",
                    "缩聚反应",
                    "凝胶化",
                    "干燥处理",
                    "煅烧处理",
                    "产物收集和表征"
                ],
                "critical_parameters": ["pH", "温度", "反应时间", "煅烧温度"],
                "equipment": ["磁力搅拌器", "pH计", "烘箱", "马弗炉"]
            },
            "hydrothermal": {
                "title": "水热法合成协议",
                "steps": [
                    "原料准备",
                    "反应液配制",
                    "高压釜装填",
                    "密封检查",
                    "水热反应",
                    "冷却处理",
                    "产物分离",
                    "洗涤干燥"
                ],
                "critical_parameters": ["温度", "压力", "反应时间", "填充度"],
                "equipment": ["高压釜", "烘箱", "离心机", "真空干燥箱"]
            },
            "solid_state": {
                "title": "固相反应法合成协议",
                "steps": [
                    "原料预处理",
                    "配料计算",
                    "混合研磨",
                    "压片成型",
                    "预烧处理",
                    "研磨混合",
                    "最终烧结",
                    "产物分析"
                ],
                "critical_parameters": ["温度", "升温速率", "保温时间", "气氛"],
                "equipment": ["球磨机", "压片机", "马弗炉", "管式炉"]
            }
        }
    
    def _load_safety_templates(self) -> Dict[str, List[str]]:
        """加载安全模板"""
        return {
            "general_safety": [
                "佩戴个人防护设备（安全眼镜、实验服、手套）",
                "确保实验区域通风良好",
                "熟悉紧急设备位置（洗眼器、淋浴器、灭火器）",
                "阅读所有化学品的安全数据表(SDS)",
                "保持工作台面整洁有序"
            ],
            "high_temperature": [
                "使用耐高温手套操作热设备",
                "确保加热设备周围无易燃物品",
                "使用坩埚钳夹取高温物品",
                "等待充分冷却后再进行下一步操作",
                "准备灭火设备以防意外"
            ],
            "chemical_handling": [
                "在通风橱内操作挥发性化学品",
                "使用适当的移液工具，避免口吸",
                "标记所有容器和溶液",
                "按照兼容性要求分类存储化学品",
                "及时清理化学品溅洒"
            ],
            "equipment_operation": [
                "操作前检查设备状态",
                "按照操作手册正确使用设备",
                "定期校准精密仪器",
                "发现异常立即停止使用",
                "使用后及时清洁维护设备"
            ]
        }
    
    async def generate_protocol(
        self,
        experiment_design: Dict[str, Any],
        detail_level: str = "detailed",
        include_safety: bool = True,
        include_troubleshooting: bool = True
    ) -> Dict[str, Any]:
        """
        生成实验协议
        
        Args:
            experiment_design: 实验设计方案
            detail_level: 详细程度 (basic, detailed, comprehensive)
            include_safety: 是否包含安全说明
            include_troubleshooting: 是否包含故障排除
        
        Returns:
            包含实验协议的字典
        """
        try:
            logger.info(f"生成实验协议，详细程度: {detail_level}")
            
            synthesis_method = experiment_design.get("synthesis_method", "sol_gel")
            
            # 获取基础协议模板
            base_template = self.protocol_templates.get(synthesis_method, self.protocol_templates["sol_gel"])
            
            # 生成协议头部信息
            protocol_header = await self._generate_protocol_header(experiment_design)
            
            # 生成材料清单
            materials_list = await self._generate_materials_list(experiment_design)
            
            # 生成设备清单
            equipment_list = await self._generate_equipment_list(experiment_design, base_template)
            
            # 生成详细步骤
            detailed_steps = await self._generate_detailed_steps(
                experiment_design, base_template, detail_level
            )
            
            # 生成安全说明
            safety_instructions = []
            if include_safety:
                safety_instructions = await self._generate_safety_instructions(experiment_design)
            
            # 生成故障排除指南
            troubleshooting_guide = []
            if include_troubleshooting:
                troubleshooting_guide = await self._generate_troubleshooting_guide(synthesis_method)
            
            # 生成质量控制要点
            quality_control = await self._generate_quality_control(experiment_design)
            
            # 生成数据记录模板
            data_recording = await self._generate_data_recording_template(experiment_design)
            
            # 组装完整协议
            protocol = {
                "protocol_header": protocol_header,
                "materials_and_reagents": materials_list,
                "equipment_and_instruments": equipment_list,
                "safety_instructions": safety_instructions,
                "experimental_procedure": detailed_steps,
                "quality_control": quality_control,
                "data_recording": data_recording,
                "troubleshooting": troubleshooting_guide,
                "references_and_notes": await self._generate_references(synthesis_method)
            }
            
            return {
                "status": "success",
                "protocol": protocol,
                "protocol_metadata": {
                    "generation_time": datetime.now().isoformat(),
                    "detail_level": detail_level,
                    "includes_safety": include_safety,
                    "includes_troubleshooting": include_troubleshooting,
                    "estimated_duration": await self._estimate_protocol_duration(detailed_steps)
                },
                "note": "实验协议生成完成，请仔细阅读所有安全说明"
            }
            
        except Exception as e:
            error_msg = f"生成实验协议时发生错误: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    async def _generate_protocol_header(self, experiment_design: Dict[str, Any]) -> Dict[str, Any]:
        """生成协议头部信息"""
        return {
            "title": f"{experiment_design.get('target_material', '未知材料')}合成实验协议",
            "experiment_id": experiment_design.get("experiment_id", "EXP-001"),
            "objective": experiment_design.get("research_objective", "材料合成与表征"),
            "method": experiment_design.get("synthesis_method", "sol_gel"),
            "date_created": datetime.now().strftime("%Y-%m-%d"),
            "version": "1.0",
            "author": "ResearchMind AI Assistant",
            "approval_required": True,
            "estimated_duration": f"{random.randint(4, 24)}小时"
        }
    
    async def _generate_materials_list(self, experiment_design: Dict[str, Any]) -> Dict[str, Any]:
        """生成材料清单"""
        # 模拟材料清单生成
        materials = {
            "primary_reagents": [
                {"name": "前驱体A", "amount": "10.0 g", "purity": "99%", "supplier": "Sigma-Aldrich"},
                {"name": "前驱体B", "amount": "5.0 g", "purity": "98%", "supplier": "Aladdin"},
                {"name": "溶剂", "amount": "100 mL", "purity": "AR", "supplier": "国药集团"}
            ],
            "auxiliary_reagents": [
                {"name": "催化剂", "amount": "1.0 g", "purity": "99%", "supplier": "Alfa Aesar"},
                {"name": "表面活性剂", "amount": "2.0 g", "purity": "CP", "supplier": "Sinopharm"}
            ],
            "consumables": [
                {"name": "烧杯", "specification": "250 mL", "quantity": 3},
                {"name": "搅拌子", "specification": "磁性", "quantity": 2},
                {"name": "滤纸", "specification": "定量", "quantity": "1盒"}
            ]
        }
        
        return materials
    
    async def _generate_equipment_list(
        self,
        experiment_design: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成设备清单"""
        base_equipment = template.get("equipment", [])
        
        equipment = {
            "major_equipment": [],
            "analytical_instruments": [],
            "safety_equipment": []
        }
        
        for eq in base_equipment:
            equipment["major_equipment"].append({
                "name": eq,
                "model": f"Model-{random.randint(100, 999)}",
                "specifications": "标准配置",
                "calibration_required": random.choice([True, False])
            })
        
        # 添加表征设备
        characterization_methods = experiment_design.get("characterization_plan", {}).get("characterization_sequence", [])
        for method_info in characterization_methods:
            method = method_info.get("method", "unknown")
            equipment["analytical_instruments"].append({
                "name": method.upper(),
                "purpose": method_info.get("details", {}).get("purpose", "分析"),
                "sample_prep": method_info.get("details", {}).get("sample_preparation", "标准制样")
            })
        
        # 安全设备
        equipment["safety_equipment"] = [
            {"name": "通风橱", "location": "实验台", "status": "正常"},
            {"name": "洗眼器", "location": "实验室入口", "status": "正常"},
            {"name": "灭火器", "location": "墙壁", "status": "正常"},
            {"name": "急救箱", "location": "实验台", "status": "齐全"}
        ]
        
        return equipment
    
    async def _generate_detailed_steps(
        self,
        experiment_design: Dict[str, Any],
        template: Dict[str, Any],
        detail_level: str
    ) -> List[Dict[str, Any]]:
        """生成详细步骤"""
        base_steps = template.get("steps", [])
        synthesis_params = experiment_design.get("synthesis_parameters", {})
        
        detailed_steps = []
        
        for i, step_name in enumerate(base_steps):
            step_detail = {
                "step_number": i + 1,
                "step_name": step_name,
                "description": await self._generate_step_description(step_name, synthesis_params, detail_level),
                "duration": f"{random.randint(15, 180)}分钟",
                "critical_parameters": await self._get_step_critical_parameters(step_name, synthesis_params),
                "safety_notes": await self._get_step_safety_notes(step_name),
                "expected_observations": await self._get_expected_observations(step_name),
                "troubleshooting_tips": await self._get_step_troubleshooting(step_name)
            }
            
            if detail_level == "comprehensive":
                step_detail.update({
                    "detailed_procedure": await self._generate_comprehensive_procedure(step_name, synthesis_params),
                    "quality_checkpoints": await self._generate_quality_checkpoints(step_name),
                    "alternative_methods": await self._generate_alternative_methods(step_name)
                })
            
            detailed_steps.append(step_detail)
        
        return detailed_steps
    
    async def _generate_step_description(
        self,
        step_name: str,
        params: Dict[str, Any],
        detail_level: str
    ) -> str:
        """生成步骤描述"""
        descriptions = {
            "原料准备和称量": f"准确称量所需原料，确保称量精度达到±0.001g。使用分析天平进行称量。",
            "溶液配制": f"在{params.get('temperature', {}).get('optimal', 25)}°C下配制溶液，充分搅拌至完全溶解。",
            "凝胶化反应": f"在pH={params.get('ph', {}).get('optimal', 7)}条件下进行凝胶化，反应时间{params.get('reaction_time', {}).get('optimal', 8)}小时。",
            "干燥处理": f"在{params.get('temperature', {}).get('optimal', 80)}°C下干燥{random.randint(12, 24)}小时。",
            "煅烧处理": f"在{params.get('calcination_temp', {}).get('optimal', 500)}°C下煅烧{random.randint(2, 6)}小时。"
        }
        
        return descriptions.get(step_name, f"执行{step_name}操作，按照标准程序进行。")
    
    async def _generate_safety_instructions(self, experiment_design: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成安全说明"""
        safety_categories = ["general_safety", "chemical_handling", "equipment_operation"]
        
        # 根据实验特点添加特殊安全要求
        synthesis_params = experiment_design.get("synthesis_parameters", {})
        if any(param.get("optimal", 0) > 200 for param in synthesis_params.values() if isinstance(param, dict)):
            safety_categories.append("high_temperature")
        
        safety_instructions = []
        for category in safety_categories:
            if category in self.safety_templates:
                safety_instructions.append({
                    "category": category,
                    "title": category.replace("_", " ").title(),
                    "instructions": self.safety_templates[category]
                })
        
        return safety_instructions
    
    async def _generate_troubleshooting_guide(self, synthesis_method: str) -> List[Dict[str, Any]]:
        """生成故障排除指南"""
        common_issues = [
            {
                "problem": "反应不完全",
                "possible_causes": ["温度过低", "反应时间不足", "催化剂失活"],
                "solutions": ["提高反应温度", "延长反应时间", "更换新鲜催化剂"],
                "prevention": "严格控制反应条件，定期检查催化剂活性"
            },
            {
                "problem": "产物纯度低",
                "possible_causes": ["原料不纯", "反应条件不当", "后处理不充分"],
                "solutions": ["使用高纯度原料", "优化反应条件", "改进纯化方法"],
                "prevention": "选择可靠供应商，建立质量控制体系"
            },
            {
                "problem": "收率偏低",
                "possible_causes": ["反应条件不优化", "副反应严重", "产物损失"],
                "solutions": ["优化反应参数", "抑制副反应", "改进分离方法"],
                "prevention": "进行条件筛选实验，建立最优工艺"
            }
        ]
        
        return common_issues
    
    async def _generate_quality_control(self, experiment_design: Dict[str, Any]) -> Dict[str, Any]:
        """生成质量控制要点"""
        return {
            "process_control": [
                "实时监控反应温度",
                "定期检查pH值",
                "观察反应现象变化",
                "记录关键参数"
            ],
            "product_quality": [
                "外观检查",
                "纯度测定",
                "结构确认",
                "性能测试"
            ],
            "acceptance_criteria": {
                "purity": ">95%",
                "yield": ">80%",
                "particle_size": "符合设计要求",
                "crystal_structure": "与目标一致"
            },
            "sampling_plan": {
                "sampling_points": ["反应中期", "反应结束", "最终产物"],
                "sample_size": "代表性样品",
                "testing_frequency": "每批次"
            }
        }
    
    async def _generate_data_recording_template(self, experiment_design: Dict[str, Any]) -> Dict[str, Any]:
        """生成数据记录模板"""
        return {
            "experimental_conditions": {
                "temperature": "记录实际温度值",
                "pressure": "记录实际压力值",
                "ph": "记录pH变化",
                "reaction_time": "记录实际反应时间"
            },
            "observations": {
                "color_changes": "记录颜色变化",
                "precipitation": "记录沉淀形成",
                "gas_evolution": "记录气体产生",
                "other_phenomena": "记录其他现象"
            },
            "measurements": {
                "yield": "计算实际收率",
                "purity": "测定产物纯度",
                "characterization_results": "记录表征数据"
            },
            "deviations": {
                "parameter_deviations": "记录参数偏差",
                "procedure_modifications": "记录程序修改",
                "unexpected_events": "记录意外事件"
            }
        }
    
    # 其他辅助方法的简化实现
    async def _get_step_critical_parameters(self, step_name: str, params: Dict[str, Any]) -> List[str]:
        """获取步骤关键参数"""
        return ["温度", "时间", "pH", "搅拌速度"]
    
    async def _get_step_safety_notes(self, step_name: str) -> List[str]:
        """获取步骤安全注意事项"""
        return ["佩戴防护设备", "注意通风", "小心操作"]
    
    async def _get_expected_observations(self, step_name: str) -> List[str]:
        """获取预期观察现象"""
        return ["溶液澄清", "温度升高", "颜色变化"]
    
    async def _get_step_troubleshooting(self, step_name: str) -> List[str]:
        """获取步骤故障排除提示"""
        return ["检查设备状态", "确认参数设置", "观察反应现象"]
    
    async def _generate_comprehensive_procedure(self, step_name: str, params: Dict[str, Any]) -> List[str]:
        """生成详细程序"""
        return [f"{step_name}的详细操作步骤1", f"{step_name}的详细操作步骤2"]
    
    async def _generate_quality_checkpoints(self, step_name: str) -> List[str]:
        """生成质量检查点"""
        return ["检查点1", "检查点2"]
    
    async def _generate_alternative_methods(self, step_name: str) -> List[str]:
        """生成替代方法"""
        return ["替代方法1", "替代方法2"]
    
    async def _generate_references(self, synthesis_method: str) -> List[str]:
        """生成参考文献"""
        return [
            "相关文献1",
            "相关文献2",
            "标准操作程序",
            "安全数据表"
        ]
    
    async def _estimate_protocol_duration(self, steps: List[Dict[str, Any]]) -> str:
        """估算协议执行时间"""
        total_minutes = sum(int(step["duration"].split("分钟")[0]) for step in steps)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}小时{minutes}分钟"
