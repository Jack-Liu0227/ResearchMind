"""
Prompts for Paper Search and Analysis MCP Server

模块划分：
1. 分类与规划Prompts - 用于请求分类和搜索优化
2. 质量评估Prompts - 用于结果检查
3. 论文分析Prompts - 用于单篇和批量分析（仅基于摘要）
4. 翻译Prompts - 用于摘要翻译
5. 报告生成Prompts - 在reporting.py中定义
"""

from datetime import datetime


def get_current_date():
    """Get current date in a readable format"""
    return datetime.now().strftime("%B %d, %Y")


# Classification Prompts
CLASSIFY_USER_REQUEST_PROMPT = """You are a Request Classification Agent. Classify the following user request:

"{query}"

Categories:
1. **valid** - Specific, clear research requests with defined topics/domains
2. **need-more-info** - Too broad but shows research intent (needs refinement)
3. **general** - Non-research requests (e.g., greetings, general questions)

Respond in JSON format:
{{
    "type": "valid|general|need-more-info",
    "user_intent": "concise description of research goal (only for valid)",
    "next_message": "message to user (only for general or need-more-info)"
}}"""


# Research Planning Prompts
GENERATE_OPTIMIZED_SEARCH_QUERIES_PROMPT = """You are a Search Query Optimization Agent. Your task is to generate the most effective search queries for academic databases (ArXiv, Google Scholar, PubMed, etc.) based on user input.

User Input: "{user_intent}"

Requirements:
1. **Primary Goal**: Generate optimized English search queries that academic databases can understand
2. **Translation**: If input is Chinese, translate to precise English academic terms
3. **Query Optimization**: Use academic keywords, synonyms, and related terms
4. **Multiple Perspectives**: Generate {max_steps} different query approaches
5. **Database Compatibility**: Ensure queries work well with ArXiv, Google Scholar, etc.

Output Format (plain text, NOT JSON):

主查询 (Primary Query): [Most direct and relevant English query]

相关查询1 (Related Query 1): [Alternative perspective or synonyms]
相关查询2 (Related Query 2): [Broader or narrower scope]
相关查询3 (Related Query 3): [Different angle or methodology]

关键词建议 (Keyword Suggestions): [comma-separated academic keywords]

Examples:

Input: "agent材料设计"
主查询: agent-based materials design
相关查询1: multi-agent systems materials science
相关查询2: artificial intelligence materials discovery
相关查询3: computational materials design agents
关键词建议: agent-based modeling, materials informatics, computational materials science, AI-driven design

Input: "machine learning drug discovery"
主查询: machine learning drug discovery
相关查询1: artificial intelligence pharmaceutical research
相关查询2: deep learning molecular design
相关查询3: AI-driven drug development
关键词建议: machine learning, drug discovery, molecular design, pharmaceutical AI, computational drug design

Current date: {current_date}"""

# Legacy prompt for backward compatibility
GENERATE_RESEARCH_PLAN_PROMPT = GENERATE_OPTIMIZED_SEARCH_QUERIES_PROMPT


# Quality Assurance Prompts
DOUBLE_CHECK_RESULTS_PROMPT = """You are a Quality Assurance Agent. Review the search results for relevance and quality.

Original Query: {original_query}

Search Results:
{search_results}

Evaluate:
1. Relevance to original query (0-1 score)
2. Quality of results (completeness, accuracy)
3. Issues found (if any)
4. Recommendations for improvement

The current date is {current_date}.

Respond in JSON format:
{{
    "relevance_score": <float between 0 and 1>,
    "quality_score": <float between 0 and 1>,
    "issues": ["issue1", "issue2"],
    "recommendations": ["recommendation1", "recommendation2"],
    "summary": "brief summary of evaluation"
}}"""


# Reflection Prompts
REFLECT_ON_RESULTS_PROMPT = """You are a research assistant evaluating whether the current search results are sufficient.

Research Question: {question}

Current Search Results: {search_results}

Instructions:
- Identify knowledge gaps or areas that need deeper exploration
- If provided results are sufficient to answer the question, set is_sufficient to true
- If there is a knowledge gap, generate follow-up queries
- Focus on technical details, implementation specifics, or emerging trends not fully covered
- The current date is {current_date}

Respond in JSON format:
{{
    "confidence": <float between 0 and 1>,
    "well_covered": ["aspect1", "aspect2"],
    "missing": ["aspect1", "aspect2"],
    "needs_more_research": <true/false>,
    "suggested_queries": ["query1", "query2"]
}}"""




# ============================================================================
# 旧版本报告生成Prompts - 报告生成现在在 reporting.py 中定义
# ============================================================================

# COMPREHENSIVE_REPORT_PROMPT - 报告生成现在在 reporting.py 中定义


# ============================================================================
# Helper Functions - 分类与规划
# ============================================================================

def format_classify_prompt(query: str) -> str:
    """Format classification prompt with query"""
    return CLASSIFY_USER_REQUEST_PROMPT.format(query=query)


def format_research_plan_prompt(user_intent: str, max_steps: int = 3) -> str:
    """Format research plan prompt with user intent"""
    return GENERATE_RESEARCH_PLAN_PROMPT.format(
        user_intent=user_intent,
        max_steps=max_steps,
        current_date=get_current_date()
    )


def format_double_check_prompt(original_query: str, search_results: str) -> str:
    """Format double check prompt with query and results"""
    return DOUBLE_CHECK_RESULTS_PROMPT.format(
        original_query=original_query,
        search_results=search_results,
        current_date=get_current_date()
    )


def format_reflect_prompt(question: str, search_results: str) -> str:
    """Format reflection prompt with question and results"""
    return REFLECT_ON_RESULTS_PROMPT.format(
        question=question,
        search_results=search_results,
        current_date=get_current_date()
    )


PAPER_SUMMARY_PROMPT_BRIEF = """请快速分析以下论文摘要：

标题: {title}
作者: {authors}
摘要: {abstract}

请简洁地总结（使用中文）：

### 研究目标
[1-2句]

### 方法论
[1-2句]

### 主要结果
[1-2句]

### 创新点
[1-2句]

要求：简洁、清晰、避免冗余"""


def format_paper_summary_prompt_brief(title: str, authors: list, abstract: str) -> str:
    """Format brief paper summary prompt for quick analysis based on abstract only"""
    authors_str = ', '.join(authors) if isinstance(authors, list) else str(authors)
    return PAPER_SUMMARY_PROMPT_BRIEF.format(
        title=title,
        authors=authors_str,
        abstract=abstract
    )


# ============================================================================
# 翻译Prompts
# ============================================================================

TRANSLATE_ABSTRACT_PROMPT = """You are a professional academic translator. Translate the following English abstract to concise Chinese.

Requirements:
- Keep it professional and academic
- Condense to 200-300 Chinese characters
- Focus on key points: background, method, results, innovation
- Use clear and precise language

English Abstract:
{abstract_en}

Return ONLY the Chinese translation (no JSON, no extra text):"""


def format_translate_abstract_prompt(abstract_en: str) -> str:
    """Format translation prompt"""
    return TRANSLATE_ABSTRACT_PROMPT.format(abstract_en=abstract_en)


