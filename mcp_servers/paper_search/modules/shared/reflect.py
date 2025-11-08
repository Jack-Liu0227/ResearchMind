"""
Reflect Module (反思模块)

功能：
1. 结果质量检查 - 检查搜索结果的相关性和质量
2. 反思迭代 - 判断是否需要更多研究
3. 建议生成 - 生成改进建议和后续查询

核心流程：
搜索结果 → 质量评估 → 反思分析 → 决策（继续/结束）→ 建议
"""
import os
import json
from typing import Dict, Any
import litellm
import structlog

logger = structlog.get_logger(__name__)

# Import prompts
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from prompts import (
    format_double_check_prompt,
    format_reflect_prompt
)


async def double_check_results(
    original_query: str,
    search_results: str,
    min_relevance: float = 0.7
) -> Dict[str, Any]:
    """
    Double-check search results for relevance and quality.

    Args:
        original_query: Original user query
        search_results: Summary of search results
        min_relevance: Minimum relevance score (default: 0.7)

    Returns:
        Dict containing relevance score, issues found, and recommendations
    """
    try:
        prompt = format_double_check_prompt(original_query, search_results)

        response = litellm.completion(
            model=os.getenv('MODEL_USE', 'gemini/gemini-2.0-flash'),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
            api_key=os.getenv('OPENAI_API_KEY'),  # 🔧 显式传递 API Key
            api_base=os.getenv('OPENAI_BASE_URL')  # 🔧 显式传递 API Base URL
        )

        result = json.loads(response.choices[0].message.content)
        result['is_acceptable'] = result.get('relevance_score', 0) >= min_relevance

        logger.info(f"Double-check result: relevance={result.get('relevance_score')}, acceptable={result.get('is_acceptable')}")
        return result

    except Exception as e:
        logger.error(f"Error in double_check_results: {e}")
        return {
            'relevance_score': 1.0,
            'quality_score': 1.0,
            'issues': [],
            'recommendations': [],
            'is_acceptable': True,
            'summary': 'Error during evaluation',
            'error': str(e)
        }


async def reflect_on_results(
    question: str,
    search_results: str,
    min_confidence: float = 0.7
) -> Dict[str, Any]:
    """
    Reflect on search results to determine if more research is needed.

    Args:
        question: The original research question
        search_results: Summary of current search results
        min_confidence: Minimum confidence threshold (default: 0.7)

    Returns:
        Dict containing reflection analysis and recommendations
    """
    try:
        prompt = format_reflect_prompt(question, search_results)

        response = litellm.completion(
            model=os.getenv('MODEL_USE', 'gemini/gemini-2.0-flash'),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
            api_key=os.getenv('OPENAI_API_KEY'),  # 🔧 显式传递 API Key
            api_base=os.getenv('OPENAI_BASE_URL')  # 🔧 显式传递 API Base URL
        )

        result = json.loads(response.choices[0].message.content)

        # Add decision based on confidence threshold
        result['sufficient'] = result.get('confidence', 0) >= min_confidence

        logger.info(f"Reflection: confidence={result.get('confidence')}, needs_more={result.get('needs_more_research')}")
        return result

    except Exception as e:
        logger.error(f"Error in reflect_on_results: {e}")
        return {
            'confidence': 0.5,
            'well_covered': [],
            'missing': ['Unable to analyze'],
            'needs_more_research': True,
            'suggested_queries': [],
            'sufficient': False,
            'error': str(e)
        }


async def evaluate_iteration_quality(
    iteration_number: int,
    total_papers_found: int,
    unique_insights: int,
    coverage_score: float
) -> Dict[str, Any]:
    """
    Evaluate the quality of a research iteration.

    Args:
        iteration_number: Current iteration number
        total_papers_found: Total number of papers found
        unique_insights: Number of unique insights discovered
        coverage_score: Coverage score (0-1)

    Returns:
        Dict containing iteration quality assessment
    """
    try:
        # Simple heuristic evaluation
        quality_score = 0.0
        
        # Papers found contributes 40%
        if total_papers_found >= 10:
            quality_score += 0.4
        elif total_papers_found >= 5:
            quality_score += 0.2
        
        # Unique insights contributes 30%
        if unique_insights >= 5:
            quality_score += 0.3
        elif unique_insights >= 3:
            quality_score += 0.15
        
        # Coverage contributes 30%
        quality_score += coverage_score * 0.3
        
        # Determine if should continue
        should_continue = (
            iteration_number < 3 and  # Max 3 iterations
            quality_score < 0.8 and   # Not yet high quality
            total_papers_found < 20   # Not too many papers
        )
        
        result = {
            'iteration': iteration_number,
            'quality_score': round(quality_score, 2),
            'total_papers': total_papers_found,
            'unique_insights': unique_insights,
            'coverage_score': round(coverage_score, 2),
            'should_continue': should_continue,
            'recommendation': 'Continue research' if should_continue else 'Sufficient research completed'
        }
        
        logger.info(f"Iteration {iteration_number} quality: {quality_score:.2f}, continue={should_continue}")
        return result
        
    except Exception as e:
        logger.error(f"Error evaluating iteration quality: {e}")
        return {
            'iteration': iteration_number,
            'quality_score': 0.5,
            'should_continue': False,
            'error': str(e)
        }


async def generate_refinement_suggestions(
    original_query: str,
    current_results: str,
    missing_aspects: list
) -> Dict[str, Any]:
    """
    Generate suggestions for refining the research.

    Args:
        original_query: Original research query
        current_results: Summary of current results
        missing_aspects: List of missing aspects

    Returns:
        Dict containing refinement suggestions
    """
    try:
        # Build prompt
        prompt = f"""Based on the research query and current results, suggest refinements:

Original Query: {original_query}

Current Results Summary:
{current_results}

Missing Aspects:
{', '.join(missing_aspects)}

Please provide:
1. 3-5 refined search queries to fill gaps
2. Suggested search strategies
3. Alternative keywords to try

Respond in JSON format:
{{
    "refined_queries": ["query1", "query2", ...],
    "strategies": ["strategy1", "strategy2", ...],
    "alternative_keywords": ["keyword1", "keyword2", ...]
}}"""

        response = litellm.completion(
            model=os.getenv('MODEL_USE', 'gemini/gemini-2.0-flash'),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"},
            api_key=os.getenv('OPENAI_API_KEY'),  # 🔧 显式传递 API Key
            api_base=os.getenv('OPENAI_BASE_URL')  # 🔧 显式传递 API Base URL
        )

        result = json.loads(response.choices[0].message.content)
        
        logger.info(f"Generated {len(result.get('refined_queries', []))} refinement suggestions")
        return result

    except Exception as e:
        logger.error(f"Error generating refinement suggestions: {e}")
        return {
            'refined_queries': [],
            'strategies': [],
            'alternative_keywords': [],
            'error': str(e)
        }

