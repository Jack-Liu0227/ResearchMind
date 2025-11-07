"""
计费配置 API

提供用户计费配置的 REST API 接口，包括 OAuth 认证
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Request, Cookie
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from .user_billing_config import get_config_manager, get_billing_context_manager
from .bohrium_oauth import get_oauth_service
from .photon_billing import get_billing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


class BillingConfigRequest(BaseModel):
    """计费配置请求"""
    user_id: str
    access_key: str
    sku_id: str
    client_name: Optional[str] = "ResearchMind"


class BillingConfigResponse(BaseModel):
    """计费配置响应"""
    success: bool
    message: str
    has_config: bool
    config: Optional[dict] = None


@router.post("/config/save")
async def save_billing_config(request: BillingConfigRequest) -> BillingConfigResponse:
    """
    保存用户的 Bohrium 计费配置

    请求示例:
    ```json
    {
        "user_id": "session_123",
        "access_key": "e3a895e74d9a4c858b64bfd1d7343e02",
        "sku_id": "10048",
        "client_name": "ResearchMind"
    }
    ```
    """
    try:
        config_manager = get_config_manager()
        success = config_manager.save_user_config(
            user_id=request.user_id,
            access_key=request.access_key,
            sku_id=request.sku_id,
            client_name=request.client_name or "ResearchMind"
        )

        if success:
            return BillingConfigResponse(
                success=True,
                message="配置保存成功",
                has_config=True,
                config={
                    "sku_id": request.sku_id,
                    "client_name": request.client_name,
                    "access_key_masked": f"{request.access_key[:8]}...{request.access_key[-4:]}"
                }
            )
        else:
            raise HTTPException(status_code=500, detail="配置保存失败")

    except Exception as e:
        logger.error(f"❌ 保存计费配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/save-from-cookie")
async def save_billing_config_from_cookie(
    user_id: str = Query(..., description="用户会话 ID"),
    appAccessKey: Optional[str] = Cookie(None),
    clientName: Optional[str] = Cookie(None)
) -> BillingConfigResponse:
    """
    从 Cookie 中读取并保存用户的 Bohrium 计费配置

    这个端点会自动从浏览器 Cookie 中读取 appAccessKey 和 clientName，
    就像 Flask 的 request.cookies.get() 一样简单！

    前端调用示例:
    ```javascript
    // 前端只需要传 user_id，Cookie 会自动发送
    const response = await fetch('/api/billing/config/save-from-cookie?user_id=' + sessionId, {
        method: 'POST',
        credentials: 'include'  // 重要：确保发送 Cookie
    });
    ```

    返回示例:
    ```json
    {
        "success": true,
        "message": "配置保存成功（来自用户 Cookie）",
        "has_config": true,
        "config": {
            "sku_id": "10048",
            "client_name": "ResearchMind",
            "access_key_masked": "e3a895e7...ce02",
            "source": "来自用户 Cookie"
        }
    }
    ```
    """
    try:
        # 检查 Cookie 中是否有用户配置
        if not appAccessKey:
            # 如果没有用户配置，返回提示信息
            logger.info(f"ℹ️ 用户 {user_id[:8]}... 未提供 Cookie，将使用开发者默认配置")
            return BillingConfigResponse(
                success=True,
                message="未检测到用户 Cookie，将使用开发者默认配置",
                has_config=False,
                config={
                    "source": "开发者本地调试 AK"
                }
            )

        # 从 Cookie 中获取配置
        logger.info(f"🍪 从 Cookie 中获取用户 Bohrium 配置")
        logger.info(f"   User ID: {user_id[:8]}...")
        logger.info(f"   AccessKey: {appAccessKey[:8]}...{appAccessKey[-4:]}")
        logger.info(f"   ClientName: {clientName or 'ResearchMind'}")
        logger.info(f"   来源: 来自用户 Cookie")

        # 保存到配置文件
        config_manager = get_config_manager()
        success = config_manager.save_user_config(
            user_id=user_id,
            access_key=appAccessKey,
            sku_id="10048",  # 默认 SKU ID
            client_name=clientName or "ResearchMind"
        )

        if success:
            return BillingConfigResponse(
                success=True,
                message="配置保存成功（来自用户 Cookie）",
                has_config=True,
                config={
                    "sku_id": "10048",
                    "client_name": clientName or "ResearchMind",
                    "access_key_masked": f"{appAccessKey[:8]}...{appAccessKey[-4:]}",
                    "source": "来自用户 Cookie"
                }
            )
        else:
            raise HTTPException(status_code=500, detail="配置保存失败")

    except Exception as e:
        logger.error(f"❌ 从 Cookie 保存计费配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/{user_id}")
async def get_billing_config(user_id: str) -> BillingConfigResponse:
    """
    获取用户的计费配置状态
    
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
    try:
        config_manager = get_config_manager()
        has_config = config_manager.has_user_config(user_id)
        
        if has_config:
            config = config_manager.get_user_config(user_id)
            return BillingConfigResponse(
                success=True,
                message="已配置",
                has_config=True,
                config={
                    "sku_id": config.get('sku_id'),
                    "client_name": config.get('client_name'),
                    "access_key_masked": f"{config['access_key'][:8]}...{config['access_key'][-4:]}"
                }
            )
        else:
            return BillingConfigResponse(
                success=True,
                message="未配置，将使用默认配置",
                has_config=False,
                config=None
            )
            
    except Exception as e:
        logger.error(f"❌ 获取计费配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/config/{user_id}")
async def delete_billing_config(user_id: str) -> BillingConfigResponse:
    """删除用户的计费配置"""
    try:
        config_manager = get_config_manager()
        success = config_manager.delete_user_config(user_id)
        
        if success:
            return BillingConfigResponse(
                success=True,
                message="配置已删除",
                has_config=False,
                config=None
            )
        else:
            return BillingConfigResponse(
                success=False,
                message="配置不存在",
                has_config=False,
                config=None
            )
            
    except Exception as e:
        logger.error(f"❌ 删除计费配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# OAuth 认证路由
# ==========================================

@auth_router.get("/login")
async def oauth_login(user_session_id: str = Query(..., description="用户会话 ID")):
    """
    启动 Bohrium OAuth 登录流程

    前端调用示例:
    ```javascript
    window.location.href = '/api/auth/login?user_session_id=' + sessionId
    ```

    返回: 重定向到 Bohrium 授权页面
    """
    try:
        oauth_service = get_oauth_service()
        auth_data = oauth_service.generate_authorization_url(user_session_id)

        logger.info(f"🔐 用户 {user_session_id[:8]}... 开始 OAuth 登录")

        # 重定向到 Bohrium 授权页面
        return RedirectResponse(url=auth_data['authorization_url'])

    except Exception as e:
        logger.error(f"❌ OAuth 登录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="状态码")
):
    """
    OAuth 回调端点

    Bohrium 授权成功后会重定向到这里，携带 code 和 state 参数

    🆕 修复：现在会设置浏览器 Cookie，以便前端能够检测用户登录状态
    """
    try:
        oauth_service = get_oauth_service()

        # 用授权码换取访问令牌和用户信息
        token_data = oauth_service.exchange_code_for_token(code, state)

        if not token_data:
            logger.error("❌ OAuth 回调失败：无法获取令牌")
            # 重定向到前端错误页面
            return RedirectResponse(url="/?auth_error=token_exchange_failed")

        user_info = token_data['user_info']
        user_session_id = token_data['user_session_id']

        # 保存用户的 Bohrium 配置
        config_manager = get_config_manager()
        success = config_manager.save_user_config(
            user_id=user_session_id,
            access_key=user_info['access_key'],
            sku_id=str(user_info['sku_id']),
            client_name=user_info.get('client_name', 'ResearchMind')
        )

        if success:
            logger.info(
                f"✅ OAuth 认证成功 - "
                f"User: {user_info.get('username', 'unknown')}, "
                f"Session: {user_session_id[:8]}..."
            )

            # 🆕 创建重定向响应并设置 Cookie
            response = RedirectResponse(
                url=f"/?auth_success=true&username={user_info.get('username', 'User')}"
            )

            # 🆕 设置 appAccessKey Cookie（有效期 30 天）
            response.set_cookie(
                key="appAccessKey",
                value=user_info['access_key'],
                max_age=30 * 24 * 60 * 60,  # 30 天
                path="/",
                httponly=False,  # 允许 JavaScript 读取（前端需要检测）
                samesite="lax",  # 防止 CSRF 攻击
                secure=False  # 开发环境使用 HTTP，生产环境应改为 True
            )

            # 🆕 设置 clientName Cookie（有效期 30 天）
            client_name = user_info.get('client_name', 'ResearchMind')
            response.set_cookie(
                key="clientName",
                value=client_name,
                max_age=30 * 24 * 60 * 60,  # 30 天
                path="/",
                httponly=False,  # 允许 JavaScript 读取
                samesite="lax",
                secure=False
            )

            logger.info(
                f"🍪 已设置用户 Cookie - "
                f"AccessKey: {user_info['access_key'][:8]}...{user_info['access_key'][-4:]}, "
                f"ClientName: {client_name}"
            )

            return response
        else:
            logger.error("❌ 保存用户配置失败")
            return RedirectResponse(url="/?auth_error=config_save_failed")

    except Exception as e:
        logger.error(f"❌ OAuth 回调异常: {e}", exc_info=True)
        return RedirectResponse(url=f"/?auth_error={str(e)}")


class OAuthStatusResponse(BaseModel):
    """OAuth 状态响应"""
    is_configured: bool
    oauth_enabled: bool
    username: Optional[str] = None
    user_id: Optional[str] = None


@auth_router.get("/status/{user_session_id}")
async def get_auth_status(user_session_id: str) -> OAuthStatusResponse:
    """
    获取用户的认证状态

    返回示例:
    ```json
    {
        "is_configured": true,
        "oauth_enabled": true,
        "username": "张三",
        "user_id": "user_123"
    }
    ```
    """
    try:
        config_manager = get_config_manager()
        has_config = config_manager.has_user_config(user_session_id)

        oauth_service = get_oauth_service()
        oauth_enabled = bool(oauth_service.config.CLIENT_ID and oauth_service.config.CLIENT_SECRET)

        if has_config:
            config = config_manager.get_user_config(user_session_id)
            return OAuthStatusResponse(
                is_configured=True,
                oauth_enabled=oauth_enabled,
                username=config.get('username'),
                user_id=user_session_id
            )
        else:
            return OAuthStatusResponse(
                is_configured=False,
                oauth_enabled=oauth_enabled,
                username=None,
                user_id=None
            )

    except Exception as e:
        logger.error(f"❌ 获取认证状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        context_manager = get_billing_context_manager()
        context = context_manager.get_context(conversation_id)

        if not context:
            return BillingStatsResponse(
                success=False,
                message=f"对话 {conversation_id} 不存在",
                data=None
            )

        snapshot = context.get_snapshot()

        return BillingStatsResponse(
            success=True,
            message="获取成功",
            data=snapshot
        )

    except Exception as e:
        logger.error(f"❌ 获取对话计费统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/user/{user_id}")
async def get_user_billing_stats(user_id: str) -> BillingStatsResponse:
    """
    获取指定用户的总计费统计（所有对话的聚合）

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
    try:
        context_manager = get_billing_context_manager()
        user_stats = context_manager.get_user_total_usage(user_id)

        return BillingStatsResponse(
            success=True,
            message="获取成功",
            data=user_stats
        )

    except Exception as e:
        logger.error(f"❌ 获取用户计费统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/global")
async def get_global_billing_stats() -> BillingStatsResponse:
    """
    获取全局计费统计

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
    try:
        billing_service = get_billing_service()
        global_stats = billing_service.get_global_stats()

        return BillingStatsResponse(
            success=True,
            message="获取成功",
            data=global_stats
        )

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

