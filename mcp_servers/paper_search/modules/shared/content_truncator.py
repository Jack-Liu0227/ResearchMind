"""
智能内容截断模块

功能：
1. 智能截断论文内容，保留最重要的部分
2. 优先保留：摘要、引言、结论、方法、结果
3. 避免简单的字符截断，保持内容完整性
"""
import re
from typing import Dict, Any, List, Tuple
import structlog

logger = structlog.get_logger(__name__)


class ContentTruncator:
    """智能内容截断器"""
    
    # 重要章节的关键词（按优先级排序）
    SECTION_KEYWORDS = {
        'abstract': ['abstract', '摘要', 'summary'],
        'introduction': ['introduction', '引言', '介绍', 'background'],
        'method': ['method', 'approach', '方法', 'methodology', 'technique'],
        'result': ['result', 'finding', '结果', 'experiment', 'evaluation'],
        'conclusion': ['conclusion', 'discussion', '结论', '讨论', 'summary'],
        'related_work': ['related work', '相关工作', 'literature review']
    }
    
    # 章节优先级（数字越小优先级越高）
    SECTION_PRIORITY = {
        'abstract': 1,
        'conclusion': 2,
        'result': 3,
        'method': 4,
        'introduction': 5,
        'related_work': 6
    }
    
    def __init__(self, max_length: int = None):
        """
        初始化内容截断器
        
        Args:
            max_length: 最大长度（字符数），默认从配置读取
        """
        if max_length is None:
            try:
                # 添加 paper_search 目录到 sys.path
                import sys
                from pathlib import Path as PathLib
                _CURRENT_FILE = PathLib(__file__)
                _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
                if str(_PAPER_SEARCH_DIR) not in sys.path:
                    sys.path.insert(0, str(_PAPER_SEARCH_DIR))

                from config import REPORT_CONTENT_MAX_LENGTH
                max_length = REPORT_CONTENT_MAX_LENGTH
            except:
                max_length = 12000
        
        self.max_length = max_length
        logger.info(f"ContentTruncator initialized with max_length={max_length}")
    
    def truncate(self, content: str, paper: Dict[str, Any] = None) -> str:
        """
        智能截断内容
        
        Args:
            content: 原始内容
            paper: 论文信息（可选，用于上下文）
        
        Returns:
            截断后的内容
        """
        if len(content) <= self.max_length:
            return content
        
        logger.info(f"Truncating content from {len(content)} to {self.max_length} chars")
        
        # 1. 尝试提取结构化章节
        sections = self._extract_sections(content)
        
        if sections:
            # 2. 按优先级选择章节
            truncated = self._select_sections_by_priority(sections)
            logger.info(f"Truncated using section-based approach: {len(truncated)} chars")
            return truncated
        else:
            # 3. 如果无法提取章节，使用智能截断
            truncated = self._smart_truncate(content)
            logger.info(f"Truncated using smart approach: {len(truncated)} chars")
            return truncated
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """
        提取内容中的章节
        
        Returns:
            章节字典 {section_type: content}
        """
        sections = {}
        
        # 尝试匹配常见的章节标题格式
        # 格式1: "## Abstract" 或 "# Abstract"
        # 格式2: "1. Introduction" 或 "I. Introduction"
        # 格式3: "Abstract\n=====" 或 "Abstract\n-----"
        
        for section_type, keywords in self.SECTION_KEYWORDS.items():
            for keyword in keywords:
                # 尝试多种格式
                patterns = [
                    rf'#+\s*{keyword}\s*\n(.*?)(?=\n#+\s*|\Z)',  # Markdown 标题
                    rf'\n{keyword}\s*\n[=\-]+\n(.*?)(?=\n\w+\s*\n[=\-]+|\Z)',  # 下划线标题
                    rf'\n\d+\.\s*{keyword}\s*\n(.*?)(?=\n\d+\.|\Z)',  # 数字标题
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                    if match:
                        section_content = match.group(1).strip()
                        if section_content and len(section_content) > 50:
                            sections[section_type] = section_content
                            break
                
                if section_type in sections:
                    break
        
        return sections
    
    def _select_sections_by_priority(self, sections: Dict[str, str]) -> str:
        """
        按优先级选择章节，直到达到最大长度
        
        Args:
            sections: 章节字典
        
        Returns:
            组合后的内容
        """
        # 按优先级排序
        sorted_sections = sorted(
            sections.items(),
            key=lambda x: self.SECTION_PRIORITY.get(x[0], 99)
        )
        
        result_parts = []
        current_length = 0
        
        for section_type, section_content in sorted_sections:
            section_header = f"\n\n## {section_type.replace('_', ' ').title()}\n\n"
            section_full = section_header + section_content
            
            if current_length + len(section_full) <= self.max_length:
                result_parts.append(section_full)
                current_length += len(section_full)
            else:
                # 如果剩余空间足够，截断当前章节
                remaining = self.max_length - current_length
                if remaining > 200:  # 至少保留 200 字符
                    truncated_section = section_header + section_content[:remaining - len(section_header) - 50] + "\n\n[...]"
                    result_parts.append(truncated_section)
                break
        
        return ''.join(result_parts)
    
    def _smart_truncate(self, content: str) -> str:
        """
        智能截断（当无法提取章节时使用）
        
        策略：
        1. 保留开头（通常是摘要/引言）
        2. 保留结尾（通常是结论）
        3. 在句子边界截断
        
        Args:
            content: 原始内容
        
        Returns:
            截断后的内容
        """
        # 分配比例：开头 60%，结尾 40%
        head_length = int(self.max_length * 0.6)
        tail_length = int(self.max_length * 0.4)
        
        # 提取开头部分（在句子边界截断）
        head = self._truncate_at_sentence_boundary(content[:head_length * 2], head_length)
        
        # 提取结尾部分（在句子边界截断）
        tail_start = max(len(content) - tail_length * 2, head_length * 2)
        tail = self._truncate_at_sentence_boundary(content[tail_start:], tail_length, from_end=True)
        
        # 组合
        result = head + "\n\n[... 中间部分已省略 ...]\n\n" + tail
        
        return result
    
    def _truncate_at_sentence_boundary(self, text: str, max_len: int, from_end: bool = False) -> str:
        """
        在句子边界截断文本
        
        Args:
            text: 文本
            max_len: 最大长度
            from_end: 是否从末尾开始（用于提取结尾部分）
        
        Returns:
            截断后的文本
        """
        if len(text) <= max_len:
            return text
        
        # 句子结束标记
        sentence_endings = ['. ', '。', '! ', '！', '? ', '？', '\n\n']
        
        if from_end:
            # 从末尾开始，找最后一个句子边界
            search_text = text[-max_len:]
            for ending in sentence_endings:
                pos = search_text.find(ending)
                if pos > 0:
                    return search_text[pos + len(ending):]
            return search_text
        else:
            # 从开头开始，找最后一个句子边界
            search_text = text[:max_len]
            for ending in sentence_endings:
                pos = search_text.rfind(ending)
                if pos > 0:
                    return search_text[:pos + len(ending)]
            return search_text


# 全局内容截断器实例
_content_truncator: ContentTruncator = None


def get_content_truncator() -> ContentTruncator:
    """获取全局内容截断器实例"""
    global _content_truncator
    
    if _content_truncator is None:
        _content_truncator = ContentTruncator()
    
    return _content_truncator

