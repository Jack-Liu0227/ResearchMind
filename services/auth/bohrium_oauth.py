"""
Bohrium OAuth 认证服务

通过验证 Bohrium AccessKey 来认证用户
"""

import logging
import hashlib
import secrets
import time
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession

from ..database.models import User
from .jwt_handler import create_access_token

logger = logging.getLogger(__name__)

# Bohrium API 配置
BOHRIUM_API_URL = "https://openapi.dp.tech/openapi/v1/api/integral/consume"
DEFAULT_SKU_ID = "10048"


class BohriumOAuthService:
    """Bohrium OAuth 认证服务"""
    
    @staticmethod
    def hash_access_key(access_key: str) -> str:
        """生成 AccessKey 的哈希值（用于快速查找和隐私保护）"""
        return hashlib.sha256(access_key.encode()).hexdigest()
    
    @staticmethod
    def verify_access_key(access_key: str, client_name: str, sku_id: str = DEFAULT_SKU_ID) -> Tuple[bool, Optional[str]]:
        """
        验证 Bohrium AccessKey 是否有效
        
        通过调用 Bohrium API 进行小额测试扣费（0 光子）来验证
        
        Args:
            access_key: Bohrium AccessKey
            client_name: 客户端名称
            sku_id: SKU ID
        
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 生成测试业务流水号
            timestamp = int(time.time())
            rand_part = secrets.randbits(16)
            biz_no = int(f"{timestamp}{rand_part}")
            
            # 调用 Bohrium API（测试扣费 0 光子）
            headers = {
                "accessKey": access_key,
                "x-app-key": client_name,
                "Content-Type": "application/json"
            }
            payload = {
                "bizNo": biz_no,
                "changeType": 1,
                "eventValue": 0,  # 测试扣费 0 光子
                "skuId": int(sku_id),
                "scene": "appCustomizeCharge"
            }
            
            logger.info(f"🔍 验证 AccessKey: {access_key[:8]}...{access_key[-4:]}")
            
            response = requests.post(BOHRIUM_API_URL, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                # 检查返回结果
                if result.get("code") == 0 or result.get("success") is True:
                    logger.info(f"✅ AccessKey 验证成功: {access_key[:8]}...{access_key[-4:]}")
                    return True, None
                else:
                    error_msg = result.get("message", "未知错误")
                    logger.warning(f"❌ AccessKey 验证失败: {error_msg}")
                    return False, error_msg
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ Bohrium API 调用失败: {error_msg}")
                return False, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = "Bohrium API 请求超时"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"验证失败: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return False, error_msg
    
    @staticmethod
    def authenticate_or_create_user(
        db: DBSession,
        access_key: str,
        client_name: str,
        sku_id: str = DEFAULT_SKU_ID,
        verify_key: bool = True
    ) -> Tuple[Optional[User], Optional[str], Optional[str]]:
        """
        通过 AccessKey 认证用户，如果不存在则创建新用户
        
        Args:
            db: 数据库会话
            access_key: Bohrium AccessKey
            client_name: 客户端名称
            sku_id: SKU ID
            verify_key: 是否验证 AccessKey（首次登录时验证，后续可跳过）
        
        Returns:
            (用户对象, JWT Token, 错误信息)
        """
        try:
            # 1. 验证 AccessKey（可选）
            if verify_key:
                is_valid, error_msg = BohriumOAuthService.verify_access_key(access_key, client_name, sku_id)
                if not is_valid:
                    return None, None, f"AccessKey 验证失败: {error_msg}"
            
            # 2. 查找或创建用户
            access_key_hash = BohriumOAuthService.hash_access_key(access_key)
            user = db.query(User).filter(User.access_key_hash == access_key_hash).first()
            
            if user:
                # 用户已存在，更新最后登录时间
                user.last_login_at = datetime.utcnow()
                user.client_name = client_name  # 更新客户端名称
                user.sku_id = sku_id  # 更新 SKU ID
                db.commit()
                db.refresh(user)
                
                logger.info(f"✅ 用户登录成功: user_id={user.id}, access_key={access_key[:8]}...{access_key[-4:]}")
            else:
                # 创建新用户
                user = User(
                    access_key=access_key,
                    access_key_hash=access_key_hash,
                    client_name=client_name,
                    sku_id=sku_id,
                    is_verified=verify_key,  # 如果验证过则标记为已验证
                    last_login_at=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                
                logger.info(f"✅ 新用户注册成功: user_id={user.id}, access_key={access_key[:8]}...{access_key[-4:]}")
            
            # 3. 生成 JWT Token
            token = create_access_token(
                data={"user_id": user.id, "access_key_hash": access_key_hash}
            )
            
            return user, token, None
            
        except Exception as e:
            logger.error(f"❌ 认证失败: {e}", exc_info=True)
            db.rollback()
            return None, None, f"认证失败: {str(e)}"


# 全局服务实例
bohrium_oauth_service = BohriumOAuthService()

