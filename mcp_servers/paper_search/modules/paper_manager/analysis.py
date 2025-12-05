"""
Paper Analysis Module (论文分析模块)

核心功能：
1. 单篇论文分析 - 基于摘要提取关键信息
2. 中文摘要翻译 - 将英文摘要凝练翻译成中文
3. 批量分析 - 并发处理多篇论文（仅使用摘要）
4. 引用标注 - 在分析结果中标注信息来源

注意：本模块专注于摘要分析，不处理报告生成
"""
from typing import Dict, Any, List, Optional, Callable
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
    content: str = None,
    use_cache: bool = True  # 🆕 新增参数
) -> Dict[str, Any]:
    """
    基于摘要分析单篇论文 - 异步版本（支持缓存）

    提取关键信息：
    - 研究目标
    - 主要方法
    - 关键结果
    - 创新点

    Args:
        paper: 论文信息字典（包含title, authors, abstract等）
        content: 全文内容（可选，不使用）
        use_cache: 是否使用缓存（默认 True）

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
    # 🆕 检查缓存
    if use_cache:
        try:
            # 添加 paper_search 目录到 sys.path
            import sys
            from pathlib import Path as PathLib
            _CURRENT_FILE = PathLib(__file__)
            _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
            if str(_PAPER_SEARCH_DIR) not in sys.path:
                sys.path.insert(0, str(_PAPER_SEARCH_DIR))

            from config import ENABLE_ANALYSIS_CACHE
            if ENABLE_ANALYSIS_CACHE:
                from ..shared.cache_manager import get_cache_manager
                cache_manager = get_cache_manager()
                cached_result = cache_manager.get(paper)
                if cached_result:
                    logger.info(f'✅ 使用缓存结果: {paper.get("paper_id", "unknown")}')
                    return cached_result
        except Exception as e:
            logger.warning(f'缓存读取失败: {e}')

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

        # 🆕 质量评估（如果启用）
        quality_assessment = None
        try:
            # 添加 paper_search 目录到 sys.path
            import sys
            from pathlib import Path as PathLib
            _CURRENT_FILE = PathLib(__file__)
            _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
            if str(_PAPER_SEARCH_DIR) not in sys.path:
                sys.path.insert(0, str(_PAPER_SEARCH_DIR))

            from config import ENABLE_QUALITY_ASSESSMENT
            if ENABLE_QUALITY_ASSESSMENT:
                from ..shared.quality_assessor import get_quality_assessor
                assessor = get_quality_assessor()

                # 评估分析质量
                quality_assessment = assessor.assess(analysis_text, paper)

                # 如果质量过低，记录警告
                if not quality_assessment['is_high_quality']:
                    logger.warning(
                        f"Low quality analysis detected for {paper_id}",
                        score=quality_assessment['score'],
                        issues=quality_assessment['issues']
                    )
        except Exception as e:
            logger.warning(f'质量评估失败: {e}')

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
            'timestamp': datetime.now().isoformat(),
            'quality_assessment': quality_assessment  # 🆕 添加质量评估结果
        }

        # 🆕 保存到缓存
        if use_cache:
            try:
                # 添加 paper_search 目录到 sys.path
                import sys
                from pathlib import Path as PathLib
                _CURRENT_FILE = PathLib(__file__)
                _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
                if str(_PAPER_SEARCH_DIR) not in sys.path:
                    sys.path.insert(0, str(_PAPER_SEARCH_DIR))

                from config import ENABLE_ANALYSIS_CACHE
                if ENABLE_ANALYSIS_CACHE:
                    from ..shared.cache_manager import get_cache_manager
                    cache_manager = get_cache_manager()
                    cache_manager.set(paper, result)
            except Exception as e:
                logger.warning(f'缓存保存失败: {e}')

        # 🆕 结果验证
        try:
            from ..shared.result_validator import get_result_validator
            validator = get_result_validator()
            validation = validator.validate_paper_analysis(result)

            if not validation['is_valid']:
                logger.warning(
                    f"Validation failed for {paper_id}",
                    errors=validation['errors']
                )

            # 添加验证结果到返回值
            result['validation'] = validation
        except Exception as e:
            logger.warning(f'结果验证失败: {e}')

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


def _clean_llm_output(text: str) -> str:
    """
    清理 LLM 输出中的格式问题

    Args:
        text: LLM 原始输出

    Returns:
        清理后的文本
    """
    import re

    if not text:
        return text

    # 移除多余的分隔符
    text = re.sub(r'\n\s*---\s*---\s*', '\n', text)
    text = re.sub(r'\n\s*---\s*\n', '\n\n', text)

    # 清理列表项中的多余破折号
    text = re.sub(r'^-\s*-\s*-\s*', '- ', text, flags=re.MULTILINE)
    text = re.sub(r'^-\s*-\s*', '- ', text, flags=re.MULTILINE)

    # 移除空的章节（只有标题和分隔符，没有内容）
    text = re.sub(r'####\s+[^:\n]+:\s*\n\s*---\s*\n', '', text)
    text = re.sub(r'####\s+[^:\n]+:\s*\n\s*\n', '', text)

    # 移除连续的空行（保留最多一个空行）
    text = re.sub(r'\n\n\n+', '\n\n', text)

    return text.strip()


def _parse_analysis_text(analysis_text: str) -> Dict[str, str]:
    """
    解析LLM返回的分析文本，提取关键信息

    使用正则表达式提取各部分内容，更加健壮

    格式：
    ### 2. 研究目标
    ### 3. 方法论
    ### 4. 主要发现与结果
    ### 5. 创新点与贡献
    """
    # 🆕 先清理输出
    analysis_text = _clean_llm_output(analysis_text)

    key_info = {
        'objective': '',
        'method': '',
        'result': '',
        'innovation': ''
    }

    import re

    # 🔧 使用正则表达式提取各部分内容（更健壮）
    # 提取"研究目标"部分（### 2. 研究目标）
    objective_match = re.search(
        r'###\s*2\.\s*研究目标(.*?)(?=###\s*3\.|$)',
        analysis_text,
        re.DOTALL | re.IGNORECASE
    )
    if objective_match:
        content = objective_match.group(1).strip()
        # 移除子标题（如 **具体的研究目标是什么？**）
        content = re.sub(r'\*\*[^*]+\*\*\s*', '', content)
        # 移除多余的换行和空格
        content = re.sub(r'\n\s*\n', '\n', content).strip()
        key_info['objective'] = content

    # 提取"方法论"部分（### 3. 方法论）
    method_match = re.search(
        r'###\s*3\.\s*方法论(.*?)(?=###\s*4\.|$)',
        analysis_text,
        re.DOTALL | re.IGNORECASE
    )
    if method_match:
        content = method_match.group(1).strip()
        content = re.sub(r'\*\*[^*]+\*\*\s*', '', content)
        content = re.sub(r'\n\s*\n', '\n', content).strip()
        key_info['method'] = content

    # 提取"主要发现与结果"部分（### 4. 主要发现与结果）
    result_match = re.search(
        r'###\s*4\.\s*主要发现与结果(.*?)(?=###\s*5\.|$)',
        analysis_text,
        re.DOTALL | re.IGNORECASE
    )
    if result_match:
        content = result_match.group(1).strip()
        content = re.sub(r'\*\*[^*]+\*\*\s*', '', content)
        content = re.sub(r'\n\s*\n', '\n', content).strip()
        key_info['result'] = content

    # 提取"创新点与贡献"部分（### 5. 创新点与贡献）
    innovation_match = re.search(
        r'###\s*5\.\s*创新点与贡献(.*?)(?=###\s*6\.|$)',
        analysis_text,
        re.DOTALL | re.IGNORECASE
    )
    if innovation_match:
        content = innovation_match.group(1).strip()
        content = re.sub(r'\*\*[^*]+\*\*\s*', '', content)
        content = re.sub(r'\n\s*\n', '\n', content).strip()
        key_info['innovation'] = content

    # 如果正则表达式解析失败，降级到原有的逐行解析
    if not any(key_info.values()):
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

    # 如果仍然解析失败，使用整个文本作为创新点
    if not any(key_info.values()):
        key_info['innovation'] = analysis_text

    return key_info


async def batch_paper_analysis(
    papers: List[Dict] = None,
    progress_callback: Optional[Callable[[dict], Any]] = None,
    max_concurrent: int = None  # 🆕 新增参数
) -> Dict[str, Any]:
    """
    批量分析多篇论文 - 受控并发版本（支持进度追踪）

    使用 Semaphore 控制并发数量，平衡性能和进度更新的实时性

    Args:
        papers: 论文列表
        progress_callback: 进度更新回调函数（可选）
        max_concurrent: 最大并发数（可选，默认从配置读取）

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

        # 🆕 从配置读取并发数
        if max_concurrent is None:
            # 添加 paper_search 目录到 sys.path
            import sys
            from pathlib import Path as PathLib
            _CURRENT_FILE = PathLib(__file__)
            _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
            if str(_PAPER_SEARCH_DIR) not in sys.path:
                sys.path.insert(0, str(_PAPER_SEARCH_DIR))

            from config import MAX_CONCURRENT_BATCH_ANALYSIS
            max_concurrent = MAX_CONCURRENT_BATCH_ANALYSIS

        logger.info(f'开始批量分析 {len(papers)} 篇论文（最大并发: {max_concurrent}）')

        # 🆕 初始化进度追踪
        total_papers = len(papers)
        completed_count = 0

        # 🆕 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        # 🆕 创建锁保护共享状态
        lock = asyncio.Lock()

        # 🆕 发送初始进度
        if progress_callback:
            await _send_progress(progress_callback, {
                "current": 0,
                "total": total_papers,
                "progress": 0.0,
                "message": f"准备分析 {total_papers} 篇论文（并发: {max_concurrent}）...",
                "status": "running"
            })

        # 处理结果
        results = []
        failed_papers = []

        # 🆕 使用 Semaphore 控制并发的分析函数
        async def analyze_with_semaphore(i: int, paper: Dict) -> None:
            """使用信号量控制并发的分析函数"""
            nonlocal completed_count

            paper_id = paper.get('paper_id', 'unknown')
            paper_title = paper.get('title', 'Unknown')[:50]

            async with semaphore:
                try:
                    # 🆕 发送当前论文分析进度
                    if progress_callback:
                        async with lock:
                            await _send_progress(progress_callback, {
                                "current": completed_count,
                                "total": total_papers,
                                "progress": completed_count / total_papers,
                                "message": f"正在分析第 {i+1}/{total_papers} 篇: {paper_title}...",
                                "status": "running"
                            })

                    # 分析论文（使用缓存）
                    analysis_result = await analyze_paper_content(paper, None, use_cache=True)

                    # 检查分析结果
                    if analysis_result.get('status') == 'error':
                        error_msg = analysis_result.get('error', 'Unknown error')
                        async with lock:
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
                        async with lock:
                            results.append(analysis_result)
                        logger.info('Paper analysis succeeded', paper_id=paper_id)

                    # 🆕 更新完成计数
                    async with lock:
                        completed_count += 1
                        current_count = completed_count

                    # 🆕 发送完成进度
                    if progress_callback:
                        async with lock:
                            await _send_progress(progress_callback, {
                                "current": current_count,
                                "total": total_papers,
                                "progress": current_count / total_papers,
                                "message": f"已完成 {current_count}/{total_papers} 篇论文分析",
                                "status": "running"
                            })

                except Exception as e:
                    # 🆕 处理异常
                    error_msg = str(e)
                    async with lock:
                        failed_papers.append({
                            'id': paper_id,
                            'title': paper.get('title', 'Unknown'),
                            'error': error_msg
                        })
                        completed_count += 1
                        current_count = completed_count

                    logger.error(
                        'Paper analysis failed with exception',
                        paper_id=paper_id,
                        error_type=type(e).__name__,
                        error_message=error_msg[:100]
                    )

                    # 🆕 即使失败也更新进度
                    if progress_callback:
                        async with lock:
                            await _send_progress(progress_callback, {
                                "current": current_count,
                                "total": total_papers,
                                "progress": current_count / total_papers,
                                "message": f"论文 {paper_id} 分析失败，继续处理...",
                                "status": "running"
                            })

        # 🆕 并发执行所有分析任务
        tasks = [analyze_with_semaphore(i, paper) for i, paper in enumerate(papers)]
        await asyncio.gather(*tasks)

        # 🆕 发送完成消息
        if progress_callback:
            success_count = len(results)
            error_count = len(failed_papers)
            await _send_progress(progress_callback, {
                "current": total_papers,
                "total": total_papers,
                "progress": 1.0,
                "message": f"批量分析完成！成功: {success_count} 篇，失败: {error_count} 篇",
                "status": "success"
            })

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

        # 🆕 发送错误消息
        if progress_callback:
            await _send_progress(progress_callback, {
                "current": 0,
                "total": len(papers) if papers else 0,
                "progress": 0.0,
                "message": f"批量分析失败: {str(e)}",
                "status": "error",
                "error": str(e)
            })

        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def _send_progress(callback: Callable, progress_data: dict):
    """
    发送进度更新（支持同步和异步回调）

    Args:
        callback: 回调函数
        progress_data: 进度数据字典
    """
    try:
        import asyncio
        if asyncio.iscoroutinefunction(callback):
            await callback(progress_data)
        else:
            callback(progress_data)
    except Exception as e:
        logger.error(f"发送进度更新失败: {str(e)}")


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

