"""
FastAPI 认证依赖

用于保护需要认证的 API 端点
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as DBSession

from ..database import get_db, User
from .jwt_handler import verify_token

logger = logging.getLogger(__name__)

# HTTP Bearer Token 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db)
) -> Optional[User]:
    """
    获取当前登录用户（依赖注入）
    
    支持两种方式传递 Token：
    1. Authorization: Bearer <token>（标准方式）
    2. Authorization: <token>（简化方式）
    
    Args:
        credentials: HTTP Bearer Token
        authorization: Authorization 头（备用）
        db: 数据库会话
    
    Returns:
        用户对象，如果未认证则抛出 401 异常
    """
    token = None
    
    # 1. 尝试从 Bearer Token 获取
    if credentials:
        token = credentials.credentials
    
    # 2. 尝试从 Authorization 头获取（支持简化格式）
    elif authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
    
    # 3. 未提供 Token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 4. 验证 Token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 5. 获取用户 ID
    user_id: int = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 6. 查询用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前激活的用户（依赖注入）
    
    Args:
        current_user: 当前用户
    
    Returns:
        用户对象，如果用户未激活则抛出 403 异常
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db)
) -> Optional[User]:
    """
    获取当前用户（可选，不强制要求认证）
    
    用于某些 API 端点既支持匿名访问，也支持认证访问的场景
    
    Returns:
        用户对象，如果未认证则返回 None
    """
    try:
        return await get_current_user(credentials, authorization, db)
    except HTTPException:
        return None

