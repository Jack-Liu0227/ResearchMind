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
from typing import Dict, Any, List
from datetime import datetime
import structlog
from litellm import completion

logger = structlog.get_logger(__name__)


class ResearchReportGenerator:
    """
    优化的研究报告生成器

    新的报告生成模式：
    1. 综合报告：基于所有文献生成完整调研报告
    2. 单篇分析：深度分析单篇论文
    3. 对比分析：多篇论文对比
    4. 空白分析：识别研究空白和机会
    """

    def __init__(self, model: str = None):
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
        papers_analysis: List[Dict[str, Any]] = None
    ) -> str:
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
            # 第一步：为每篇论文生成详细分析（限制并发数量以节省内存）
            import asyncio
            import gc

            # 内存优化：限制并发任务数量
            MAX_CONCURRENT_TASKS = 8  # 限制为8个并发任务，高并发处理
            BATCH_SIZE = 8  # 每批处理8篇论文

            async def analyze_single_paper(i, paper):
                """分析单篇论文"""
                logger.info(f"Analyzing paper {i+1}/{len(papers_info)}: {paper.get('title', 'Unknown')[:50]}...")

                # 获取全文或摘要
                full_text = paper.get('full_text', '')
                abstract = paper.get('abstract', '')
                content = full_text if full_text and len(full_text) > 100 else abstract

                # 内存优化：截断内容长度
                content = content[:3000]  # 减少从5000到3000

                # 生成单篇论文的详细分析
                analysis_prompt = f"""请对以下论文进行深度分析：

标题: {paper.get('title', 'Unknown')}
作者: {', '.join(paper.get('authors', []))}
发表时间: {paper.get('published', 'Unknown')}
URL: {paper.get('url', 'N/A')}

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
                    # 使用 asyncio 包装同步的 completion 调用
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: completion(
                            model=self.model,
                            messages=[{"role": "user", "content": analysis_prompt}],
                            temperature=0.3,
                            max_tokens=1500  # 减少token数量以节省内存
                        )
                    )

                    analysis_text = response.choices[0].message.content.strip()
                    logger.info(f"Successfully analyzed paper {i+1}")
                    return {
                        'paper': paper,
                        'analysis': analysis_text
                    }

                except Exception as e:
                    logger.error(f"Failed to analyze paper {i+1}: {e}")
                    # 使用简单分析作为后备
                    return {
                        'paper': paper,
                        'analysis': f"**摘要**: {abstract[:300]}..."
                    }

            # 分批处理论文以节省内存
            logger.info(f"Starting batch analysis of {len(papers_info)} papers (batch size: {BATCH_SIZE})...")
            detailed_analyses = []

            for batch_start in range(0, len(papers_info), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(papers_info))
                batch_papers = papers_info[batch_start:batch_end]

                logger.info(f"Processing batch {batch_start//BATCH_SIZE + 1}: papers {batch_start+1}-{batch_end}")

                # 使用信号量限制并发任务数量
                semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

                async def bounded_analyze(i, paper):
                    async with semaphore:
                        return await analyze_single_paper(batch_start + i, paper)

                # 处理当前批次
                batch_tasks = [bounded_analyze(i, paper) for i, paper in enumerate(batch_papers)]
                batch_results = await asyncio.gather(*batch_tasks)
                detailed_analyses.extend(batch_results)

                # 及时释放内存
                gc.collect()
                logger.info(f"Completed batch {batch_start//BATCH_SIZE + 1}, memory freed")

            logger.info(f"Completed analysis of {len(papers_info)} papers")

            # 第二步：准备所有分析的摘要（内存优化版本）
            analyses_summary = []
            for i, item in enumerate(detailed_analyses, 1):
                paper = item['paper']
                analysis = item['analysis']
                summary = f"""
## 文献 {i}: {paper.get('title', 'Unknown')}

**作者**: {', '.join(paper.get('authors', []))}
**发表时间**: {paper.get('published', 'Unknown')}
**URL**: {paper.get('url', 'N/A')}

{analysis}

---
"""
                analyses_summary.append(summary)

            # 第三步：生成综合总结（内存优化：分段处理）
            logger.info("Generating synthesis from detailed analyses...")

            # 内存优化：只使用前3篇论文的详细分析来生成综合总结
            # 这样可以显著减少token数量和内存使用
            max_analyses_for_synthesis = min(3, len(analyses_summary))
            selected_analyses = analyses_summary[:max_analyses_for_synthesis]

            synthesis_prompt = f"""基于以下 {len(detailed_analyses)} 篇论文的分析（展示前 {max_analyses_for_synthesis} 篇详细分析），生成一份综合研究报告。

研究主题: {topic}

详细分析（代表性论文）:
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

            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.7,
                max_tokens=2000  # 减少从3000到2000
            )

            report_content = response.choices[0].message.content.strip()

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
            # 内存优化：只包含前5篇论文的详细分析，其余论文在参考文献中列出
            max_detailed_analyses = min(5, len(analyses_summary))
            detailed_section = ''.join(analyses_summary[:max_detailed_analyses])

            full_report = header + report_content + "\n\n---\n\n# 详细文献分析\n\n" + detailed_section

            # 如果有更多论文，添加说明
            if len(analyses_summary) > max_detailed_analyses:
                full_report += f"\n\n*注：本报告详细展示了前 {max_detailed_analyses} 篇论文的分析，其余 {len(analyses_summary) - max_detailed_analyses} 篇论文的信息见参考文献。*\n"

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

                if source == 'arxiv':
                    references += f"[{i}] {authors}. \"{title}\". arXiv:{paper_id}, {year}.\n"
                else:
                    url = paper.get('url', '')
                    references += f"[{i}] {authors}. \"{title}\". {year}. {url}\n"

            full_report += references

            # 最后释放内存
            gc.collect()

            logger.info("Comprehensive report generated successfully")
            return full_report

        except Exception as e:
            logger.error(f"Failed to generate comprehensive report: {e}")
            # 降级到简单报告
            return self._generate_simple_report(papers_info, topic, papers_analysis)

    async def generate_lightweight_report(
        self,
        papers_info: List[Dict[str, Any]],
        topic: str,
        papers_analysis: List[Dict[str, Any]] = None
    ) -> str:
        """
        生成轻量级报告（内存受限环境专用）

        特点：
        - 不使用LLM进行详细分析
        - 只提取摘要和关键信息
        - 内存占用极低
        - 适合4G内存环境

        Args:
            papers_info: 论文信息列表
            topic: 研究主题
            papers_analysis: 论文分析列表（可选）

        Returns:
            str: Markdown格式的轻量级报告
        """
        logger.info(f"Generating lightweight report for {len(papers_info)} papers (memory-optimized)")

        report_sections = []

        # 标题
        report_sections.append(f"# {topic} - 研究调研报告（轻量版）\n")
        report_sections.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_sections.append(f"**文献数量**: {len(papers_info)}\n")
        report_sections.append(f"**生成方式**: 轻量级摘要（内存优化）\n\n")

        # 文献统计
        report_sections.append("## 文献统计\n\n")
        report_sections.append(f"- 总论文数: {len(papers_info)}\n")

        # 按来源统计
        sources = {}
        for paper in papers_info:
            source = paper.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1

        for source, count in sources.items():
            report_sections.append(f"- {source}: {count}篇\n")

        report_sections.append("\n")

        # 文献列表
        report_sections.append("## 文献列表\n\n")
        for i, paper in enumerate(papers_info, 1):
            report_sections.append(f"### {i}. {paper.get('title', 'Unknown Title')}\n\n")

            # 安全处理authors字段
            authors_raw = paper.get('authors', ['Unknown'])
            if isinstance(authors_raw, list):
                authors_str = ', '.join(str(a) for a in authors_raw)
            else:
                authors_str = str(authors_raw)

            report_sections.append(f"- **作者**: {authors_str}\n")
            report_sections.append(f"- **发表时间**: {paper.get('published', 'Unknown')}\n")
            report_sections.append(f"- **来源**: {paper.get('source', 'unknown')}\n")

            url = paper.get('url', '')
            if url:
                report_sections.append(f"- **链接**: {url}\n")

            abstract = paper.get('abstract', '')
            if abstract:
                report_sections.append(f"\n**摘要**: {abstract[:200]}...\n\n")

        # 参考文献
        report_sections.append("\n## 参考文献\n\n")
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

            if source == 'arxiv':
                paper_id = paper.get('paper_id', 'unknown')
                report_sections.append(f"[{i}] {authors}. \"{title}\". arXiv:{paper_id}, {year}.\n")
            else:
                url = paper.get('url', '')
                report_sections.append(f"[{i}] {authors}. \"{title}\". {year}. {url}\n")

        logger.info("Lightweight report generated successfully")
        return '\n'.join(report_sections)

    def _generate_simple_report(
        self,
        papers_info: List[Dict[str, Any]],
        topic: str,
        papers_analysis: List[Dict[str, Any]] = None
    ) -> str:
        """
        生成简单报告（降级方案，不使用LLM）
        """
        report_sections = []

        # 标题
        report_sections.append(f"# {topic} - 研究调研报告\n")
        report_sections.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_sections.append(f"**文献数量**: {len(papers_info)}\n\n")

        # 文献列表
        report_sections.append("## 文献列表\n\n")
        for i, paper in enumerate(papers_info, 1):
            report_sections.append(f"### {i}. {paper.get('title', 'Unknown Title')}\n\n")

            # 安全处理authors字段
            authors_raw = paper.get('authors', ['Unknown'])
            if isinstance(authors_raw, list):
                authors_str = ', '.join(str(a) for a in authors_raw)
            else:
                authors_str = str(authors_raw)

            report_sections.append(f"- **作者**: {authors_str}\n")
            report_sections.append(f"- **发表时间**: {paper.get('published', 'Unknown')}\n")
            report_sections.append(f"- **来源**: {paper.get('source', 'unknown')}\n")

            url = paper.get('url', '')
            if url:
                report_sections.append(f"- **链接**: {url}\n")

            abstract = paper.get('abstract', '')
            if abstract:
                report_sections.append(f"\n**摘要**: {abstract[:300]}...\n\n")

            # 如果有分析结果
            if papers_analysis and i-1 < len(papers_analysis):
                analysis = papers_analysis[i-1]
                if analysis and 'key_info' in analysis:
                    key_info = analysis['key_info']
                    if key_info.get('innovation'):
                        report_sections.append(f"**创新点**: {key_info['innovation']}\n\n")

        # 参考文献
        report_sections.append("\n## 参考文献\n\n")
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

            if source == 'arxiv':
                paper_id = paper.get('paper_id', 'unknown')
                report_sections.append(f"[{i}] {authors}. \"{title}\". arXiv:{paper_id}, {year}.\n")
            else:
                url = paper.get('url', '')
                report_sections.append(f"[{i}] {authors}. \"{title}\". {year}. {url}\n")

        return '\n'.join(report_sections)


# ============================================================================
# 外部接口函数（保持向后兼容）
# ============================================================================

async def generate_research_report(
    papers_info: List[Dict[str, Any]],
    topic: str,
    papers_analysis: List[Dict[str, Any]] = None,
    use_lightweight_mode: bool = False
) -> Dict[str, Any]:
    """
    生成综合研究报告（优化版）

    新的报告生成模式：
    - 使用LLM一次性生成完整的专业调研报告
    - 包含研究概述、核心发现、技术路线、趋势分析、研究空白等
    - 自动降级到简单报告（如果LLM失败）
    - 支持轻量级模式（内存受限环境）

    Args:
        papers_info: 论文信息列表（必须包含title, authors, abstract等）
        topic: 研究主题
        papers_analysis: 论文分析列表（可选，如果有会包含更多细节）
        use_lightweight_mode: 是否使用轻量级模式（内存受限环境）

    Returns:
        Dict containing:
        - report_content: Markdown格式的报告内容
        - metadata: 报告元数据
    """
    try:
        logger.info(f'Generating research report for topic: {topic} with {len(papers_info)} papers')
        logger.info(f'Lightweight mode: {use_lightweight_mode}')

        # Initialize report generator
        report_gen = ResearchReportGenerator()

        if not papers_info:
            return {
                'status': 'error',
                'error': 'No valid papers found',
                'timestamp': datetime.now().isoformat()
            }

        # 根据模式选择报告生成方法
        if use_lightweight_mode:
            logger.info("Using lightweight report generation (memory-optimized)")
            full_report = await report_gen.generate_lightweight_report(
                papers_info=papers_info,
                topic=topic,
                papers_analysis=papers_analysis
            )
        else:
            logger.info("Using comprehensive report generation")
            # Generate comprehensive report using new method
            full_report = await report_gen.generate_comprehensive_report(
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
            'mode': 'lightweight' if use_lightweight_mode else 'comprehensive'
        }

        return result

    except Exception as e:
        logger.error(f'Failed to generate research report: {str(e)}')
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def generate_research_report_with_data_collection(
    papers_info: List[Dict[str, Any]],
    topic: str,
    papers_analysis: List[Dict[str, Any]] = None
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

        # 获取所有论文的全文
        from ..paper_manager.content_fetcher import get_paper_content_by_source

        enriched_papers = []
        for paper in papers_info:
            try:
                # 获取全文
                content_result = get_paper_content_by_source(paper, paper.get('source'))

                # 将全文添加到论文信息中
                enriched_paper = paper.copy()
                enriched_paper['full_text'] = content_result.get('content', '')
                enriched_paper['content_metadata'] = content_result.get('metadata', {})

                enriched_papers.append(enriched_paper)

                logger.info(f"Got content for paper: {paper.get('title', 'Unknown')[:50]}...")

            except Exception as e:
                logger.warning(f"Failed to get content for paper {paper.get('paper_id', 'unknown')}: {e}")
                # 失败时只使用摘要
                enriched_paper = paper.copy()
                enriched_paper['full_text'] = paper.get('abstract', '')
                enriched_paper['content_metadata'] = {'fallback': True, 'fallback_reason': str(e)}
                enriched_papers.append(enriched_paper)

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

