"""
Shared Tools (共享工具)

包含所有共享的工具：
- 规划
- 反思
- 健康检查
- 错误处理
- 协调器
- 搜索源
"""
from .planning import (
    classify_user_request,
    generate_research_plan,
)

from .reflect import (
    double_check_results,
    reflect_on_results,
    evaluate_iteration_quality,
    generate_refinement_suggestions,
)

from .health import (
    health_check,
)

from .error_handling import (
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

from .orchestrator import (
    WorkflowType,
    DeepResearchOrchestrator,
    get_orchestrator,
)

from .search_source import (
    PaperResult,
    SearchSource,
    ArxivSearchSource,
    TavilySearchSource,
    SemanticScholarSearchSource,
    SearchSourceFactory,
)

from .field_mapping import (
    normalize_paper_fields,
    batch_normalize_papers,
    merge_paper_data,
)

__all__ = [
    # 规划
    'classify_user_request',
    'generate_research_plan',

    # 反思
    'double_check_results',
    'reflect_on_results',
    'evaluate_iteration_quality',
    'generate_refinement_suggestions',

    # 健康检查
    'health_check',

    # 错误处理
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

    # 协调器
    'WorkflowType',
    'DeepResearchOrchestrator',
    'get_orchestrator',

    # 搜索源
    'PaperResult',
    'SearchSource',
    'ArxivSearchSource',
    'TavilySearchSource',
    'SemanticScholarSearchSource',
    'SearchSourceFactory',

    # 字段映射
    'normalize_paper_fields',
    'batch_normalize_papers',
    'merge_paper_data',
]

