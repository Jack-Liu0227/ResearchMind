# MCP Paper Search 架构文档

## 📐 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│                      MCP Paper Search Server                         │
│                      (FastMCP 服务器)                                │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  - 接收工具调用请求                                          │   │
│  │  - 路由到相应的模块                                          │   │
│  │  - 返回处理结果                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
└───────────────────────────┬───────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬───────────────────┐
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│              │    │              │    │              │    │              │
│   Search     │    │    Paper     │    │   Report     │    │   Context    │
│   Module     │    │   Manager    │    │  Generator   │    │   Manager    │
│              │    │              │    │              │    │              │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │                   │
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
        │  External    │    │   Shared     │    │   Session    │
        │   APIs       │    │   Utils      │    │   Folder     │
        │  - ArXiv     │    │  - File I/O  │    │   Manager    │
        │  - Tavily    │    │  - Logging   │    │              │
        │  - LiteLLM   │    │  - Helpers   │    │              │
        └──────────────┘    └──────────────┘    └──────────────┘
```

**说明**: Data Layer 已合并到 Context Manager 中

## 🏛️ 核心模块

### 1. Search Module (搜索模块)

**位置**: `modules/search/`

**职责**:
- 执行学术论文搜索
- 支持多个搜索源
- 标准化搜索结果

**当前支持的检索来源**:
- ✅ **ArXiv**: 物理、数学、计算机科学等领域的预印本论文
- ✅ **Tavily Academic**: 学术网页搜索

**计划支持的检索来源**:
- 🔜 **Google Scholar**: 学术文献搜索
- 🔜 **CNKI**: 中国知网
- 🔜 **PubMed**: 生物医学文献
- 🔜 **IEEE Xplore**: 电气电子工程文献
- 🔜 **Semantic Scholar**: AI 驱动的学术搜索
- 🔜 **Web of Science**: 综合学术数据库
- 🔜 **Scopus**: 综合学术数据库

**扩展性设计**:
- 每个检索来源独立实现
- 统一的搜索接口
- 支持动态添加新来源
- 支持多源并行搜索和结果合并

**子模块**:

#### ArXiv Search (`arxiv.py`)

```python
def search_arxiv_papers_impl(
    topic: str,
    max_results: int = 10,
    sort_by: str = "relevance"
) -> List[Dict[str, Any]]:
    """
    搜索 ArXiv 论文
    
    工作流程:
    1. 构建搜索查询
    2. 调用 ArXiv API
    3. 解析 XML 响应
    4. 提取论文信息
    5. 标准化格式
    6. 创建文件夹（使用 UUID）
    7. 保存论文信息
    """
```

**关键特性**:
- 支持多种排序方式（相关性、更新时间、提交时间）
- 自动创建唯一文件夹（`{topic}_{uuid}`）
- 保存论文信息到 JSON 文件
- 添加 `source: 'arxiv'` 标识

#### Tavily Search (`tavily.py`)

```python
def search_academic_web_impl(
    query: str,
    max_results: int = 5,
    search_depth: str = "advanced"
) -> List[Dict[str, Any]]:
    """
    使用 Tavily 搜索学术资源
    
    工作流程:
    1. 调用 Tavily API
    2. 解析 JSON 响应
    3. 提取搜索结果
    4. 标准化格式
    5. 添加 source 标识
    """
```

**搜索类型**:
- `search_academic_web`: 学术资源搜索
- `search_web`: 通用网页搜索
- `search_news`: 新闻搜索

**关键特性**:
- 支持高级搜索深度
- 返回内容摘要
- 添加 `source: 'tavily'` 标识

### 2. Paper Manager Module (论文管理模块)

**位置**: `modules/paper_manager/`

**职责**:
- 下载论文 PDF
- 管理论文存储
- 导出论文数据

**子模块**:

#### Download (`download.py`)

```python
def download_arxiv_paper_impl(
    arxiv_id: str,
    save_dir: str = "./paper_search/papers"
) -> Dict[str, Any]:
    """
    下载 ArXiv 论文 PDF
    
    工作流程:
    1. 构建 PDF URL
    2. 发送 HTTP 请求
    3. 保存到文件
    4. 返回文件路径
    """
```

#### Storage (`storage.py`)

```python
def get_paper_info_impl(paper_id: str) -> str:
    """
    获取论文信息
    
    工作流程:
    1. 查找论文信息文件
    2. 读取 JSON 文件
    3. 返回论文信息
    """
```

#### Export Tools (`export_tools.py`)

```python
def save_papers_to_csv(
    papers: List[Dict[str, Any]],
    output_path: str = None,
    output_dir: str = None,
    session_id: str = None
) -> Dict[str, Any]:
    """
    导出论文到 CSV

    工作流程:
    1. 创建 DataFrame
    2. 转换为 CSV 字符串
    3. 返回 CSV 内容供前端下载
    """
```

**文件夹命名策略**:
```python
import uuid
random_id = str(uuid.uuid4())[:8]
folder_name = f"{source}_papers_{random_id}"
```

### 3. Report Generator Module (报告生成模块)

**位置**: `modules/report_generator/`

**职责**:
- 分析论文内容
- 生成研究报告
- 保存报告到文件

**子模块**:

#### Analysis (`analysis.py`)

```python
def analyze_paper_content_impl(
    arxiv_id: str,
    content: str,
    analysis_type: str = "summary"
) -> Dict[str, Any]:
    """
    分析论文内容
    
    分析类型:
    - summary: 生成摘要
    - comprehensive: 全面分析
    - keywords: 提取关键词
    
    工作流程:
    1. 根据分析类型选择提示词
    2. 调用 LLM 分析
    3. 解析分析结果
    4. 返回结构化数据
    """
```

#### Reporting (`reporting.py`)

```python
class ReportGenerator:
    def generate_research_report(
        self,
        paper_ids: List[str],
        papers_info: List[Dict[str, Any]],
        papers_content: List[str],
        papers_analysis: List[Dict[str, Any]],
        topic: str
    ) -> str:
        """
        生成研究报告
        
        报告结构:
        1. 标题和元数据
        2. 执行摘要
        3. 研究背景
        4. 文献综述
        5. 研究趋势
        6. 结论与展望
        7. 参考文献
        8. 无法获取的论文（如果有）
        """
```

**报告生成流程**:
```
1. 收集论文信息
   ↓
2. 获取论文内容
   ↓
3. 分析每篇论文
   ↓
4. 生成执行摘要（使用 LLM）
   ↓
5. 生成研究背景（使用 LLM）
   ↓
6. 生成文献综述（格式化）
   ↓
7. 生成研究趋势（基于关键词）
   ↓
8. 生成结论与展望（使用 LLM）
   ↓
9. 添加参考文献
   ↓
10. 添加失败论文列表（如果有）
   ↓
11. 保存到文件
```

**格式优化**:
- 移除空的摘要和关键词
- 只显示有效的字段（长度 > 10）
- 添加 PDF 链接
- 字段之间添加空行
- 添加无分析信息提示

### 4. Context Manager Module (上下文管理模块)

**位置**: `modules/context_manager/`

**职责**:
- 管理缓存
- 管理会话
- 向量存储（包含原 Data Layer 功能）
- 嵌入服务
- 文档摄取
- 防止上下文丢失

**子模块**:

#### Cache (`cache.py`)

```python
class CacheManager:
    def __init__(self):
        self.cache = {}  # LRU cache
        self.ttl = 24 * 3600  # 24 hours
        self.max_size = 1000

    def get(self, key: str) -> Any:
        """获取缓存"""

    def set(self, key: str, value: Any):
        """设置缓存"""

    def cleanup_expired(self):
        """清理过期缓存"""
```

#### Session Manager (`session_manager.py`)

```python
class SessionManager:
    def create_session(self) -> str:
        """创建新会话"""

    def save_session(self, session_id: str, data: Dict):
        """保存会话"""

    def load_session(self, session_id: str) -> Dict:
        """加载会话"""
```

#### ChromaDB Vector Store (`chroma_store.py`)

```python
class ChromaVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db", session_id: Optional[str] = None):
        """
        初始化 ChromaDB 向量存储

        Args:
            persist_directory: 基础持久化目录
            session_id: 可选的会话 ID，用于会话级别存储
        """
        if session_id:
            # 使用会话文件夹
            session_folder = get_session_folder(session_id)
            self.persist_directory = Path(session_folder) / "chroma_db"
        else:
            # 使用全局目录
            self.persist_directory = Path(persist_directory)

    def add_documents(self, texts, embeddings, metadata, ids):
        """添加文档到向量存储"""

    def search(self, query_embedding, top_k=5):
        """语义搜索"""
```

#### Embedding Service (`embeddings.py`)

```python
class GoogleEmbeddings:
    def __init__(self, model_name: str = 'models/text-embedding-004'):
        """初始化 Google Embeddings 服务"""

    async def embed_text(self, text: str) -> List[float]:
        """获取文本的嵌入向量（768 维）"""

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量获取嵌入向量"""

    async def embed_query(self, query: str) -> List[float]:
        """获取查询的嵌入向量"""
```

#### Document Ingestion (`ingestion.py`)

```python
async def ingest_papers_to_vector_store(
    paper_ids: List[str],
    collection_name: str,
    vector_store: ChromaVectorStore,
    embedding_service: GoogleEmbeddings,
    get_paper_content_func
):
    """
    将论文摄取到向量存储

    1. 提取论文内容
    2. 分块处理
    3. 生成嵌入
    4. 存储到 ChromaDB
    """
```

#### Service Management (`services.py`)

```python
def get_vector_store(session_id: Optional[str] = None):
    """
    获取向量存储实例

    - 如果提供 session_id，返回会话级别的 ChromaDB
    - 否则返回全局 ChromaDB
    """

def get_embedding_service():
    """获取嵌入服务实例"""

def get_session_manager():
    """获取会话管理器实例"""
```

**说明**:
- Data Layer 已合并到 Context Manager 中
- 统一管理会话、缓存和向量化功能
- 支持会话级别的 ChromaDB 存储

## 🔄 数据流

### 完整研究流程

```
1. 用户请求: "生成关于 AI for science 的研究报告"
   ↓
2. Search Module:
   - search_arxiv_papers("AI for science", max_results=5)
   - search_academic_web("AI for science", max_results=5)
   ↓ 返回论文列表
3. Paper Manager:
   - download_arxiv_paper(arxiv_id) for each paper
   - get_paper_info(paper_id) for each paper
   - get_arxiv_paper_content(arxiv_id) for each paper
   ↓ 返回论文信息和内容
4. Report Generator:
   - analyze_paper_content(arxiv_id, analysis_type="comprehensive") for each paper
   ↓ 返回分析结果
5. Report Generator:
   - generate_research_report(paper_ids, topic)
   - 生成执行摘要（LLM）
   - 生成研究背景（LLM）
   - 生成文献综述（格式化）
   - 生成研究趋势（关键词分析）
   - 生成结论与展望（LLM）
   ↓ 返回完整报告
6. Report Generator:
   - save_report_to_file(report, topic)
   ↓ 返回报告路径
7. 返回给用户:
   {
     status: "success",
     report: "# AI for science - 研究调研报告\n...",
     report_path: "path/to/report.md",
     failed_papers: [...]
   }
```

## 🛠️ 技术栈

### 核心框架
- **FastMCP**: MCP 服务器框架
- **LiteLLM**: 多模型 LLM 接口
- **ChromaDB**: 向量数据库

### 外部 API
- **ArXiv API**: 学术论文搜索
- **Tavily API**: 网页和学术搜索
- **Google Gemini**: LLM 和 Embedding 服务

### 数据处理
- **Pandas**: 数据处理和导出
- **openpyxl**: Excel 文件操作
- **requests**: HTTP 请求

### 日志和监控
- **structlog**: 结构化日志
- **logging**: Python 标准日志

## 📊 性能优化

### 1. 缓存策略

**搜索结果缓存**:
```python
cache_key = f"search:{query}:{source}"
if cache_key in cache:
    return cache[cache_key]
else:
    results = search_api(query)
    cache[cache_key] = results
    return results
```

**论文内容缓存**:
```python
cache_key = f"content:{arxiv_id}"
if cache_key in cache:
    return cache[cache_key]
else:
    content = download_and_parse(arxiv_id)
    cache[cache_key] = content
    return content
```

### 2. 批量处理

**批量分析论文**:
```python
async def batch_analyze_papers(paper_ids: List[str]):
    tasks = [analyze_paper_content(pid) for pid in paper_ids]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. 错误处理

**重试机制**:
```python
@retry(max_attempts=3, delay=1)
def call_api(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
```

**降级策略**:
```python
try:
    results = search_arxiv_papers(query)
except Exception as e:
    logger.warning(f"ArXiv search failed: {e}")
    results = search_academic_web(query)  # 降级到 Tavily
```

## 🔐 安全性

### API 密钥管理
```python
import os
from dotenv import load_dotenv

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
```

### 文件路径验证
```python
def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)
```

### 错误信息脱敏
```python
try:
    result = api_call()
except Exception as e:
    logger.error(f"API call failed: {type(e).__name__}")
    return {"status": "error", "error": "Internal server error"}
```

## 📈 可扩展性

### 添加新的搜索源

1. 在 `modules/search/` 创建新文件（如 `google_scholar.py`）
2. 实现搜索函数
3. 在 `server.py` 注册为工具
4. 更新文档

### 添加新的分析类型

1. 在 `modules/report_generator/prompts.py` 添加新提示词
2. 在 `analysis.py` 添加新分析逻辑
3. 更新 `analyze_paper_content` 函数
4. 更新文档

### 添加新的导出格式

1. 在 `modules/paper_manager/export_tools.py` 添加新函数
2. 在 `server.py` 注册为工具
3. 更新文档

## 📚 参考资料

- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [ArXiv API 文档](https://arxiv.org/help/api)
- [Tavily API 文档](https://tavily.com/docs)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [LiteLLM 文档](https://docs.litellm.ai/)

