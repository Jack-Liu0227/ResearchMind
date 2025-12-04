"""
Paper Analysis Module (论文分析模块)

核心功能：
1. 单篇论文分析 - 基于摘要提取关键信息
2. 中文摘要翻译 - 将英文摘要凝练翻译成中文
3. 批量分析 - 并发处理多篇论文（仅使用摘要）
4. 引用标注 - 在分析结果中标注信息来源

注意：本模块专注于摘要分析，不处理报告生成
"""
from typing import Dict, Any, List
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


def format_paper_citation_info(paper: Dict[str, Any], index: int = None) -> str:
    """
    为单篇论文生成引用信息标注

    Args:
        paper: 论文信息字典
        index: 文献编号（可选）

    Returns:
        引用信息字符串
    """
    authors = paper.get('authors', [])
    if isinstance(authors, list):
        if len(authors) > 3:
            author_str = ', '.join(authors[:3]) + ', et al.'
        elif len(authors) > 0:
            author_str = ', '.join(authors)
        else:
            author_str = 'Unknown'
    else:
        author_str = str(authors) if authors else 'Unknown'

    year = paper.get('published', '')[:4] if paper.get('published') else 'Unknown'
    title = paper.get('title', 'Unknown')

    if index:
        return f"[{index}] {author_str} ({year}). {title}"
    else:
        return f"{author_str} ({year}). {title}"


async def analyze_paper_content(
    paper: Dict[str, Any],
    content: str = None
) -> Dict[str, Any]:
    """
    基于摘要分析单篇论文 - 异步版本

    提取关键信息：
    - 研究目标
    - 主要方法  
    - 关键结果
    - 创新点

    Args:
        paper: 论文信息字典（包含title, authors, abstract等）
        content: 全文内容（可选，不使用）

    Returns:
        Dict containing:
        - paper_id: 论文ID
        - title: 标题
        - objective: 研究目标
        - method: 主要方法
        - result: 关键结果
        - innovation: 创新点
        - abstract_zh: 中文摘要
    """
    try:
        from litellm import completion
        import os
        import asyncio
        from pathlib import Path
        import sys

        # 导入prompts模块 - 从paper_search目录导入
        prompts_path = str(Path(__file__).parent.parent.parent)
        if prompts_path not in sys.path:
            sys.path.insert(0, prompts_path)
        
        from prompts import format_paper_summary_prompt_brief

        paper_id = paper.get('paper_id', 'unknown')
        title = paper.get('title', 'Unknown')
        authors = paper.get('authors', [])
        abstract = paper.get('abstract', '')
        source = paper.get('source', 'unknown')

        # 使用LLM分析摘要
        model = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')
        api_key = os.getenv('OPENAI_API_KEY')
        api_base = os.getenv('OPENAI_BASE_URL')

        prompt = format_paper_summary_prompt_brief(
            title=title,
            authors=authors,
            abstract=abstract
        )

        # 重试机制
        max_retries = 3
        retry_delay = 3

        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: completion(
                            model=model,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3,
                            timeout=60,
                            api_key=api_key,
                            api_base=api_base
                        )
                    ),
                    timeout=70
                )
                break

            except (asyncio.TimeoutError, Exception) as e:
                error_type = type(e).__name__
                logger.warning(
                    f'Attempt {attempt + 1}/{max_retries} failed for paper {paper_id}',
                    error_type=error_type,
                    error_message=str(e)[:100]
                )

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    error_msg = f'Failed after {max_retries} attempts: {error_type}'
                    logger.error(f'Analysis failed for {paper_id}', error=error_msg)
                    raise Exception(error_msg)

        analysis_text = response.choices[0].message.content.strip()

        # 解析分析结果
        key_info = _parse_analysis_text(analysis_text)

        # 翻译摘要
        abstract_zh = await _condense_abstract_to_chinese_async(abstract) if abstract else ""

        # 生成引用信息
        citation_info = format_paper_citation_info(paper)

        result = {
            'paper_id': paper_id,
            'title': title,
            'authors': authors,
            'url': paper.get('url') or paper.get('pdf_url') or '',
            'source': source,
            'abstract_zh': abstract_zh,
            'key_info': key_info,
            'citation_info': citation_info,  # 添加引用信息
            'data_source': '基于论文摘要分析',  # 标注数据来源
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f'Completed analysis for paper {paper_id}')
        return result

    except Exception as e:
        logger.error(f'Analysis failed for {paper.get("paper_id", "unknown")}: {str(e)}')
        return {
            'paper_id': paper.get('paper_id', 'unknown'),
            'title': paper.get('title', 'Unknown'),
            'status': 'error',
            'error': str(e),
            'key_info': {
                'objective': 'N/A',
                'method': 'N/A',
                'result': 'N/A',
                'innovation': 'N/A'
            }
        }


def _parse_analysis_text(analysis_text: str) -> Dict[str, str]:
    """
    解析LLM返回的分析文本，提取关键信息
    
    格式：
    - 研究目标
    - 方法论  
    - 主要结果
    - 创新点
    """
    key_info = {
        'objective': '',
        'method': '',
        'result': '',
        'innovation': ''
    }

    lines = analysis_text.split('\n')
    current_key = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测标题
        if '研究目标' in line or '目标' in line:
            current_key = 'objective'
        elif '方法' in line or '方法论' in line:
            current_key = 'method'
        elif '结果' in line or '发现' in line:
            current_key = 'result'
        elif '创新' in line or '贡献' in line:
            current_key = 'innovation'
        elif current_key and line and not line.startswith('**') and not line.startswith('###'):
            # 累积内容
            if key_info[current_key]:
                key_info[current_key] += ' ' + line
            else:
                key_info[current_key] = line

    # 如果解析失败，使用整个文本作为创新点
    if not any(key_info.values()):
        key_info['innovation'] = analysis_text

    return key_info


async def batch_paper_analysis(
    papers: List[Dict] = None
) -> Dict[str, Any]:
    """
    批量分析多篇论文 - 异步并发版本

    仅使用摘要进行快速分析，不处理报告生成

    Args:
        papers: 论文列表

    Returns:
        包含批量分析结果的字典
    """
    try:
        import asyncio

        if not papers:
            return {
                'status': 'error',
                'error': 'No papers provided',
                'total_papers': 0,
                'successful_analyses': 0,
                'failed_analyses': 0
            }

        logger.info(f'开始批量分析 {len(papers)} 篇论文')

        # 创建所有分析任务
        tasks = []
        for paper in papers:
            tasks.append(analyze_paper_content(paper, None))

        # 并发执行所有任务
        analysis_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        results = []
        failed_papers = []

        for i, analysis_result in enumerate(analysis_results):
            paper = papers[i]
            paper_id = paper.get('paper_id', 'unknown')

            # 检查是否是异常
            if isinstance(analysis_result, Exception):
                error_msg = str(analysis_result)
                failed_papers.append({
                    'id': paper_id,
                    'title': paper.get('title', 'Unknown'),
                    'error': error_msg
                })
                logger.error(
                    'Paper analysis failed',
                    paper_id=paper_id,
                    error_type=type(analysis_result).__name__,
                    error_message=error_msg[:100]
                )
            elif analysis_result.get('status') == 'error':
                error_msg = analysis_result.get('error', 'Unknown error')
                failed_papers.append({
                    'id': paper_id,
                    'title': paper.get('title', 'Unknown'),
                    'error': error_msg
                })
                logger.error(
                    'Paper analysis returned error',
                    paper_id=paper_id,
                    error_message=error_msg[:100]
                )
            else:
                results.append(analysis_result)
                logger.info('Paper analysis succeeded', paper_id=paper_id)

        # 返回结果
        batch_result = {
            'status': 'success',
            'total_papers': len(papers),
            'successful_analyses': len(results),
            'failed_analyses': len(failed_papers),
            'results': results,
            'failures': failed_papers,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(
            'Batch analysis completed',
            total=len(papers),
            successful=len(results),
            failed=len(failed_papers)
        )
        return batch_result

    except Exception as e:
        logger.error(f'批量分析失败: {str(e)}')
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def _condense_abstract_to_chinese_async(abstract_en: str) -> str:
    """
    将英文摘要翻译成中文 - 异步版本
    """
    if not abstract_en:
        return "暂无摘要"

    try:
        import os
        from litellm import completion
        import asyncio
        from pathlib import Path
        import sys

        # 导入prompts模块 - 从paper_search目录导入
        prompts_path = str(Path(__file__).parent.parent.parent)
        if prompts_path not in sys.path:
            sys.path.insert(0, prompts_path)
        
        from prompts import format_translate_abstract_prompt

        model = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')
        api_key = os.getenv('OPENAI_API_KEY')
        api_base = os.getenv('OPENAI_BASE_URL')
        prompt = format_translate_abstract_prompt(abstract_en)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                api_key=api_key,
                api_base=api_base
            )
        )

        translation = response.choices[0].message.content.strip()
        logger.info(f"Successfully translated abstract using LLM")
        return translation

    except Exception as e:
        logger.warning(f"LLM translation failed, using fallback: {e}")

        # Fallback: 简单提取
        sentences = abstract_en.split('. ')
        key_sentences = []

        keywords_map = {
            'propose': '提出',
            'present': '提出',
            'introduce': '介绍',
            'develop': '开发',
            'demonstrate': '证明',
            'show': '展示',
            'achieve': '实现',
            'improve': '改进'
        }

        for sentence in sentences[:5]:
            sentence_lower = sentence.lower()
            for keyword in keywords_map:
                if keyword in sentence_lower:
                    key_sentences.append(sentence.strip())
                    break

        if not key_sentences:
            return f"本文{abstract_en[:200]}..."

        condensed = "本文" + "；".join(key_sentences[:3])
        return condensed[:300] + "..." if len(condensed) > 300 else condensed

