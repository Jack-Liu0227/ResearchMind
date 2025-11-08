"""
Analysis Module (分析模块)

功能：
1. 论文内容分析 - 提取关键信息、摘要、方法论
2. 关键词提取 - 自动提取论文关键词
3. 摘要生成 - 生成中文凝练摘要
4. 批量分析 - 批量处理多篇论文
5. 质量评估 - 评估论文质量和相关性

核心流程：
论文 PDF → 提取全文 → 分析内容 → 生成摘要 → 批量处理
"""
import json
from typing import Dict, Any, List
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


async def analyze_paper_content(
    paper: Dict[str, Any],
    content: str = None
) -> Dict[str, Any]:
    """
    单篇论文深度分析（作为调研报告的组件）- 异步版本

    提取并总结：
    - 研究目标
    - 主要方法
    - 关键结果
    - 创新点

    Args:
        paper: 论文信息字典（包含title, authors, abstract等）
        content: 全文内容（可选，如果有会提供更详细的分析）

    Returns:
        Dict containing:
        - paper_id: 论文ID
        - title: 标题
        - objective: 研究目标
        - method: 主要方法
        - result: 关键结果
        - innovation: 创新点
        - abstract_zh: 中文摘要（如果原文是英文）
    """
    try:
        from litellm import completion
        import os
        import asyncio
        from prompts import format_paper_summary_prompt

        paper_id = paper.get('paper_id', 'unknown')
        title = paper.get('title', 'Unknown')
        authors = paper.get('authors', [])
        abstract = paper.get('abstract', '')
        source = paper.get('source', 'unknown')

        # 准备内容摘录
        content_excerpt = ""
        if content:
            content_excerpt = content[:2000]  # 取前2000字符

        # 使用LLM分析（带重试机制）
        model = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')
        api_key = os.getenv('OPENAI_API_KEY')
        api_base = os.getenv('OPENAI_BASE_URL')

        prompt = format_paper_summary_prompt(
            title=title,
            authors=authors,
            abstract=abstract,
            content_excerpt=content_excerpt
        )

        # 重试机制：最多尝试 3 次
        max_retries = 3
        retry_delay = 2  # 秒
        last_error = None

        for attempt in range(max_retries):
            try:
                # 使用 asyncio 包装同步的 completion 调用，添加超时
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: completion(
                            model=model,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3,
                            timeout=30,  # 30秒超时
                            api_key=api_key,  # 🔧 显式传递 API Key
                            api_base=api_base  # 🔧 显式传递 API Base URL
                        )
                    ),
                    timeout=35  # 总超时 35 秒
                )
                break  # 成功则跳出重试循环

            except (asyncio.TimeoutError, Exception) as e:
                last_error = e
                error_type = type(e).__name__
                logger.warning(f'Attempt {attempt + 1}/{max_retries} failed for paper {paper_id}: {error_type} - {str(e)}')

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    # 最后一次尝试失败，抛出异常
                    raise Exception(f'Failed after {max_retries} attempts: {str(last_error)}')

        analysis_text = response.choices[0].message.content.strip()

        # 解析分析结果（简单的文本解析）
        key_info = _parse_analysis_text(analysis_text)

        # 翻译摘要 (也需要异步化)
        abstract_zh = await _condense_abstract_to_chinese_async(abstract) if abstract else ""

        result = {
            'paper_id': paper_id,
            'title': title,
            'authors': authors,
            'url': paper.get('url') or paper.get('pdf_url') or '',
            'pdf_url': paper.get('pdf_url', ''),
            'source': source,
            'abstract_zh': abstract_zh,
            'key_info': key_info,
            'analysis_text': analysis_text,
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
    """
    key_info = {
        'objective': '',
        'method': '',
        'result': '',
        'innovation': ''
    }

    # 简单的文本解析
    lines = analysis_text.split('\n')
    current_key = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测标题
        if '核心贡献' in line or '**核心贡献**' in line:
            current_key = 'innovation'
        elif '研究方法' in line or '**研究方法**' in line:
            current_key = 'method'
        elif '主要结果' in line or '**主要结果**' in line:
            current_key = 'result'
        elif '创新点' in line or '**创新点**' in line:
            current_key = 'innovation'
        elif current_key and line and not line.startswith('**'):
            # 累积内容
            if key_info[current_key]:
                key_info[current_key] += ' ' + line
            else:
                key_info[current_key] = line

    # 如果解析失败，使用整个文本作为创新点
    if not any(key_info.values()):
        key_info['innovation'] = analysis_text[:200]

    return key_info


async def batch_paper_analysis(
    papers: List[Dict] = None,
    papers_content: List[str] = None
) -> Dict[str, Any]:
    """
    批量分析多篇论文（只使用摘要，不使用全文）- 异步并发版本

    功能：
    - 提取研究目标、方法、结果、创新点
    - 生成中文摘要
    - 使用异步并发执行，大幅提升性能

    注意：此函数只使用论文摘要进行分析，不使用全文。
    如果需要基于全文的深度分析，请使用 generate_research_report。

    Args:
        papers: 论文列表（包含完整信息）
        papers_content: 论文全文内容列表（已弃用，不再使用）

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

        logger.info(f'开始批量分析 {len(papers)} 篇论文（只使用摘要，异步并发执行）')

        # 创建所有分析任务
        tasks = []
        for paper in papers:
            # 只使用摘要，不使用全文
            # papers_content 参数已弃用，为了向后兼容保留但不使用
            content = None
            tasks.append(analyze_paper_content(paper, content))

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
                failed_papers.append({
                    'id': paper_id,
                    'error': str(analysis_result)
                })
                logger.error(f'分析论文 {paper_id} 失败: {str(analysis_result)}')
            elif analysis_result.get('status') == 'error':
                failed_papers.append({
                    'id': paper_id,
                    'error': analysis_result.get('error', 'Unknown error')
                })
                logger.error(f'分析论文 {paper_id} 失败: {analysis_result.get("error")}')
            else:
                results.append(analysis_result)
                logger.info(f'成功分析论文 {paper_id}')

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

        logger.info(f'批量分析完成: {len(results)} 成功, {len(failed_papers)} 失败')
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
    将英文摘要凝练翻译成中文（使用LLM）- 异步版本

    提取关键信息：
    - 研究背景和动机
    - 主要方法
    - 核心结果
    - 创新点和贡献
    """
    if not abstract_en:
        return "暂无摘要"

    try:
        # 使用LLM进行翻译
        import os
        from litellm import completion
        import sys
        from pathlib import Path
        import asyncio

        # Import prompts
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from prompts import format_translate_abstract_prompt

        model = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')
        api_key = os.getenv('OPENAI_API_KEY')
        api_base = os.getenv('OPENAI_BASE_URL')
        prompt = format_translate_abstract_prompt(abstract_en)

        # 使用 asyncio 包装同步的 completion 调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                api_key=api_key,  # 🔧 显式传递 API Key
                api_base=api_base  # 🔧 显式传递 API Base URL
            )
        )

        translation = response.choices[0].message.content.strip()
        logger.info(f"Successfully translated abstract using LLM")
        return translation

    except Exception as e:
        logger.warning(f"LLM translation failed, using rule-based fallback: {e}")

        # Fallback: 规则提取
        sentences = abstract_en.split('. ')
        key_sentences = []

        # 提取包含关键词的句子
        keywords_map = {
            'propose': '提出',
            'present': '提出',
            'introduce': '介绍',
            'develop': '开发',
            'demonstrate': '证明',
            'show': '展示',
            'achieve': '实现',
            'improve': '改进',
            'novel': '新颖',
            'new': '新',
            'first': '首次'
        }

        for sentence in sentences[:5]:  # 只看前5句
            sentence_lower = sentence.lower()
            for keyword in keywords_map:
                if keyword in sentence_lower:
                    key_sentences.append(sentence.strip())
                    break

        if not key_sentences:
            # 如果没有找到关键句子，返回前200字的简化版
            return f"本文{abstract_en[:200]}..."

        # 简化翻译
        condensed = "本文" + "；".join(key_sentences[:3])
        return condensed[:300] + "..." if len(condensed) > 300 else condensed


def _condense_abstract_to_chinese(abstract_en: str) -> str:
    """
    将英文摘要凝练翻译成中文（使用LLM）- 同步版本（保留用于向后兼容）

    提取关键信息：
    - 研究背景和动机
    - 主要方法
    - 核心结果
    - 创新点和贡献
    """
    if not abstract_en:
        return "暂无摘要"

    try:
        # 使用LLM进行翻译
        import os
        from litellm import completion
        import sys
        from pathlib import Path

        # Import prompts
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from prompts import format_translate_abstract_prompt

        model = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')
        api_key = os.getenv('OPENAI_API_KEY')
        api_base = os.getenv('OPENAI_BASE_URL')
        prompt = format_translate_abstract_prompt(abstract_en)

        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            api_key=api_key,  # 🔧 显式传递 API Key
            api_base=api_base  # 🔧 显式传递 API Base URL
        )

        translation = response.choices[0].message.content.strip()
        logger.info(f"Successfully translated abstract using LLM")
        return translation

    except Exception as e:
        logger.warning(f"LLM translation failed, using rule-based fallback: {e}")

        # Fallback: 规则提取
        sentences = abstract_en.split('. ')
        key_sentences = []

        # 提取包含关键词的句子
        keywords_map = {
            'propose': '提出',
            'present': '提出',
            'introduce': '介绍',
            'develop': '开发',
            'demonstrate': '证明',
            'show': '展示',
            'achieve': '实现',
            'improve': '改进',
            'novel': '新颖',
            'new': '新',
            'first': '首次'
        }

        for sentence in sentences[:5]:  # 只看前5句
            sentence_lower = sentence.lower()
            for keyword in keywords_map:
                if keyword in sentence_lower:
                    key_sentences.append(sentence.strip())
                    break

        if not key_sentences:
            # 如果没有找到关键句子，返回前200字的简化版
            return f"本文{abstract_en[:200]}..."

        # 简化翻译
        condensed = "本文" + "；".join(key_sentences[:3])
        return condensed[:300] + "..." if len(condensed) > 300 else condensed


# _extract_key_information 已被 analyze_paper_content 中的 LLM 分析替代

