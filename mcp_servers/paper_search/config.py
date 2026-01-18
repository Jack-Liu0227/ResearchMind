"""
全局配置文件

统一管理所有配置参数，支持环境变量覆盖
"""
import os
import sys
from pathlib import Path

# 🔧 导入统一路径管理模块
_PROJECT_ROOT = Path(__file__).parent.parent.parent  # ResearchMind根目录
utils_path = _PROJECT_ROOT / "utils"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

from utils.paths import session_data_root, ensure_dirs

# ==================== 数据存储根目录配置 ====================

# 从环境变量读取根目录（支持相对路径和绝对路径）
SESSION_DATA_ROOT = session_data_root()

# ==================== 子目录结构定义 ====================

# 论文分析缓存目录
CACHE_DIR = SESSION_DATA_ROOT / 'cache' / 'analysis'

# 搜索上下文缓存目录
SEARCH_CACHE_DIR = SESSION_DATA_ROOT / 'cache' / 'search'

# 研究报告目录
REPORTS_DIR = SESSION_DATA_ROOT / 'reports'

# 导出数据目录
EXPORTS_DIR = SESSION_DATA_ROOT / 'exports'

# 数据库文件目录（使用 SESSION_DATA_ROOT 的父目录）
DATABASE_DIR = SESSION_DATA_ROOT.parent / 'database'

# 可视化图表目录
VISUALIZATIONS_DIR = SESSION_DATA_ROOT / 'visualizations'

# 晶体结构文件目录
STRUCTURES_DIR = SESSION_DATA_ROOT / 'structures'

# 日志文件目录
LOGS_DIR = SESSION_DATA_ROOT / 'logs'

# 临时文件目录
TEMP_DIR = SESSION_DATA_ROOT / 'temp'

# 现有的论文会话目录（保留，不修改）
PAPERS_DIR = SESSION_DATA_ROOT / 'papers'
SIMULATION_DIR = SESSION_DATA_ROOT / 'simulation'
PAPER_SESSIONS_FILE = SESSION_DATA_ROOT / 'paper_sessions.json'
METADATA_DIR = SESSION_DATA_ROOT / 'metadata'
IMAGES_DIR = SESSION_DATA_ROOT / 'images'

# ==================== 目录自动创建 ====================

def ensure_data_directories():
    """
    确保核心数据目录存在
    
    注意：只创建必需的核心目录，其他目录（cache, reports, exports等）
    会在实际使用时按需创建，避免产生大量空目录。

    Returns:
        bool: 核心目录创建成功返回 True
    """
    # 只创建核心必需目录，其他目录按需创建
    core_directories = [
        DATABASE_DIR,       # 数据库文件（必需）
        PAPERS_DIR,         # 论文会话（核心功能）
        SIMULATION_DIR,     # 模拟数据（核心功能）
        METADATA_DIR,       # 元数据（核心功能）
    ]

    try:
        ensure_dirs(*core_directories)

        import structlog
        logger = structlog.get_logger(__name__)
        logger.debug(f"Core data directories initialized at {SESSION_DATA_ROOT}")
        return True
    except Exception as e:
        import structlog
        logger = structlog.get_logger(__name__)
        logger.error(f"Failed to create core data directories: {e}")
        return False

# 启动时只创建核心目录
ensure_data_directories()

# ==================== 并发控制 ====================

# 获取论文内容的最大并发数
MAX_CONCURRENT_FETCH = int(os.getenv('MAX_CONCURRENT_FETCH', '10'))

# 分析论文的最大并发数
MAX_CONCURRENT_ANALYSIS = int(os.getenv('MAX_CONCURRENT_ANALYSIS', '10'))

# 批量分析的最大并发数（使用 Semaphore 控制）
MAX_CONCURRENT_BATCH_ANALYSIS = int(os.getenv('MAX_CONCURRENT_BATCH_ANALYSIS', '10'))


# ==================== 超时配置 ====================

# 获取论文全文的超时时间（秒）
FETCH_TIMEOUT = int(os.getenv('FETCH_TIMEOUT', '30'))

# 分析单篇论文的超时时间（秒）
ANALYSIS_TIMEOUT = int(os.getenv('ANALYSIS_TIMEOUT', '300'))

# LLM API 调用超时（秒）
LLM_API_TIMEOUT = int(os.getenv('LLM_API_TIMEOUT', '60'))


# ==================== 内容长度限制 ====================

# 报告生成时内容的最大长度（字符数）
REPORT_CONTENT_MAX_LENGTH = int(os.getenv('REPORT_CONTENT_MAX_LENGTH', '12000'))

# 摘要分析时内容的最大长度（字符数）
ABSTRACT_MAX_LENGTH = int(os.getenv('ABSTRACT_MAX_LENGTH', '5000'))


# ==================== LLM 配置 ====================

# 分析阶段的 max_tokens
LLM_ANALYSIS_MAX_TOKENS = int(os.getenv('LLM_ANALYSIS_MAX_TOKENS', '2500'))

# 综合报告阶段的 max_tokens
LLM_SYNTHESIS_MAX_TOKENS = int(os.getenv('LLM_SYNTHESIS_MAX_TOKENS', '8000'))

# 默认 LLM 模型
DEFAULT_MODEL = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')

# LLM 温度参数
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))


# ==================== 重试配置 ====================

# LLM API 调用的最大重试次数
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# 重试初始延迟（秒）
RETRY_INITIAL_DELAY = int(os.getenv('RETRY_INITIAL_DELAY', '3'))

# 重试延迟倍数（指数退避）
RETRY_BACKOFF_MULTIPLIER = int(os.getenv('RETRY_BACKOFF_MULTIPLIER', '2'))


# ==================== 缓存配置 ====================

# 是否启用分析结果缓存
ENABLE_ANALYSIS_CACHE = os.getenv('ENABLE_ANALYSIS_CACHE', 'true').lower() == 'true'

# 缓存过期时间（秒，0 表示永不过期）
CACHE_EXPIRY = int(os.getenv('CACHE_EXPIRY', '0'))

# 注意：CACHE_DIR 和 SEARCH_CACHE_DIR 已在上方定义，使用统一的 SESSION_DATA_ROOT

# ==================== 流式生成配置 ====================

# 是否启用流式生成（LLM响应实时输出）
ENABLE_STREAMING = os.getenv('ENABLE_STREAMING', 'false').lower() == 'true'

# 流式生成的缓冲区大小（字符数）
STREAMING_BUFFER_SIZE = int(os.getenv('STREAMING_BUFFER_SIZE', '50'))

# 流式生成的更新间隔（秒）
STREAMING_UPDATE_INTERVAL = float(os.getenv('STREAMING_UPDATE_INTERVAL', '0.1'))

# ==================== 领域特定配置 ====================

# 是否启用领域特定Prompt（默认启用）
ENABLE_DOMAIN_PROMPTS = os.getenv('ENABLE_DOMAIN_PROMPTS', 'true').lower() == 'true'

# 手动指定领域（可选，留空则自动检测）
# 支持的领域：materials_science, biomedical, computer_science, physics, chemistry, general
MANUAL_DOMAIN = os.getenv('MANUAL_DOMAIN', '')

# 领域检测最低置信度阈值
DOMAIN_DETECTION_THRESHOLD = int(os.getenv('DOMAIN_DETECTION_THRESHOLD', '2'))


# ==================== 进度追踪配置 ====================

# 进度更新的最小间隔（秒）
PROGRESS_UPDATE_MIN_INTERVAL = float(os.getenv('PROGRESS_UPDATE_MIN_INTERVAL', '0.5'))

# 是否启用进度节流
ENABLE_PROGRESS_THROTTLE = os.getenv('ENABLE_PROGRESS_THROTTLE', 'true').lower() == 'true'


# ==================== 质量控制配置 ====================

# 分析质量的最低分数（0-1）
MIN_QUALITY_SCORE = float(os.getenv('MIN_QUALITY_SCORE', '0.5'))

# 是否启用质量评估
ENABLE_QUALITY_ASSESSMENT = os.getenv('ENABLE_QUALITY_ASSESSMENT', 'false').lower() == 'true'


# ==================== 日志配置 ====================

# 日志级别
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# 是否启用详细日志
VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'


# ==================== 配置验证 ====================

def validate_config():
    """验证配置的合理性"""
    issues = []
    
    # 检查并发数
    if MAX_CONCURRENT_FETCH < 1:
        issues.append("MAX_CONCURRENT_FETCH must be >= 1")
    if MAX_CONCURRENT_ANALYSIS < 1:
        issues.append("MAX_CONCURRENT_ANALYSIS must be >= 1")
    
    # 检查超时
    if FETCH_TIMEOUT < 5:
        issues.append("FETCH_TIMEOUT should be >= 5 seconds")
    if ANALYSIS_TIMEOUT != 0 and ANALYSIS_TIMEOUT < 30:
        issues.append("ANALYSIS_TIMEOUT should be >= 30 seconds or 0 to disable")
    
    # 检查内容长度
    if REPORT_CONTENT_MAX_LENGTH < 1000:
        issues.append("REPORT_CONTENT_MAX_LENGTH should be >= 1000")
    
    # 检查 LLM 参数
    if LLM_TEMPERATURE < 0 or LLM_TEMPERATURE > 2:
        issues.append("LLM_TEMPERATURE should be between 0 and 2")
    
    if issues:
        import structlog
        logger = structlog.get_logger(__name__)
        for issue in issues:
            logger.warning(f"Configuration issue: {issue}")
    
    return len(issues) == 0


# 启动时验证配置
validate_config()
