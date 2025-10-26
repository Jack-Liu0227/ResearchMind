"""
Deep Research Agent prompts (plain text, minimal formatting)
"""

from datetime import datetime


def get_current_date() -> str:
    """Return current date in a readable format."""
    return datetime.now().strftime("%B %d, %Y")


def get_current_datetime() -> dict:
    """Return current date and time components without special formatting."""
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "weekday": now.strftime("%A"),
        "formatted": now.strftime("%Y-%m-%d %H:%M:%S %A"),
    }


# Plain Chinese instruction without Markdown formatting for direct frontend display
DEEP_RESEARCH_INSTRUCTION = (
    "您是学术文献研究助手，使用中文简洁回复。当前时间：{current_date}（{current_year}年）。"
    "按需调用工具，检索前调用 generate_research_plan 规划。"
    "分三级：快速检索、摘要分析、全文报告。"
    "输出只返回简短文本和直链，不使用加粗、表格或代码块。"
    "步骤："
    "1 规划：generate_research_plan(user_intent)，只取第一个查询。"
    "2 快速检索：search_papers(query, expand_query=True, num_expanded_queries=3, max_results=2)。工具自动保存CSV，回复仅附 csv_download_url。"
    "3 摘要分析（按需）：batch_paper_analysis(csv_file_path=...)，自动保存MD和CSV，回复附 md_download_url 与 csv_download_url。"
    "4 全文报告（按需）：generate_research_report(topic, csv_file_path=...)，自动保存MD和CSV，回复附 md_download_url 与 csv_download_url。"
    "5 上传附件：ingest_uploaded_papers(files=[{filename, content, encoding}], session_id?, topic?)，返回规范化列表与 csv_download_url，可用于后续步骤。"
    "6 向量化与语义搜索（按需）：ingest_papers_to_vector_store(...)；semantic_search_papers(query, top_k, collection_name)。"
    "约束：对话中 search_papers 只调用一次；Level2/Level3 必须使用 Level1 产生的 csv_file_path 自动推导 session_id。"
    "文件路径统一：所有结果存储在 papers/<session_id>/ 下，前端直接展示。"
)


def get_deep_research_instruction() -> str:
    """Return the instruction string with current date inserted, plain text."""
    now = datetime.now()
    return (
        DEEP_RESEARCH_INSTRUCTION
        .replace("{current_date}", now.strftime("%Y-%m-%d"))
        .replace("{current_year}", str(now.year))
    )

