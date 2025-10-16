"""
Deep Research Agent - Simplified Single Agent Version

参考 database_agent 和 simulation_agent 的设计：
- 直接使用 MCPToolset
- 所有 paper_search 工具直接暴露给 Agent
- 避免复杂的子 agent 嵌套架构
- 更可靠，无超时问题

功能：
- 智能搜索论文（ArXiv, Tavily）
- 提取全文内容
- 生成科学研究格式的调研报告
- 批量分析论文
- 向量化存储和语义搜索

可用工具（12个核心工具）：
- 规划（1个）：generate_research_plan
- 检索（7个）：search_arxiv_papers, search_papers_by_author, get_paper_info, tavily_search, tavily_academic_search, tavily_news_search
- 文献下载（1个）：download_paper
- 批量汇总（1个）：batch_paper_analysis
- 获取全文生成报告（1个）：generate_research_report
- 向量化（2个）：ingest_papers_to_vector_store, semantic_search_papers
"""
# 导出主智能体
from .agent import root_agent

__all__ = [
    'root_agent',  # 主智能体实例
]