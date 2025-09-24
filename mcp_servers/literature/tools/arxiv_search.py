"""
ArXiv搜索工具
提供ArXiv论文数据库的搜索功能
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ArxivSearchTool:
    """ArXiv搜索工具类"""
    
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.session = None
    
    async def _get_session(self):
        """获取HTTP会话"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10, 
        sort_by: str = "relevance"
    ) -> Dict[str, Any]:
        """
        搜索ArXiv论文
        
        Args:
            query: 搜索查询词
            max_results: 最大结果数量
            sort_by: 排序方式 (relevance, lastUpdatedDate, submittedDate)
        
        Returns:
            包含搜索结果的字典
        """
        try:
            logger.info(f"ArXiv搜索: {query}, 最大结果: {max_results}")
            
            # 构建搜索参数
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": sort_by,
                "sortOrder": "descending"
            }
            
            session = await self._get_session()
            
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"ArXiv API请求失败: {response.status}")
                
                content = await response.text()
                
            # 解析XML响应
            papers = self._parse_arxiv_response(content)
            
            result = {
                "status": "success",
                "query": query,
                "total_results": len(papers),
                "papers": papers,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"ArXiv搜索完成，找到{len(papers)}篇论文")
            return result
            
        except Exception as e:
            logger.error(f"ArXiv搜索失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    def _parse_arxiv_response(self, xml_content: str) -> List[Dict[str, Any]]:
        """解析ArXiv API的XML响应"""
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # 定义命名空间
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            # 查找所有entry元素
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                paper = {}
                
                # 标题
                title_elem = entry.find('atom:title', namespaces)
                if title_elem is not None:
                    paper['title'] = title_elem.text.strip().replace('\n', ' ')
                
                # 作者
                authors = []
                author_elems = entry.findall('atom:author', namespaces)
                for author_elem in author_elems:
                    name_elem = author_elem.find('atom:name', namespaces)
                    if name_elem is not None:
                        authors.append(name_elem.text.strip())
                paper['authors'] = authors
                
                # 摘要
                summary_elem = entry.find('atom:summary', namespaces)
                if summary_elem is not None:
                    paper['abstract'] = summary_elem.text.strip().replace('\n', ' ')
                
                # ArXiv ID和链接
                id_elem = entry.find('atom:id', namespaces)
                if id_elem is not None:
                    paper['arxiv_url'] = id_elem.text.strip()
                    # 提取ArXiv ID
                    arxiv_id = id_elem.text.split('/')[-1]
                    paper['arxiv_id'] = arxiv_id
                
                # PDF链接
                links = entry.findall('atom:link', namespaces)
                for link in links:
                    if link.get('type') == 'application/pdf':
                        paper['pdf_url'] = link.get('href')
                        break
                
                # 发布日期
                published_elem = entry.find('atom:published', namespaces)
                if published_elem is not None:
                    paper['published_date'] = published_elem.text.strip()
                
                # 更新日期
                updated_elem = entry.find('atom:updated', namespaces)
                if updated_elem is not None:
                    paper['updated_date'] = updated_elem.text.strip()
                
                # 分类
                categories = []
                category_elems = entry.findall('atom:category', namespaces)
                for cat_elem in category_elems:
                    term = cat_elem.get('term')
                    if term:
                        categories.append(term)
                paper['categories'] = categories
                
                # 主要分类
                primary_category = entry.find('arxiv:primary_category', namespaces)
                if primary_category is not None:
                    paper['primary_category'] = primary_category.get('term')
                
                papers.append(paper)
                
        except ET.ParseError as e:
            logger.error(f"解析ArXiv XML响应失败: {e}")
            raise Exception(f"解析ArXiv响应失败: {e}")
        
        return papers
    
    async def get_paper_details(self, arxiv_id: str) -> Dict[str, Any]:
        """
        获取特定论文的详细信息
        
        Args:
            arxiv_id: ArXiv论文ID
        
        Returns:
            论文详细信息
        """
        try:
            logger.info(f"获取ArXiv论文详情: {arxiv_id}")
            
            params = {
                "id_list": arxiv_id,
                "max_results": 1
            }
            
            session = await self._get_session()
            
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"ArXiv API请求失败: {response.status}")
                
                content = await response.text()
            
            papers = self._parse_arxiv_response(content)
            
            if papers:
                return {
                    "status": "success",
                    "paper": papers[0],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "error": "未找到指定论文",
                    "arxiv_id": arxiv_id,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取ArXiv论文详情失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "arxiv_id": arxiv_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None

# 使用示例
async def main():
    """测试ArXiv搜索工具"""
    tool = ArxivSearchTool()
    
    try:
        # 测试搜索
        result = await tool.search("machine learning", max_results=5)
        print("搜索结果:")
        print(f"状态: {result['status']}")
        if result['status'] == 'success':
            print(f"找到 {result['total_results']} 篇论文")
            for i, paper in enumerate(result['papers'], 1):
                print(f"\n{i}. {paper['title']}")
                print(f"   作者: {', '.join(paper['authors'][:3])}...")
                print(f"   ArXiv ID: {paper.get('arxiv_id', 'N/A')}")
        else:
            print(f"错误: {result['error']}")
    
    finally:
        await tool.close()

if __name__ == "__main__":
    asyncio.run(main())
