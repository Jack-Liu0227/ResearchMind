"""
用户认证 API

提供基于 Bohrium OAuth 的用户认证接口
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Cookie, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .database import get_db, User
from .auth import bohrium_oauth_service, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ==================== 请求/响应模型 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    access_key: str
    client_name: str = "ResearchMind"
    sku_id: str = "10048"


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[dict] = None


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    id: int
    access_key_masked: str
    client_name: str
    sku_id: str
    total_photons_used: float
    total_tokens_used: int
    created_at: str
    last_login_at: Optional[str]


# ==================== API 端点 ====================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: DBSession = Depends(get_db)
):
    """
    用户登录（通过 Bohrium AccessKey）
    
    验证 AccessKey 有效性，如果用户不存在则自动注册
    """
    try:
        user, token, error = bohrium_oauth_service.authenticate_or_create_user(
            db=db,
            access_key=request.access_key,
            client_name=request.client_name,
            sku_id=request.sku_id,
            verify_key=True  # 首次登录时验证 AccessKey
        )
        
        if error:
            return LoginResponse(
                success=False,
                message=error
            )
        
        return LoginResponse(
            success=True,
            message="登录成功",
            token=token,
            user={
                "id": user.id,
                "access_key_masked": f"{user.access_key[:8]}...{user.access_key[-4:]}",
                "client_name": user.client_name,
                "sku_id": user.sku_id
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 登录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/login-from-cookie", response_model=LoginResponse)
async def login_from_cookie(
    appAccessKey: Optional[str] = Cookie(None),
    clientName: Optional[str] = Cookie(None),
    db: DBSession = Depends(get_db)
):
    """
    从 Cookie 自动登录
    
    读取浏览器 Cookie 中的 appAccessKey 和 clientName，自动登录
    """
    try:
        if not appAccessKey:
            return LoginResponse(
                success=False,
                message="未检测到 Bohrium Cookie，请手动登录"
            )
        
        user, token, error = bohrium_oauth_service.authenticate_or_create_user(
            db=db,
            access_key=appAccessKey,
            client_name=clientName or "ResearchMind",
            sku_id="10048",
            verify_key=False  # Cookie 登录时跳过验证（提升性能）
        )
        
        if error:
            return LoginResponse(
                success=False,
                message=error
            )
        
        logger.info(f"✅ Cookie 自动登录成功: user_id={user.id}")
        
        return LoginResponse(
            success=True,
            message="自动登录成功（来自 Cookie）",
            token=token,
            user={
                "id": user.id,
                "access_key_masked": f"{user.access_key[:8]}...{user.access_key[-4:]}",
                "client_name": user.client_name,
                "sku_id": user.sku_id
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Cookie 登录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户信息
    
    需要在请求头中携带 Authorization: Bearer <token>
    """
    return UserInfoResponse(
        id=current_user.id,
        access_key_masked=f"{current_user.access_key[:8]}...{current_user.access_key[-4:]}",
        client_name=current_user.client_name,
        sku_id=current_user.sku_id,
        total_photons_used=current_user.total_photons_used,
        total_tokens_used=current_user.total_tokens_used,
        created_at=current_user.created_at.isoformat(),
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    用户登出
    
    前端应删除本地存储的 Token
    """
    logger.info(f"✅ 用户登出: user_id={current_user.id}")
    
    return {
        "success": True,
        "message": "登出成功"
    }

