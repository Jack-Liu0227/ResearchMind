"""
Report Generator Agent Tools (报告生成代理工具)

包含所有报告生成相关的工具：
- 报告生成
- 报告保存
"""
from .reporting import (
    generate_research_report,
    generate_research_report_with_data_collection,
)

from ..paper_manager.export_tools import (
    save_report_to_file,
)

__all__ = [
    # 报告生成
    'generate_research_report',
    'generate_research_report_with_data_collection',
    
    # 报告保存
    'save_report_to_file',
]

