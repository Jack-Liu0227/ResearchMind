"""
Reporting Module (报告模块)

功能：
1. 报告生成 - 生成学术规范的研究报告
2. 格式化输出 - Markdown 格式输出
3. 引用管理 - GB/T 7714-2015 格式引用
4. 引用追踪 - 正文中插入引用标注

核心流程：
论文 IDs → 提取全文 → 分析论文 → 构建引用映射 → LLM 生成带引用的综述 → 格式化引用 → 保存报告
"""
import os
import re
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import structlog
from litellm import completion
import asyncio
from .citation_manager import CitationManager

logger = structlog.get_logger(__name__)


def _generate_fallback_analysis(
    paper: Dict[str, Any],
    reason: str,
    error_msg: str = ""
) -> str:
    """
    生成 fallback 分析（超时或失败时使用）

    Args:
        paper: 论文信息字典
        reason: 失败原因（如"分析超时"、"分析失败"）
        error_msg: 详细错误信息（可选）

    Returns:
        Markdown 格式的 fallback 分析文本
    """
    abstract = paper.get('abstract', '')
    full_text = paper.get('full_text', '')
    content_type = paper.get('content_type', '未知')

    # 生成内容预览
    if abstract:
        content_preview = abstract[:200]
    elif full_text:
        content_preview = full_text[:200]
    else:
        content_preview = "信息不足（无摘要和全文）"

    # 生成 fallback 文本
    fallback_text = f"""### 1. 研究背景与动机

**研究解决什么问题？**
{content_preview}

**为什么这个问题重要？**
（{reason}，详细信息请参考原文）

---

### 2. 研究目标

（{reason}，详细信息请参考原文）

---

### 3. 方法论

**使用了什么方法？**
（{reason}，详细信息请参考原文）

**方法有何创新之处？**
（{reason}，详细信息请参考原文）

---

### 4. 主要发现与结果

**关键结果是什么？**
（{reason}，详细信息请参考原文）

**有哪些重要发现？**
（{reason}，详细信息请参考原文）

---

### 5. 创新点与贡献

**这项工作的创新之处？**
（{reason}，详细信息请参考原文）

**对领域的贡献？**
（{reason}，详细信息请参考原文）

---

### 6. 局限性

**存在哪些局限性？**
（{reason}，详细信息请参考原文）

**有哪些未解决的问题？**
（{reason}，详细信息请参考原文）

---

**可用内容**: {content_type}
**内容预览**: {abstract[:500] if abstract else (full_text[:500] if full_text else '无内容')}

*注：{reason}{f'（{error_msg}）' if error_msg else ''}，仅显示可用内容*
"""
    return fallback_text


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

# 🆕 从配置文件导入
import sys
from pathlib import Path as PathLib

# 添加 paper_search 目录到 sys.path
_CURRENT_FILE = PathLib(__file__)
_PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
if str(_PAPER_SEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(_PAPER_SEARCH_DIR))

from config import (
    FETCH_TIMEOUT,
    ANALYSIS_TIMEOUT,
    REPORT_CONTENT_MAX_LENGTH,
    LLM_ANALYSIS_MAX_TOKENS,
    LLM_SYNTHESIS_MAX_TOKENS,
    MAX_CONCURRENT_FETCH,
    MAX_CONCURRENT_ANALYSIS
)


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
        papers_analysis: Optional[List[Dict[str, Any]]] = None,
        progress_callback: Optional[Callable[[dict], Any]] = None  # 🆕 新增进度回调
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
            progress_callback: 进度回调函数（可选）

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
                # 🆕 使用配置中的并发数

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

                # 批量顺序处理论文：先执行前 MAX_CONCURRENT_FETCH 个，完成后再执行后面的
                logger.info(f"Fetching content for {len(papers_needing_content)} papers with max {MAX_CONCURRENT_FETCH} concurrent tasks (timeout: {FETCH_TIMEOUT}s)...")

                fetched_results = []
                total_papers = len(papers_needing_content)

                # 分批处理
                for batch_start in range(0, total_papers, MAX_CONCURRENT_FETCH):
                    batch_end = min(batch_start + MAX_CONCURRENT_FETCH, total_papers)
                    batch_papers = papers_needing_content[batch_start:batch_end]

                    logger.info(f"Processing batch: papers {batch_start+1}-{batch_end}/{total_papers}")

                    # 🆕 发送进度更新
                    if progress_callback:
                        await _send_progress(progress_callback, {
                            "current": batch_start,
                            "total": len(papers_info) + 1,
                            "progress": batch_start / (len(papers_info) + 1),
                            "message": f"正在获取论文内容 ({batch_start+1}-{batch_end}/{total_papers})...",
                            "status": "running"
                        })

                    # 创建当前批次的任务
                    batch_tasks = [fetch_paper_content(i, paper) for i, paper in batch_papers]

                    # 并行执行当前批次的任务
                    batch_results = await asyncio.gather(*batch_tasks)
                    fetched_results.extend(batch_results)

                    # 及时释放内存
                    gc.collect()
                    logger.info(f"Batch {batch_start//MAX_CONCURRENT_FETCH + 1} completed, memory freed")

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

                # 🆕 智能内容截断（保留重要章节）
                if len(content) > REPORT_CONTENT_MAX_LENGTH:
                    try:
                        from ..shared.content_truncator import get_content_truncator
                        truncator = get_content_truncator()
                        content = truncator.truncate(content, paper)
                        logger.info(f"Content truncated intelligently to {len(content)} chars")
                    except Exception as e:
                        logger.warning(f"Smart truncation failed, using simple truncation: {e}")
                        content = content[:REPORT_CONTENT_MAX_LENGTH]

                logger.info(f"Analyzing paper {i+1} using {content_type} ({len(content)} chars, max={REPORT_CONTENT_MAX_LENGTH})")

                # 将content_type存储到paper字典中，以便后续使用
                paper['content_type'] = content_type

                # 🆕 使用领域特定Prompt
                try:
                    from ..shared.domain_prompts import get_domain_prompt
                    analysis_prompt, detected_domain = get_domain_prompt(
                        paper=paper,
                        content=content,
                        content_type=content_type
                    )
                    # 存储检测到的领域
                    paper['detected_domain'] = detected_domain
                    logger.info(f"Using {detected_domain} domain prompt for paper {i+1}")
                except Exception as e:
                    logger.warning(f"Failed to get domain prompt, using general prompt: {e}")
                    # 降级到通用Prompt
                    analysis_prompt = f"""分析以下论文（中文输出）：

**论文信息**
标题: {paper.get('title', 'Unknown')}
作者: {', '.join(paper.get('authors', [])[:3])}{'等' if len(paper.get('authors', [])) > 3 else ''}
发表: {paper.get('published', 'Unknown')}
依据: {content_type}

**内容**
{content}

**输出格式示例**

### 1. 研究背景与动机
本研究针对[具体问题]，该问题在[领域]中至关重要，因为[原因]。

### 2. 研究目标
旨在[具体目标1]、[具体目标2]。

### 3. 方法论
采用[方法名称]，创新点在于[具体创新]。

### 4. 主要发现与结果
- 关键发现1：[具体结果]
- 关键发现2：[具体结果]

### 5. 创新点与贡献
- 创新：[具体创新点]
- 贡献：[对领域的具体贡献]

### 6. 局限性
- 局限1：[具体局限]
- 未解决：[具体问题]

**要求**：专业、客观、简洁（每部分2-3句）
"""
                    paper['detected_domain'] = 'general'

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
                                max_tokens=LLM_ANALYSIS_MAX_TOKENS  # 🔧 使用环境变量配置
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
                    # 🆕 使用统一的 fallback 函数
                    fallback_analysis = _generate_fallback_analysis(paper, "分析超时")
                    return (i, {'paper': paper, 'analysis': fallback_analysis}, 'timeout')
                except Exception as e:
                    logger.error(f"Failed to analyze paper {i+1}: {e}")
                    # 🆕 使用统一的 fallback 函数
                    fallback_analysis = _generate_fallback_analysis(paper, "分析失败", str(e))
                    return (i, {'paper': paper, 'analysis': fallback_analysis}, 'error')

            # 批量顺序处理论文：先执行前 MAX_CONCURRENT_ANALYSIS 个，完成后再执行后面的
            logger.info(f"Starting batch analysis of {len(enriched_papers)} papers (max {MAX_CONCURRENT_ANALYSIS} concurrent, timeout: {ANALYSIS_TIMEOUT}s)...")
            detailed_analyses = []
            total_papers = len(enriched_papers)

            # 分批处理
            for batch_start in range(0, total_papers, MAX_CONCURRENT_ANALYSIS):
                batch_end = min(batch_start + MAX_CONCURRENT_ANALYSIS, total_papers)
                batch_papers = enriched_papers[batch_start:batch_end]

                logger.info(f"Processing analysis batch: papers {batch_start+1}-{batch_end}/{total_papers}")

                # 🆕 发送进度更新
                if progress_callback:
                    await _send_progress(progress_callback, {
                        "current": batch_start,
                        "total": len(papers_info) + 1,
                        "progress": batch_start / (len(papers_info) + 1),
                        "message": f"正在分析论文 ({batch_start+1}-{batch_end}/{total_papers})...",
                        "status": "running"
                    })

                # 创建当前批次的任务
                batch_tasks = [analyze_single_paper(i, paper) for i, paper in enumerate(batch_papers)]

                # 并行执行当前批次的任务
                batch_results = await asyncio.gather(*batch_tasks)

                # 提取结果
                for i, result, status in batch_results:
                    detailed_analyses.append(result)

                # 及时释放内存
                gc.collect()
                logger.info(f"Completed analysis batch {batch_start//MAX_CONCURRENT_ANALYSIS + 1}, memory freed")

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

            # 第三步：初始化引用管理器
            logger.info("Initializing citation manager...")
            citation_manager = CitationManager(papers_info)

            # 生成文献列表供LLM参考
            reference_list_for_llm = citation_manager.generate_reference_list_for_prompt()

            # 第四步：生成综合总结（使用所有论文的分析 + 引用管理）
            logger.info("Generating synthesis with citation tracking...")

            # 使用所有论文的详细分析来生成综合总结
            # 为了生成更全面的报告，我们使用所有文献
            selected_analyses = analyses_summary

            synthesis_prompt = f"""你是一位资深学术研究员，正在撰写一份关于"{topic}"的综合研究报告。

**重要要求 - 引用规范**：
1. 在陈述观点、数据、方法时，必须标注文献来源
2. 引用格式：在句末用 ^[序号]^ 标注，例如："深度学习可以预测材料性能^[1]^"
3. 多篇文献：^[1,2,5]^ 或 ^[1-3]^
4. 每个关键论断都要有文献支撑
5. 引用要均衡分布，避免某些文献被忽略

**文献资料**（共{len(papers_info)}篇）：

{reference_list_for_llm}

**详细分析**：
{''.join(selected_analyses[:])}

（注：为节省token，仅显示前5篇详细分析，但请基于所有{len(papers_info)}篇文献生成综述）

请生成以下部分（使用中文，符合学术写作规范）：

## 摘要 (Abstract)
- 研究背景（1-2句）
- 调研范围与方法（1句）
- 主要发现（2-3句）
- 研究意义（1句）
（总计150-200字）

## 1. 引言 (Introduction)
### 1.1 研究背景
- 领域重要性和发展历程
- 当前面临的主要挑战

### 1.2 调研目的与范围
- 本次调研的目标
- 文献来源与筛选标准
- 调研时间范围

## 2. 研究现状综述 (Literature Review)
### 2.1 主流技术路线
- 技术方法分类与对比
- 各方法的理论基础
- 代表性工作总结

### 2.2 关键技术分析
- 核心技术要点
- 技术优势与局限
- 性能对比分析

### 2.3 应用场景与案例
- 典型应用领域
- 成功案例分析
- 实际应用中的挑战

## 3. 研究趋势与热点 (Trends and Hotspots)
### 3.1 当前研究热点
- 高频研究主题
- 新兴研究方向
- 跨学科融合趋势

### 3.2 技术演进路径
- 历史发展脉络
- 当前技术前沿
- 未来发展预测

### 3.3 关键发现与创新点
- 重要突破性成果
- 创新性方法与思路
- 对领域的贡献

## 4. 研究空白与机遇 (Research Gaps and Opportunities)
### 4.1 现有研究的局限性
- 方法论局限
- 数据与实验局限
- 理论框架不足

### 4.2 未解决的关键问题
- 技术瓶颈
- 理论难题
- 应用障碍

### 4.3 潜在研究方向
- 值得深入的研究课题
- 跨学科合作机会
- 创新性研究思路

## 5. 结论与展望 (Conclusion and Future Work)
### 5.1 主要结论
- 核心发现总结
- 技术现状评估
- 领域发展态势

### 5.2 研究建议
- 对研究者的建议
- 对实践者的建议
- 对政策制定者的建议

### 5.3 未来展望
- 短期发展预期（1-2年）
- 中长期发展方向（3-5年）
- 潜在突破性进展

要求：
1. 语言专业、客观、严谨
2. 逻辑清晰、层次分明
3. 有深度、有见解
4. 引用具体文献支撑观点
5. 避免空泛表述，注重实质内容
"""

            # 🆕 发送综合报告生成进度
            if progress_callback:
                await _send_progress(progress_callback, {
                    "current": len(papers_info),
                    "total": len(papers_info) + 1,
                    "progress": len(papers_info) / (len(papers_info) + 1),
                    "message": "正在生成综合研究报告...",
                    "status": "running"
                })

            try:
                # 🆕 使用流式生成处理器
                from ..shared.streaming_handler import get_streaming_handler

                # 添加 paper_search 目录到 sys.path
                import sys
                from pathlib import Path as PathLib
                _CURRENT_FILE = PathLib(__file__)
                _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
                if str(_PAPER_SEARCH_DIR) not in sys.path:
                    sys.path.insert(0, str(_PAPER_SEARCH_DIR))

                from config import ENABLE_STREAMING

                streaming_handler = get_streaming_handler(
                    model=self.model,
                    enable_streaming=ENABLE_STREAMING
                )

                # 定义流式回调函数
                async def stream_callback(content_chunk: str):
                    """流式内容回调"""
                    if progress_callback:
                        await _send_progress(progress_callback, {
                            "current": len(papers_info),
                            "total": len(papers_info) + 1,
                            "progress": len(papers_info) / (len(papers_info) + 1),
                            "message": "正在生成综合研究报告...",
                            "status": "streaming",
                            "stream_content": content_chunk  # 🆕 流式内容片段
                        })

                # 使用流式生成（如果启用）
                report_content = await streaming_handler.generate_with_streaming(
                    messages=[{"role": "user", "content": synthesis_prompt}],
                    temperature=0.7,
                    max_tokens=LLM_SYNTHESIS_MAX_TOKENS,
                    stream_callback=stream_callback if ENABLE_STREAMING else None
                )

                if not report_content:
                    logger.warning("LLM returned empty content for synthesis, using fallback")
                    report_content = "## 摘要\n\n（综合分析生成失败，请查看附录中的详细文献分析）\n"
                else:
                    # 处理引用标注：^[1]^ → <sup>[1]</sup>
                    logger.info("Processing citation markers...")
                    report_content = citation_manager.process_citations(report_content)

                    # 验证引用有效性
                    is_valid, errors = citation_manager.validate_citations(report_content)
                    if not is_valid:
                        logger.warning(f"Citation validation found {len(errors)} issues:")
                        for error in errors[:5]:  # 只记录前5个错误
                            logger.warning(f"  - {error}")
                    else:
                        logger.info("All citations validated successfully")

                    # 记录引用统计
                    uncited = citation_manager.get_uncited_papers()
                    if uncited:
                        logger.warning(f"{len(uncited)} papers were not cited in the synthesis")
                        logger.debug(f"Uncited papers: {uncited[:10]}")  # 只记录前10个

            except Exception as llm_error:
                logger.error(f"LLM synthesis failed: {llm_error}")
                logger.warning("Using fallback synthesis content")
                report_content = "## 摘要\n\n（综合分析生成失败，请查看附录中的详细文献分析）\n"

            # 及时释放内存
            gc.collect()

            # 添加元数据（学术报告格式）
            header = f"""# {topic}
## 学术调研报告

---

**报告信息**

| 项目 | 内容 |
|------|------|
| 生成时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| 文献数量 | {len(papers_info)} 篇 |
| 分析方法 | AI深度分析（基于LLM） |
| 报告类型 | 综合性学术调研报告 |

---

"""

            # 组合最终报告 = 头部 + 综合总结（主报告）+ 附录（详细分析）
            # 将详细的单篇分析移至附录
            appendix_section = f"""

---

# 附录：详细文献分析

本附录包含对每篇文献的详细分析，供深入研究参考。

{''.join(analyses_summary)}
"""

            full_report = header + report_content + appendix_section

            # 添加参考文献（使用CitationManager生成GB/T 7714-2015格式）
            logger.info("Generating references in GB/T 7714-2015 format...")
            references = "\n\n---\n\n" + citation_manager.generate_all_references_gb7714()

            full_report += references

            # 记录引用统计
            citation_stats = citation_manager.get_citation_statistics()
            cited_count = sum(1 for c in citation_stats.values() if c > 0)
            logger.info(f"Citation statistics: {cited_count}/{len(papers_info)} papers cited")

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
    papers_analysis: Optional[List[Dict[str, Any]]] = None,
    progress_callback: Optional[Callable[[dict], Any]] = None,  # 🆕 新增进度回调
    session_id: str = "default",  # 🆕 新增会话ID参数
    save_version: bool = True  # 🆕 新增是否保存版本参数
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
        progress_callback: 进度回调函数（可选）
        session_id: 会话ID（用于版本管理）
        save_version: 是否保存版本（默认True）

    Returns:
        Dict containing:
        - report_content: Markdown format的报告内容
        - metadata: 报告元数据
        - version_info: 版本信息（如果save_version=True）
    """
    try:
        logger.info(f'Generating comprehensive research report for topic: {topic} with {len(papers_info)} papers')

        # 🆕 发送初始进度
        if progress_callback:
            await _send_progress(progress_callback, {
                "current": 0,
                "total": len(papers_info) + 1,  # 论文数 + 1个综合步骤
                "progress": 0.0,
                "message": f"准备生成研究报告（{len(papers_info)} 篇论文）...",
                "status": "running"
            })

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
            papers_analysis=papers_analysis,
            progress_callback=progress_callback  # 🆕 传递回调
        )

        logger.info(f'Research report generated successfully')

        # 🆕 保存报告版本（如果启用）
        version_info = None
        if save_version:
            try:
                from ..shared.report_version_manager import get_version_manager

                version_manager = get_version_manager(session_id)
                version_info = version_manager.save_report_version(
                    report_content=full_report,
                    topic=topic,
                    papers_count=len(papers_info),
                    analysis_params={
                        'model': report_gen.model,
                        'mode': 'comprehensive'
                    },
                    metadata={
                        'structured_analyses_count': len(structured_analyses)
                    }
                )
                logger.info(f"Report version saved: {version_info['version_id']}")
            except Exception as e:
                logger.error(f"Failed to save report version: {e}")
                # 不影响主流程，继续执行

        # 🆕 发送完成消息
        if progress_callback:
            await _send_progress(progress_callback, {
                "current": len(papers_info) + 1,
                "total": len(papers_info) + 1,
                "progress": 1.0,
                "message": f"研究报告生成完成！",
                "status": "success"
            })

        # 返回内容供前端使用
        result = {
            'status': 'success',
            'report': full_report,
            'papers_count': len(papers_info),
            'topic': topic,
            'timestamp': datetime.now().isoformat(),
            'message': 'Research report generated successfully.',
            'mode': 'comprehensive',
            'structured_analyses': structured_analyses,  # 添加结构化分析数据
            'version_info': version_info  # 🆕 添加版本信息
        }

        return result

    except Exception as e:
        logger.error(f'Failed to generate research report: {str(e)}')
        import traceback
        logger.error(f'Traceback: {traceback.format_exc()}')

        # 🆕 发送错误消息
        if progress_callback:
            await _send_progress(progress_callback, {
                "current": 0,
                "total": len(papers_info) + 1 if papers_info else 1,
                "progress": 0.0,
                "message": f"报告生成失败: {str(e)}",
                "status": "error",
                "error": str(e)
            })

        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def _send_progress(callback: Callable, progress_data: dict):
    """发送进度更新（支持同步和异步回调）"""
    try:
        import asyncio
        if asyncio.iscoroutinefunction(callback):
            await callback(progress_data)
        else:
            callback(progress_data)
    except Exception as e:
        logger.error(f"发送进度更新失败: {str(e)}")


async def generate_research_report_with_data_collection(
    papers_info: List[Dict[str, Any]],
    topic: str,
    papers_analysis: Optional[List[Dict[str, Any]]] = None,
    progress_callback: Optional[Callable[[dict], Any]] = None,  # 🆕 新增进度回调
    session_id: str = "default",  # 🆕 新增会话ID参数
    save_version: bool = True  # 🆕 新增是否保存版本参数
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
        progress_callback: 进度回调函数（可选）
        session_id: 会话ID（用于版本管理）
        save_version: 是否保存版本（默认True）

    Returns:
        Dict containing report and metadata
    """
    try:
        logger.info(f'Generating research report for topic: {topic} with {len(papers_info)} papers')

        # 异步并行获取所有论文的全文
        import gc
        from ..paper_manager.content_fetcher import get_paper_content_by_source_async

        # 🆕 使用配置中的并发数

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

        # 批量顺序处理论文：先执行前 MAX_CONCURRENT_FETCH 个，完成后再执行后面的
        logger.info(f"Fetching content for {len(papers_info)} papers (max {MAX_CONCURRENT_FETCH} concurrent, timeout: {FETCH_TIMEOUT}s)...")

        enriched_papers = []
        total_papers = len(papers_info)

        # 分批处理
        for batch_start in range(0, total_papers, MAX_CONCURRENT_FETCH):
            batch_end = min(batch_start + MAX_CONCURRENT_FETCH, total_papers)
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
            logger.info(f"Completed fetch batch {batch_start//MAX_CONCURRENT_FETCH + 1}, memory freed")

        # 使用增强后的论文信息生成报告
        return await generate_research_report(
            papers_info=enriched_papers,
            topic=topic,
            papers_analysis=papers_analysis,
            progress_callback=progress_callback,  # 🆕 传递回调
            session_id=session_id,  # 🆕 传递会话ID
            save_version=save_version  # 🆕 传递版本保存标志
        )

    except Exception as e:
        logger.error(f'Failed to generate research report: {str(e)}')
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

