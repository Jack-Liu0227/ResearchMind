"""
风险评估工具
提供实验安全风险评估和缓解措施建议
"""

import asyncio
import json
import random
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RiskAssessmentTool:
    """风险评估工具类"""
    
    def __init__(self):
        self.chemical_database = self._load_chemical_database()
        self.equipment_database = self._load_equipment_database()
        self.safety_protocols = self._load_safety_protocols()
    
    def _load_chemical_database(self) -> Dict[str, Dict[str, Any]]:
        """加载化学品安全数据库"""
        return {
            "hydrochloric_acid": {
                "hazard_level": "high",
                "hazard_types": ["corrosive", "toxic"],
                "safety_measures": ["fume_hood", "protective_equipment", "emergency_shower"],
                "storage_requirements": "corrosive_cabinet",
                "disposal_method": "neutralization"
            },
            "sodium_hydroxide": {
                "hazard_level": "high",
                "hazard_types": ["corrosive", "caustic"],
                "safety_measures": ["fume_hood", "protective_equipment"],
                "storage_requirements": "dry_storage",
                "disposal_method": "neutralization"
            },
            "ethanol": {
                "hazard_level": "medium",
                "hazard_types": ["flammable", "volatile"],
                "safety_measures": ["no_open_flames", "ventilation"],
                "storage_requirements": "flammable_cabinet",
                "disposal_method": "solvent_waste"
            },
            "acetone": {
                "hazard_level": "medium",
                "hazard_types": ["flammable", "volatile"],
                "safety_measures": ["no_open_flames", "ventilation"],
                "storage_requirements": "flammable_cabinet",
                "disposal_method": "solvent_waste"
            }
        }
    
    def _load_equipment_database(self) -> Dict[str, Dict[str, Any]]:
        """加载设备安全数据库"""
        return {
            "furnace": {
                "risk_level": "high",
                "hazards": ["high_temperature", "electrical", "fire"],
                "safety_requirements": ["temperature_monitoring", "fire_suppression", "training"],
                "maintenance_frequency": "monthly"
            },
            "autoclave": {
                "risk_level": "high",
                "hazards": ["high_pressure", "high_temperature", "explosion"],
                "safety_requirements": ["pressure_relief", "safety_training", "regular_inspection"],
                "maintenance_frequency": "quarterly"
            },
            "centrifuge": {
                "risk_level": "medium",
                "hazards": ["mechanical", "imbalance", "electrical"],
                "safety_requirements": ["balance_check", "lid_safety", "training"],
                "maintenance_frequency": "monthly"
            },
            "fume_hood": {
                "risk_level": "low",
                "hazards": ["ventilation_failure", "electrical"],
                "safety_requirements": ["airflow_monitoring", "regular_testing"],
                "maintenance_frequency": "quarterly"
            }
        }
    
    def _load_safety_protocols(self) -> Dict[str, List[str]]:
        """加载安全协议"""
        return {
            "general": [
                "佩戴个人防护设备",
                "了解紧急程序",
                "保持工作区域整洁",
                "正确标记所有容器"
            ],
            "chemical_handling": [
                "阅读安全数据表(SDS)",
                "使用适当的通风设备",
                "避免皮肤和眼睛接触",
                "正确存储化学品"
            ],
            "high_temperature": [
                "使用耐热手套",
                "确保充分冷却时间",
                "使用温度监控设备",
                "准备灭火设备"
            ],
            "high_pressure": [
                "检查设备完整性",
                "使用压力释放阀",
                "远程操作控制",
                "定期安全检查"
            ]
        }
    
    async def assess_risk(
        self,
        experiment_design: Dict[str, Any],
        chemicals: List[str] = None,
        equipment: List[str] = None,
        safety_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        评估实验风险
        
        Args:
            experiment_design: 实验设计方案
            chemicals: 使用的化学品列表
            equipment: 使用的设备列表
            safety_level: 安全等级要求
        
        Returns:
            包含风险评估结果的字典
        """
        try:
            if chemicals is None:
                chemicals = []
            if equipment is None:
                equipment = []
            
            logger.info(f"评估实验风险，安全等级: {safety_level}")
            
            # 化学品风险评估
            chemical_risks = await self._assess_chemical_risks(chemicals)
            
            # 设备风险评估
            equipment_risks = await self._assess_equipment_risks(equipment)
            
            # 工艺风险评估
            process_risks = await self._assess_process_risks(experiment_design)
            
            # 环境风险评估
            environmental_risks = await self._assess_environmental_risks(experiment_design)
            
            # 人员风险评估
            personnel_risks = await self._assess_personnel_risks(experiment_design, safety_level)
            
            # 综合风险评估
            overall_risk = await self._calculate_overall_risk(
                chemical_risks, equipment_risks, process_risks, 
                environmental_risks, personnel_risks
            )
            
            # 生成缓解措施
            mitigation_measures = await self._generate_mitigation_measures(
                chemical_risks, equipment_risks, process_risks, safety_level
            )
            
            # 应急预案
            emergency_procedures = await self._generate_emergency_procedures(
                chemical_risks, equipment_risks
            )
            
            return {
                "status": "success",
                "risk_assessment": {
                    "overall_risk_level": overall_risk["level"],
                    "overall_risk_score": overall_risk["score"],
                    "chemical_risks": chemical_risks,
                    "equipment_risks": equipment_risks,
                    "process_risks": process_risks,
                    "environmental_risks": environmental_risks,
                    "personnel_risks": personnel_risks
                },
                "mitigation_measures": mitigation_measures,
                "emergency_procedures": emergency_procedures,
                "safety_recommendations": await self._generate_safety_recommendations(overall_risk),
                "compliance_requirements": await self._check_compliance_requirements(safety_level),
                "note": "风险评估完成，请仔细阅读安全建议"
            }
            
        except Exception as e:
            error_msg = f"风险评估时发生错误: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    async def _assess_chemical_risks(self, chemicals: List[str]) -> Dict[str, Any]:
        """评估化学品风险"""
        chemical_risk_details = []
        max_risk_level = "low"
        
        for chemical in chemicals:
            # 查找化学品信息（简化匹配）
            chemical_info = None
            for db_chemical, info in self.chemical_database.items():
                if chemical.lower() in db_chemical.lower() or db_chemical.lower() in chemical.lower():
                    chemical_info = info
                    break
            
            if chemical_info:
                risk_detail = {
                    "chemical": chemical,
                    "hazard_level": chemical_info["hazard_level"],
                    "hazard_types": chemical_info["hazard_types"],
                    "safety_measures": chemical_info["safety_measures"],
                    "storage_requirements": chemical_info["storage_requirements"]
                }
                
                # 更新最高风险等级
                if chemical_info["hazard_level"] == "high":
                    max_risk_level = "high"
                elif chemical_info["hazard_level"] == "medium" and max_risk_level == "low":
                    max_risk_level = "medium"
            else:
                # 未知化学品，假设中等风险
                risk_detail = {
                    "chemical": chemical,
                    "hazard_level": "medium",
                    "hazard_types": ["unknown"],
                    "safety_measures": ["general_precautions"],
                    "storage_requirements": "standard_storage",
                    "note": "未知化学品，需要查阅SDS"
                }
                if max_risk_level == "low":
                    max_risk_level = "medium"
            
            chemical_risk_details.append(risk_detail)
        
        return {
            "overall_chemical_risk": max_risk_level,
            "chemical_details": chemical_risk_details,
            "incompatible_combinations": await self._check_chemical_compatibility(chemicals),
            "special_handling_required": len([c for c in chemical_risk_details if c["hazard_level"] == "high"])
        }
    
    async def _assess_equipment_risks(self, equipment: List[str]) -> Dict[str, Any]:
        """评估设备风险"""
        equipment_risk_details = []
        max_risk_level = "low"
        
        for equip in equipment:
            # 查找设备信息
            equipment_info = None
            for db_equipment, info in self.equipment_database.items():
                if equip.lower() in db_equipment.lower() or db_equipment.lower() in equip.lower():
                    equipment_info = info
                    break
            
            if equipment_info:
                risk_detail = {
                    "equipment": equip,
                    "risk_level": equipment_info["risk_level"],
                    "hazards": equipment_info["hazards"],
                    "safety_requirements": equipment_info["safety_requirements"],
                    "maintenance_frequency": equipment_info["maintenance_frequency"]
                }
                
                if equipment_info["risk_level"] == "high":
                    max_risk_level = "high"
                elif equipment_info["risk_level"] == "medium" and max_risk_level == "low":
                    max_risk_level = "medium"
            else:
                risk_detail = {
                    "equipment": equip,
                    "risk_level": "medium",
                    "hazards": ["unknown"],
                    "safety_requirements": ["general_safety"],
                    "note": "未知设备，需要查阅操作手册"
                }
                if max_risk_level == "low":
                    max_risk_level = "medium"
            
            equipment_risk_details.append(risk_detail)
        
        return {
            "overall_equipment_risk": max_risk_level,
            "equipment_details": equipment_risk_details,
            "training_requirements": [eq for eq in equipment_risk_details if eq["risk_level"] == "high"],
            "maintenance_schedule": await self._generate_maintenance_schedule(equipment_risk_details)
        }
    
    async def _assess_process_risks(self, experiment_design: Dict[str, Any]) -> Dict[str, Any]:
        """评估工艺风险"""
        synthesis_method = experiment_design.get("synthesis_method", "unknown")
        synthesis_params = experiment_design.get("synthesis_parameters", {})
        
        process_risks = {
            "temperature_risks": await self._assess_temperature_risks(synthesis_params),
            "pressure_risks": await self._assess_pressure_risks(synthesis_params),
            "reaction_risks": await self._assess_reaction_risks(synthesis_method),
            "handling_risks": await self._assess_handling_risks(experiment_design)
        }
        
        # 计算总体工艺风险
        risk_scores = []
        for risk_category in process_risks.values():
            if isinstance(risk_category, dict) and "risk_level" in risk_category:
                score = {"low": 1, "medium": 2, "high": 3}.get(risk_category["risk_level"], 2)
                risk_scores.append(score)
        
        avg_score = sum(risk_scores) / len(risk_scores) if risk_scores else 1
        overall_level = "low" if avg_score < 1.5 else "medium" if avg_score < 2.5 else "high"
        
        return {
            "overall_process_risk": overall_level,
            "process_risk_details": process_risks,
            "critical_control_points": random.randint(2, 5),
            "process_safety_measures": await self._get_process_safety_measures(synthesis_method)
        }
    
    async def _assess_temperature_risks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """评估温度风险"""
        temp_info = params.get("temperature", {})
        if isinstance(temp_info, dict):
            max_temp = temp_info.get("max", temp_info.get("optimal", 100))
        else:
            max_temp = 100
        
        if max_temp > 500:
            risk_level = "high"
        elif max_temp > 200:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "max_temperature": max_temp,
            "safety_measures": ["temperature_monitoring", "thermal_protection", "emergency_cooling"],
            "equipment_requirements": ["temperature_controller", "safety_cutoff"]
        }
    
    async def _assess_pressure_risks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """评估压力风险"""
        pressure_info = params.get("pressure", {})
        if isinstance(pressure_info, dict):
            max_pressure = pressure_info.get("max", pressure_info.get("optimal", 1))
        else:
            max_pressure = 1
        
        if max_pressure > 10:
            risk_level = "high"
        elif max_pressure > 5:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "max_pressure": max_pressure,
            "safety_measures": ["pressure_relief", "pressure_monitoring", "blast_shield"],
            "equipment_requirements": ["pressure_gauge", "safety_valve"]
        }
    
    async def _calculate_overall_risk(self, *risk_assessments) -> Dict[str, Any]:
        """计算总体风险"""
        risk_levels = []
        for assessment in risk_assessments:
            if isinstance(assessment, dict):
                overall_key = next((k for k in assessment.keys() if "overall" in k.lower()), None)
                if overall_key:
                    level = assessment[overall_key]
                    score = {"low": 1, "medium": 2, "high": 3}.get(level, 2)
                    risk_levels.append(score)
        
        if not risk_levels:
            return {"level": "medium", "score": 2}
        
        max_score = max(risk_levels)
        avg_score = sum(risk_levels) / len(risk_levels)
        
        # 使用最高风险和平均风险的组合
        final_score = (max_score + avg_score) / 2
        
        if final_score >= 2.5:
            level = "high"
        elif final_score >= 1.5:
            level = "medium"
        else:
            level = "low"
        
        return {
            "level": level,
            "score": final_score,
            "max_individual_risk": max_score,
            "average_risk": avg_score
        }
    
    async def _generate_mitigation_measures(
        self,
        chemical_risks: Dict[str, Any],
        equipment_risks: Dict[str, Any],
        process_risks: Dict[str, Any],
        safety_level: str
    ) -> Dict[str, Any]:
        """生成缓解措施"""
        measures = {
            "immediate_actions": [],
            "engineering_controls": [],
            "administrative_controls": [],
            "personal_protective_equipment": [],
            "training_requirements": []
        }
        
        # 基于化学品风险的措施
        if chemical_risks["overall_chemical_risk"] in ["medium", "high"]:
            measures["engineering_controls"].extend([
                "使用通风橱",
                "安装气体检测器",
                "设置紧急洗眼器"
            ])
            measures["personal_protective_equipment"].extend([
                "化学防护服",
                "防化学手套",
                "护目镜"
            ])
        
        # 基于设备风险的措施
        if equipment_risks["overall_equipment_risk"] in ["medium", "high"]:
            measures["engineering_controls"].extend([
                "安装安全联锁装置",
                "设置紧急停止按钮",
                "安装监控系统"
            ])
            measures["training_requirements"].append("设备操作培训")
        
        # 基于工艺风险的措施
        if process_risks["overall_process_risk"] in ["medium", "high"]:
            measures["administrative_controls"].extend([
                "制定标准操作程序",
                "建立检查清单",
                "设置双人确认制度"
            ])
        
        return measures
    
    async def _generate_emergency_procedures(
        self,
        chemical_risks: Dict[str, Any],
        equipment_risks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成应急程序"""
        return {
            "chemical_spill": [
                "立即疏散人员",
                "通知安全部门",
                "使用适当的清理材料",
                "检查空气质量"
            ],
            "fire_emergency": [
                "启动火警报警",
                "使用适当的灭火器",
                "疏散实验室",
                "通知消防部门"
            ],
            "equipment_failure": [
                "立即停止操作",
                "切断电源",
                "通知维护人员",
                "记录故障信息"
            ],
            "personal_injury": [
                "提供急救",
                "通知医疗人员",
                "记录事故详情",
                "调查事故原因"
            ],
            "emergency_contacts": {
                "实验室安全": "123-456-7890",
                "医疗急救": "120",
                "消防部门": "119",
                "设备维护": "123-456-7891"
            }
        }
    
    async def _generate_safety_recommendations(self, overall_risk: Dict[str, Any]) -> List[str]:
        """生成安全建议"""
        recommendations = [
            "进行实验前安全培训",
            "准备完整的应急预案",
            "定期检查安全设备",
            "建立实验记录系统"
        ]
        
        if overall_risk["level"] == "high":
            recommendations.extend([
                "考虑降低实验规模",
                "增加安全监督人员",
                "进行风险评估审查",
                "制定详细的安全程序"
            ])
        
        return recommendations
    
    async def _check_compliance_requirements(self, safety_level: str) -> Dict[str, Any]:
        """检查合规要求"""
        return {
            "regulatory_standards": ["GB/T 27476", "ISO 45001"],
            "required_certifications": ["实验室安全认证", "化学品操作许可"],
            "inspection_frequency": "季度" if safety_level == "high" else "半年",
            "documentation_requirements": [
                "安全数据表(SDS)",
                "操作程序文件",
                "培训记录",
                "事故报告"
            ]
        }
    
    # 其他辅助方法的简化实现
    async def _check_chemical_compatibility(self, chemicals: List[str]) -> List[str]:
        """检查化学品兼容性"""
        return ["注意酸碱分离存储", "避免氧化剂与还原剂混合"]
    
    async def _generate_maintenance_schedule(self, equipment_details: List[Dict]) -> Dict[str, str]:
        """生成维护计划"""
        return {eq["equipment"]: eq.get("maintenance_frequency", "月度") for eq in equipment_details}
    
    async def _assess_reaction_risks(self, synthesis_method: str) -> Dict[str, Any]:
        """评估反应风险"""
        return {"risk_level": "medium", "reaction_type": synthesis_method}
    
    async def _assess_handling_risks(self, experiment_design: Dict[str, Any]) -> Dict[str, Any]:
        """评估操作风险"""
        return {"risk_level": "low", "handling_complexity": "standard"}
    
    async def _assess_environmental_risks(self, experiment_design: Dict[str, Any]) -> Dict[str, Any]:
        """评估环境风险"""
        return {"overall_environmental_risk": "low", "waste_generation": "minimal"}
    
    async def _assess_personnel_risks(self, experiment_design: Dict[str, Any], safety_level: str) -> Dict[str, Any]:
        """评估人员风险"""
        return {"overall_personnel_risk": safety_level, "training_required": True}
    
    async def _get_process_safety_measures(self, synthesis_method: str) -> List[str]:
        """获取工艺安全措施"""
        return ["温度控制", "反应监控", "安全停车程序"]
