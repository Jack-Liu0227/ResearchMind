"""
认证模块（简化版）

✅ 认证方式：完全基于 Cookie（不使用 JWT Token）
✅ 保留 Bohrium OAuth 服务用于验证 AccessKey（可选）

已移除：
- ❌ JWT Token 相关功能（jwt_handler.py）
- ❌ 用户依赖注入（dependencies.py）
"""

from .bohrium_oauth import bohrium_oauth_service, BohriumOAuthService

__all__ = [
    "bohrium_oauth_service",
    "BohriumOAuthService"
]

