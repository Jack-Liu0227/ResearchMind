"""
Journal Resolver (OpenAlex aggregator)

Provides a unified endpoint to resolve paper/journal metadata with multi-source
fallback, light rate limiting, and optional Redis-backed caching.
"""

import asyncio
import hashlib
import json
import logging
from typing import Optional, Dict, Any

import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/journal", tags=["journal-resolver"])


# Simple per-source rate limiters
_locks = {
    "openalex": asyncio.Lock(),
    "crossref": asyncio.Lock(),
}
_last_req: Dict[str, float] = {"openalex": 0.0, "crossref": 0.0}
_min_interval = {"openalex": 0.3, "crossref": 0.3}


def _cache_key(payload: Dict[str, Any]) -> str:
    m = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return f"cache:journal:resolve:{m.hexdigest()}"


def _get_redis():
    try:
        from .redis_session_manager import get_redis_manager, is_redis_available
        if is_redis_available():
            mgr = get_redis_manager()
            return getattr(mgr, "redis_client", None)
    except Exception:
        pass
    return None


async def _wait_slot(source: str):
    import time
    async with _locks[source]:
        now = time.time()
        gap = now - _last_req[source]
        if gap < _min_interval[source]:
            await asyncio.sleep(_min_interval[source] - gap)
        _last_req[source] = time.time()


async def _openalex_get(url: str) -> Optional[Dict[str, Any]]:
    await _wait_slot("openalex")
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()


async def _crossref_get(url: str) -> Optional[Dict[str, Any]]:
    await _wait_slot("crossref")
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()


async def _resolve_from_openalex(doi: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    try:
        if doi:
            clean_doi = doi.lower().replace("https://doi.org/", "").replace("http://doi.org/", "")
            url = f"https://api.openalex.org/works/doi:{clean_doi}"
            data = await _openalex_get(url)
        elif title:
            q = httpx.QueryParams({"search": title, "per_page": 1})
            url = f"https://api.openalex.org/works?{q}"
            data = await _openalex_get(url)
            if data and data.get("results"):
                data = data["results"][0]
        else:
            return result

        if not data:
            return result

        # Extract fields
        result["source"] = "openalex"
        cited_by_count = data.get("cited_by_count")
        result["cited_by_count"] = cited_by_count
        # Backward/Frontend compatibility: use citation_count naming too.
        result["citation_count"] = cited_by_count
        host = data.get("host_venue") or {}
        result["journal_name"] = host.get("display_name") or host.get("publisher")
        result["issn"] = (host.get("issn_l") or (host.get("issn") or [None]))
        result["doi"] = data.get("doi")
        return result
    except Exception as e:
        logger.warning(f"OpenAlex resolve failed: {e}")
        return {}


async def _resolve_from_crossref(doi: Optional[str]) -> Dict[str, Any]:
    if not doi:
        return {}
    try:
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        url = f"https://api.crossref.org/works/{clean_doi}"
        data = await _crossref_get(url)
        if not data:
            return {}
        msg = data.get("message", {})
        container = msg.get("container-title", [])
        return {
            "source": "crossref",
            "journal_name": container[0] if container else None,
            "publisher": msg.get("publisher"),
        }
    except Exception as e:
        logger.warning(f"CrossRef fallback failed: {e}")
        return {}


@router.get("/resolve")
async def resolve_journal(
    doi: Optional[str] = Query(None, description="DOI"),
    title: Optional[str] = Query(None, description="Paper title (optional)")
):
    """Resolve paper/journal info via OpenAlex with Crossref fallback.

    Returns cited_by_count/citation_count, journal_name, issn, and data source markers.
    Includes simple Redis/in-memory caching to reduce rate usage.
    """
    key_payload = {"doi": doi or "", "title": title or ""}
    key = _cache_key(key_payload)

    # Try Redis cache
    redis = _get_redis()
    if redis is not None:
        try:
            cached = redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # Resolve
    primary = await _resolve_from_openalex(doi=doi, title=title)
    if not primary and doi:
        # Fallback to CrossRef for journal_name
        primary = await _resolve_from_crossref(doi)

    result = {
        "status": "success" if primary else "error",
        "data": primary or None,
    }

    # Store in Redis cache (TTL 1 day)
    if redis is not None and primary:
        try:
            redis.setex(key, 24 * 3600, json.dumps(result, ensure_ascii=False))
        except Exception:
            pass

    return result
