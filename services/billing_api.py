"""
计费统计 API

提供计费统计和查询接口
"""

import logging
from fastapi import APIRouter, HTTPException, Cookie
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .user_billing_config import get_billing_context_manager
from .photon_billing import get_billing_service
from .pricing_service import PricingService

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
    获取指定对话的统计数据

    返回数据包含：
    - total_tokens: Token 使用量（仅供参考，不用于扣费）
    - total_photons_charged: 按功能扣费累计的光子数
    - feature_charges: 功能扣费明细列表

    返回示例:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "data": {
            "conversation_id": "conv_123",
            "user_id": "user_456",
            "total_tokens": 15000,
            "total_photons_charged": 50,
            "request_count": 10,
            "feature_charges": [
                {"feature_type": "report", "photons": 30, "timestamp": "2025-11-03T23:00:00"},
                {"feature_type": "structure_gen", "photons": 10, "timestamp": "2025-11-03T23:15:00"}
            ],
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
    获取指定用户的总统计数据（所有对话的聚合）

    ⚠️ 注意：此端点已弃用，建议使用 WebSocket 的 get_user_stats 消息
    ⚠️ REST API 无法验证用户身份，存在安全风险
    ⚠️ 仅用于开发和调试，生产环境应使用 WebSocket

    返回示例:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "data": {
            "user_id": "user_456",
            "total_conversations": 5,
            "total_tokens": 50000,
            "total_photons_charged": 150,
            "total_requests": 50,
            "conversations": [
                {
                    "conversation_id": "conv_123",
                    "total_tokens": 15000,
                    "total_photons_charged": 50,
                    "request_count": 10,
                    "feature_charges": [...]
                }
            ]
        }
    }
    ```
    """
    # ⚠️ 安全警告：REST API 无法验证用户身份
    logger.warning(f"⚠️ [安全警告] REST API 获取用户统计: user_id={user_id}（无身份验证）")

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
    获取全局统计数据

    返回示例:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "data": {
            "total_tokens": 100000,
            "total_photons_charged": 300,
            "total_requests": 100,
            "total_sessions": 20,
            "start_time": "2025-11-03T00:00:00",
            "current_time": "2025-11-03T23:30:00"
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


# ==========================================
# 🆕 定价系统 API（简化版）
# ==========================================

class PermissionCheckRequest(BaseModel):
    """权限检查请求"""
    feature_type: str
    quantity: int = 1


class PermissionCheckResponse(BaseModel):
    """权限检查响应"""
    success: bool
    allowed: bool
    reason: str
    photons_required: int


@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission(request: PermissionCheckRequest):
    """
    检查功能所需光子数（简化版，不涉及用户数据库）

    Args:
        request: 权限检查请求

    Returns:
        权限检查结果
    """
    try:
        from .pricing_service import PricingService

        result = PricingService.check_permission(
            feature_type=request.feature_type,
            quantity=request.quantity
        )

        return PermissionCheckResponse(
            success=True,
            **result
        )

    except Exception as e:
        logger.error(f"❌ 检查权限失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing/config")
async def get_pricing_config():
    """
    获取收费标准配置

    Returns:
        完整的收费标准配置
    """
    try:
        from .pricing_config import (
            FEATURE_PRICING,
            PRICING_MULTIPLIER,
            FREE_QUOTA_CONFIG,
            INVITATION_REWARDS_INVITER,
            INVITATION_REWARDS_INVITEE,
            BATCH_DISCOUNT,
            get_latest_pricing_version,
            PRICING_CHANGELOG
        )

        # 计算实际生效的价格（应用倍率）
        effective_pricing = {
            k: int(v * PRICING_MULTIPLIER)
            for k, v in FEATURE_PRICING.items()
        }

        return {
            "success": True,
            "version": get_latest_pricing_version(),
            "feature_pricing": effective_pricing,
            "free_quota": FREE_QUOTA_CONFIG,
            "invitation_rewards": {
                "inviter": INVITATION_REWARDS_INVITER,
                "invitee": INVITATION_REWARDS_INVITEE,
            },
            "batch_discount": BATCH_DISCOUNT,
            "changelog": PRICING_CHANGELOG,
        }

    except Exception as e:
        logger.error(f"❌ 获取收费标准配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 💳 扣费接口（前端主动扣费）
# ==========================================

class ChargeRequest(BaseModel):
    """扣费请求模型"""
    feature_type: str  # 功能类型（如 'report', 'structure_gen' 等）
    session_id: str    # 会话 ID
    quantity: int = 1  # 数量（默认 1）


class ChargeResponse(BaseModel):
    """扣费响应模型"""
    success: bool
    message: str
    photons: Optional[int] = None
    feature_type: Optional[str] = None
    session_id: Optional[str] = None
    error_code: Optional[str] = None


@router.post("/charge", response_model=ChargeResponse)
async def charge_for_feature(
    request: ChargeRequest,
    appAccessKey: Optional[str] = Cookie(None),
    clientName: Optional[str] = Cookie(None)
):
    """
    执行功能扣费（前端主动调用）

    Args:
        request: 扣费请求（包含 feature_type, session_id, quantity）
        appAccessKey: 从 Cookie 中提取的 Bohrium AccessKey
        clientName: 从 Cookie 中提取的客户端名称

    Returns:
        扣费结果

    Raises:
        HTTPException: 当 Cookie 不存在或扣费失败时
    """
    try:
        # 1. 验证 Cookie 凭证
        if not appAccessKey:
            logger.error(f"❌ [扣费] Cookie 中未找到 appAccessKey")
            return ChargeResponse(
                success=False,
                message="未检测到 Bohrium Cookie，请在浏览器中登录 Bohrium 平台后刷新页面",
                error_code="NO_COOKIE_ACCESS_KEY",
                feature_type=request.feature_type,
                session_id=request.session_id
            )

        # 2. 记录扣费请求
        logger.info(f"💳 [扣费请求] feature_type={request.feature_type}, session_id={request.session_id}, quantity={request.quantity}")
        logger.info(f"💳 [扣费请求] 使用 Cookie 凭证: AK={appAccessKey[:8]}...{appAccessKey[-4:]}, client_name={clientName or 'ResearchMind'}")

        # 3. 调用 PricingService 执行扣费
        result = PricingService.charge_for_feature(
            feature_type=request.feature_type,
            session_id=request.session_id,
            user_access_key=appAccessKey,
            user_client_name=clientName or "researchmind-uuid1759932177",
            quantity=request.quantity
        )

        # 4. 返回扣费结果
        if result.get("success"):
            logger.info(f"✅ [扣费成功] feature_type={request.feature_type}, photons={result.get('photons', 0)}")
            return ChargeResponse(
                success=True,
                message=result.get("message", "扣费成功"),
                photons=result.get("photons", 0),
                feature_type=request.feature_type,
                session_id=request.session_id
            )
        else:
            logger.error(f"❌ [扣费失败] feature_type={request.feature_type}, message={result.get('message')}")
            return ChargeResponse(
                success=False,
                message=result.get("message", "扣费失败"),
                photons=result.get("photons", 0),
                feature_type=request.feature_type,
                session_id=request.session_id,
                error_code=result.get("error_code", "CHARGE_FAILED")
            )

    except Exception as e:
        logger.error(f"❌ [扣费异常] feature_type={request.feature_type}, error={e}", exc_info=True)
        return ChargeResponse(
            success=False,
            message=f"扣费异常: {str(e)}",
            feature_type=request.feature_type,
            session_id=request.session_id,
            error_code="INTERNAL_ERROR"
        )
