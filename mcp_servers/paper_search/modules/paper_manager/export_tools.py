"""
Export Tools Module (导出工具模块)

功能：
1. 保存论文信息到CSV
2. 保存总结到文件
3. 保存报告到文件
"""
import os
from typing import Dict, Any, List
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
                elif key == 'URL':
                    paper['url'] = paper.pop('URL')
                elif key == 'Published':
                    paper['published'] = paper.pop('Published')
                elif key == 'Source':
                    paper['source'] = paper.pop('Source')
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
    file_prefix: str = 'papers'
) -> Dict[str, Any]:
    """
    生成论文信息的CSV内容并保存到文件

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
        output_path: 输出文件路径（可选）
        output_dir: 输出目录（可选）
        session_id: 会话ID（用于确定保存位置）
        topic: 主题（用于确定保存位置）
        file_prefix: 文件名前缀（默认: 'papers'，可以是 'summary_papers', 'report_papers' 等）

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

            # 构建行数据
            row = {
                'ID': paper_id,
                'Title': title,
                'Authors': authors_str,
                'Abstract': abstract,
                'URL': download_url,
                'Published': paper.get('published', ''),
                'Source': paper.get('source', 'unknown'),
                'Categories': categories_str,
                'LocalFile': local_file,  # 新增：本地文件路径（用于上传文件）
            }

            # 添加可选字段
            if 'score' in paper:
                row['Score'] = paper.get('score', '')
            if 'published_date' in paper:
                row['Published_Date'] = paper.get('published_date', '')

            data.append(row)

        # 创建DataFrame
        df = pd.DataFrame(data)

        # 去除所有值都为空的行（排除列名）
        # 将空字符串、None、NaN都视为空值
        df = df.replace('', pd.NA).dropna(how='all')

        # 转换为CSV字符串
        csv_content = df.to_csv(index=False, encoding='utf-8-sig')

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
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    saved_file_path = os.path.join(save_dir, f'{file_prefix}_{timestamp}.csv')

                # 保存文件
                with open(saved_file_path, 'w', encoding='utf-8-sig') as f:
                    f.write(csv_content)

                logger.info(f"成功保存CSV到文件: {saved_file_path}")
            except Exception as e:
                logger.error(f"保存CSV文件失败: {e}")

        logger.info(f"成功生成 {len(papers)} 篇论文的CSV数据")

        return {
            'status': 'success',
            'total_papers': len(papers),
            'csv_content': csv_content,
            'columns': list(df.columns),
            'file_path': saved_file_path,
            'message': f'成功生成 {len(papers)} 篇论文的CSV数据' + (f'，已保存到 {saved_file_path}' if saved_file_path else '')
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
    file_prefix: str = 'analysis_results'
) -> Dict[str, Any]:
    """
    保存论文分析结果到CSV文件

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
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    saved_file_path = os.path.join(save_dir, f'{file_prefix}_{timestamp}.csv')

                # 保存文件
                with open(saved_file_path, 'w', encoding='utf-8-sig') as f:
                    f.write(csv_content)

                logger.info(f"成功保存分析结果CSV到文件: {saved_file_path}")
            except Exception as e:
                logger.error(f"保存分析结果CSV文件失败: {e}")

        logger.info(f"成功生成 {len(data)} 条分析结果的CSV数据")

        return {
            'status': 'success',
            'total_results': len(data),
            'csv_content': csv_content,
            'columns': list(df.columns),
            'file_path': saved_file_path,
            'message': f'成功生成 {len(data)} 条分析结果的CSV数据' + (f'，已保存到 {saved_file_path}' if saved_file_path else '')
        }

    except Exception as e:
        logger.error(f"生成分析结果CSV数据失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def save_report_papers_to_csv(
    papers: List[Dict[str, Any]],
    output_path: str = None,
    output_dir: str = None,
    session_id: str = None,
    topic: str = None,
    file_prefix: str = 'report_papers'
) -> Dict[str, Any]:
    """
    保存报告中引用的论文信息到CSV文件（专门用于研究报告）

    Args:
        papers: 论文列表,每篇论文包含:
            - paper_id: 论文ID
            - title: 标题
            - authors: 作者列表
            - abstract: 摘要
            - published: 发表时间
            - source: 来源
            - url: URL
        output_path: 输出文件路径(可选)
        output_dir: 输出目录(可选)
        session_id: 会话ID
        topic: 主题
        file_prefix: 文件名前缀(默认: 'report_papers')

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

        if not papers:
            return {
                'status': 'error',
                'error': 'No papers provided'
            }

        # 构建CSV数据
        data = []
        for i, paper in enumerate(papers, 1):
            # 提取作者
            authors = paper.get('authors', [])
            if isinstance(authors, list):
                authors_str = ', '.join(str(a) for a in authors)
            else:
                authors_str = str(authors)

            # 清理摘要中的换行符
            abstract = paper.get('abstract', '')
            if abstract:
                abstract = ' '.join(abstract.split())

            # 清理标题中的换行符
            title = paper.get('title', 'Unknown Title')
            if title:
                title = ' '.join(title.split())

            # 提取发表年份
            published = paper.get('published', 'Unknown')
            year = published[:4] if published and len(published) >= 4 else 'Unknown'

            # 获取URL,优先使用url,其次使用pdf_url
            url = paper.get('url', '') or paper.get('pdf_url', '')

            # 构建行数据
            row = {
                'No.': i,
                'ID': paper.get('paper_id', 'unknown'),
                'Title': title,
                'Authors': authors_str,
                'Year': year,
                'Source': paper.get('source', 'unknown'),
                'URL': url or '',
                'Abstract': abstract,
            }

            data.append(row)

        # 创建DataFrame
        df = pd.DataFrame(data)

        # 去除所有值都为空的行（排除列名）
        # 将空字符串、None、NaN都视为空值
        df = df.replace('', pd.NA).dropna(how='all')

        # 转换为CSV字符串
        csv_content = df.to_csv(index=False, encoding='utf-8-sig')

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
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    saved_file_path = os.path.join(save_dir, f'{file_prefix}_{timestamp}.csv')

                # 保存文件
                with open(saved_file_path, 'w', encoding='utf-8-sig') as f:
                    f.write(csv_content)

                logger.info(f"成功保存报告论文CSV到文件: {saved_file_path}")
            except Exception as e:
                logger.error(f"保存报告论文CSV文件失败: {e}")

        logger.info(f"成功生成 {len(data)} 篇报告论文的CSV数据")

        return {
            'status': 'success',
            'total_papers': len(data),
            'csv_content': csv_content,
            'columns': list(df.columns),
            'file_path': saved_file_path,
            'message': f'成功生成 {len(data)} 篇报告论文的CSV数据' + (f'，已保存到 {saved_file_path}' if saved_file_path else '')
        }

    except Exception as e:
        logger.error(f"生成报告论文CSV数据失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

