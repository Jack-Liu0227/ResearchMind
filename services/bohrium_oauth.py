"""
Bohrium OAuth 认证服务

通过 Bohrium 平台的 OAuth 功能自动获取用户的 ID 和 AccessKey
"""

import os
import logging
import requests
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import secrets
import hashlib
import base64
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class BohriumOAuthConfig:
    """Bohrium OAuth 配置"""
    
    # OAuth 端点（需要根据 Bohrium 实际文档调整）
    OAUTH_BASE_URL = os.getenv('BOHRIUM_OAUTH_BASE_URL', 'https://openapi.dp.tech/oauth')
    AUTHORIZE_URL = f"{OAUTH_BASE_URL}/authorize"
    TOKEN_URL = f"{OAUTH_BASE_URL}/token"
    USER_INFO_URL = f"{OAUTH_BASE_URL}/userinfo"
    
    # 应用配置
    CLIENT_ID = os.getenv('BOHRIUM_CLIENT_ID', '')
    CLIENT_SECRET = os.getenv('BOHRIUM_CLIENT_SECRET', '')
    REDIRECT_URI = os.getenv('BOHRIUM_REDIRECT_URI', 'http://localhost:50003/api/auth/callback')
    
    # OAuth 作用域
    SCOPE = 'openid profile billing'  # 需要根据 Bohrium 文档调整


class BohriumOAuthService:
    """Bohrium OAuth 服务"""
    
    def __init__(self):
        self.config = BohriumOAuthConfig()
        
        # 验证配置
        if not self.config.CLIENT_ID or not self.config.CLIENT_SECRET:
            logger.warning("⚠️ Bohrium OAuth 未配置 CLIENT_ID 或 CLIENT_SECRET")
        else:
            logger.info(
                f"💎 Bohrium OAuth 服务已初始化 - "
                f"Client ID: {self.config.CLIENT_ID[:8]}..."
            )
        
        # 存储 state 和 code_verifier（用于 PKCE）
        self.pending_auth: Dict[str, Dict[str, Any]] = {}
    
    def generate_authorization_url(self, user_session_id: str) -> Dict[str, str]:
        """
        生成 OAuth 授权 URL
        
        Args:
            user_session_id: 用户会话 ID
            
        Returns:
            包含授权 URL 和 state 的字典
        """
        # 生成随机 state（防止 CSRF 攻击）
        state = secrets.token_urlsafe(32)
        
        # 生成 PKCE code_verifier 和 code_challenge
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        # 保存 state 和 code_verifier
        self.pending_auth[state] = {
            'user_session_id': user_session_id,
            'code_verifier': code_verifier,
            'created_at': datetime.now()
        }
        
        # 构建授权 URL
        params = {
            'client_id': self.config.CLIENT_ID,
            'redirect_uri': self.config.REDIRECT_URI,
            'response_type': 'code',
            'scope': self.config.SCOPE,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        auth_url = f"{self.config.AUTHORIZE_URL}?{urlencode(params)}"
        
        logger.info(f"🔐 生成授权 URL - Session: {user_session_id[:8]}..., State: {state[:8]}...")
        
        return {
            'authorization_url': auth_url,
            'state': state
        }
    
    def exchange_code_for_token(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """
        用授权码换取访问令牌
        
        Args:
            code: 授权码
            state: 状态码（用于验证）
            
        Returns:
            包含 access_token 和用户信息的字典，失败返回 None
        """
        # 验证 state
        if state not in self.pending_auth:
            logger.error(f"❌ 无效的 state: {state[:8]}...")
            return None
        
        auth_data = self.pending_auth[state]
        code_verifier = auth_data['code_verifier']
        user_session_id = auth_data['user_session_id']
        
        # 清理已使用的 state
        del self.pending_auth[state]
        
        # 请求访问令牌
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.config.REDIRECT_URI,
            'client_id': self.config.CLIENT_ID,
            'client_secret': self.config.CLIENT_SECRET,
            'code_verifier': code_verifier
        }
        
        try:
            logger.info(f"🔐 正在交换授权码 - Session: {user_session_id[:8]}...")
            
            response = requests.post(
                self.config.TOKEN_URL,
                data=token_data,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"❌ 获取令牌失败: HTTP {response.status_code} - {response.text}")
                return None
            
            token_response = response.json()
            access_token = token_response.get('access_token')
            
            if not access_token:
                logger.error(f"❌ 响应中没有 access_token: {token_response}")
                return None
            
            logger.info(f"✅ 成功获取访问令牌 - Session: {user_session_id[:8]}...")
            
            # 获取用户信息
            user_info = self.get_user_info(access_token)
            
            if user_info:
                return {
                    'access_token': access_token,
                    'refresh_token': token_response.get('refresh_token'),
                    'expires_in': token_response.get('expires_in', 3600),
                    'user_info': user_info,
                    'user_session_id': user_session_id
                }
            else:
                logger.error("❌ 获取用户信息失败")
                return None
                
        except Exception as e:
            logger.error(f"❌ 交换授权码异常: {e}", exc_info=True)
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息（包括 AccessKey 和 SKU ID）
        
        Args:
            access_token: 访问令牌
            
        Returns:
            用户信息字典，失败返回 None
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                self.config.USER_INFO_URL,
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"❌ 获取用户信息失败: HTTP {response.status_code}")
                return None
            
            user_info = response.json()
            
            logger.info(f"✅ 成功获取用户信息 - User ID: {user_info.get('user_id', 'unknown')}")
            
            # 返回标准化的用户信息
            return {
                'user_id': user_info.get('user_id') or user_info.get('id'),
                'username': user_info.get('username') or user_info.get('name'),
                'email': user_info.get('email'),
                'access_key': user_info.get('access_key') or user_info.get('accessKey'),
                'sku_id': user_info.get('sku_id') or user_info.get('skuId'),
                'client_name': user_info.get('client_name', 'ResearchMind'),
                'raw_data': user_info  # 保留原始数据
            }
            
        except Exception as e:
            logger.error(f"❌ 获取用户信息异常: {e}", exc_info=True)
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            新的令牌信息，失败返回 None
        """
        try:
            token_data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': self.config.CLIENT_ID,
                'client_secret': self.config.CLIENT_SECRET
            }
            
            response = requests.post(
                self.config.TOKEN_URL,
                data=token_data,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"❌ 刷新令牌失败: HTTP {response.status_code}")
                return None
            
            token_response = response.json()
            logger.info("✅ 成功刷新访问令牌")
            
            return {
                'access_token': token_response.get('access_token'),
                'refresh_token': token_response.get('refresh_token', refresh_token),
                'expires_in': token_response.get('expires_in', 3600)
            }
            
        except Exception as e:
            logger.error(f"❌ 刷新令牌异常: {e}", exc_info=True)
            return None
    
    def cleanup_expired_states(self, max_age_minutes: int = 10):
        """清理过期的 state"""
        now = datetime.now()
        expired_states = [
            state for state, data in self.pending_auth.items()
            if (now - data['created_at']).total_seconds() > max_age_minutes * 60
        ]
        
        for state in expired_states:
            del self.pending_auth[state]
        
        if expired_states:
            logger.info(f"🧹 清理了 {len(expired_states)} 个过期的 OAuth state")


# 全局单例
_oauth_service: Optional[BohriumOAuthService] = None


def get_oauth_service() -> BohriumOAuthService:
    """获取全局 OAuth 服务实例"""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = BohriumOAuthService()
    return _oauth_service

