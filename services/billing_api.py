"""
计费统计 API

提供计费统计和查询接口
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .user_billing_config import get_billing_context_manager
from .photon_billing import get_billing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ==========================================
# 🔧 优化：计费 API 缓存
# ==========================================

class BillingCache:
    """简单的内存缓存，用于计费统计 API"""

    def __init__(self, ttl_seconds: int = 30):
        """
        初始化缓存

        Args:
            ttl_seconds: 缓存过期时间（秒）
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[Any, datetime]] = {}

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            value, expire_time = self._cache[key]
            if datetime.now() < expire_time:
                logger.debug(f"✅ 缓存命中: {key}")
                return value
            else:
                # 过期，删除
                del self._cache[key]
                logger.debug(f"⏰ 缓存过期: {key}")
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        expire_time = datetime.now() + timedelta(seconds=self.ttl_seconds)
        self._cache[key] = (value, expire_time)
        logger.debug(f"💾 缓存设置: {key}")

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        logger.debug("🗑️ 缓存已清空")


# 全局缓存实例（30秒 TTL）
billing_cache = BillingCache(ttl_seconds=30)


class BillingConfigResponse(BaseModel):
    """计费配置响应"""
    success: bool
    message: str
    has_config: bool
    config: Optional[dict] = None


@router.get("/config/{user_id}")
async def get_billing_config(user_id: str) -> BillingConfigResponse:
    """
    获取用户的计费配置状态（从数据库读取）

    ⚠️ 注意：此接口仅用于显示用户配置状态，不用于计费
    计费时必须从 Cookie 读取 appAccessKey 和 clientName

    返回示例:
    ```json
    {
        "success": true,
        "message": "已配置",
        "has_config": true,
        "config": {
            "sku_id": "10048",
            "client_name": "ResearchMind",
            "access_key_masked": "e3a895e7...ce02"
        }
    }
    ```
    """
    from .database import get_db, User

    # 尝试将 user_id 转换为整数（数据库用户 ID）
    try:
        db_user_id = int(user_id)
    except ValueError:
        # user_id 不是整数（可能是 session_id），返回未配置
        return BillingConfigResponse(
            success=True,
            message="未配置（user_id 不是数据库用户 ID）",
            has_config=False,
            config=None
        )

    # 使用 try-finally 确保数据库会话正确关闭
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == db_user_id).first()

        if user and user.access_key:
            return BillingConfigResponse(
                success=True,
                message="已配置",
                has_config=True,
                config={
                    "sku_id": user.sku_id or "10048",
                    "client_name": user.client_name or "ResearchMind",
                    "access_key_masked": f"{user.access_key[:8]}...{user.access_key[-4:]}"
                }
            )
        else:
            return BillingConfigResponse(
                success=True,
                message="未配置",
                has_config=False,
                config=None
            )
    except Exception as e:
        logger.error(f"❌ 获取计费配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# delete_billing_config 已删除 - 用户配置现在存储在数据库中，通过用户管理接口删除


# ==========================================
# 计费统计 API
# ==========================================

class BillingStatsResponse(BaseModel):
    """计费统计响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.get("/stats/conversation/{conversation_id}")
async def get_conversation_billing_stats(conversation_id: str) -> BillingStatsResponse:
    """
    获取指定对话的计费统计

    🔧 优化：添加 30 秒缓存以减少重复查询

    返回示例:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "data": {
            "conversation_id": "conv_123",
            "user_id": "user_456",
            "total_tokens": 15000,
            "total_photons": 5.0,
            "request_count": 10,
            "charged": false,
            "has_user_config": true,
            "billing_source": "用户账户",
            "created_at": "2025-11-03T23:00:00",
            "updated_at": "2025-11-03T23:30:00"
        }
    }
    ```
    """
    # 🔧 优化：检查缓存
    cache_key = f"stats:conversation:{conversation_id}"
    cached = billing_cache.get(cache_key)
    if cached:
        return cached

    try:
        context_manager = get_billing_context_manager()
        context = context_manager.get_context(conversation_id)

        if not context:
            result = BillingStatsResponse(
                success=False,
                message=f"对话 {conversation_id} 不存在",
                data=None
            )
            # 不缓存失败结果
            return result

        snapshot = context.get_snapshot()

        result = BillingStatsResponse(
            success=True,
            message="获取成功",
            data=snapshot
        )

        # 🔧 优化：缓存成功结果
        billing_cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"❌ 获取对话计费统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/user/{user_id}")
async def get_user_billing_stats(user_id: str) -> BillingStatsResponse:
    """
    获取指定用户的总计费统计（所有对话的聚合）

    🔧 优化：添加 30 秒缓存以减少重复查询

    返回示例:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "data": {
            "user_id": "user_456",
            "total_conversations": 5,
            "total_tokens": 50000,
            "total_photons": 16.6667,
            "total_requests": 50,
            "conversations": [
                {
                    "conversation_id": "conv_123",
                    "total_tokens": 15000,
                    "total_photons": 5.0,
                    "request_count": 10
                }
            ]
        }
    }
    ```
    """
    # 🔧 优化：检查缓存
    cache_key = f"stats:user:{user_id}"
    cached = billing_cache.get(cache_key)
    if cached:
        return cached

    try:
        context_manager = get_billing_context_manager()
        user_stats = context_manager.get_user_total_usage(user_id)

        result = BillingStatsResponse(
            success=True,
            message="获取成功",
            data=user_stats
        )

        # 🔧 优化：缓存结果
        billing_cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"❌ 获取用户计费统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/global")
async def get_global_billing_stats() -> BillingStatsResponse:
    """
    获取全局计费统计

    🔧 优化：添加 30 秒缓存以减少重复查询

    返回示例:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "data": {
            "total_tokens": 100000,
            "total_photons": 33.3333,
            "total_requests": 100,
            "total_sessions": 20,
            "start_time": "2025-11-03T00:00:00",
            "current_time": "2025-11-03T23:30:00",
            "billing_config": {
                "tokens_per_photon": 3000,
                "billing_enabled": true,
                "precision": 4
            }
        }
    }
    ```
    """
    # 🔧 优化：检查缓存
    cache_key = "stats:global"
    cached = billing_cache.get(cache_key)
    if cached:
        return cached

    try:
        billing_service = get_billing_service()
        global_stats = billing_service.get_global_stats()

        result = BillingStatsResponse(
            success=True,
            message="获取成功",
            data=global_stats
        )

        # 🔧 优化：缓存结果
        billing_cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"❌ 获取全局计费统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    success: bool
    message: str
    conversations: List[Dict[str, Any]]


@router.get("/conversations/user/{user_id}")
async def list_user_conversations(user_id: str) -> ConversationListResponse:
    """
    列出指定用户的所有对话及其计费信息

    返回示例:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "conversations": [
            {
                "conversation_id": "conv_123",
                "user_id": "user_456",
                "total_tokens": 15000,
                "total_photons": 5.0,
                "request_count": 10,
                "charged": false,
                "created_at": "2025-11-03T23:00:00"
            }
        ]
    }
    ```
    """
    try:
        context_manager = get_billing_context_manager()
        contexts = context_manager.list_contexts(user_id=user_id)

        conversations = [ctx.get_snapshot() for ctx in contexts]

        return ConversationListResponse(
            success=True,
            message="获取成功",
            conversations=conversations
        )

    except Exception as e:
        logger.error(f"❌ 列出用户对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

