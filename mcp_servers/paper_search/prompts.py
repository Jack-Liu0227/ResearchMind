"""
Prompts for Paper Search MCP Server
All prompts are centralized here for easy management and modification.
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
# 旧版本报告生成Prompts已废弃
# 现在使用 COMPREHENSIVE_REPORT_PROMPT 和 reporting.py 中的自定义prompt
# ============================================================================


# Helper Functions
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


# 旧版本helper函数已删除（对应的prompts已废弃）
# format_extract_paper_prompt, format_aggregate_prompt, format_final_report_prompt


# ============================================================================
# 优化的调研报告生成提示词
# ============================================================================

COMPREHENSIVE_REPORT_PROMPT = """你是一位资深的学术研究员。请基于以下文献信息，生成一份专业的研究调研报告。

研究主题: {topic}

文献信息:
{papers_info}

请按照以下结构生成报告（使用中文）：

## 1. 研究概述 (200-300字)
- 研究领域的重要性和背景
- 当前研究的主要挑战
- 本次调研的文献范围

## 2. 核心发现
针对每篇重要文献，总结：
- 研究目标
- 主要方法
- 关键结果
- 创新点

## 3. 技术路线分析
- 主流技术方法对比
- 各方法的优缺点
- 技术演进趋势

## 4. 研究热点与趋势
- 当前研究热点
- 未来发展方向
- 潜在突破点

## 5. 研究空白与机会
- 现有研究的局限性
- 尚未解决的问题
- 可能的研究方向

## 6. 总结与建议
- 主要结论
- 对研究者的建议
- 未来展望

要求：
- 使用专业学术语言
- 逻辑清晰，层次分明
- 突出重点，避免冗余
- 客观中立，有理有据
"""


PAPER_SUMMARY_PROMPT = """请对以下论文进行深度分析和总结：

标题: {title}
作者: {authors}
摘要: {abstract}
全文摘录: {content_excerpt}

请提供：
1. **核心贡献** (1-2句话)
2. **研究方法** (简要说明)
3. **主要结果** (关键发现)
4. **创新点** (与现有工作的区别)
5. **局限性** (如果有)

要求简洁专业，每部分不超过100字。"""


MULTI_PAPER_COMPARISON_PROMPT = """请对以下多篇论文进行对比分析：

{papers_summary}

请分析：
1. **共同点**: 这些研究有哪些共同的方法或结论？
2. **差异点**: 各研究的独特之处是什么？
3. **互补性**: 这些研究如何相互补充？
4. **演进趋势**: 从时间顺序看，研究有何演进？

要求：
- 客观对比，不偏不倚
- 突出关键差异
- 总结发展脉络
"""


RESEARCH_GAP_ANALYSIS_PROMPT = """基于以下文献综述，分析研究空白和机会：

文献总结:
{literature_summary}

请分析：
1. **已解决的问题**: 现有研究已经很好解决的问题
2. **部分解决的问题**: 有研究但仍有改进空间的问题
3. **未解决的问题**: 明显的研究空白
4. **新兴机会**: 可能的创新方向

要求：
- 基于文献事实
- 指出具体问题
- 提供可行建议
"""


def format_comprehensive_report_prompt(topic: str, papers_info: list) -> str:
    """Format comprehensive report prompt"""
    papers_text = []
    for i, paper in enumerate(papers_info, 1):
        # 优先使用全文，否则使用摘要
        full_text = paper.get('full_text', '')
        abstract = paper.get('abstract', 'N/A')

        # 如果有全文，使用全文的前3000字符
        if full_text and len(full_text) > 100:
            content_preview = full_text[:3000] + "..." if len(full_text) > 3000 else full_text
            content_type = "全文"
        else:
            content_preview = abstract[:500] + "..." if len(abstract) > 500 else abstract
            content_type = "摘要"

        paper_text = f"""
### 文献 {i}
- 标题: {paper.get('title', 'Unknown')}
- 作者: {', '.join(paper.get('authors', []))}
- 发表时间: {paper.get('published', 'Unknown')}
- URL: {paper.get('url', 'N/A')}
- 内容类型: {content_type}
- 内容: {content_preview}
"""
        papers_text.append(paper_text)

    return COMPREHENSIVE_REPORT_PROMPT.format(
        topic=topic,
        papers_info='\n'.join(papers_text)
    )


def format_paper_summary_prompt(title: str, authors: list, abstract: str, content_excerpt: str = "") -> str:
    """Format paper summary prompt"""
    authors_str = ', '.join(authors) if isinstance(authors, list) else str(authors)
    return PAPER_SUMMARY_PROMPT.format(
        title=title,
        authors=authors_str,
        abstract=abstract,
        content_excerpt=content_excerpt[:2000] if content_excerpt else "Not available"
    )


def format_multi_paper_comparison_prompt(papers_summary: list) -> str:
    """Format multi-paper comparison prompt"""
    summary_text = '\n\n'.join(f"**论文 {i+1}**:\n{s}" for i, s in enumerate(papers_summary))
    return MULTI_PAPER_COMPARISON_PROMPT.format(papers_summary=summary_text)


def format_research_gap_analysis_prompt(literature_summary: str) -> str:
    """Format research gap analysis prompt"""
    return RESEARCH_GAP_ANALYSIS_PROMPT.format(literature_summary=literature_summary)


# ============================================================================
# 文献深度分析提示词 (Deep Analysis Prompts)
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


# ============================================================================
# 未使用的Prompts已删除
# DEEP_ANALYSIS_PROMPT - 未使用（reporting.py使用自定义prompt）
# EXTRACT_KEY_INFO_PROMPT - 未使用（analysis.py使用PAPER_SUMMARY_PROMPT）
# ============================================================================


# ============================================================================
# 报告模板搜索提示词 (Report Template Search Prompts)
# ============================================================================

SEARCH_REPORT_TEMPLATE_PROMPT = """Search for high-quality research report templates for the topic: "{topic}"

Search queries to use:
1. "academic research report template {topic}"
2. "scientific literature review template {topic}"
3. "IEEE research report format {topic}"
4. "research survey paper structure {topic}"

Focus on finding:
- Standard academic report structures
- Section organization best practices
- Citation and reference formats
- Visual presentation guidelines

Return the search query that would be most effective."""


ANALYZE_REPORT_TEMPLATE_PROMPT = """Analyze the following report template/structure and extract key sections.

Template Content:
{template_content}

Extract:
1. Main sections and their order
2. Recommended content for each section
3. Formatting guidelines
4. Citation style

Return in JSON format:
{{
    "sections": [
        {{"name": "...", "description": "...", "order": 1}},
        ...
    ],
    "formatting_guidelines": "...",
    "citation_style": "..."
}}"""


GENERATE_REPORT_WITH_TEMPLATE_PROMPT = """Generate a comprehensive research report based on the following template and papers.

Topic: {topic}
Template Structure: {template_structure}

Papers Summary:
{papers_summary}

Generate a complete report following the template structure. Include:
- All sections from the template
- Proper citations in IEEE format
- Professional academic language
- Clear organization and flow

Return the complete report in Markdown format."""


# ============================================================================
# 多源文献汇总提示词 (Multi-Source Literature Aggregation)
# ============================================================================

AGGREGATE_MULTI_SOURCE_PAPERS_PROMPT = """Aggregate and analyze papers from multiple sources.

Papers from different sources:
{papers_data}

Analyze:
1. **Coverage**: How well do these papers cover the topic?
2. **Quality**: Assess the quality and relevance of each source
3. **Overlap**: Identify duplicate or highly similar papers
4. **Gaps**: What aspects are missing or under-represented?
5. **Recommendations**: Which papers are most valuable?

Return in JSON format:
{{
    "coverage_score": <0-1>,
    "quality_assessment": {{"arxiv": "...", "tavily": "...", ...}},
    "duplicates": ["paper_id1", "paper_id2", ...],
    "gaps": ["gap1", "gap2", ...],
    "top_papers": ["paper_id1", "paper_id2", ...]
}}"""


# ============================================================================
# Helper Functions for New Prompts
# ============================================================================

def format_translate_abstract_prompt(abstract_en: str) -> str:
    """Format translation prompt"""
    return TRANSLATE_ABSTRACT_PROMPT.format(abstract_en=abstract_en)


# 未使用的helper函数已删除
# format_deep_analysis_prompt - 未使用
# format_extract_key_info_prompt - 未使用


def format_search_report_template_prompt(topic: str) -> str:
    """Format report template search prompt"""
    return SEARCH_REPORT_TEMPLATE_PROMPT.format(topic=topic)


def format_analyze_report_template_prompt(template_content: str) -> str:
    """Format report template analysis prompt"""
    return ANALYZE_REPORT_TEMPLATE_PROMPT.format(template_content=template_content)


def format_generate_report_with_template_prompt(topic: str, template_structure: str, papers_summary: str) -> str:
    """Format report generation with template prompt"""
    return GENERATE_REPORT_WITH_TEMPLATE_PROMPT.format(
        topic=topic,
        template_structure=template_structure,
        papers_summary=papers_summary
    )


def format_aggregate_multi_source_prompt(papers_data: str) -> str:
    """Format multi-source aggregation prompt"""
    return AGGREGATE_MULTI_SOURCE_PAPERS_PROMPT.format(papers_data=papers_data)

