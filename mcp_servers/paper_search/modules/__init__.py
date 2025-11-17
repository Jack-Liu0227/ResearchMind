"""
Paper Search Modules Package
Modular implementations organized by business logic.

模块划分按照业务逻辑：
1. arxiv - ArXiv 检索模块（ArXiv 搜索、论文信息、内容提取）
2. tavily - Tavily 网页搜索模块（通用搜索、学术搜索、新闻搜索）
3. google_scholar - Google Scholar 模块（关键词搜索、高级搜索、作者信息）
4. cnki - CNKI 中国知网模块（占位符，未来实现）
5. planning - 规划模块（请求分类、研究计划）
6. reflect - 反思模块（质量检查、反思迭代）
7. analysis - 分析模块（内容分析、批量处理）
8. reporting - 报告模块（报告生成）
9. storage - 存储模块（向量存储、会话管理）
10. intelligent_workflow - 智能研究流程模块（模式B：自动化研究流程）
11. health - 健康检查
"""

# ArXiv Module (ArXiv 检索模块)
from .search.arxiv import (
    search_arxiv_papers,
    search_papers_by_author,
    get_arxiv_paper_content,
)

# Tavily Module (Tavily 网页搜索模块)
from .search.tavily import (
    search_web,
    search_academic_web,
    search_news,
    is_tavily_available,
)

# Planning Module (规划模块)
from .shared.planning import (
    classify_user_request,
    generate_research_plan,
)

# Reflect Module (反思模块) - 暂未使用
# from .shared.reflect import (
#     double_check_results,
#     reflect_on_results,
#     evaluate_iteration_quality,
#     generate_refinement_suggestions,
# )

# Analysis Module (分析模块)
from .paper_manager.analysis import (
    analyze_paper_content,
    batch_paper_analysis,
)

# Note: Storage functions are now in data_layer/
# Import them from data_layer if needed

# Reporting Module (报告模块)
from .report_generator.reporting import (
    generate_research_report,
    generate_research_report_with_data_collection,
)

# Health Module (健康检查) - 暂未使用
# from .shared.health import (
#     health_check,
# )

# Export Tools Module (导出工具模块)
from .paper_manager.export_tools import (
    save_papers_to_csv,
    save_analysis_results_to_csv,
)

# Uploaded Documents Module (用户上传文件处理)
from .paper_manager.uploaded_documents import ingest_uploaded_documents

# Unified Tools Module (统一工具模块)
from .unified_tools import (
    search_papers,
    get_paper_content_async,
    download_paper_file,
    get_paper_info,
)

# Context Manager Module (上下文管理模块) - 暂未使用
# from .context_manager.cache import (
#     SearchContextManager,
#     get_context_manager,
#     check_and_use_cache,
#     save_to_cache,
# )

# Search Source Module (搜索源模块 - 统一搜索接口) - 暂未使用
# from .shared.search_source import (
#     PaperResult,
#     SearchSource,
#     ArxivSearchSource,
#     TavilySearchSource,
#     GoogleScholarSearchSource,
#     SearchSourceFactory,
# )

# Orchestrator Module (协调层模块) - 暂未使用
# from .shared.orchestrator import (
#     WorkflowType,
#     DeepResearchOrchestrator,
#     get_orchestrator,
# )

# Error Handling Module (错误处理模块)
from .shared.error_handling import (
    ResearchError,
    SearchError,
    DownloadError,
    AnalysisError,
    ReportGenerationError,
    CacheError,
    NetworkError,
    TimeoutError,
    ValidationError,
    retry,
    timeout,
    handle_error,
    safe_execute,
    safe_execute_async,
    ErrorRecoveryStrategy,
)


__all__ = [
    # ArXiv (ArXiv 检索)
    'search_arxiv_papers',
    'search_papers_by_author',
    'get_arxiv_paper_content',

    # Tavily (网页搜索)
    'search_web',
    'search_academic_web',
    'search_news',
    'is_tavily_available',

    # Planning (规划)
    'classify_user_request',
    'generate_research_plan',

    # Analysis (分析)
    'analyze_paper_content',
    'batch_paper_analysis',

    # Reporting (报告)
    'generate_research_report',
    'generate_research_report_with_data_collection',

    # Export Tools (导出工具)
    'save_papers_to_csv',
    'save_analysis_results_to_csv',
    'save_report_papers_to_csv',
    'ingest_uploaded_documents',

    # Unified Tools (统一工具)
    'search_papers',
    'get_paper_content',
    'download_paper_file',
    'get_paper_info',

    # Error Handling (错误处理)
    'ResearchError',
    'SearchError',
    'DownloadError',
    'AnalysisError',
    'ReportGenerationError',
    'CacheError',
    'NetworkError',
    'TimeoutError',
    'ValidationError',
    'retry',
    'timeout',
    'handle_error',
    'safe_execute',
    'safe_execute_async',
    'ErrorRecoveryStrategy',
]

