"""
分析质量评估模块

功能：
1. 评估 LLM 生成的论文分析质量
2. 检测低质量分析（过短、缺失关键部分、格式错误等）
3. 提供质量分数和改进建议
"""
import re
from typing import Dict, Any, List, Tuple
import structlog

logger = structlog.get_logger(__name__)


class QualityAssessor:
    """分析质量评估器"""
    
    # 必需的章节标题（正则表达式）
    REQUIRED_SECTIONS = [
        r'###\s*1\.\s*研究背景',
        r'###\s*2\.\s*研究目标',
        r'###\s*3\.\s*方法',
        r'###\s*4\.\s*.*发现.*结果',
        r'###\s*5\.\s*创新',
        r'###\s*6\.\s*局限'
    ]
    
    # 最小内容长度（字符数）
    MIN_TOTAL_LENGTH = 200
    MIN_SECTION_LENGTH = 30
    
    # 质量阈值
    QUALITY_THRESHOLD = 0.5
    
    def __init__(self, min_quality_score: float = None):
        """
        初始化质量评估器
        
        Args:
            min_quality_score: 最低质量分数（0-1），默认从配置读取
        """
        if min_quality_score is None:
            try:
                # 添加 paper_search 目录到 sys.path
                import sys
                from pathlib import Path as PathLib
                _CURRENT_FILE = PathLib(__file__)
                _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
                if str(_PAPER_SEARCH_DIR) not in sys.path:
                    sys.path.insert(0, str(_PAPER_SEARCH_DIR))

                from config import MIN_QUALITY_SCORE
                min_quality_score = MIN_QUALITY_SCORE
            except:
                min_quality_score = self.QUALITY_THRESHOLD
        
        self.min_quality_score = min_quality_score
        logger.info(f"QualityAssessor initialized with min_quality_score={min_quality_score}")
    
    def assess(self, analysis_text: str, paper: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        评估分析质量
        
        Args:
            analysis_text: 分析文本
            paper: 论文信息（可选，用于上下文）
        
        Returns:
            评估结果字典：
            {
                'score': float,           # 质量分数（0-1）
                'is_high_quality': bool,  # 是否高质量
                'issues': List[str],      # 问题列表
                'suggestions': List[str], # 改进建议
                'metrics': Dict           # 详细指标
            }
        """
        issues = []
        suggestions = []
        metrics = {}
        
        # 1. 检查总长度
        total_length = len(analysis_text)
        metrics['total_length'] = total_length
        
        if total_length < self.MIN_TOTAL_LENGTH:
            issues.append(f"分析过短（{total_length} < {self.MIN_TOTAL_LENGTH} 字符）")
            suggestions.append("增加分析深度和细节")
        
        # 2. 检查必需章节
        missing_sections = []
        section_lengths = {}
        
        for i, section_pattern in enumerate(self.REQUIRED_SECTIONS, 1):
            if not re.search(section_pattern, analysis_text, re.IGNORECASE):
                missing_sections.append(f"章节 {i}")
            else:
                # 提取章节内容并检查长度
                section_content = self._extract_section_content(analysis_text, section_pattern)
                section_length = len(section_content)
                section_lengths[f'section_{i}'] = section_length
                
                if section_length < self.MIN_SECTION_LENGTH:
                    issues.append(f"章节 {i} 内容过短（{section_length} < {self.MIN_SECTION_LENGTH} 字符）")
        
        if missing_sections:
            issues.append(f"缺失章节: {', '.join(missing_sections)}")
            suggestions.append("补充缺失的章节")
        
        metrics['section_lengths'] = section_lengths
        metrics['missing_sections'] = len(missing_sections)
        
        # 3. 检查是否包含 fallback 标记
        fallback_markers = ['分析超时', '分析失败', '详细信息请参考原文']
        has_fallback = any(marker in analysis_text for marker in fallback_markers)
        metrics['has_fallback'] = has_fallback
        
        if has_fallback:
            issues.append("包含 fallback 标记，可能是降级分析")
            suggestions.append("重新分析以获得完整结果")
        
        # 4. 检查内容质量指标
        # 4.1 检查是否有实质内容（不只是问号和括号）
        substantive_content = re.sub(r'[？\?\(\)（）\[\]【】]', '', analysis_text)
        substantive_ratio = len(substantive_content) / max(total_length, 1)
        metrics['substantive_ratio'] = substantive_ratio
        
        if substantive_ratio < 0.7:
            issues.append(f"实质内容比例过低（{substantive_ratio:.2%}）")
            suggestions.append("减少占位符，增加实质分析")
        
        # 4.2 检查是否有具体数据/结果
        has_numbers = bool(re.search(r'\d+', analysis_text))
        metrics['has_numbers'] = has_numbers
        
        # 4.3 检查是否有引用/参考
        has_references = bool(re.search(r'(参考|引用|文献|论文|研究)', analysis_text))
        metrics['has_references'] = has_references
        
        # 5. 计算质量分数
        score = self._calculate_score(metrics, issues)
        
        # 6. 判断是否高质量
        is_high_quality = score >= self.min_quality_score and len(issues) == 0
        
        result = {
            'score': score,
            'is_high_quality': is_high_quality,
            'issues': issues,
            'suggestions': suggestions,
            'metrics': metrics
        }
        
        # 记录评估结果
        paper_id = paper.get('paper_id', 'unknown') if paper else 'unknown'
        logger.info(
            f"Quality assessment for {paper_id}",
            score=f"{score:.2f}",
            is_high_quality=is_high_quality,
            issues_count=len(issues)
        )
        
        return result
    
    def _extract_section_content(self, text: str, section_pattern: str) -> str:
        """提取章节内容"""
        match = re.search(section_pattern, text, re.IGNORECASE)
        if not match:
            return ""
        
        start = match.end()
        # 查找下一个章节或文本结尾
        next_section = re.search(r'###\s*\d+\.', text[start:])
        end = start + next_section.start() if next_section else len(text)
        
        return text[start:end].strip()
    
    def _calculate_score(self, metrics: Dict, issues: List[str]) -> float:
        """
        计算质量分数（0-1）
        
        评分标准：
        - 基础分：0.5
        - 长度充足：+0.1
        - 所有章节完整：+0.2
        - 无 fallback：+0.1
        - 实质内容充足：+0.1
        - 每个问题：-0.1
        """
        score = 0.5  # 基础分
        
        # 长度充足
        if metrics.get('total_length', 0) >= self.MIN_TOTAL_LENGTH * 2:
            score += 0.1
        
        # 所有章节完整
        if metrics.get('missing_sections', 0) == 0:
            score += 0.2
        
        # 无 fallback
        if not metrics.get('has_fallback', False):
            score += 0.1
        
        # 实质内容充足
        if metrics.get('substantive_ratio', 0) >= 0.8:
            score += 0.1
        
        # 扣除问题分数
        score -= len(issues) * 0.1
        
        # 限制在 0-1 范围
        return max(0.0, min(1.0, score))


# 全局质量评估器实例
_quality_assessor: QualityAssessor = None


def get_quality_assessor() -> QualityAssessor:
    """获取全局质量评估器实例"""
    global _quality_assessor
    
    if _quality_assessor is None:
        _quality_assessor = QualityAssessor()
    
    return _quality_assessor

