"""
Orchestrator Module (协调层模块)

中央协调器 - 高优先级优化功能

功能：
1. 协调所有代理完成完整研究流程
2. 管理工作流程状态
3. 提供统一的入口点
4. 处理错误和重试

设计模式：门面模式 + 策略模式
"""
import os
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import structlog

from .search_source import SearchSourceFactory, PaperResult
from ..context_manager.cache import get_context_manager
from .planning import generate_research_plan
from ..paper_manager.analysis import batch_paper_analysis
from ..report_generator.reporting import ResearchReportGenerator
from ..paper_manager.export_tools import save_summary_to_file, save_report_to_file

logger = structlog.get_logger(__name__)


# ============================================================================
# 工作流类型枚举
# ============================================================================

class WorkflowType:
    """工作流类型"""
    QUICK = "quick"      # 快速搜索（仅搜索和保存）
    STANDARD = "standard"  # 标准流程（搜索 + 分析 + 总结）
    DEEP = "deep"        # 深度研究（搜索 + 分析 + 总结 + 报告）
    FULL = "full"        # 完整流程（所有步骤 + 迭代优化）


# ============================================================================
# 深度研究协调器
# ============================================================================

class DeepResearchOrchestrator:
    """深度研究协调器 - 协调所有代理完成完整研究流程"""
    
    def __init__(self):
        """初始化协调器"""
        self.context_manager = get_context_manager()
        self.report_generator = ResearchReportGenerator()
        logger.info("DeepResearchOrchestrator initialized")
    
    async def execute_research_workflow(
        self,
        user_query: str,
        workflow_type: str = WorkflowType.STANDARD,
        max_results_per_source: int = 3,
        sources: Optional[List[str]] = None,
        use_cache: bool = True,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行完整的研究工作流

        Args:
            user_query: 用户查询
            workflow_type: 工作流类型（quick/standard/deep/full）
            max_results_per_source: 每个源的最大结果数（默认: 3，以节省资源）
            sources: 要使用的搜索源列表（默认：['arxiv', 'tavily']）
            use_cache: 是否使用缓存
            output_dir: 输出目录
        
        Returns:
            包含完整研究结果的字典
        """
        logger.info(f"Starting research workflow: {workflow_type} for query: {user_query}")
        
        try:
            # 1. 检查缓存
            if use_cache:
                cached_result = self._check_cache(user_query, workflow_type)
                if cached_result:
                    logger.info("Using cached result")
                    return cached_result
            
            # 2. 生成研究计划
            plan = await self._generate_plan(user_query)
            
            # 3. 执行搜索
            papers = await self._execute_search(
                plan=plan,
                max_results_per_source=max_results_per_source,
                sources=sources or ['arxiv', 'tavily']
            )
            
            if not papers:
                return {
                    'status': 'error',
                    'error': 'No papers found',
                    'timestamp': datetime.now().isoformat()
                }
            
            # 4. 保存到 Excel（所有工作流都需要）
            excel_result = self._save_to_excel(papers, output_dir)
            
            result = {
                'status': 'success',
                'workflow_type': workflow_type,
                'query': user_query,
                'total_papers': len(papers),
                'papers': [p.to_dict() for p in papers],
                'excel_path': excel_result.get('output_path'),
                'timestamp': datetime.now().isoformat()
            }
            
            # 5. 根据工作流类型执行后续步骤
            if workflow_type in [WorkflowType.STANDARD, WorkflowType.DEEP, WorkflowType.FULL]:
                # 分析和总结
                analysis_result = await self._analyze_papers(papers)
                summary_result = self._save_summary(analysis_result, output_dir)
                
                result['analysis'] = analysis_result
                result['summary_path'] = summary_result.get('output_path')
            
            if workflow_type in [WorkflowType.DEEP, WorkflowType.FULL]:
                # 生成报告
                report_result = await self._generate_report(
                    papers=papers,
                    topic=user_query,
                    output_dir=output_dir
                )
                
                result['report'] = report_result
                result['report_path'] = report_result.get('output_path')
            
            if workflow_type == WorkflowType.FULL:
                # 迭代优化（未来实现）
                pass
            
            # 6. 保存到缓存
            if use_cache:
                self._save_to_cache(user_query, workflow_type, result)
            
            logger.info(f"Research workflow completed: {workflow_type}")
            return result
            
        except Exception as e:
            logger.error(f"Research workflow failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def stream_research_workflow(
        self,
        user_query: str,
        workflow_type: str = WorkflowType.STANDARD,
        max_results_per_source: int = 3,
        sources: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行研究工作流，实时返回进度

        Args:
            user_query: 用户查询
            workflow_type: 工作流类型
            max_results_per_source: 每个源的最大结果数（默认: 3，以节省资源）
            sources: 要使用的搜索源列表
        
        Yields:
            进度消息
        """
        try:
            yield f"🔍 开始研究工作流: {workflow_type}\n"
            yield f"📝 查询: {user_query}\n\n"
            
            # 1. 生成计划
            yield "📋 正在生成研究计划...\n"
            plan = await self._generate_plan(user_query)
            yield f"✅ 计划生成完成\n\n"
            
            # 2. 执行搜索
            yield "🔍 正在搜索论文...\n"
            papers = await self._execute_search(
                plan=plan,
                max_results_per_source=max_results_per_source,
                sources=sources or ['arxiv', 'tavily']
            )
            yield f"✅ 找到 {len(papers)} 篇论文\n\n"

            # 3. 分析和总结
            if workflow_type in [WorkflowType.STANDARD, WorkflowType.DEEP, WorkflowType.FULL]:
                yield "📊 正在分析论文...\n"
                analysis_result = await self._analyze_papers(papers)
                yield f"✅ 分析完成\n\n"

                yield "📝 正在生成总结...\n"
                summary_result = self._save_summary(analysis_result, None)
                yield f"✅ 总结已保存: {summary_result.get('output_path')}\n\n"

            # 4. 生成报告
            if workflow_type in [WorkflowType.DEEP, WorkflowType.FULL]:
                yield "📄 正在生成研究报告...\n"
                report_result = await self._generate_report(
                    papers=papers,
                    topic=user_query,
                    output_dir=None
                )
                yield f"✅ 报告已生成: {report_result.get('output_path')}\n\n"
            
            yield "🎉 研究工作流完成！\n"
            
        except Exception as e:
            yield f"❌ 错误: {str(e)}\n"
    
    # ========================================================================
    # 私有辅助方法
    # ========================================================================
    
    def _check_cache(self, query: str, workflow_type: str) -> Optional[Dict[str, Any]]:
        """检查缓存"""
        try:
            cache_key = f"{query}_{workflow_type}"
            cached = self.context_manager.check_recent_search(cache_key, "workflow")
            if cached:
                _, cached_data = cached
                return cached_data.get('results')
            return None
        except Exception as e:
            logger.error(f"Failed to check cache: {e}")
            return None
    
    def _save_to_cache(self, query: str, workflow_type: str, result: Dict[str, Any]):
        """保存到缓存"""
        try:
            cache_key = f"{query}_{workflow_type}"
            self.context_manager.save_search_results(cache_key, "workflow", [result])
        except Exception as e:
            logger.error(f"Failed to save to cache: {e}")
    
    async def _generate_plan(self, user_query: str) -> Dict[str, Any]:
        """生成研究计划"""
        try:
            plan = await generate_research_plan(user_query, max_steps=3)
            return plan
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            return {'primary_query': user_query, 'related_queries': []}
    
    async def _execute_search(
        self,
        plan: Dict[str, Any],
        max_results_per_source: int,
        sources: List[str]
    ) -> List[PaperResult]:
        """异步并行执行搜索"""
        import asyncio

        primary_query = plan.get('primary_query', '')

        async def search_single_source(source_name: str) -> List[PaperResult]:
            """异步搜索单个源"""
            try:
                source = SearchSourceFactory.create(source_name)
                if source and source.is_available():
                    logger.info(f"Searching {source_name} for: {primary_query}")
                    papers = await source.search(primary_query, max_results_per_source)
                    logger.info(f"Found {len(papers)} papers from {source_name}")
                    return papers
                else:
                    logger.warning(f"Source {source_name} is not available")
                    return []
            except Exception as e:
                logger.error(f"Search failed for {source_name}: {e}")
                return []

        # 并行执行所有源的搜索
        logger.info(f"Executing parallel search across {len(sources)} sources...")
        search_tasks = [search_single_source(source_name) for source_name in sources]
        search_results = await asyncio.gather(*search_tasks)

        # 合并结果
        all_papers = []
        for papers in search_results:
            all_papers.extend(papers)

        # 去重
        unique_papers = self._deduplicate_papers(all_papers)
        return unique_papers
    
    def _deduplicate_papers(self, papers: List[PaperResult]) -> List[PaperResult]:
        """去重论文"""
        seen_titles = set()
        unique_papers = []
        
        for paper in papers:
            title_lower = paper.title.lower().strip()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_papers.append(paper)
        
        return unique_papers

    async def _analyze_papers(self, papers: List[PaperResult]) -> Dict[str, Any]:
        """分析论文"""
        try:
            papers_dict = [p.to_dict() for p in papers]
            return batch_paper_analysis(papers_dict, analysis_type="summary")
        except Exception as e:
            logger.error(f"Failed to analyze papers: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _save_summary(self, analysis_result: Dict[str, Any], output_dir: Optional[str]) -> Dict[str, Any]:
        """保存总结"""
        try:
            return save_summary_to_file(analysis_result, output_dir=output_dir)
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _generate_report(
        self,
        papers: List[PaperResult],
        topic: str,
        output_dir: Optional[str]
    ) -> Dict[str, Any]:
        """生成报告"""
        try:
            # 提取论文 IDs
            paper_ids = [p.paper_id for p in papers]
            papers_info = [p.to_dict() for p in papers]
            
            # 生成报告（简化版，不提取全文）
            report_content = self.report_generator.generate_report(
                paper_ids=paper_ids,
                papers_info=papers_info,
                papers_content=[],  # 暂不提取全文
                papers_analysis=[],
                topic=topic
            )
            
            # 保存报告
            report_result = {
                'report': report_content,
                'topic': topic,
                'timestamp': datetime.now().isoformat()
            }
            
            save_result = save_report_to_file(report_result, output_dir=output_dir)
            return {**report_result, **save_result}
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {'status': 'error', 'error': str(e)}


# ============================================================================
# 全局实例
# ============================================================================

_orchestrator = None

def get_orchestrator() -> DeepResearchOrchestrator:
    """获取全局协调器实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DeepResearchOrchestrator()
    return _orchestrator

