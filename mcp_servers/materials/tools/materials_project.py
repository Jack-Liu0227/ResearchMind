"""
Materials Project API工具
提供Materials Project数据库的搜索和数据获取功能
"""

import asyncio
import aiohttp
import os
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MaterialsProjectTool:
    """Materials Project API工具类"""
    
    def __init__(self):
        self.base_url = "https://api.materialsproject.org/v1"
        self.api_key = os.getenv("MATERIALS_PROJECT_API_KEY", "demo_key")
        self.session = None
    
    async def _get_session(self):
        """获取HTTP会话"""
        if self.session is None:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def search_structure(
        self,
        formula: Optional[str] = None,
        elements: Optional[List[str]] = None,
        crystal_system: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        搜索Materials Project数据库中的晶体结构
        
        Args:
            formula: 化学式
            elements: 元素列表
            crystal_system: 晶系
            max_results: 最大结果数量
        
        Returns:
            包含搜索结果的字典
        """
        try:
            logger.info(f"Materials Project搜索: formula={formula}, elements={elements}")
            
            # 模拟API调用（实际使用时需要真实的API密钥）
            if self.api_key == "demo_key":
                return await self._mock_search_structure(formula, elements, crystal_system, max_results)
            
            session = await self._get_session()
            
            # 构建查询参数
            params = {
                "_limit": max_results,
                "_fields": "material_id,formula_pretty,crystal_system,space_group,volume,density"
            }
            
            if formula:
                params["formula"] = formula
            if elements:
                params["elements"] = ",".join(elements)
            if crystal_system:
                params["crystal_system"] = crystal_system
            
            # 发送请求
            async with session.get(f"{self.base_url}/materials", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = []
                    for item in data.get("data", []):
                        results.append({
                            "material_id": item.get("material_id"),
                            "formula": item.get("formula_pretty"),
                            "crystal_system": item.get("crystal_system"),
                            "space_group": item.get("space_group", {}).get("symbol"),
                            "volume": item.get("volume"),
                            "density": item.get("density"),
                            "source": "Materials Project"
                        })
                    
                    return {
                        "status": "success",
                        "count": len(results),
                        "results": results,
                        "query": {
                            "formula": formula,
                            "elements": elements,
                            "crystal_system": crystal_system
                        }
                    }
                else:
                    error_msg = f"API请求失败: {response.status}"
                    logger.error(error_msg)
                    return {"status": "error", "message": error_msg}
                    
        except Exception as e:
            error_msg = f"搜索Materials Project时发生错误: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    async def _mock_search_structure(
        self,
        formula: Optional[str] = None,
        elements: Optional[List[str]] = None,
        crystal_system: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """模拟Materials Project搜索结果"""
        
        # 模拟数据库
        mock_data = [
            {
                "material_id": "mp-1234",
                "formula": "Li2O",
                "crystal_system": "cubic",
                "space_group": "Fm-3m",
                "volume": 123.45,
                "density": 2.013,
                "source": "Materials Project (Mock)"
            },
            {
                "material_id": "mp-5678",
                "formula": "Fe2O3",
                "crystal_system": "trigonal",
                "space_group": "R-3c",
                "volume": 301.23,
                "density": 5.242,
                "source": "Materials Project (Mock)"
            },
            {
                "material_id": "mp-9012",
                "formula": "SiO2",
                "crystal_system": "hexagonal",
                "space_group": "P6222",
                "volume": 113.01,
                "density": 2.648,
                "source": "Materials Project (Mock)"
            },
            {
                "material_id": "mp-3456",
                "formula": "TiO2",
                "crystal_system": "tetragonal",
                "space_group": "P42/mnm",
                "volume": 62.43,
                "density": 4.230,
                "source": "Materials Project (Mock)"
            },
            {
                "material_id": "mp-7890",
                "formula": "CaCO3",
                "crystal_system": "trigonal",
                "space_group": "R-3c",
                "volume": 367.84,
                "density": 2.711,
                "source": "Materials Project (Mock)"
            }
        ]
        
        # 过滤结果
        filtered_results = []
        for item in mock_data:
            match = True
            
            if formula and formula.lower() not in item["formula"].lower():
                match = False
            
            if elements:
                item_elements = set()
                for char in item["formula"]:
                    if char.isupper():
                        item_elements.add(char)
                    elif char.islower() and item_elements:
                        last_element = list(item_elements)[-1]
                        item_elements.remove(last_element)
                        item_elements.add(last_element + char)
                
                if not any(elem in item_elements for elem in elements):
                    match = False
            
            if crystal_system and crystal_system.lower() != item["crystal_system"].lower():
                match = False
            
            if match:
                filtered_results.append(item)
        
        # 限制结果数量
        filtered_results = filtered_results[:max_results]
        
        return {
            "status": "success",
            "count": len(filtered_results),
            "results": filtered_results,
            "query": {
                "formula": formula,
                "elements": elements,
                "crystal_system": crystal_system
            },
            "note": "这是模拟数据，实际使用需要配置真实的Materials Project API密钥"
        }
    
    async def get_structure_details(self, material_id: str) -> Dict[str, Any]:
        """获取材料的详细结构信息"""
        try:
            if self.api_key == "demo_key":
                return {
                    "status": "success",
                    "material_id": material_id,
                    "structure": "模拟结构数据",
                    "note": "需要真实API密钥获取实际结构数据"
                }
            
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/materials/{material_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "data": data
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"获取材料详情失败: {response.status}"
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "message": f"获取材料详情时发生错误: {str(e)}"
            }
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None
