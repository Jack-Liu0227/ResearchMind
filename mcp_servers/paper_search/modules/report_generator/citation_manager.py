"""
Citation Manager Module (引用管理模块)

功能：
1. 文献编号映射管理
2. GB/T 7714-2015 格式化
3. 引用标注处理（^[1]^ → <sup>[1]</sup>）
4. 引用验证与统计
"""

import re
from typing import Dict, Any, List, Tuple, Set
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class CitationManager:
    """引用管理器 - 管理文献编号、格式化和引用追踪"""
    
    def __init__(self, papers_info: List[Dict[str, Any]]):
        """
        初始化引用管理器
        
        Args:
            papers_info: 论文信息列表
        """
        self.papers_info = papers_info
        self.reference_map = self._build_reference_map()
        self.citation_stats = {i: 0 for i in range(1, len(papers_info) + 1)}
        logger.info(f"CitationManager initialized with {len(papers_info)} papers")
    
    def _build_reference_map(self) -> Dict[int, Dict[str, Any]]:
        """构建文献引用映射"""
        ref_map = {}
        for i, paper in enumerate(self.papers_info, 1):
            ref_map[i] = {
                'paper_id': paper.get('paper_id', '') or paper.get('id', '') or paper.get('arxiv_id', ''),
                'title': paper.get('title', 'Unknown'),
                'authors': paper.get('authors', []),
                'year': paper.get('published', '')[:4] if paper.get('published') else 'Unknown',
                'source': paper.get('source', 'unknown'),
                'journal': paper.get('journal', '') or paper.get('venue', ''),
                'volume': paper.get('volume', ''),
                'issue': paper.get('issue', ''),
                'pages': paper.get('pages', ''),
                'doi': paper.get('doi', ''),
                'url': paper.get('url', '') or paper.get('pdf_url', ''),
                'abstract': paper.get('abstract', '')[:300],  # 摘要前300字
                'full_info': paper
            }
        return ref_map
    
    def generate_reference_list_for_prompt(self) -> str:
        """
        为LLM Prompt生成文献列表
        
        Returns:
            格式化的文献列表字符串，供LLM理解和引用
        """
        ref_list = []
        for i, ref in self.reference_map.items():
            # 处理作者
            authors = ref['authors']
            if isinstance(authors, list):
                if len(authors) > 3:
                    author_str = ', '.join(authors[:3]) + ', et al.'
                else:
                    author_str = ', '.join(authors)
            else:
                author_str = str(authors)
            
            # 构建文献条目
            entry = f"""[{i}] {author_str} ({ref['year']}). {ref['title']}
    来源: {ref['source']}
    摘要: {ref['abstract']}..."""
            
            ref_list.append(entry)
        
        return '\n\n'.join(ref_list)
    
    def format_reference_gb7714(self, index: int) -> str:
        """
        按GB/T 7714-2015格式化单条参考文献
        
        Args:
            index: 文献编号（1-based）
        
        Returns:
            格式化的参考文献条目
        """
        if index not in self.reference_map:
            return f"[{index}] 未找到文献信息"
        
        ref = self.reference_map[index]
        
        # 处理作者
        authors = ref['authors']
        if isinstance(authors, list):
            if len(authors) > 3:
                author_str = ', '.join(authors[:3]) + ', 等'
            elif len(authors) > 0:
                author_str = ', '.join(authors)
            else:
                author_str = 'Unknown'
        else:
            author_str = str(authors) if authors else 'Unknown'
        
        title = ref['title']
        year = ref['year']
        source = ref['source']
        
        # 根据来源选择格式
        if source == 'arxiv':
            # arXiv预印本 - 电子文献格式 [EB/OL]
            paper_id = ref['paper_id']
            url = ref['url'] or f"https://arxiv.org/abs/{paper_id}"
            access_date = datetime.now().strftime('%Y-%m-%d')
            # 🔧 使 URL 可点击
            url_link = f"[{url}]({url})" if url else url
            return f"[{index}] {author_str}. {title}[EB/OL]. ({year})[{access_date}]. {url_link}."
        
        elif source in ['semantic_scholar', 'pubmed', 'google_scholar']:
            # 期刊论文格式 [J] 或 [J/OL]
            journal = ref['journal']
            volume = ref['volume']
            issue = ref['issue']
            pages = ref['pages']
            doi = ref['doi']
            url = ref['url']
            
            citation = f"[{index}] {author_str}. {title}"
            
            if journal:
                # 有期刊信息 - 标准期刊格式
                if url or doi:
                    citation += "[J/OL]. "
                else:
                    citation += "[J]. "
                
                citation += f"{journal}, {year}"
                
                if volume:
                    citation += f", {volume}"
                if issue:
                    citation += f"({issue})"
                if pages:
                    citation += f": {pages}"
                
                # 🔧 添加DOI或URL（使其可点击）
                if doi:
                    doi_url = f"https://doi.org/{doi}"
                    citation += f". DOI: [{doi}]({doi_url})"
                elif url:
                    access_date = datetime.now().strftime('%Y-%m-%d')
                    url_link = f"[{url}]({url})"
                    citation += f"[{access_date}]. {url_link}"
            else:
                # 无期刊信息 - 简化格式
                citation += f"[J]. {year}"
                if url:
                    url_link = f"[{url}]({url})"
                    citation += f". {url_link}"

            return citation + "."
        
        else:
            # 通用格式
            url = ref['url']
            citation = f"[{index}] {author_str}. {title}[J]. {year}"
            if url:
                # 🔧 使 URL 可点击
                url_link = f"[{url}]({url})"
                citation += f". {url_link}"
            return citation + "."
    
    def generate_all_references_gb7714(self, use_anchor_links: bool = True) -> str:
        """
        生成完整的参考文献列表（GB/T 7714-2015格式）

        Args:
            use_anchor_links: 是否添加 HTML 锚点和可点击链接（默认 True）

        Returns:
            Markdown格式的参考文献列表
        """
        references = "# 参考文献\n\n"
        for i in range(1, len(self.papers_info) + 1):
            ref_entry = self.format_reference_gb7714(i)

            if use_anchor_links:
                # 🔧 添加 HTML 锚点，使引用可以跳转到这里
                # 格式：<a id="ref-n"></a>[n] 作者. 标题...
                references += f'<a id="ref-{i}"></a>{ref_entry}\n\n'
            else:
                references += f"{ref_entry}\n\n"

        return references

    def process_citations(self, text: str, use_anchor_links: bool = True) -> str:
        """
        处理引用标注：将 ^[1]^ 转换为可点击的 Markdown 锚点链接

        支持的格式：
        - 单个引用：^[1]^ → [1](#ref-1)
        - 范围引用：^[1-3]^ → [1](#ref-1), [2](#ref-2), [3](#ref-3)
        - 多个引用：^[1,3,5]^ → [1](#ref-1), [3](#ref-3), [5](#ref-5)
        - 混合格式：^[1-3,5,7-9]^ → [1](#ref-1), [2](#ref-2), ..., [9](#ref-9)

        Args:
            text: 包含引用标记的文本
            use_anchor_links: 是否使用锚点链接（默认 True）

        Returns:
            处理后的文本
        """
        if use_anchor_links:
            # 🔧 新实现：转换为可点击的 Markdown 锚点链接
            text = self._convert_citation_markers_to_md_links(text)
        else:
            # 旧实现：转换为 <sup> 标签
            # 单个引用：^[数字]^
            text = re.sub(r'\^(\[\d+\])\^', r'<sup>\1</sup>', text)

            # 范围引用：^[数字-数字]^
            text = re.sub(r'\^(\[\d+-\d+\])\^', r'<sup>\1</sup>', text)

            # 多个引用：^[数字,数字,...]^
            text = re.sub(r'\^(\[\d+(?:,\s*\d+)+\])\^', r'<sup>\1</sup>', text)

        # 统计引用次数
        self._update_citation_stats(text)

        return text

    def _convert_citation_markers_to_md_links(self, text: str) -> str:
        """
        将上标引用格式转换为 Markdown 锚点链接

        转换规则：
        - ^[n]^ → [n](#ref-n)
        - ^[1-3]^ → [1](#ref-1), [2](#ref-2), [3](#ref-3)
        - ^[1,3,5]^ → [1](#ref-1), [3](#ref-3), [5](#ref-5)
        - ^[1-3,5,7-9]^ → [1](#ref-1), [2](#ref-2), ..., [9](#ref-9)

        Args:
            text: 包含引用标记的文本

        Returns:
            转换后的文本
        """
        def expand_citation(match):
            """展开引用标记为锚点链接"""
            citation_content = match.group(1)  # 提取 [1-3,5] 中的 1-3,5

            # 解析引用编号
            numbers = []
            parts = citation_content.split(',')

            for part in parts:
                part = part.strip()
                if '-' in part:
                    # 范围引用：1-3
                    start, end = map(int, part.split('-'))
                    numbers.extend(range(start, end + 1))
                else:
                    # 单个引用：1
                    numbers.append(int(part))

            # 生成锚点链接
            links = [f'[{n}](#ref-{n})' for n in numbers]

            # 返回格式化的链接列表
            return ', '.join(links)

        # 匹配 ^[...] 格式的引用标记
        # 支持：^[1]^, ^[1-3]^, ^[1,3,5]^, ^[1-3,5,7-9]^
        pattern = r'\^\[([0-9,\-\s]+)\]\^'
        text = re.sub(pattern, expand_citation, text)

        return text

    def _update_citation_stats(self, text: str):
        """更新引用统计"""
        # 提取所有引用编号
        citations = re.findall(r'<sup>\[(\d+(?:-\d+)?(?:,\s*\d+)*)\]</sup>', text)

        for citation in citations:
            # 处理范围引用 [1-3]
            if '-' in citation:
                start, end = map(int, citation.split('-'))
                for i in range(start, end + 1):
                    if i in self.citation_stats:
                        self.citation_stats[i] += 1
            # 处理多个引用 [1,3,5]
            elif ',' in citation:
                indices = [int(x.strip()) for x in citation.split(',')]
                for i in indices:
                    if i in self.citation_stats:
                        self.citation_stats[i] += 1
            # 处理单个引用 [1]
            else:
                i = int(citation)
                if i in self.citation_stats:
                    self.citation_stats[i] += 1

    def get_citation_statistics(self) -> Dict[int, int]:
        """
        获取引用统计

        Returns:
            {文献编号: 被引用次数}
        """
        return self.citation_stats.copy()

    def get_uncited_papers(self) -> List[int]:
        """
        获取未被引用的文献编号列表

        Returns:
            未被引用的文献编号列表
        """
        return [i for i, count in self.citation_stats.items() if count == 0]

    def validate_citations(self, text: str) -> Tuple[bool, List[str]]:
        """
        验证引用的有效性

        Args:
            text: 包含引用的文本

        Returns:
            (是否全部有效, 错误信息列表)
        """
        errors = []

        # 提取所有引用编号
        citations = re.findall(r'<sup>\[(\d+(?:-\d+)?(?:,\s*\d+)*)\]</sup>', text)

        max_ref = len(self.papers_info)

        for citation in citations:
            # 处理范围引用
            if '-' in citation:
                start, end = map(int, citation.split('-'))
                if start > end:
                    errors.append(f"无效的范围引用 [{start}-{end}]：起始编号大于结束编号")
                if start < 1 or end > max_ref:
                    errors.append(f"引用编号超出范围 [{start}-{end}]：有效范围为 [1-{max_ref}]")
            # 处理多个引用
            elif ',' in citation:
                indices = [int(x.strip()) for x in citation.split(',')]
                for i in indices:
                    if i < 1 or i > max_ref:
                        errors.append(f"引用编号超出范围 [{i}]：有效范围为 [1-{max_ref}]")
            # 处理单个引用
            else:
                i = int(citation)
                if i < 1 or i > max_ref:
                    errors.append(f"引用编号超出范围 [{i}]：有效范围为 [1-{max_ref}]")

        return (len(errors) == 0, errors)

    def generate_citation_report(self) -> str:
        """
        生成引用统计报告

        Returns:
            Markdown格式的统计报告
        """
        total_papers = len(self.papers_info)
        cited_papers = sum(1 for count in self.citation_stats.values() if count > 0)
        uncited = self.get_uncited_papers()

        report = f"""
## 引用统计报告

- **文献总数**: {total_papers}
- **被引用文献数**: {cited_papers}
- **未被引用文献数**: {len(uncited)}
- **引用覆盖率**: {cited_papers/total_papers*100:.1f}%

### 引用频次分布

| 文献编号 | 标题 | 引用次数 |
|---------|------|---------|
"""

        # 按引用次数排序
        sorted_stats = sorted(self.citation_stats.items(), key=lambda x: x[1], reverse=True)

        for i, count in sorted_stats[:10]:  # 只显示前10个
            title = self.reference_map[i]['title'][:50]
            report += f"| [{i}] | {title}... | {count} |\n"

        if uncited:
            report += f"\n### 未被引用的文献\n\n"
            for i in uncited[:5]:  # 只显示前5个
                title = self.reference_map[i]['title'][:50]
                report += f"- [{i}] {title}...\n"

        return report


