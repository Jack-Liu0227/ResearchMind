"""
用户认证 API（简化版）

✅ 认证方式：完全基于 Cookie（不使用 JWT Token）
✅ 数据库：仅用于统计和历史记录

已移除的接口：
- ❌ POST /api/auth/login（不再需要）
- ❌ POST /api/auth/login-from-cookie（不再需要）
- ❌ GET /api/auth/me（已简化，不需要 JWT Token）
- ❌ POST /api/auth/logout（不再需要）
"""

import logging
from typing import Optional
from fastapi import APIRouter, Cookie
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ==================== 响应模型 ====================

class UserInfoResponse(BaseModel):
    """用户信息响应"""
    access_key_masked: str
    client_name: str
    sku_id: str


# ==================== API 端点 ====================

@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    appAccessKey: Optional[str] = Cookie(None),
    clientName: Optional[str] = Cookie(None)
):
    """
    获取当前用户信息（基于 Cookie）

    ✅ 不需要 JWT Token，直接从 Cookie 读取
    """
    if not appAccessKey:
        return {
            "access_key_masked": "未检测到 Cookie",
            "client_name": clientName or "ResearchMind",
            "sku_id": "10048"
        }

    return UserInfoResponse(
        access_key_masked=f"{appAccessKey[:8]}...{appAccessKey[-4:]}",
        client_name=clientName or "ResearchMind",
        sku_id="10048"
    )

