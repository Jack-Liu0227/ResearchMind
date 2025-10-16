# Deep Research Agent 架构文档

## 📐 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│                        Deep Research Agent                           │
│                        (主协调代理)                                  │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  - 接收用户请求                                              │   │
│  │  - 分析任务类型                                              │   │
│  │  - 委派给子代理                                              │   │
│  │  - 协调子代理工作                                            │   │
│  │  - 整合结果返回用户                                          │   │
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
│   Agent      │    │   Manager    │    │  Generator   │    │   Manager    │
│              │    │              │    │              │    │              │
│  (搜索代理)  │    │  (论文管理)  │    │  (报告生成)  │    │  (上下文管理)│
│              │    │              │    │              │    │              │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │                   │
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                    │
                                    ▼
                        ┌──────────────────────┐
                        │                      │
                        │  MCP Paper Search    │
                        │  (论文搜索服务)      │
                        │                      │
                        │  - ArXiv API         │
                        │  - Tavily API        │
                        │  - Vector Store      │
                        │  - Embedding Service │
                        │                      │
                        └──────────────────────┘
```

## 🏛️ 核心组件

### 1. Deep Research Agent (主协调代理)

**文件**: `agents/deep_research/agent.py`

**职责**:
- 作为系统的入口点，接收用户请求
- 分析用户意图，确定需要调用哪些子代理
- 协调多个子代理的工作流程
- 整合子代理的结果，返回给用户

**核心方法**:
```python
class DeepResearchAgent(BaseAgent):
    def __init__(self):
        # 初始化子代理
        self.search_agent = SearchAgent()
        self.paper_manager_agent = PaperManagerAgent()
        self.report_generator_agent = ReportGeneratorAgent()
        self.context_manager_agent = ContextManagerAgent()
        
        # 将子代理注册为工具
        self.tools = [
            AgentTool(self.search_agent),
            AgentTool(self.paper_manager_agent),
            AgentTool(self.report_generator_agent),
            AgentTool(self.context_manager_agent)
        ]
    
    async def _run_async_impl(self, context):
        # 执行主代理逻辑
        async for event in self.main_agent.run_async(context):
            yield event
```

**关键特性**:
- 使用 `AgentTool` 包装子代理，使其可以被主代理调用
- 支持错误处理和重试机制
- 提供时间上下文（当前日期时间）

### 2. Search Agent (搜索代理)

**文件**: `agents/deep_research/search/agent.py`

**职责**:
- **只负责检索论文信息**
- 不做任何分析、下载、总结等操作
- 返回论文列表（标题、作者、摘要、链接等）

**当前支持的检索来源**:
- ✅ **ArXiv**: 物理、数学、计算机科学等领域的预印本论文
- ✅ **Tavily Academic**: 学术网页搜索
- ✅ **Google Scholar**: 学术文献搜索

**计划支持的检索来源**:
- 🔜 **CNKI**: 中国知网
- 🔜 **PubMed**: 生物医学文献
- 🔜 **IEEE Xplore**: 电气电子工程文献
- 🔜 **Semantic Scholar**: AI 驱动的学术搜索
- 🔜 **Web of Science**: 综合学术数据库
- 🔜 **Scopus**: 综合学术数据库

**工具** (7个):
```python
tools = [
    'generate_research_plan',           # 优化搜索词（必须先调用）
    'search_arxiv_papers',              # ArXiv 主题搜索
    'search_papers_by_author',          # ArXiv 作者搜索
    'get_paper_info',                   # 获取论文详情
    'tavily_academic_search',           # Tavily 学术搜索
    'tavily_search',                    # Tavily 网页搜索
    'tavily_news_search',               # Tavily 新闻搜索
]
```

**搜索策略**:
1. **优化搜索词**: 必须先调用 `generate_research_plan` 优化搜索词
2. **多源搜索**: 默认使用 ArXiv + Tavily + Scholar
3. **结果合并**: 合并多个源的结果并去重

**工作流程**:
```
用户查询 → 优化搜索词 → 多源搜索 → 合并去重 → 返回论文列表
```

### 3. Paper Manager Agent (论文管理代理)

**文件**: `agents/deep_research/paper_manager/agent.py`

**职责**:
- 获取论文全文内容
- 生成中文摘要和总结
- 管理论文（可以保存文献到本地）
- **返回总结内容，不保存总结文件**

**工具**:
```python
tools = [
    'download_paper',              # 下载 PDF 到本地
    'get_arxiv_paper_content',     # 提取 ArXiv 论文全文
    'analyze_paper_content',       # 单篇论文分析
    'batch_paper_analysis',        # 批量分析论文
]
```

**工作流程**:
```
接收论文列表 → 获取全文 → 批量分析 → 返回总结内容
```

### 4. Report Generator Agent (报告生成代理)

**文件**: `agents/deep_research/report_generator/agent.py`

**职责**:
- 根据论文总结和全文信息生成研究报告
- 支持 IEEE/Nature/ArXiv 格式
- **返回报告内容，不保存报告文件**

**工具**:
```python
tools = [
    'generate_research_report'  # 生成研究报告
]
```

**报告结构（IEEE 格式）**:
```markdown
# {主题} - 研究调研报告

## Executive Summary（执行摘要）
[综合所有论文的核心内容]

## Background（背景介绍）
[基于论文标题和摘要生成]

## Current Status（研究现状）
[当前研究状态]

## Existing Methods（现有方法）
[现有研究方法]

## Detailed Analysis（详细分析）
[详细分析每篇论文]

## Open Problems（开放问题）
[未解决的问题]

## Potential Solutions（潜在解决方案）
[可能的解决方案]

## Future Outlook（未来展望）
[未来研究方向]

## References（参考文献）
[IEEE 格式引用]
```

**工作流程**:
```
接收论文总结 → 生成报告 → 返回报告内容
```

### 5. Context Manager Agent (向量化和语义搜索代理)

**文件**: `agents/deep_research/context_manager/agent.py`

**职责**:
- 将论文内容向量化存储到 ChromaDB
- 基于向量相似度进行语义搜索
- 提供 Embedding 功能
- 缓存管理

**工具**:
```python
tools = [
    'ingest_papers_to_vector_store',  # 向量化存储论文
    'semantic_search_papers',         # 语义搜索论文
    'get_cache_stats',                # 获取缓存统计
    'cleanup_expired_cache'           # 清理过期缓存
]
```

**向量化存储**:
- 使用 ChromaDB 向量数据库
- Embedding 模型使用默认配置
- 支持多个集合（collection）管理不同主题的论文

**工作流程**:
```
接收论文列表 → 提取内容 → 向量化 → 存储到 ChromaDB → 返回结果
```

## 🗂️ 会话文件夹管理

### 设计目标

**问题**: 之前每次操作都创建新的 UUID 文件夹，导致同一会话的内容分散在多个文件夹中。

**解决方案**: 使用会话级别的文件夹管理，确保一次对话只使用一个文件夹。

### 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Session Folder Manager (会话文件夹管理器)                            │
│                                                                       │
│ 核心功能:                                                             │
│ 1. 维护 session_id → folder_path 映射                               │
│ 2. 持久化映射到 session_folders.json                                │
│ 3. 自动创建会话文件夹                                                 │
│ 4. 生成会话元数据                                                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Search       │    │ Paper        │    │ Report       │
│ Module       │    │ Manager      │    │ Generator    │
│              │    │              │    │              │
│ 使用会话文件夹│    │ 使用会话文件夹│    │ 使用会话文件夹│
└──────────────┘    └──────────────┘    └──────────────┘
```

### 文件夹命名策略

```python
# 有主题
{topic}_{session_id[:8]}
例如: ai_for_science_c0eaa665

# 无主题
session_{timestamp}_{session_id[:8]}
例如: session_20251006_030000_c0eaa665
```

### 会话映射持久化

**文件**: `./paper_search/session_folders.json`

```json
{
  "c0eaa665-b2d0-4cb5-9649-4ee68b508f24": "./paper_search/papers/ai_for_science_c0eaa665",
  "d1f2e3a4-c5b6-7d8e-9f0a-1b2c3d4e5f6g": "./paper_search/papers/llm_for_alloys_d1f2e3a4"
}
```

### 会话元数据

**文件**: `{session_folder}/session_metadata.json`

```json
{
  "session_id": "c0eaa665-b2d0-4cb5-9649-4ee68b508f24",
  "topic": "AI for science",
  "created_at": "2025-10-06T03:00:00",
  "folder_path": "./paper_search/papers/ai_for_science_c0eaa665"
}
```

### 文件夹结构

```
paper_search/papers/
└── ai_for_science_c0eaa665/        # 会话文件夹
    ├── session_metadata.json       # 会话元数据
    ├── papers_info.json            # 论文信息
    ├── papers.xlsx                 # Excel 导出
    ├── research_report.md          # 研究报告
    ├── summary.md                  # 摘要
    ├── chroma_db/                  # ChromaDB 向量数据库（会话级别）
    │   ├── chroma.sqlite3          # ChromaDB 数据库文件
    │   └── ...                     # 其他 ChromaDB 文件
    └── downloads/                  # 下载的 PDF
        ├── 2410.13768v1.pdf
        └── 2407.10022v1.pdf
```

### ChromaDB 会话级别存储

**设计目标**: 每个会话使用独立的 ChromaDB 实例，避免冲突

**实现方式**:
```python
# ChromaVectorStore 初始化
def __init__(self, persist_directory: str = "./chroma_db", session_id: Optional[str] = None):
    if session_id:
        # 使用会话文件夹
        session_folder = get_session_folder(session_id)
        self.persist_directory = Path(session_folder) / "chroma_db"
    else:
        # 使用全局目录
        self.persist_directory = Path(persist_directory)
```

**优势**:
- ✅ 避免不同会话之间的冲突
- ✅ 易于清理和归档
- ✅ 支持会话恢复
- ✅ 向后兼容（无 session_id 时使用全局存储）

## 🔄 数据流

### 搜索流程

```
┌─────────────────────────────────────────────────────────────────────┐
│ 用户: "搜索 LLM for alloys"                                          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 主代理 (Deep Research Agent)                                         │
│                                                                       │
│ 1. 接收用户请求                                                       │
│ 2. 分析任务类型: 搜索任务                                             │
│ 3. 选择子代理: Search Agent                                          │
│ 4. 构建调用参数: {query: "LLM for alloys", max_results: 5}          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Search Agent (搜索代理)                                              │
│                                                                       │
│ 1. 分析查询类型: 学术论文搜索                                         │
│ 2. 选择搜索策略: 双源搜索 (ArXiv + Tavily)                           │
│ 3. 并行调用搜索工具:                                                  │
│    ├─ search_arxiv_papers("LLM for alloys", max_results=5)          │
│    └─ search_academic_web("LLM for alloys", max_results=5)          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────┐                    ┌──────────────────┐
│ ArXiv API        │                    │ Tavily API       │
│                  │                    │                  │
│ 返回:            │                    │ 返回:            │
│ [                │                    │ [                │
│   {              │                    │   {              │
│     title: "..." │                    │     title: "..." │
│     authors: []  │                    │     url: "..."   │
│     arxiv_id: "" │                    │     content: ""  │
│     source: "arxiv"                   │     source: "tavily"
│   },             │                    │   },             │
│   ...            │                    │   ...            │
│ ]                │                    │ ]                │
└──────────────────┘                    └──────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Search Agent (搜索代理)                                              │
│                                                                       │
│ 4. 合并结果                                                           │
│ 5. 去重                                                               │
│ 6. 标准化格式                                                         │
│ 7. 按相关性排序                                                       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 返回给主代理:                                                         │
│ [                                                                     │
│   {title: "Rapid and Automated Alloy Design...",                    │
│    authors: ["Author 1", "Author 2"],                               │
│    arxiv_id: "2410.13768v1",                                        │
│    source: "arxiv"},                                                 │
│   {title: "LLM Applications in Materials Science",                  │
│    url: "https://...",                                              │
│    source: "tavily"},                                               │
│   ...                                                                │
│ ]                                                                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 主代理 (Deep Research Agent)                                         │
│                                                                       │
│ 5. 接收搜索结果                                                       │
│ 6. 格式化输出                                                         │
│ 7. 返回给用户                                                         │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 用户收到结果:                                                         │
│ "找到 10 篇相关论文 (5 篇来自 ArXiv, 5 篇来自 Tavily)"               │
│ [论文列表...]                                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 报告生成流程

```
┌─────────────────────────────────────────────────────────────────────┐
│ 用户: "生成关于 AI for science 的研究报告"                           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 主代理 (Deep Research Agent)                                         │
│                                                                       │
│ 1. 接收用户请求                                                       │
│ 2. 分析任务类型: 报告生成任务                                         │
│ 3. 规划执行步骤:                                                      │
│    ├─ 步骤1: 搜索论文 (Search Agent)                                 │
│    ├─ 步骤2: 下载和管理论文 (Paper Manager)                          │
│    └─ 步骤3: 生成报告 (Report Generator)                             │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 步骤1: Search Agent (搜索代理)                                       │
│                                                                       │
│ 1. 搜索 "AI for science" 相关论文                                    │
│ 2. 使用 ArXiv + Tavily 双源搜索                                      │
│ 3. 返回论文列表                                                       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 返回: 论文ID列表                                                      │
│ [                                                                     │
│   "2411.12761v1",  # AI-Empowered Human Research                    │
│   "2212.06352v1",  # Seamless Management of AI Models               │
│   "2401.11839v1",  # AI for social science                          │
│   ...                                                                │
│ ]                                                                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 步骤2: Paper Manager (论文管理代理)                                  │
│                                                                       │
│ 对每篇论文执行:                                                       │
│ 1. download_arxiv_paper(arxiv_id)                                   │
│    → 下载 PDF 到会话文件夹                                           │
│                                                                       │
│ 2. get_paper_info(paper_id)                                         │
│    → 获取论文元数据 (标题、作者、摘要等)                             │
│                                                                       │
│ 3. get_arxiv_paper_content(arxiv_id)                                │
│    → 提取论文全文内容                                                 │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 返回: 论文信息和内容                                                  │
│ {                                                                     │
│   papers_info: [                                                     │
│     {title: "...", authors: [...], published: "...", ...},          │
│     ...                                                              │
│   ],                                                                 │
│   papers_content: [                                                  │
│     "Full text of paper 1...",                                      │
│     "Full text of paper 2...",                                      │
│     ...                                                              │
│   ]                                                                  │
│ }                                                                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 步骤3: Report Generator (报告生成代理)                               │
│                                                                       │
│ 3.1 分析每篇论文                                                      │
│     analyze_paper_content(arxiv_id, analysis_type="comprehensive")  │
│     → 提取: 摘要、关键词、研究目标、方法、结果、创新点               │
│                                                                       │
│ 3.2 生成报告各部分 (使用 LLM)                                        │
│     ├─ 执行摘要: 综合所有论文的核心内容                              │
│     ├─ 研究背景: 基于论文标题和摘要生成                              │
│     ├─ 文献综述: 格式化每篇论文的详细信息                            │
│     ├─ 研究趋势: 基于关键词频率分析                                  │
│     └─ 结论与展望: 综合分析和未来方向                                │
│                                                                       │
│ 3.3 整合成完整报告                                                    │
│     - 添加标题和元数据                                                │
│     - 组合所有部分                                                    │
│     - 添加参考文献                                                    │
│     - 添加失败论文列表 (如果有)                                       │
│                                                                       │
│ 3.4 保存报告                                                          │
│     save_report_to_file(report, topic, session_id)                  │
│     → 保存到会话文件夹: ai_for_science_c0eaa665/research_report.md  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 返回给主代理:                                                         │
│ {                                                                     │
│   status: "success",                                                 │
│   report: "# AI for science - 研究调研报告\n\n...",                  │
│   report_path: "./paper_search/papers/ai_for_science_c0eaa665/...", │
│   total_papers: 5,                                                   │
│   valid_papers: 5,                                                   │
│   failed_papers: []                                                  │
│ }                                                                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 主代理 (Deep Research Agent)                                         │
│                                                                       │
│ 4. 接收报告结果                                                       │
│ 5. 格式化输出                                                         │
│ 6. 返回给用户                                                         │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 用户收到结果:                                                         │
│ "研究报告已生成！"                                                    │
│ "报告路径: ./paper_search/papers/ai_for_science_c0eaa665/..."       │
│ "共分析 5 篇论文"                                                     │
│ [显示报告内容...]                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

### 核心框架
- **Google ADK**: Agent Development Kit
- **LiteLLM**: 多模型 LLM 接口
- **FastMCP**: MCP 服务器框架

### 数据存储
- **ChromaDB**: 向量数据库
- **JSON**: 会话和缓存存储

### API 服务
- **ArXiv API**: 学术论文搜索
- **Tavily API**: 网页和学术搜索
- **Google Gemini**: LLM 服务

## 📊 性能优化

### 1. 缓存机制

**搜索缓存**:
- 缓存搜索结果 24 小时
- 避免重复搜索相同内容
- 使用 LRU 策略管理缓存大小

**论文内容缓存**:
- 缓存已下载的论文内容
- 避免重复下载和解析

### 2. 并发处理

**并行搜索**:
```python
# 同时调用多个搜索源
results = await asyncio.gather(
    search_arxiv_papers(query),
    search_academic_web(query)
)
```

**批量处理**:
```python
# 批量分析论文
for paper_id in paper_ids:
    analysis = await analyze_paper_content(paper_id)
    papers_analysis.append(analysis)
```

### 3. 错误处理

**重试机制**:
- API 调用失败时自动重试
- 最多重试 3 次

**降级策略**:
- 如果某个源失败，使用其他源
- 如果论文无法下载，继续处理其他论文

## 🔐 安全性

### API 密钥管理
- 使用环境变量存储 API 密钥
- 不在代码中硬编码密钥

### 数据隐私
- 本地存储论文和报告
- 不上传用户数据到外部服务

### 错误信息
- 不在错误信息中暴露敏感信息
- 记录详细日志用于调试

## 📈 可扩展性

### 添加新的搜索源

1. 在 MCP Paper Search 中添加新的搜索工具
2. 在 Search Agent 的提示词中添加新工具说明
3. 更新搜索策略

### 添加新的分析功能

1. 在 MCP Paper Search 中添加新的分析工具
2. 在 Report Generator 中调用新工具
3. 更新报告模板

### 添加新的子代理

1. 创建新的子代理类
2. 在主代理中注册新子代理
3. 更新主代理提示词

## 🐛 调试

### 日志级别

```python
import structlog

logger = structlog.get_logger()
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### 常见问题

**Q: 子代理没有被调用？**
A: 检查是否使用 `AgentTool` 包装并注册到主代理

**Q: 报告生成失败？**
A: 检查论文内容是否成功获取，查看失败论文列表

**Q: 搜索结果为空？**
A: 检查 API 密钥配置，查看网络连接

## 📚 参考资料

- [Google ADK 文档](https://github.com/google/adk)
- [LiteLLM 文档](https://docs.litellm.ai/)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [ArXiv API 文档](https://arxiv.org/help/api)
- [Tavily API 文档](https://tavily.com/docs)

