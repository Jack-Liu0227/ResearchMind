"""
Export Tools Module (导出工具模块)

功能：
1. 保存论文信息到CSV
2. 保存总结到文件
3. 保存报告到文件
4. 清理CSV中的无效数据
"""
import os
import shutil
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available, CSV export will be disabled")


def read_papers_from_csv(csv_file_path: str) -> List[Dict[str, Any]]:
    """
    从CSV文件读取论文信息

    Args:
        csv_file_path: CSV文件路径(相对路径或绝对路径)

    Returns:
        论文列表,每篇论文包含CSV中的所有字段
    """
    if not PANDAS_AVAILABLE:
        logger.error("pandas not available, cannot read CSV")
        return []

    try:
        import pandas as pd

        # 检查文件是否存在
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV file not found: {csv_file_path}")
            return []

        # 读取CSV文件
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig')

        # 转换为字典列表
        papers = df.to_dict('records')

        # 清理NaN值,转换为None或空字符串
        for paper in papers:
            for key, value in list(paper.items()):
                if pd.isna(value):
                    paper[key] = ''
                # 重命名字段以匹配标准格式
                if key == 'ID':
                    paper['paper_id'] = paper.pop('ID')
                    paper['id'] = paper['paper_id']  # 兼容性
                elif key == 'Title':
                    paper['title'] = paper.pop('Title')
                elif key == 'Authors':
                    authors_str = paper.pop('Authors')
                    # 将CSV中的作者字符串转换为列表
                    if isinstance(authors_str, str) and authors_str.strip():
                        paper['authors'] = [author.strip() for author in authors_str.split(',')]
                    else:
                        paper['authors'] = []
                elif key == 'Abstract':
                    paper['abstract'] = paper.pop('Abstract')
                    paper['summary'] = paper['abstract']  # 兼容性
                elif key == 'URL':
                    paper['url'] = paper.pop('URL')
                elif key == 'PDF_URL':
                    paper['pdf_url'] = paper.pop('PDF_URL')
                elif key == 'Published':
                    paper['published'] = paper.pop('Published')
                    paper['published_date'] = paper['published']  # 兼容性
                elif key == 'Source':
                    paper['source'] = paper.pop('Source')
                elif key == 'Categories':
                    categories_str = paper.pop('Categories')
                    # 将CSV中的分类字符串转换为列表
                    if isinstance(categories_str, str) and categories_str.strip():
                        paper['categories'] = [cat.strip() for cat in categories_str.split(',')]
                    else:
                        paper['categories'] = []
                elif key == 'DOI':
                    paper['doi'] = paper.pop('DOI')
                elif key == 'CitationCount':
                    citation_count = paper.pop('CitationCount')
                    # 转换为整数
                    if citation_count and str(citation_count).strip():
                        try:
                            paper['citation_count'] = int(citation_count)
                        except (ValueError, TypeError):
                            paper['citation_count'] = 0
                    else:
                        paper['citation_count'] = 0
                elif key == 'Score':
                    score = paper.pop('Score')
                    # 转换为浮点数
                    if score and str(score).strip():
                        try:
                            paper['score'] = float(score)
                        except (ValueError, TypeError):
                            paper['score'] = 0.0
                    else:
                        paper['score'] = 0.0
                elif key == 'LocalFile':
                    # 恢复本地文件路径（用于上传文件）
                    local_file = paper.pop('LocalFile')
                    if local_file and isinstance(local_file, str) and local_file.strip():
                        paper['local_file'] = local_file
                        # 同时构建 upload_metadata 以兼容旧代码
                        paper['upload_metadata'] = {
                            'saved_path': local_file,
                            'filename': local_file.split('/')[-1] if '/' in local_file else local_file.split('\\')[-1]
                        }
                elif key == 'FullText':
                    # 恢复完整文本（用于报告生成）
                    full_text = paper.pop('FullText')
                    if full_text and isinstance(full_text, str) and full_text.strip():
                        paper['full_text'] = full_text
                        paper['content'] = full_text  # 同时设置 content 字段以兼容旧代码
                # 兼容旧列名（Published_Date）
                elif key == 'Published_Date':
                    # 如果 published 字段为空，使用 Published_Date
                    if not paper.get('published'):
                        paper['published'] = paper.pop('Published_Date')
                        paper['published_date'] = paper['published']
                    else:
                        paper.pop('Published_Date')  # 删除重复字段

        logger.info(f"Successfully read {len(papers)} papers from CSV: {csv_file_path}")
        return papers

    except Exception as e:
        logger.error(f"Failed to read CSV file {csv_file_path}: {e}")
        return []


def save_summary_to_file(
    summary_result: Dict[str, Any],
    output_path: str = None,
    output_dir: str = None,
    session_id: str = None,
    topic: str = None,
    file_prefix: str = 'summary'
) -> Dict[str, Any]:
    """
    生成批量总结的Markdown内容并保存到文件

    Args:
        summary_result: batch_paper_analysis的返回结果
        output_path: 输出文件路径（可选）
        output_dir: 输出目录（可选）
        session_id: 会话ID（用于确定保存位置）
        topic: 主题（用于确定保存位置）
        file_prefix: 文件名前缀（默认: 'summary'）

    Returns:
        包含Markdown内容和文件路径的字典
    """
    try:
        # 构建Markdown内容
        markdown_lines = []
        markdown_lines.append("# 论文批量分析报告\n\n")
        markdown_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        markdown_lines.append(f"**总论文数**: {summary_result.get('total_papers', 0)}\n")
        markdown_lines.append(f"**成功分析**: {summary_result.get('successful_analyses', 0)}\n")
        markdown_lines.append(f"**失败分析**: {summary_result.get('failed_analyses', 0)}\n\n")
        markdown_lines.append("---\n\n")

        # 添加总的综合分析（如果有）
        if summary_result.get('overall_analysis'):
            markdown_lines.append("## 📊 综合分析\n\n")
            markdown_lines.append(f"{summary_result['overall_analysis']}\n\n")
            markdown_lines.append("---\n\n")
        elif summary_result.get('results') and len(summary_result['results']) > 0:
            # 如果没有提供overall_analysis，生成一个简单的总结
            markdown_lines.append("## 📊 综合分析\n\n")

            # 统计研究方法
            methods = set()
            innovations = []
            for result in summary_result['results']:
                key_info = result.get('key_info', {})
                if key_info.get('method'):
                    methods.add(key_info['method'][:50])  # 取前50字符
                if key_info.get('innovation'):
                    innovations.append(key_info['innovation'][:100])  # 取前100字符

            markdown_lines.append("### 主要研究方法\n\n")
            if methods:
                for method in list(methods)[:5]:  # 最多显示5个
                    markdown_lines.append(f"- {method}\n")
            else:
                markdown_lines.append("- 暂无提取\n")
            markdown_lines.append("\n")

            markdown_lines.append("### 主要创新点\n\n")
            if innovations:
                for innovation in innovations[:5]:  # 最多显示5个
                    markdown_lines.append(f"- {innovation}\n")
            else:
                markdown_lines.append("- 暂无提取\n")
            markdown_lines.append("\n")

            markdown_lines.append("---\n\n")

        # 写入每篇论文的详细分析
        markdown_lines.append("## 📄 详细文献分析\n\n")

        if summary_result.get('results'):
            for i, result in enumerate(summary_result['results'], 1):
                markdown_lines.append(f"### {i}. {result.get('title', '未知标题')}\n\n")

                # 基本信息
                authors = result.get('authors', [])
                if isinstance(authors, list):
                    authors_str = ', '.join(str(a) for a in authors)
                else:
                    authors_str = str(authors)

                markdown_lines.append(f"**论文ID**: {result.get('paper_id', '未知')}\n\n")
                markdown_lines.append(f"**作者**: {authors_str}\n\n")
                markdown_lines.append(f"**发表时间**: {result.get('published', '未知')}\n\n")

                # URL
                url = result.get('url', '') or result.get('pdf_url', '')
                if url:
                    markdown_lines.append(f"**链接**: {url}\n\n")

                # 中文摘要
                markdown_lines.append(f"**中文摘要**: {result.get('abstract_zh', '暂无')}\n\n")

                # 关键信息
                key_info = result.get('key_info', {})
                markdown_lines.append("#### 关键信息\n\n")
                markdown_lines.append(f"**研究目标**: {key_info.get('objective', '未提取')}\n\n")
                markdown_lines.append(f"**研究方法**: {key_info.get('method', '未提取')}\n\n")
                markdown_lines.append(f"**主要结果**: {key_info.get('result', '未提取')}\n\n")
                markdown_lines.append(f"**创新点**: {key_info.get('innovation', '未提取')}\n\n")

                markdown_lines.append("---\n\n")

        # 写入失败的论文
        if summary_result.get('failures'):
            markdown_lines.append("## ⚠️ 分析失败的论文\n\n")
            for failure in summary_result['failures']:
                markdown_lines.append(f"- {failure.get('id', '未知')}: {failure.get('error', '未知错误')}\n")

        # 合并所有行
        markdown_content = ''.join(markdown_lines)

        # 保存到文件
        saved_file_path = None
        if session_id or output_dir:
            try:
                from ..shared.session_folder_manager import get_session_folder

                # 确定保存目录
                if session_id and topic:
                    save_dir = get_session_folder(session_id, topic)
                elif output_dir:
                    save_dir = output_dir
                else:
                    save_dir = os.path.join(os.getcwd(), 'papers')

                # 确保目录存在
                os.makedirs(save_dir, exist_ok=True)

                # 确定文件路径
                if output_path:
                    saved_file_path = output_path
                else:
                    # 检查 file_prefix 是否已经包含时间戳（格式：YYYYMMDD_HHMMSS）
                    import re
                    if re.search(r'\d{8}_\d{6}$', file_prefix):
                        # 已包含时间戳，直接使用
                        saved_file_path = os.path.join(save_dir, f'{file_prefix}.md')
                    else:
                        # 未包含时间戳，添加时间戳
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        saved_file_path = os.path.join(save_dir, f'{file_prefix}_{timestamp}.md')

                # 保存文件
                with open(saved_file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

                logger.info(f"成功保存总结到文件: {saved_file_path}")
            except Exception as e:
                logger.error(f"保存总结文件失败: {e}")

        logger.info(f"成功生成总结Markdown内容")

        return {
            'status': 'success',
            'markdown_content': markdown_content,
            'total_papers': summary_result.get('total_papers', 0),
            'file_path': saved_file_path,
            'message': f'成功生成总结Markdown内容' + (f'，已保存到 {saved_file_path}' if saved_file_path else '')
        }

    except Exception as e:
        logger.error(f"生成总结失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def save_report_to_file(
    report_result: Dict[str, Any],
    output_path: str = None,
    output_dir: str = None,
    session_id: str = None,
    topic: str = None,
    file_prefix: str = 'report'
) -> Dict[str, Any]:
    """
    生成研究报告的Markdown内容并保存到文件

    Args:
        report_result: generate_research_report的返回结果
        output_path: 输出文件路径（可选）
        output_dir: 输出目录（可选）
        session_id: 会话ID（用于确定保存位置）
        topic: 主题（用于确定保存位置）
        file_prefix: 文件名前缀（默认: 'report'）

    Returns:
        包含Markdown内容和文件路径的字典
    """
    try:
        # 提取报告内容
        report_content = report_result.get('report', '')

        # 如果是字典格式，转换为Markdown
        if isinstance(report_content, dict):
            markdown_lines = []
            markdown_lines.append("# 研究报告\n\n")
            markdown_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            markdown_lines.append("---\n\n")

            for section, content in report_content.items():
                markdown_lines.append(f"## {section}\n\n")
                markdown_lines.append(f"{content}\n\n")

            markdown_content = ''.join(markdown_lines)
        else:
            # 直接使用文本内容
            markdown_content = report_content

        # 保存到文件
        saved_file_path = None
        if session_id or output_dir:
            try:
                from ..shared.session_folder_manager import get_session_folder, PAPER_DIR

                # 确定保存目录
                if session_id and topic:
                    save_dir = get_session_folder(session_id, topic)
                elif output_dir:
                    save_dir = output_dir
                else:
                    # 使用 MCP server 的 papers 目录作为后备
                    save_dir = PAPER_DIR

                # 确保目录存在
                os.makedirs(save_dir, exist_ok=True)

                # 确定文件路径
                if output_path:
                    saved_file_path = output_path
                else:
                    # 检查 file_prefix 是否已经包含时间戳（格式：YYYYMMDD_HHMMSS）
                    import re
                    if re.search(r'\d{8}_\d{6}$', file_prefix):
                        # 已包含时间戳，直接使用
                        saved_file_path = os.path.join(save_dir, f'{file_prefix}.md')
                    else:
                        # 未包含时间戳，添加时间戳
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        saved_file_path = os.path.join(save_dir, f'{file_prefix}_{timestamp}.md')

                # 保存文件
                with open(saved_file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

                logger.info(f"成功保存报告到文件: {saved_file_path}")
            except Exception as e:
                logger.error(f"保存报告文件失败: {e}")

        logger.info(f"成功生成报告Markdown内容")

        return {
            'status': 'success',
            'markdown_content': markdown_content,
            'topic': report_result.get('topic', 'research'),
            'file_path': saved_file_path,
            'message': f'成功生成报告Markdown内容' + (f'，已保存到 {saved_file_path}' if saved_file_path else '')
        }

    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def save_papers_to_csv(
    papers: List[Dict[str, Any]],
    output_path: str = None,
    output_dir: str = None,
    session_id: str = None,
    topic: str = None,
    file_prefix: str = 'papers',
    append_mode: bool = True
) -> Dict[str, Any]:
    """
    生成论文信息的CSV内容并保存到文件（支持追加模式）

    Args:
        papers: 论文列表，每篇论文包含：
            - id/arxiv_id/paper_id: 论文ID
            - title: 标题
            - authors: 作者列表
            - abstract/summary: 摘要
            - pdf_url/url: 下载链接
            - published: 发表时间
            - source: 来源
            - categories: 分类（可选）
            - score: 相关性评分（可选）
            - full_text: 完整文本（可选，用于报告生成）
        output_path: 输出文件路径（可选）
        output_dir: 输出目录（可选）
        session_id: 会话ID（用于确定保存位置）
        topic: 主题（用于确定保存位置）
        file_prefix: 文件名前缀（默认: 'papers'，可以是 'summary_papers', 'report_papers' 等）
        append_mode: 是否启用追加模式（默认: True）
                    - True: 合并到现有 CSV 文件，去重后保存
                    - False: 创建新的带时间戳的 CSV 文件

    Returns:
        包含CSV数据和文件路径的字典
    """
    if not PANDAS_AVAILABLE:
        return {
            'status': 'error',
            'error': 'pandas not installed, cannot export to CSV'
        }

    try:
        # 准备数据
        data = []
        for paper in papers:
            # 提取ID
            paper_id = (
                paper.get('id') or
                paper.get('arxiv_id') or
                paper.get('paper_id') or
                paper.get('title', '')[:50]
            )

            # 提取作者
            authors = paper.get('authors', [])
            if isinstance(authors, list):
                authors_str = ', '.join(str(a) for a in authors)
            else:
                authors_str = str(authors)

            # 提取摘要并清理换行符
            abstract = (
                paper.get('abstract') or
                paper.get('summary') or
                paper.get('content', '')
            )
            # 清理换行符和多余空格,避免CSV格式问题
            if abstract:
                abstract = ' '.join(abstract.split())

            # 提取下载链接
            download_url = (
                paper.get('pdf_url') or
                paper.get('url') or
                paper.get('link', '')
            )

            # 提取分类
            categories = paper.get('categories', [])
            if isinstance(categories, list):
                categories_str = ', '.join(str(c) for c in categories)
            else:
                categories_str = str(categories)

            # 清理标题中的换行符
            title = paper.get('title', 'Unknown Title')
            if title:
                title = ' '.join(title.split())

            # 提取本地文件路径（用于上传文件）
            local_file = ''
            if paper.get('source') == 'upload':
                # 优先从 upload_metadata 中获取
                upload_metadata = paper.get('upload_metadata', {})
                local_file = upload_metadata.get('saved_path', '') or paper.get('local_file', '')

            # 提取完整文本（用于报告生成）
            full_text = paper.get('full_text', '') or paper.get('content', '')
            # 清理换行符和多余空格
            if full_text:
                full_text = ' '.join(full_text.split())

            # 提取 PDF URL（与 URL 分开）
            pdf_url = paper.get('pdf_url', '')

            # 提取 DOI
            doi = paper.get('doi', '')

            # 提取引用次数（保留数字类型，避免空字符串）
            citation_count = paper.get('citation_count')
            if citation_count is None or citation_count == '':
                citation_count = ''  # 空值用空字符串表示
            else:
                citation_count = int(citation_count) if citation_count else ''

            # 合并 Published 和 Published_Date（优先使用 published）
            published = paper.get('published', '') or paper.get('published_date', '')

            # 构建行数据
            row = {
                'ID': paper_id,
                'Title': title,
                'Authors': authors_str,
                'Abstract': abstract,
                'URL': download_url,
                'PDF_URL': pdf_url,  # 新增：PDF 下载链接
                'Published': published,  # 合并后的发表日期
                'Source': paper.get('source', 'unknown'),
                'Categories': categories_str,
                'DOI': doi,  # 新增：DOI 标识符
                'CitationCount': citation_count,  # 新增：引用次数
                'FullText': full_text,  # 完整文本（用于报告生成）
                'LocalFile': local_file,  # 本地文件路径（用于上传文件）
            }

            # 添加可选字段
            if 'score' in paper:
                row['Score'] = paper.get('score', '')

            data.append(row)

        # 创建DataFrame
        df = pd.DataFrame(data)

        # 去除所有值都为空的行（排除列名）
        # 将空字符串、None、NaN都视为空值
        df = df.replace('', pd.NA).dropna(how='all')

        # 清理无效行（在保存前）
        logger.info(f"清理前共 {len(df)} 行数据")
        df_cleaned = df[~df.apply(is_invalid_paper_row, axis=1)]
        invalid_count = len(df) - len(df_cleaned)
        if invalid_count > 0:
            logger.info(f"清理了 {invalid_count} 个无效行")
        df = df_cleaned

        # 转换为CSV字符串
        csv_content = df.to_csv(index=False, encoding='utf-8-sig')

        # 保存到文件
        saved_file_path = None
        papers_added = len(papers)
        total_papers = len(papers)

        if session_id or output_dir:
            try:
                from ..shared.session_folder_manager import get_session_folder, PAPER_DIR

                # 确定保存目录
                if session_id and topic:
                    save_dir = get_session_folder(session_id, topic)
                elif output_dir:
                    save_dir = output_dir
                else:
                    # 使用 MCP server 的 papers 目录作为后备
                    save_dir = PAPER_DIR

                # 确保目录存在
                os.makedirs(save_dir, exist_ok=True)

                # 确定文件路径
                if output_path:
                    saved_file_path = output_path
                else:
                    # 追加模式：使用固定文件名 all_papers.csv
                    # 非追加模式：使用带时间戳的文件名
                    if append_mode:
                        saved_file_path = os.path.join(save_dir, 'all_papers.csv')
                    else:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        saved_file_path = os.path.join(save_dir, f'{file_prefix}_{timestamp}.csv')

                # 追加模式：合并现有数据
                if append_mode and os.path.exists(saved_file_path):
                    logger.info(f"追加模式：读取现有CSV文件: {saved_file_path}")
                    try:
                        # 读取现有CSV
                        existing_df = pd.read_csv(saved_file_path, encoding='utf-8-sig')
                        logger.info(f"现有CSV包含 {len(existing_df)} 篇论文")

                        # 合并新旧数据
                        combined_df = pd.concat([existing_df, df], ignore_index=True)

                        # 去重：基于 ID 列，保留最后出现的（最新的）
                        if 'ID' in combined_df.columns:
                            before_dedup = len(combined_df)
                            combined_df = combined_df.drop_duplicates(subset=['ID'], keep='last')
                            after_dedup = len(combined_df)
                            duplicates_removed = before_dedup - after_dedup
                            logger.info(f"去重：移除 {duplicates_removed} 篇重复论文")

                        # 清理无效行（在合并后）
                        before_clean = len(combined_df)
                        combined_df_cleaned = combined_df[~combined_df.apply(is_invalid_paper_row, axis=1)]
                        invalid_removed = before_clean - len(combined_df_cleaned)
                        if invalid_removed > 0:
                            logger.info(f"清理：移除 {invalid_removed} 个无效行")
                        combined_df = combined_df_cleaned

                        # 更新统计信息
                        total_papers = len(combined_df)
                        papers_added = total_papers - len(existing_df) + duplicates_removed

                        # 使用合并后的数据
                        df = combined_df
                        csv_content = df.to_csv(index=False, encoding='utf-8-sig')

                        logger.info(f"合并后共 {total_papers} 篇论文（新增 {papers_added} 篇）")
                    except Exception as e:
                        logger.warning(f"读取现有CSV失败，将创建新文件: {e}")

                # 保存文件
                with open(saved_file_path, 'w', encoding='utf-8-sig') as f:
                    f.write(csv_content)

                logger.info(f"成功保存CSV到文件: {saved_file_path}")
            except Exception as e:
                logger.error(f"保存CSV文件失败: {e}")

        logger.info(f"成功生成 {len(papers)} 篇论文的CSV数据")

        # 构建返回消息
        if append_mode and papers_added < len(papers):
            message = f'已追加 {papers_added} 篇论文到 CSV，当前共 {total_papers} 篇'
        else:
            message = f'成功生成 {total_papers} 篇论文的CSV数据'

        if saved_file_path:
            message += f'，已保存到 {saved_file_path}'

        return {
            'status': 'success',
            'total_papers': total_papers,
            'papers_added': papers_added,
            'csv_content': csv_content,
            'columns': list(df.columns),
            'file_path': saved_file_path,
            'message': message
        }

    except Exception as e:
        logger.error(f"生成CSV数据失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def save_analysis_results_to_csv(
    analysis_results: List[Dict[str, Any]],
    output_path: str = None,
    output_dir: str = None,
    session_id: str = None,
    topic: str = None,
    file_prefix: str = 'analysis_results',
    append_mode: bool = True
) -> Dict[str, Any]:
    """
    保存论文分析结果到CSV文件（支持追加模式和去重）

    Args:
        analysis_results: 分析结果列表,每个结果包含:
            - paper_id: 论文ID
            - title: 标题
            - authors: 作者列表
            - abstract_zh: 中文摘要
            - key_info: 关键信息(objective, method, result, innovation)
            - analysis_text: 完整分析文本
        output_path: 输出文件路径(可选)
        output_dir: 输出目录(可选)
        session_id: 会话ID
        topic: 主题
        file_prefix: 文件名前缀(默认: 'analysis_results')
        append_mode: 是否启用追加模式（默认: True）
                    - True: 合并到现有 CSV 文件，基于ID和URL去重后保存
                    - False: 创建新的带时间戳的 CSV 文件

    Returns:
        包含CSV数据和文件路径的字典
    """
    if not PANDAS_AVAILABLE:
        return {
            'status': 'error',
            'error': 'pandas not installed, cannot export to CSV'
        }

    try:
        import pandas as pd

        if not analysis_results:
            return {
                'status': 'error',
                'error': 'No analysis results provided'
            }

        # 构建CSV数据
        data = []
        for result in analysis_results:
            # 跳过错误的结果
            if result.get('status') == 'error':
                continue

            # 提取作者
            authors = result.get('authors', [])
            if isinstance(authors, list):
                authors_str = ', '.join(str(a) for a in authors)
            else:
                authors_str = str(authors)

            # 提取关键信息
            key_info = result.get('key_info', {})

            # 清理中文摘要中的换行符
            abstract_zh = result.get('abstract_zh', '')
            if abstract_zh:
                abstract_zh = ' '.join(abstract_zh.split())

            # 清理标题中的换行符
            title = result.get('title', 'Unknown Title')
            if title:
                title = ' '.join(title.split())

            # 构建行数据
            # 获取URL,优先使用url,其次使用pdf_url
            url = result.get('url', '') or result.get('pdf_url', '')
            if not url:
                # 如果都没有,尝试从arxiv_id构造
                arxiv_id = result.get('paper_id', '') or result.get('id', '')
                if arxiv_id and 'arxiv' in result.get('source', '').lower():
                    url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"

            row = {
                'ID': result.get('paper_id', 'unknown'),
                'Title': title,
                'Authors': authors_str,
                'Source': result.get('source', 'unknown'),
                'URL': url or 'N/A',
                'Abstract_ZH': abstract_zh,
                'Objective': key_info.get('objective', 'N/A'),
                'Method': key_info.get('method', 'N/A'),
                'Result': key_info.get('result', 'N/A'),
                'Innovation': key_info.get('innovation', 'N/A'),
            }

            data.append(row)

        if not data:
            return {
                'status': 'error',
                'error': 'No valid analysis results to export'
            }

        # 创建DataFrame
        df = pd.DataFrame(data)

        # 去除所有值都为空的行（排除列名）
        # 将空字符串、None、NaN都视为空值
        df = df.replace('', pd.NA).dropna(how='all')

        # 转换为CSV字符串
        csv_content = df.to_csv(index=False, encoding='utf-8-sig')

        # 保存到文件
        saved_file_path = None
        papers_added = len(data)
        total_papers = len(data)

        if session_id or output_dir:
            try:
                from ..shared.session_folder_manager import get_session_folder, PAPER_DIR

                # 确定保存目录
                if session_id and topic:
                    save_dir = get_session_folder(session_id, topic)
                elif output_dir:
                    save_dir = output_dir
                else:
                    # 使用 MCP server 的 papers 目录作为后备
                    save_dir = PAPER_DIR

                # 确保目录存在
                os.makedirs(save_dir, exist_ok=True)

                # 确定文件路径
                if output_path:
                    saved_file_path = output_path
                else:
                    # 检查 file_prefix 是否已经包含时间戳（格式：YYYYMMDD_HHMMSS）
                    import re
                    has_timestamp = re.search(r'\d{8}_\d{6}$', file_prefix)

                    if has_timestamp:
                        # file_prefix 已包含时间戳，直接使用（无论 append_mode 是什么）
                        saved_file_path = os.path.join(save_dir, f'{file_prefix}.csv')
                    elif append_mode:
                        # 追加模式且无时间戳：使用固定文件名
                        # analysis_results -> analysis_results.csv
                        # report_papers -> report_papers.csv
                        saved_file_path = os.path.join(save_dir, f'{file_prefix}.csv')
                    else:
                        # 非追加模式且无时间戳：添加时间戳
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        saved_file_path = os.path.join(save_dir, f'{file_prefix}_{timestamp}.csv')

                # 追加模式：合并现有数据并去重
                if append_mode and os.path.exists(saved_file_path):
                    logger.info(f"追加模式：读取现有分析结果CSV文件: {saved_file_path}")
                    try:
                        # 读取现有CSV
                        existing_df = pd.read_csv(saved_file_path, encoding='utf-8-sig')
                        logger.info(f"现有CSV包含 {len(existing_df)} 条分析结果")

                        # 合并新旧数据
                        combined_df = pd.concat([existing_df, df], ignore_index=True)

                        # 去重：基于 ID 和 URL 列，保留最后出现的（最新的）
                        before_dedup = len(combined_df)

                        # 先基于ID去重
                        if 'ID' in combined_df.columns:
                            combined_df = combined_df.drop_duplicates(subset=['ID'], keep='last')

                        # 再基于URL去重（处理ID不同但URL相同的情况）
                        if 'URL' in combined_df.columns:
                            # 过滤掉URL为空或N/A的行后再去重
                            url_mask = (combined_df['URL'].notna()) & (combined_df['URL'] != '') & (combined_df['URL'] != 'N/A')
                            url_duplicates = combined_df[url_mask].duplicated(subset=['URL'], keep='last')
                            combined_df = combined_df[~url_duplicates | ~url_mask]

                        after_dedup = len(combined_df)
                        duplicates_removed = before_dedup - after_dedup
                        logger.info(f"去重：移除 {duplicates_removed} 条重复分析结果")

                        # 更新统计信息
                        total_papers = len(combined_df)
                        papers_added = total_papers - len(existing_df) + duplicates_removed

                        # 使用合并后的数据
                        df = combined_df
                        csv_content = df.to_csv(index=False, encoding='utf-8-sig')

                        logger.info(f"合并后共 {total_papers} 条分析结果（新增 {papers_added} 条）")
                    except Exception as e:
                        logger.warning(f"读取现有CSV失败，将创建新文件: {e}")

                # 保存文件
                with open(saved_file_path, 'w', encoding='utf-8-sig') as f:
                    f.write(csv_content)

                logger.info(f"成功保存分析结果CSV到文件: {saved_file_path}")
            except Exception as e:
                logger.error(f"保存分析结果CSV文件失败: {e}")

        logger.info(f"成功生成 {len(data)} 条分析结果的CSV数据")

        # 构建返回消息
        if append_mode and papers_added < len(data):
            message = f'已追加 {papers_added} 条分析结果到 CSV，当前共 {total_papers} 条'
        else:
            message = f'成功生成 {total_papers} 条分析结果的CSV数据'

        if saved_file_path:
            message += f'，已保存到 {saved_file_path}'

        return {
            'status': 'success',
            'total_results': total_papers,
            'papers_added': papers_added,
            'csv_content': csv_content,
            'columns': list(df.columns),
            'file_path': saved_file_path,
            'message': message
        }

    except Exception as e:
        logger.error(f"生成分析结果CSV数据失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


# ============================================================================
# CSV 数据清理功能
# ============================================================================

def is_invalid_paper_row(row: pd.Series) -> bool:
    """
    判断论文行是否无效

    无效行的定义：
    1. ID 包含 'unknown'
    2. Title 是 'Unknown Title' 且 Abstract 为空
    3. Source 是 'unknown' 且其他关键字段为空
    4. 所有关键字段都为空

    Args:
        row: DataFrame 的一行

    Returns:
        True 如果是无效行，False 否则
    """
    # 检查 ID 是否包含 unknown
    if pd.notna(row.get('ID')) and 'unknown' in str(row['ID']).lower():
        return True

    # 检查 Title 是否是 Unknown Title 且 Abstract 为空
    title = str(row.get('Title', '')).strip()
    abstract = str(row.get('Abstract', '')).strip()
    if title == 'Unknown Title' and (pd.isna(row.get('Abstract')) or not abstract):
        return True

    # 检查 Source 是否是 unknown 且 Abstract 为空
    source = str(row.get('Source', '')).strip()
    if source == 'unknown' and (pd.isna(row.get('Abstract')) or not abstract):
        return True

    # 检查所有关键字段是否都为空
    key_fields = ['ID', 'Title', 'Authors', 'Abstract', 'URL']
    all_empty = all(
        pd.isna(row.get(field)) or str(row.get(field, '')).strip() == ''
        for field in key_fields
    )
    if all_empty:
        return True

    return False


def clean_csv_file(
    csv_path: str,
    backup: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    清理 CSV 文件中的无效行

    Args:
        csv_path: CSV 文件路径
        backup: 是否备份原文件（默认 True）
        dry_run: 是否只检查不修改（默认 False）

    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - original_count: 原始行数
        - valid_count: 有效行数
        - invalid_count: 无效行数
        - invalid_rows: 无效行的详细信息
        - backup_path: 备份文件路径（如果创建了备份）
        - message: 消息
    """
    if not PANDAS_AVAILABLE:
        return {
            'status': 'error',
            'error': 'pandas not available'
        }

    try:
        # 检查文件是否存在
        if not os.path.exists(csv_path):
            return {
                'status': 'error',
                'error': f'CSV file not found: {csv_path}'
            }

        # 读取 CSV
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        original_count = len(df)

        # 查找无效行
        invalid_mask = df.apply(is_invalid_paper_row, axis=1)
        invalid_df = df[invalid_mask]
        valid_df = df[~invalid_mask]

        invalid_count = len(invalid_df)
        valid_count = len(valid_df)

        # 收集无效行信息
        invalid_rows = []
        for idx, row in invalid_df.iterrows():
            invalid_rows.append({
                'row_number': int(idx) + 2,  # +2 因为 CSV 有表头且索引从0开始
                'ID': str(row.get('ID', '')),
                'Title': str(row.get('Title', ''))[:50],
                'Source': str(row.get('Source', '')),
                'Abstract': str(row.get('Abstract', ''))[:50] if pd.notna(row.get('Abstract')) else ''
            })

        result = {
            'status': 'success',
            'original_count': original_count,
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'invalid_rows': invalid_rows,
            'csv_path': csv_path
        }

        # 如果是 dry_run，只返回检查结果
        if dry_run:
            result['message'] = f'检查完成：发现 {invalid_count} 个无效行（未修改文件）'
            return result

        # 如果没有无效行，直接返回
        if invalid_count == 0:
            result['message'] = '没有发现无效行'
            return result

        # 备份原文件
        if backup:
            backup_path = csv_path + '.backup'
            shutil.copy2(csv_path, backup_path)
            result['backup_path'] = backup_path
            logger.info(f"已备份 CSV 文件到: {backup_path}")

        # 保存清理后的数据
        valid_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

        result['message'] = f'清理完成：移除 {invalid_count} 个无效行，保留 {valid_count} 个有效行'
        logger.info(f"清理 CSV 文件: {csv_path}, 移除 {invalid_count} 个无效行")

        return result

    except Exception as e:
        logger.error(f"清理 CSV 文件失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def clean_all_csv_files(
    session_dir: str = None,
    backup: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    清理指定目录或所有会话目录中的 CSV 文件

    Args:
        session_dir: 会话目录路径（如果为 None，清理所有会话）
        backup: 是否备份原文件
        dry_run: 是否只检查不修改

    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - cleaned_files: 清理的文件列表
        - total_invalid: 总共移除的无效行数
        - results: 每个文件的清理结果
    """
    from pathlib import Path
    from ..shared.session_folder_manager import PAPER_DIR

    try:
        # 确定要清理的目录
        if session_dir:
            search_dirs = [Path(session_dir)]
        else:
            search_dirs = [Path(PAPER_DIR)]

        # 查找所有 CSV 文件
        csv_files = []
        for search_dir in search_dirs:
            if search_dir.exists():
                csv_files.extend(search_dir.glob('*/all_papers.csv'))

        if not csv_files:
            return {
                'status': 'success',
                'cleaned_files': [],
                'total_invalid': 0,
                'message': '没有找到 CSV 文件'
            }

        # 清理每个文件
        results = []
        total_invalid = 0
        cleaned_files = []

        for csv_path in csv_files:
            result = clean_csv_file(str(csv_path), backup=backup, dry_run=dry_run)
            results.append(result)

            if result['status'] == 'success' and result['invalid_count'] > 0:
                total_invalid += result['invalid_count']
                cleaned_files.append(str(csv_path))

        return {
            'status': 'success',
            'cleaned_files': cleaned_files,
            'total_invalid': total_invalid,
            'total_files': len(csv_files),
            'results': results,
            'message': f'清理完成：处理 {len(csv_files)} 个文件，移除 {total_invalid} 个无效行'
        }

    except Exception as e:
        logger.error(f"批量清理 CSV 文件失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

