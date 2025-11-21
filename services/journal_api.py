"""
Journal Information API
提供期刊信息查询的后端代理接口，解决 CORS 跨域问题
"""

import os
import logging
import httpx
import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 速率限制：Semantic Scholar API 每秒最多 1 个请求
SEMANTIC_SCHOLAR_RATE_LIMIT = 1.0  # 秒
_last_semantic_scholar_request_time = 0.0
_semantic_scholar_lock = asyncio.Lock()

async def wait_for_rate_limit():
    """等待以遵守 Semantic Scholar API 速率限制（使用锁确保串行执行）"""
    global _last_semantic_scholar_request_time
    import time

    async with _semantic_scholar_lock:
        current_time = time.time()
        time_since_last_request = current_time - _last_semantic_scholar_request_time

        if time_since_last_request < SEMANTIC_SCHOLAR_RATE_LIMIT:
            wait_time = SEMANTIC_SCHOLAR_RATE_LIMIT - time_since_last_request
            logger.debug(f"⏳ [Rate Limit] 等待 {wait_time:.2f} 秒以遵守速率限制")
            await asyncio.sleep(wait_time)

        _last_semantic_scholar_request_time = time.time()

# 创建路由
router = APIRouter(prefix="/api/journal", tags=["journal"])

# API 配置
EASYSCHOLAR_API_BASE = "https://easyscholar.cc/open/getPublicationRank"
EASYSCHOLAR_API_KEY = os.getenv("EASYSCHOLAR_API_KEY", "20bdbb8588cd469d9af25d1cd6ae7640")

SEMANTIC_SCHOLAR_API_BASE = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")


class JournalInfoResponse(BaseModel):
    """期刊信息响应"""
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DOIResponse(BaseModel):
    """DOI 响应"""
    status: str
    doi: Optional[str] = None
    error: Optional[str] = None


class JournalNameResponse(BaseModel):
    """期刊名称响应"""
    status: str
    journal_name: Optional[str] = None
    error: Optional[str] = None


@router.get("/info", response_model=JournalInfoResponse)
async def get_journal_info(journal_name: str = Query(..., description="期刊名称")):
    """
    获取期刊信息（代理 EasyScholar API）

    Args:
        journal_name: 期刊名称

    Returns:
        期刊信息（影响因子、分区等）
    """
    try:
        logger.info(f"📚 [Journal API] 查询期刊信息: {journal_name}")

        # 🔧 修复：参数名应该是 secretKey 而不是 apiKey
        url = f"{EASYSCHOLAR_API_BASE}?publicationName={journal_name}&secretKey={EASYSCHOLAR_API_KEY}"

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # 检查 API 返回的状态码
        if data.get("code") != 200:
            error_msg = data.get("msg", "未知错误")
            logger.error(f"❌ [Journal API] EasyScholar API 返回错误: {error_msg}")
            return JournalInfoResponse(
                status="error",
                error=f"EasyScholar API 错误: {error_msg}"
            )

        logger.info(f"✅ [Journal API] 查询成功: {journal_name}")
        return JournalInfoResponse(status="success", data=data)

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ [Journal API] EasyScholar API 错误: {e.response.status_code}")
        return JournalInfoResponse(
            status="error",
            error=f"EasyScholar API 错误: {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"❌ [Journal API] 查询失败: {str(e)}")
        return JournalInfoResponse(
            status="error",
            error=f"查询失败: {str(e)}"
        )


class PaperInfoResponse(BaseModel):
    """文献信息响应（包含 DOI 和期刊名称）"""
    status: str
    doi: Optional[str] = None
    journal_name: Optional[str] = None
    venue: Optional[str] = None
    error: Optional[str] = None


@router.get("/doi", response_model=DOIResponse)
async def get_doi_from_semantic_scholar(paper_id: str = Query(..., description="Semantic Scholar Paper ID")):
    """
    从 Semantic Scholar 获取 DOI（代理 Semantic Scholar API）

    Args:
        paper_id: Semantic Scholar Paper ID

    Returns:
        DOI 字符串
    """
    try:
        logger.info(f"🔍 [Journal API] 查询 DOI: {paper_id}")

        # 🆕 等待以遵守速率限制
        await wait_for_rate_limit()

        # 移除可能的前缀（s2_）
        clean_paper_id = paper_id.replace("s2_", "")

        url = f"{SEMANTIC_SCHOLAR_API_BASE}/paper/{clean_paper_id}?fields=externalIds"

        headers = {}
        if SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
            logger.info("🔑 [Journal API] 使用 API Key 认证")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        doi = data.get("externalIds", {}).get("DOI")

        if doi:
            logger.info(f"✅ [Journal API] 获取 DOI 成功: {doi}")
            return DOIResponse(status="success", doi=doi)
        else:
            logger.warning(f"⚠️ [Journal API] 该文献没有 DOI")
            return DOIResponse(status="error", error="该文献没有 DOI")

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ [Journal API] Semantic Scholar API 错误: {e.response.status_code}")
        return DOIResponse(
            status="error",
            error=f"Semantic Scholar API 错误: {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"❌ [Journal API] 查询失败: {str(e)}")
        return DOIResponse(
            status="error",
            error=f"查询失败: {str(e)}"
        )


@router.get("/paper-info", response_model=PaperInfoResponse)
async def get_paper_info_from_semantic_scholar(paper_id: str = Query(..., description="Semantic Scholar Paper ID")):
    """
    从 Semantic Scholar 获取文献信息（包含 DOI 和期刊名称）

    Args:
        paper_id: Semantic Scholar Paper ID

    Returns:
        文献信息（DOI、期刊名称、venue）
    """
    try:
        logger.info(f"🔍 [Journal API] 查询文献信息: {paper_id}")

        # 🆕 等待以遵守速率限制
        await wait_for_rate_limit()

        # 移除可能的前缀（s2_）
        clean_paper_id = paper_id.replace("s2_", "")

        # 🆕 查询更多字段：externalIds, venue, journal
        url = f"{SEMANTIC_SCHOLAR_API_BASE}/paper/{clean_paper_id}?fields=externalIds,venue,journal"

        headers = {}
        if SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
            logger.info("🔑 [Journal API] 使用 API Key 认证")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        # 提取 DOI
        doi = data.get("externalIds", {}).get("DOI")

        # 提取期刊/会议名称
        venue = data.get("venue", "")
        journal = data.get("journal")
        journal_name = ""

        # 优先级 1：venue 字段（通常最准确）
        if venue and isinstance(venue, str) and venue.strip():
            journal_name = venue.strip()
            logger.info(f"📚 [Journal API] 从 venue 字段获取期刊名称: {journal_name}")
        # 优先级 2：journal.name 字段
        elif journal and isinstance(journal, dict):
            journal_name = journal.get("name", "").strip()
            if journal_name:
                logger.info(f"📚 [Journal API] 从 journal.name 字段获取期刊名称: {journal_name}")

        # 优先级 3：如果有 DOI，尝试从 CrossRef 获取期刊名称
        if not journal_name and doi:
            logger.info(f"📚 [Journal API] venue 和 journal 为空，尝试从 DOI 获取期刊名称: {doi}")
            try:
                clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
                crossref_url = f"https://api.crossref.org/works/{clean_doi}"

                async with httpx.AsyncClient(timeout=10.0) as client:
                    crossref_response = await client.get(crossref_url, headers={"Accept": "application/json"})
                    crossref_response.raise_for_status()
                    crossref_data = crossref_response.json()

                # 从 CrossRef 获取期刊名称
                container_titles = crossref_data.get("message", {}).get("container-title", [])
                if container_titles:
                    journal_name = container_titles[0]
                    logger.info(f"✅ [Journal API] 从 CrossRef 获取期刊名称成功: {journal_name}")
                else:
                    # 尝试从 publisher 字段获取
                    publisher = crossref_data.get("message", {}).get("publisher", "")
                    if publisher:
                        journal_name = publisher
                        logger.info(f"ℹ️ [Journal API] 从 CrossRef publisher 字段获取: {journal_name}")
            except Exception as e:
                logger.warning(f"⚠️ [Journal API] 从 CrossRef 获取期刊名称失败: {str(e)}")

        # 构建响应
        if doi or journal_name:
            logger.info(f"✅ [Journal API] 获取文献信息成功: DOI={doi}, Journal={journal_name}")
            return PaperInfoResponse(
                status="success",
                doi=doi,
                journal_name=journal_name if journal_name else None,
                venue=venue if venue else None
            )
        else:
            logger.warning(f"⚠️ [Journal API] 该文献没有 DOI 和期刊名称")
            return PaperInfoResponse(
                status="error",
                error="该文献没有 DOI 和期刊名称"
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ [Journal API] Semantic Scholar API 错误: {e.response.status_code}")
        return PaperInfoResponse(
            status="error",
            error=f"Semantic Scholar API 错误: {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"❌ [Journal API] 查询失败: {str(e)}")
        return PaperInfoResponse(
            status="error",
            error=f"查询失败: {str(e)}"
        )


@router.get("/name-from-doi", response_model=JournalNameResponse)
async def get_journal_name_from_doi(doi: str = Query(..., description="DOI 标识符")):
    """
    从 DOI 获取期刊名称（代理 CrossRef API）
    
    Args:
        doi: DOI 标识符
    
    Returns:
        期刊名称
    """
    try:
        logger.info(f"🔍 [Journal API] 从 DOI 获取期刊名称: {doi}")
        
        # 清理 DOI
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        
        url = f"https://api.crossref.org/works/{clean_doi}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()

        # 🔧 修复：安全地获取期刊名称，避免 list index out of range 错误
        container_titles = data.get("message", {}).get("container-title", [])
        journal_name = container_titles[0] if container_titles else None

        if journal_name:
            logger.info(f"✅ [Journal API] 获取期刊名称成功: {journal_name}")
            return JournalNameResponse(status="success", journal_name=journal_name)
        else:
            # 尝试从其他字段获取期刊名称
            message = data.get("message", {})

            # 尝试从 publisher 字段获取
            publisher = message.get("publisher")
            if publisher:
                logger.info(f"ℹ️ [Journal API] 从 publisher 字段获取: {publisher}")
                return JournalNameResponse(status="success", journal_name=publisher)

            # 尝试从 institution 字段获取（用于会议论文）
            institution = message.get("institution")
            if institution and isinstance(institution, list) and institution:
                institution_name = institution[0].get("name") if isinstance(institution[0], dict) else str(institution[0])
                logger.info(f"ℹ️ [Journal API] 从 institution 字段获取: {institution_name}")
                return JournalNameResponse(status="success", journal_name=institution_name)

            # 检查是否为图书章节
            book_title = message.get("container-title-short") or message.get("book-title")
            if book_title:
                if isinstance(book_title, list):
                    book_title = book_title[0] if book_title else None
                if book_title:
                    logger.info(f"ℹ️ [Journal API] 从 book-title 字段获取: {book_title}")
                    return JournalNameResponse(status="success", journal_name=book_title)

            logger.warning(f"⚠️ [Journal API] 无法从 DOI 获取期刊名称，DOI: {doi}")
            logger.debug(f"📋 [Journal API] CrossRef 返回的数据: {data}")
            return JournalNameResponse(status="error", error="无法从 DOI 获取期刊名称")
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ [Journal API] CrossRef API 错误: {e.response.status_code}")
        return JournalNameResponse(
            status="error",
            error=f"CrossRef API 错误: {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"❌ [Journal API] 查询失败: {str(e)}")
        return JournalNameResponse(
            status="error",
            error=f"查询失败: {str(e)}"
        )


class PIIToDOIResponse(BaseModel):
    """PII 转 DOI 响应"""
    status: str
    doi: Optional[str] = None
    pii: Optional[str] = None
    journal_name: Optional[str] = None
    error: Optional[str] = None


@router.get("/pii-to-doi", response_model=PIIToDOIResponse)
async def convert_pii_to_doi(pii: str = Query(..., description="ScienceDirect PII")):
    """
    将 ScienceDirect PII 转换为 DOI

    Args:
        pii: ScienceDirect Publisher Item Identifier (例如: S1366554525002327)

    Returns:
        PIIToDOIResponse: 包含 DOI 和期刊名称的响应

    Example:
        GET /api/journal/pii-to-doi?pii=S1366554525002327
    """
    logger.info(f"🔍 [Journal API] PII 转 DOI: {pii}")

    try:
        # 方法 1：通过 Crossref API 搜索 PII
        # Crossref 支持通过 PII 搜索文献
        crossref_url = f"https://api.crossref.org/works?query={pii}&rows=5"

        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"🔍 [Journal API] 查询 Crossref API: {crossref_url}")
            response = await client.get(crossref_url)
            response.raise_for_status()
            data = response.json()

            items = data.get('message', {}).get('items', [])

            if not items:
                logger.warning(f"⚠️ [Journal API] Crossref 未找到 PII: {pii}")
                return PIIToDOIResponse(
                    status="error",
                    pii=pii,
                    error="未找到对应的 DOI"
                )

            # 遍历结果，找到最匹配的
            for item in items:
                # 检查是否包含 PII
                title = item.get('title', [''])[0].lower()
                abstract = item.get('abstract', '').lower()

                # 获取 DOI
                doi = item.get('DOI')

                # 获取期刊名称
                journal_name = None
                container_title = item.get('container-title', [])
                if container_title:
                    journal_name = container_title[0]

                # 如果找到 DOI，返回第一个结果
                if doi:
                    logger.info(f"✅ [Journal API] PII 转 DOI 成功: {pii} -> {doi}")
                    if journal_name:
                        logger.info(f"📚 [Journal API] 期刊名称: {journal_name}")

                    return PIIToDOIResponse(
                        status="success",
                        doi=doi,
                        pii=pii,
                        journal_name=journal_name
                    )

            # 如果没有找到 DOI
            logger.warning(f"⚠️ [Journal API] Crossref 结果中未找到有效的 DOI")
            return PIIToDOIResponse(
                status="error",
                pii=pii,
                error="未找到有效的 DOI"
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ [Journal API] Crossref API 错误: {e.response.status_code}")
        return PIIToDOIResponse(
            status="error",
            pii=pii,
            error=f"Crossref API 错误: {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"❌ [Journal API] PII 转 DOI 失败: {str(e)}")
        return PIIToDOIResponse(
            status="error",
            pii=pii,
            error=f"查询失败: {str(e)}"
        )


class SpringerJournalInfoResponse(BaseModel):
    """Springer 期刊信息响应"""
    status: str
    journal_name: Optional[str] = None
    journal_id: Optional[str] = None
    issn: Optional[str] = None
    error: Optional[str] = None


@router.get("/springer-journal-info", response_model=SpringerJournalInfoResponse)
async def get_springer_journal_info(journal_id: str = Query(..., description="Springer 期刊 ID")):
    """
    从 Springer 期刊主页获取期刊名称

    Args:
        journal_id: Springer 期刊 ID (例如: 10458)

    Returns:
        SpringerJournalInfoResponse: 包含期刊名称的响应

    Example:
        GET /api/journal/springer-journal-info?journal_id=10458
    """
    logger.info(f"🔍 [Journal API] 查询 Springer 期刊信息: {journal_id}")

    try:
        url = f"https://link.springer.com/journal/{journal_id}"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            logger.info(f"🔍 [Journal API] 访问 Springer 页面: {url}")
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

            # 使用正则表达式提取期刊名称
            # Springer 页面通常在 <title> 标签中包含期刊名称
            import re

            # 方法 1：从 <title> 标签提取
            title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
            if title_match:
                title_text = title_match.group(1).strip()
                # 移除 "| SpringerLink" 等后缀
                journal_name = re.sub(r'\s*\|\s*SpringerLink.*$', '', title_text).strip()

                if journal_name:
                    logger.info(f"✅ [Journal API] 从 <title> 提取期刊名称: {journal_name}")
                    return SpringerJournalInfoResponse(
                        status="success",
                        journal_name=journal_name,
                        journal_id=journal_id
                    )

            # 方法 2：从 meta 标签提取
            meta_match = re.search(r'<meta\s+name=["\']citation_journal_title["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if meta_match:
                journal_name = meta_match.group(1).strip()
                logger.info(f"✅ [Journal API] 从 meta 标签提取期刊名称: {journal_name}")
                return SpringerJournalInfoResponse(
                    status="success",
                    journal_name=journal_name,
                    journal_id=journal_id
                )

            # 方法 3：从 JSON-LD 提取
            jsonld_match = re.search(r'<script\s+type=["\']application/ld\+json["\'][^>]*>([^<]+)</script>', html, re.IGNORECASE)
            if jsonld_match:
                try:
                    import json
                    jsonld_data = json.loads(jsonld_match.group(1))
                    if isinstance(jsonld_data, dict):
                        journal_name = jsonld_data.get('name')
                        if journal_name:
                            logger.info(f"✅ [Journal API] 从 JSON-LD 提取期刊名称: {journal_name}")
                            return SpringerJournalInfoResponse(
                                status="success",
                                journal_name=journal_name,
                                journal_id=journal_id
                            )
                except:
                    pass

            # 如果所有方法都失败
            logger.warning(f"⚠️ [Journal API] 无法从页面提取期刊名称")
            return SpringerJournalInfoResponse(
                status="error",
                journal_id=journal_id,
                error="无法从页面提取期刊名称"
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ [Journal API] Springer 页面访问错误: {e.response.status_code}")
        return SpringerJournalInfoResponse(
            status="error",
            journal_id=journal_id,
            error=f"页面访问错误: {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"❌ [Journal API] Springer 期刊信息获取失败: {str(e)}")
        return SpringerJournalInfoResponse(
            status="error",
            journal_id=journal_id,
            error=f"查询失败: {str(e)}"
        )
