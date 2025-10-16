"""
Planning Module (规划模块)

功能：
1. 请求分类 - 判断用户请求类型
2. 研究计划生成 - 生成多步骤研究计划
3. 查询优化 - 中文→英文翻译、查询扩展

核心流程：
用户输入 → 请求分类 → 生成研究计划 → 输出搜索查询
"""
import os
from typing import Dict, Any
import litellm
import structlog

logger = structlog.get_logger(__name__)

# Import prompts
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from prompts import (
    format_classify_prompt,
    format_research_plan_prompt
)


async def classify_user_request(query: str) -> Dict[str, Any]:
    """
    Classify user request into categories: valid, general, or need-more-info.

    Args:
        query: User's research request or query

    Returns:
        Dict containing classification type, user_intent (for valid), and next_message (for others)
    """
    try:
        # Format prompt
        prompt = format_classify_prompt(query)
        
        # Call LLM
        response = await litellm.acompletion(
            model=os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash'),
            messages=[
                {"role": "system", "content": "You are a research request classifier."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        # Parse response
        content = response.choices[0].message.content
        
        # Simple parsing (you can make this more robust)
        if "有效研究请求" in content or "valid research" in content.lower():
            # Extract user intent
            lines = content.split('\n')
            user_intent = query  # Default to original query
            for line in lines:
                if "用户意图" in line or "user intent" in line.lower():
                    user_intent = line.split(':', 1)[-1].strip()
                    break
            
            return {
                'type': 'valid',
                'user_intent': user_intent,
                'original_query': query
            }
        elif "一般问题" in content or "general question" in content.lower():
            return {
                'type': 'general',
                'next_message': '这是一个一般性问题，我可以直接回答。',
                'original_query': query
            }
        else:
            return {
                'type': 'need_more_info',
                'next_message': '请提供更多信息以便我更好地帮助您。',
                'original_query': query
            }
    
    except Exception as e:
        logger.error(f"Error classifying request: {e}")
        return {
            'type': 'error',
            'error': str(e),
            'original_query': query
        }


async def generate_research_plan(user_intent: str, max_steps: int = 3) -> Dict[str, Any]:
    """
    Generate optimized search queries for ArXiv, Google Scholar, and other academic databases.
    根据用户搜索词生成最相关的、能被ArXiv等数据库识别的检索词。

    Args:
        user_intent: User's research intent (可以是中文或英文)
        max_steps: Maximum number of research steps (default: 3)

    Returns:
        Dict containing optimized search queries and research plan
    """
    try:
        # Format prompt for optimized search queries
        prompt = format_research_plan_prompt(user_intent, max_steps)

        # Call LLM
        response = await litellm.acompletion(
            model=os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash'),
            messages=[
                {"role": "system", "content": "You are a search query optimization specialist for academic databases."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Lower temperature for more consistent query generation
        )

        # Parse response
        content = response.choices[0].message.content
        logger.info(f"Optimized search queries response: {content}")

        # Extract optimized queries
        primary_query = ""
        related_queries = []
        keywords = []

        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Extract primary query
            if line.startswith('主查询') or line.startswith('Primary Query'):
                primary_query = line.split(':', 1)[1].strip() if ':' in line else ""

            # Extract related queries
            elif line.startswith('相关查询') or line.startswith('Related Query'):
                query = line.split(':', 1)[1].strip() if ':' in line else ""
                if query:
                    related_queries.append(query)

            # Extract keywords
            elif line.startswith('关键词建议') or line.startswith('Keyword Suggestions'):
                keywords_str = line.split(':', 1)[1].strip() if ':' in line else ""
                if keywords_str:
                    keywords = [k.strip() for k in keywords_str.split(',')]

        # Build optimized search plan
        search_queries = []
        if primary_query:
            search_queries.append(primary_query)
        search_queries.extend(related_queries[:max_steps-1])  # Limit to max_steps

        # Ensure we have at least one query
        if not search_queries:
            # Fallback: use original user intent
            search_queries = [user_intent]

        # Build steps from optimized queries
        steps = []
        for i, query in enumerate(search_queries, 1):
            steps.append({
                'step_number': i,
                'description': f"搜索查询 {i}: {query}",
                'query_en': query,
                'query_cn': user_intent if i == 1 else "",  # Only first step gets original Chinese
                'optimized': True
            })

        return {
            'status': 'success',
            'user_intent': user_intent,
            'primary_query': primary_query,
            'related_queries': related_queries,
            'keywords': keywords,
            'optimized_queries': search_queries,
            'total_steps': len(steps),
            'steps': steps,
            'raw_plan': content
        }
    
    except Exception as e:
        logger.error(f"Error generating research plan: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'user_intent': user_intent
        }

