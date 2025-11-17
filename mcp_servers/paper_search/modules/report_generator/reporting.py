"""
Reporting Module (报告模块)

功能：
1. 报告生成 - 生成 IEEE 标准格式的研究报告
2. 格式化输出 - Markdown 格式输出
3. 引用管理 - IEEE 格式引用

核心流程：
论文 IDs → 提取全文 → 分析论文 → 生成报告结构 → LLM 填充内容 → 保存报告
"""
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
from litellm import completion
import asyncio

logger = structlog.get_logger(__name__)


def extract_structured_analysis(analysis_text: str) -> Dict[str, str]:
    """
    从LLM生成的分析文本中提取结构化信息

    Args:
        analysis_text: LLM生成的完整分析文本

    Returns:
        Dict containing:
        - background: 研究背景与动机
        - objective: 研究目标
        - method: 方法论
        - result: 主要发现与结果
        - innovation: 创新点与贡献
        - limitation: 局限性
    """
    sections = {
        'background': '',
        'objective': '',
        'method': '',
        'result': '',
        'innovation': '',
        'limitation': ''
    }

    # 定义各部分的标题模式
    patterns = {
        'background': r'###\s*1\.\s*研究背景与动机(.*?)(?=###\s*2\.|$)',
        'objective': r'###\s*2\.\s*研究目标(.*?)(?=###\s*3\.|$)',
        'method': r'###\s*3\.\s*方法论(.*?)(?=###\s*4\.|$)',
        'result': r'###\s*4\.\s*主要发现与结果(.*?)(?=###\s*5\.|$)',
        'innovation': r'###\s*5\.\s*创新点与贡献(.*?)(?=###\s*6\.|$)',
        'limitation': r'###\s*6\.\s*局限性(.*?)$'
    }

    # 提取各部分内容
    for key, pattern in patterns.items():
        match = re.search(pattern, analysis_text, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            # 清理内容：移除多余的换行和空格
            content = ' '.join(content.split())
            # 限制长度
            if len(content) > 500:
                content = content[:497] + '...'
            sections[key] = content

    return sections

# 全局超时配置
FETCH_TIMEOUT = 30  # 获取全文超时时间（秒）
ANALYSIS_TIMEOUT = 300  # 分析论文超时时间（秒）- 增加到120秒以适应LLM响应延迟


class ResearchReportGenerator:
    """
    优化的研究报告生成器

    新的报告生成模式：
    1. 综合报告：基于所有文献生成完整调研报告
    2. 单篇分析：深度分析单篇论文
    3. 对比分析：多篇论文对比
    4. 空白分析：识别研究空白和机会
    """

    def __init__(self, model: str = ""):
        """
        初始化报告生成器

        Args:
            model: LLM 模型名称（默认从环境变量 MODEL_USE 读取）
        """
        self.model = model or os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')
        logger.info("ResearchReportGenerator initialized", model=self.model)

    async def generate_comprehensive_report(
        self,
        papers_info: List[Dict[str, Any]],
        topic: str,
        papers_analysis: Optional[List[Dict[str, Any]]] = None
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        生成综合调研报告（按块生成每篇论文的详细分析，然后合并）

        优化：支持内存受限环境（4G内存）
        - 限制并发任务数量
        - 分批处理论文
        - 及时释放内存

        Args:
            papers_info: 论文信息列表（包含title, authors, abstract, full_text等）
            topic: 研究主题
            papers_analysis: 论文分析列表（可选，如果有会包含更多细节）

        Returns:
            str: Markdown 格式的综合研究报告
        """
        logger.info("Generating comprehensive research report",
                   topic=topic,
                   num_papers=len(papers_info))

        try:
            # 检查是否已经获取了全文，如果没有则获取
            import gc
            from ..paper_manager.content_fetcher import get_paper_content_by_source_async

            # 确定哪些论文需要获取内容
            papers_needing_content = []
            enriched_papers = []

            for i, paper in enumerate(papers_info):
                # 检查是否已经有全文内容
                if 'full_text' in paper and paper['full_text']:
                    enriched_papers.append(paper)
                else:
                    papers_needing_content.append((i, paper))
                    # 添加一个占位符以保持索引一致
                    enriched_papers.append(None)

            # 如果有需要获取内容的论文，则并行获取
            if papers_needing_content:
                # 内存优化：减少并发任务数量以降低API压力
                MAX_CONCURRENT_TASKS = 5  # 设置为5个并发任务以降低API压力和超时风险

                async def fetch_paper_content(i: int, paper: Dict[str, Any]) -> tuple:
                    """异步获取单篇论文的全文（带超时控制）"""
                    try:
                        logger.info(f"Fetching content {i+1}/{len(papers_needing_content)}: {paper.get('title', 'Unknown')[:50]}...")

                        # 使用新的异步内容获取函数
                        content_result = await asyncio.wait_for(
                            get_paper_content_by_source_async(paper, paper.get('source', ''), timeout=FETCH_TIMEOUT),
                            timeout=FETCH_TIMEOUT + 5  # 额外的5秒缓冲
                        )

                        # 将全文添加到论文信息中
                        enriched_paper = paper.copy()
                        enriched_paper['full_text'] = content_result.get('content', '')
                        enriched_paper['content_metadata'] = content_result.get('metadata', {})

                        logger.info(f"Successfully got content for paper {i+1}")
                        return (i, enriched_paper, 'success')

                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout fetching content for paper {paper.get('paper_id', 'unknown')} (>{FETCH_TIMEOUT}s)")
                        # 超时时只使用摘要
                        enriched_paper = paper.copy()
                        enriched_paper['full_text'] = paper.get('abstract', '')
                        enriched_paper['content_metadata'] = {'fallback': True, 'fallback_reason': f'Timeout after {FETCH_TIMEOUT}s'}
                        return (i, enriched_paper, 'timeout')
                    except Exception as e:
                        logger.warning(f"Failed to get content for paper {paper.get('paper_id', 'unknown')}: {e}")
                        # 失败时只使用摘要
                        enriched_paper = paper.copy()
                        enriched_paper['full_text'] = paper.get('abstract', '')
                        enriched_paper['content_metadata'] = {'fallback': True, 'fallback_reason': str(e)}
                        return (i, enriched_paper, 'error')

                # 批量顺序处理论文：先执行前MAX_CONCURRENT_TASKS个，完成后再执行后面的
                logger.info(f"Fetching content for {len(papers_needing_content)} papers with max {MAX_CONCURRENT_TASKS} concurrent tasks (timeout: {FETCH_TIMEOUT}s)...")

                fetched_results = []
                total_papers = len(papers_needing_content)

                # 分批处理
                for batch_start in range(0, total_papers, MAX_CONCURRENT_TASKS):
                    batch_end = min(batch_start + MAX_CONCURRENT_TASKS, total_papers)
                    batch_papers = papers_needing_content[batch_start:batch_end]

                    logger.info(f"Processing batch: papers {batch_start+1}-{batch_end}/{total_papers}")

                    # 创建当前批次的任务
                    batch_tasks = [fetch_paper_content(i, paper) for i, paper in batch_papers]

                    # 并行执行当前批次的任务
                    batch_results = await asyncio.gather(*batch_tasks)
                    fetched_results.extend(batch_results)

                    # 及时释放内存
                    gc.collect()
                    logger.info(f"Batch {batch_start//MAX_CONCURRENT_TASKS + 1} completed, memory freed")

                # 将获取到的内容放回正确的位置
                for original_index, enriched_paper, status in fetched_results:
                    enriched_papers[original_index] = enriched_paper
            
            # 及时释放内存
            gc.collect()
            logger.info("Content fetching completed, memory freed")

            # 第二步：为每篇论文生成详细分析（限制并发数量以节省内存）
            async def analyze_single_paper(i, paper):
                """分析单篇论文（带超时控制）"""
                logger.info(f"Analyzing paper {i+1}/{len(enriched_papers)}: {paper.get('title', 'Unknown')[:50]}...")

                # 获取全文或摘要
                full_text = paper.get('full_text', '')
                abstract = paper.get('abstract', '')

                # 确定使用哪种内容进行分析
                if full_text and len(full_text) > 100:
                    content = full_text
                    content_type = "全文"
                elif abstract and len(abstract) > 50:
                    content = abstract
                    content_type = "摘要"
                else:
                    # 如果既没有全文也没有摘要，使用标题作为最后的fallback
                    content = f"标题: {paper.get('title', 'Unknown')}"
                    content_type = "仅标题"
                    logger.warning(f"Paper {i+1} has no content, using title only")

                # 内存优化：截断内容长度
                content = content[:3000]  # 减少从5000到3000

                logger.info(f"Analyzing paper {i+1} using {content_type} ({len(content)} chars)")

                # 将content_type存储到paper字典中，以便后续使用
                paper['content_type'] = content_type

                # 生成单篇论文的详细分析
                analysis_prompt = f"""请对以下论文进行深度分析：

标题: {paper.get('title', 'Unknown')}
作者: {', '.join(paper.get('authors', []))}
发表时间: {paper.get('published', 'Unknown')}
URL: {paper.get('url', 'N/A')}
分析依据: {content_type}

内容:
{content}

请按照以下结构分析（使用中文）：

### 1. 研究背景与动机
- 研究解决什么问题？
- 为什么这个问题重要？

### 2. 研究目标
- 具体的研究目标是什么？

### 3. 方法论
- 使用了什么方法？
- 方法有何创新之处？

### 4. 主要发现与结果
- 关键结果是什么？
- 有哪些重要发现？

### 5. 创新点与贡献
- 这项工作的创新之处？
- 对领域的贡献？

### 6. 局限性
- 存在哪些局限性？
- 有哪些未解决的问题？

要求：详细、专业、客观、简洁
"""

                try:
                    # 使用 asyncio 包装同步的 completion 调用，并添加超时控制
                    loop = asyncio.get_event_loop()
                    response = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: completion(
                                model=self.model,
                                messages=[{"role": "user", "content": analysis_prompt}],
                                temperature=0.3,
                                max_tokens=1500  # 减少token数量以节省内存
                            )
                        ),
                        timeout=ANALYSIS_TIMEOUT
                    )

                    # 安全地处理响应对象
                    analysis_text = ""
                    if response is not None:
                        # 使用字典方式访问属性以避免类型检查错误
                        response_dict = vars(response) if hasattr(response, '__dict__') else {}
                        choices = response_dict.get('choices', [])
                        if choices and len(choices) > 0:
                            choice = choices[0]
                            choice_dict = vars(choice) if hasattr(choice, '__dict__') else {}
                            message = choice_dict.get('message')
                            if message is not None:
                                message_dict = vars(message) if hasattr(message, '__dict__') else {}
                                content = message_dict.get('content', '')
                                if content:
                                    analysis_text = content.strip()
                    logger.info(f"Successfully analyzed paper {i+1}")
                    return (i, {'paper': paper, 'analysis': analysis_text}, 'success')

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout analyzing paper {i+1} (>{ANALYSIS_TIMEOUT}s), using fallback")
                    # 超时时使用完整结构的简化分析作为后备
                    # 根据可用内容生成fallback
                    content_preview = ""
                    if abstract:
                        content_preview = abstract[:200]
                    elif full_text:
                        content_preview = full_text[:200]
                    else:
                        content_preview = "信息不足（无摘要和全文）"

                    fallback_analysis = f"""### 1. 研究背景与动机

**研究解决什么问题？**
{content_preview}

**为什么这个问题重要？**
（分析超时，详细信息请参考原文）

---

### 2. 研究目标

（分析超时，详细信息请参考原文）

---

### 3. 方法论

**使用了什么方法？**
（分析超时，详细信息请参考原文）

**方法有何创新之处？**
（分析超时，详细信息请参考原文）

---

### 4. 主要发现与结果

**关键结果是什么？**
（分析超时，详细信息请参考原文）

**有哪些重要发现？**
（分析超时，详细信息请参考原文）

---

### 5. 创新点与贡献

**这项工作的创新之处？**
（分析超时，详细信息请参考原文）

**对领域的贡献？**
（分析超时，详细信息请参考原文）

---

### 6. 局限性

**存在哪些局限性？**
（分析超时，详细信息请参考原文）

**有哪些未解决的问题？**
（分析超时，详细信息请参考原文）

---

**可用内容**: {content_type}
**内容预览**: {abstract[:500] if abstract else (full_text[:500] if full_text else '无内容')}

*注：分析超时，仅显示可用内容*
"""
                    return (i, {'paper': paper, 'analysis': fallback_analysis}, 'timeout')
                except Exception as e:
                    logger.error(f"Failed to analyze paper {i+1}: {e}")
                    # 使用完整结构的简化分析作为后备
                    # 根据可用内容生成fallback
                    content_preview = ""
                    if abstract:
                        content_preview = abstract[:200]
                    elif full_text:
                        content_preview = full_text[:200]
                    else:
                        content_preview = "信息不足（无摘要和全文）"

                    fallback_analysis = f"""### 1. 研究背景与动机

**研究解决什么问题？**
{content_preview}

**为什么这个问题重要？**
（分析失败，详细信息请参考原文）

---

### 2. 研究目标

（分析失败，详细信息请参考原文）

---

### 3. 方法论

**使用了什么方法？**
（分析失败，详细信息请参考原文）

**方法有何创新之处？**
（分析失败，详细信息请参考原文）

---

### 4. 主要发现与结果

**关键结果是什么？**
（分析失败，详细信息请参考原文）

**有哪些重要发现？**
（分析失败，详细信息请参考原文）

---

### 5. 创新点与贡献

**这项工作的创新之处？**
（分析失败，详细信息请参考原文）

**对领域的贡献？**
（分析失败，详细信息请参考原文）

---

### 6. 局限性

**存在哪些局限性？**
（分析失败，详细信息请参考原文）

**有哪些未解决的问题？**
（分析失败，详细信息请参考原文）

---

**可用内容**: {content_type}
**内容预览**: {abstract[:500] if abstract else (full_text[:500] if full_text else '无内容')}

*注：分析失败（{str(e)}），仅显示可用内容*
"""
                    return (i, {'paper': paper, 'analysis': fallback_analysis}, 'error')

            # 批量顺序处理论文：先执行前MAX_CONCURRENT_TASKS个，完成后再执行后面的
            MAX_CONCURRENT_TASKS = 10  # 设置为5个并发任务以降低API压力和超时风险

            logger.info(f"Starting batch analysis of {len(enriched_papers)} papers (max {MAX_CONCURRENT_TASKS} concurrent, timeout: {ANALYSIS_TIMEOUT}s)...")
            detailed_analyses = []
            total_papers = len(enriched_papers)

            # 分批处理
            for batch_start in range(0, total_papers, MAX_CONCURRENT_TASKS):
                batch_end = min(batch_start + MAX_CONCURRENT_TASKS, total_papers)
                batch_papers = enriched_papers[batch_start:batch_end]

                logger.info(f"Processing analysis batch: papers {batch_start+1}-{batch_end}/{total_papers}")

                # 创建当前批次的任务
                batch_tasks = [analyze_single_paper(i, paper) for i, paper in enumerate(batch_papers)]

                # 并行执行当前批次的任务
                batch_results = await asyncio.gather(*batch_tasks)

                # 提取结果
                for i, result, status in batch_results:
                    detailed_analyses.append(result)

                # 及时释放内存
                gc.collect()
                logger.info(f"Completed analysis batch {batch_start//MAX_CONCURRENT_TASKS + 1}, memory freed")

            logger.info(f"Completed analysis of {len(enriched_papers)} papers")

            # 第二步：准备所有分析的摘要（内存优化版本）+ 提取结构化数据
            analyses_summary = []
            structured_analyses = []  # 用于保存到CSV的结构化数据

            for i, item in enumerate(detailed_analyses, 1):
                paper = item['paper']
                analysis = item['analysis']
                # 获取分析来源标注
                content_type = paper.get('content_type', '未知')
                summary = f"""
## 文献 {i}: {paper.get('title', 'Unknown')}

**作者**: {', '.join(paper.get('authors', []))}
**发表时间**: {paper.get('published', 'Unknown')}
**来源**: {paper.get('source', 'Unknown')}
**URL**: {paper.get('url', 'N/A')}
**【分析来源：{content_type}】**

{analysis}

---
"""
                analyses_summary.append(summary)

                # 提取结构化信息用于CSV保存
                structured_info = extract_structured_analysis(analysis)

                # 构建CSV行数据
                structured_analyses.append({
                    'paper_id': paper.get('paper_id', '') or paper.get('id', '') or paper.get('arxiv_id', ''),
                    'title': paper.get('title', 'Unknown'),
                    'authors': paper.get('authors', []),
                    'source': paper.get('source', 'unknown'),
                    'url': paper.get('url', '') or paper.get('pdf_url', ''),
                    'abstract_zh': structured_info.get('background', ''),  # 使用背景作为中文摘要
                    'key_info': {
                        'objective': structured_info.get('objective', 'N/A'),
                        'method': structured_info.get('method', 'N/A'),
                        'result': structured_info.get('result', 'N/A'),
                        'innovation': structured_info.get('innovation', 'N/A')
                    },
                    'analysis_text': analysis,
                    'content_type': content_type
                })

            # 第三步：生成综合总结（使用所有论文的分析）
            logger.info("Generating synthesis from detailed analyses...")

            # 使用所有论文的详细分析来生成综合总结
            # 为了生成更全面的报告，我们使用所有文献
            selected_analyses = analyses_summary

            synthesis_prompt = f"""基于以下 {len(detailed_analyses)} 篇论文的分析，生成一份综合研究报告。

研究主题: {topic}

详细分析:
{''.join(selected_analyses)}

请生成以下部分（使用中文，简洁明了）：

## 研究概述
- 研究领域的重要性和背景
- 当前研究的主要挑战
- 本次调研的文献范围

## 技术路线分析
- 主流技术方法对比
- 各方法的优缺点
- 技术演进趋势

## 研究热点与趋势
- 当前研究热点
- 未来发展方向
- 潜在突破点

## 研究空白与机会
- 现有研究的局限性
- 尚未解决的问题
- 可能的研究方向

## 总结与建议
- 主要结论
- 对研究者的建议
- 未来展望

要求：专业、客观、有深度、简洁
"""

            try:
                response = completion(
                    model=self.model,
                    messages=[{"role": "user", "content": synthesis_prompt}],
                    temperature=0.7,
                    max_tokens=2000  # 减少从3000到2000
                )

                # 安全地处理响应对象
                report_content = ""
                if response is not None:
                    # 使用字典方式访问属性以避免类型检查错误
                    response_dict = vars(response) if hasattr(response, '__dict__') else {}
                    choices = response_dict.get('choices', [])
                    if choices and len(choices) > 0:
                        choice = choices[0]
                        choice_dict = vars(choice) if hasattr(choice, '__dict__') else {}
                        message = choice_dict.get('message')
                        if message is not None:
                            message_dict = vars(message) if hasattr(message, '__dict__') else {}
                            content = message_dict.get('content', '')
                            if content:
                                report_content = content.strip()

                if not report_content:
                    logger.warning("LLM returned empty content for synthesis, using fallback")
                    report_content = "## 研究概述\n\n（综合分析生成失败，请查看下方详细文献分析）\n"

            except Exception as llm_error:
                logger.error(f"LLM synthesis failed: {llm_error}")
                logger.warning("Using fallback synthesis content")
                report_content = "## 研究概述\n\n（综合分析生成失败，请查看下方详细文献分析）\n"

            # 及时释放内存
            gc.collect()

            # 添加元数据
            header = f"""# {topic} - 研究调研报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**文献数量**: {len(papers_info)}
**生成方式**: AI深度分析（内存优化版本）

---

"""

            # 组合最终报告 = 头部 + 综合总结 + 详细分析
            # 包含所有论文的详细分析
            detailed_section = ''.join(analyses_summary)

            full_report = header + report_content + "\n\n---\n\n# 详细文献分析\n\n" + detailed_section

            # 添加参考文献
            references = "\n\n---\n\n## 参考文献\n\n"
            for i, paper in enumerate(papers_info, 1):
                # 安全处理authors字段
                authors_raw = paper.get('authors', ['Unknown'])
                if isinstance(authors_raw, list):
                    authors = ', '.join(str(a) for a in authors_raw)
                else:
                    authors = str(authors_raw)

                title = paper.get('title', 'Unknown Title')
                year = paper.get('published', 'Unknown')[:4] if paper.get('published') else 'Unknown'
                source = paper.get('source', 'unknown')
                paper_id = paper.get('paper_id', 'unknown')
                url = paper.get('url', '')

                if source == 'arxiv':
                    references += f"[{i}] {authors}. \"{title}\". arXiv:{paper_id}, {year}. {url}\n"
                else:
                    references += f"[{i}] {authors}. \"{title}\". {year}. {url}\n"

            full_report += references

            # 最后释放内存
            gc.collect()

            logger.info("Comprehensive report generated successfully")
            logger.info(f"Extracted {len(structured_analyses)} structured analyses for CSV export")
            return full_report, structured_analyses

        except Exception as e:
            import traceback
            logger.error(f"Failed to generate comprehensive report: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # 不再降级，直接抛出异常让调用者处理
            raise


# ============================================================================
# 外部接口函数（保持向后兼容）
# ============================================================================

async def generate_research_report(
    papers_info: List[Dict[str, Any]],
    topic: str,
    papers_analysis: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    生成综合研究报告

    使用LLM生成完整的专业调研报告：
    - 研究概述、核心发现、技术路线、趋势分析、研究空白等
    - 每篇论文的详细分析（6部分结构）
    - 参考文献列表

    Args:
        papers_info: 论文信息列表（必须包含title, authors, abstract等）
        topic: 研究主题
        papers_analysis: 论文分析列表（可选，如果有会包含更多细节）

    Returns:
        Dict containing:
        - report_content: Markdown format的报告内容
        - metadata: 报告元数据
    """
    try:
        logger.info(f'Generating comprehensive research report for topic: {topic} with {len(papers_info)} papers')

        # Initialize report generator
        report_gen = ResearchReportGenerator()

        if not papers_info:
            return {
                'status': 'error',
                'error': 'No valid papers found',
                'timestamp': datetime.now().isoformat()
            }

        # Generate comprehensive report
        logger.info("Using comprehensive report generation")
        full_report, structured_analyses = await report_gen.generate_comprehensive_report(
            papers_info=papers_info,
            topic=topic,
            papers_analysis=papers_analysis
        )

        logger.info(f'Research report generated successfully')

        # 返回内容供前端使用
        result = {
            'status': 'success',
            'report': full_report,
            'papers_count': len(papers_info),
            'topic': topic,
            'timestamp': datetime.now().isoformat(),
            'message': 'Research report generated successfully.',
            'mode': 'comprehensive',
            'structured_analyses': structured_analyses  # 添加结构化分析数据
        }

        return result

    except Exception as e:
        logger.error(f'Failed to generate research report: {str(e)}')
        import traceback
        logger.error(f'Traceback: {traceback.format_exc()}')
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def generate_research_report_with_data_collection(
    papers_info: List[Dict[str, Any]],
    topic: str,
    papers_analysis: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    生成研究报告（增强版，自动获取全文）

    优化后的工作流程：
    1. 接收已准备好的论文信息
    2. 获取所有论文的全文（失败则使用摘要）
    3. 接收已完成的论文分析（可选）
    4. 生成综合报告

    Args:
        papers_info: 论文信息列表（包含title, authors, abstract, url等）
        topic: 研究主题
        papers_analysis: 论文分析列表（可选）

    Returns:
        Dict containing report and metadata
    """
    try:
        logger.info(f'Generating research report for topic: {topic} with {len(papers_info)} papers')

        # 异步并行获取所有论文的全文
        import gc
        from ..paper_manager.content_fetcher import get_paper_content_by_source_async

        MAX_CONCURRENT_TASKS = 5  # 最多5个并发任务以降低API压力

        async def fetch_paper_content(i: int, paper: Dict[str, Any]) -> tuple:
            """异步获取单篇论文的全文（带超时控制）"""
            try:
                logger.info(f"Fetching content {i+1}/{len(papers_info)}: {paper.get('title', 'Unknown')[:50]}...")

                # 使用新的异步内容获取函数
                content_result = await asyncio.wait_for(
                    get_paper_content_by_source_async(paper, paper.get('source', ''), timeout=FETCH_TIMEOUT),
                    timeout=FETCH_TIMEOUT + 5  # 额外的5秒缓冲
                )

                # 将全文添加到论文信息中
                enriched_paper = paper.copy()
                enriched_paper['full_text'] = content_result.get('content', '')
                enriched_paper['content_metadata'] = content_result.get('metadata', {})

                logger.info(f"Successfully got content for paper {i+1}")
                return (i, enriched_paper, 'success')

            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching content for paper {paper.get('paper_id', 'unknown')} (>{FETCH_TIMEOUT}s)")
                # 超时时只使用摘要
                enriched_paper = paper.copy()
                enriched_paper['full_text'] = paper.get('abstract', '')
                enriched_paper['content_metadata'] = {'fallback': True, 'fallback_reason': f'Timeout after {FETCH_TIMEOUT}s'}
                return (i, enriched_paper, 'timeout')
            except Exception as e:
                logger.warning(f"Failed to get content for paper {paper.get('paper_id', 'unknown')}: {e}")
                # 失败时只使用摘要
                enriched_paper = paper.copy()
                enriched_paper['full_text'] = paper.get('abstract', '')
                enriched_paper['content_metadata'] = {'fallback': True, 'fallback_reason': str(e)}
                return (i, enriched_paper, 'error')

        # 批量顺序处理论文：先执行前MAX_CONCURRENT_TASKS个，完成后再执行后面的
        logger.info(f"Fetching content for {len(papers_info)} papers (max {MAX_CONCURRENT_TASKS} concurrent, timeout: {FETCH_TIMEOUT}s)...")

        enriched_papers = []
        total_papers = len(papers_info)

        # 分批处理
        for batch_start in range(0, total_papers, MAX_CONCURRENT_TASKS):
            batch_end = min(batch_start + MAX_CONCURRENT_TASKS, total_papers)
            batch_papers = papers_info[batch_start:batch_end]

            logger.info(f"Processing fetch batch: papers {batch_start+1}-{batch_end}/{total_papers}")

            # 创建当前批次的任务
            batch_tasks = [fetch_paper_content(i, paper) for i, paper in enumerate(batch_papers)]

            # 并行执行当前批次的任务
            batch_results = await asyncio.gather(*batch_tasks)

            # 提取结果
            for i, enriched_paper, status in batch_results:
                enriched_papers.append(enriched_paper)

            # 及时释放内存
            gc.collect()
            logger.info(f"Completed fetch batch {batch_start//MAX_CONCURRENT_TASKS + 1}, memory freed")

        # 使用增强后的论文信息生成报告
        return await generate_research_report(
            papers_info=enriched_papers,
            topic=topic,
            papers_analysis=papers_analysis
        )

    except Exception as e:
        logger.error(f'Failed to generate research report: {str(e)}')
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

