"""
光子计费服务 (Photon Billing Service)

根据 token 使用量计算光子消耗
默认收费标准：3000 tokens = 1 光子
"""

import os
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class PhotonBillingConfig:
    """光子计费配置"""

    # Bohrium 平台凭证
    BOHRIUM_SKU_ID = os.getenv('BOHRIUM_SKU_ID', '10048')
    BOHRIUM_ACCESS_KEY = os.getenv('BOHRIUM_ACCESS_KEY', '')

    # 从环境变量读取收费标准，默认 3000 tokens = 1 光子
    TOKENS_PER_PHOTON = int(os.getenv('PHOTON_TOKENS_PER_PHOTON', '3000'))

    # 是否启用计费（默认启用）
    BILLING_ENABLED = os.getenv('PHOTON_BILLING_ENABLED', 'true').lower() == 'true'

    # 计费精度（保留小数位数）
    BILLING_PRECISION = int(os.getenv('PHOTON_BILLING_PRECISION', '4'))

    # 是否记录详细日志
    VERBOSE_LOGGING = os.getenv('PHOTON_BILLING_VERBOSE', 'false').lower() == 'true'


class PhotonBillingService:
    """
    光子计费服务
    
    功能：
    1. 跟踪每个会话的 token 使用量
    2. 计算光子消耗
    3. 提供使用统计
    """
    
    def __init__(self):
        """初始化计费服务"""
        self.config = PhotonBillingConfig()
        
        # 会话级别的使用统计
        # session_id -> {
        #     'total_tokens': int,
        #     'total_photons': float,
        #     'requests': [{'timestamp': str, 'tokens': int, 'photons': float, 'model': str}]
        # }
        self.session_usage: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_tokens': 0,
            'total_photons': 0.0,
            'requests': []
        })
        
        # 全局统计
        self.global_stats = {
            'total_tokens': 0,
            'total_photons': 0.0,
            'total_requests': 0,
            'start_time': datetime.now().isoformat()
        }
        
        # 验证配置
        if self.config.BILLING_ENABLED and not self.config.BOHRIUM_ACCESS_KEY:
            logger.warning("⚠️ 计费已启用但未配置 BOHRIUM_ACCESS_KEY")

        logger.info(
            f"💎 光子计费服务已启动 - "
            f"SKU ID: {self.config.BOHRIUM_SKU_ID}, "
            f"AccessKey: {'已配置' if self.config.BOHRIUM_ACCESS_KEY else '未配置'}, "
            f"收费标准: {self.config.TOKENS_PER_PHOTON} tokens/光子, "
            f"计费状态: {'启用' if self.config.BILLING_ENABLED else '禁用'}"
        )
    
    def calculate_photons(self, tokens: int) -> float:
        """
        根据 token 数量计算光子消耗
        
        Args:
            tokens: token 数量
            
        Returns:
            光子数量（保留指定精度）
        """
        if not self.config.BILLING_ENABLED or tokens <= 0:
            return 0.0
        
        photons = tokens / self.config.TOKENS_PER_PHOTON
        return round(photons, self.config.BILLING_PRECISION)
    
    def record_usage(
        self,
        session_id: str,
        tokens: int,
        model: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        记录 token 使用并计算光子消耗
        
        Args:
            session_id: 会话 ID
            tokens: 使用的 token 数量
            model: 使用的模型名称
            metadata: 额外的元数据（如 agent_id, tool_name 等）
            
        Returns:
            包含本次使用和累计统计的字典
        """
        if not self.config.BILLING_ENABLED:
            return {
                'billing_enabled': False,
                'message': '计费功能已禁用'
            }
        
        # 计算光子消耗
        photons = self.calculate_photons(tokens)
        
        # 记录本次请求
        request_record = {
            'timestamp': datetime.now().isoformat(),
            'tokens': tokens,
            'photons': photons,
            'model': model,
            'metadata': metadata or {}
        }
        
        # 更新会话统计
        session_data = self.session_usage[session_id]
        session_data['total_tokens'] += tokens
        session_data['total_photons'] += photons
        session_data['requests'].append(request_record)
        
        # 更新全局统计
        self.global_stats['total_tokens'] += tokens
        self.global_stats['total_photons'] += photons
        self.global_stats['total_requests'] += 1
        
        # 构建返回结果
        result = {
            'billing_enabled': True,
            'current_request': {
                'tokens': tokens,
                'photons': photons,
                'model': model
            },
            'session_total': {
                'tokens': session_data['total_tokens'],
                'photons': round(session_data['total_photons'], self.config.BILLING_PRECISION),
                'requests_count': len(session_data['requests'])
            },
            'billing_config': {
                'tokens_per_photon': self.config.TOKENS_PER_PHOTON,
                'precision': self.config.BILLING_PRECISION
            }
        }
        
        # 详细日志
        if self.config.VERBOSE_LOGGING:
            logger.info(
                f"💎 [计费] 会话 {session_id[:8]}... | "
                f"本次: {tokens} tokens = {photons} 光子 | "
                f"累计: {session_data['total_tokens']} tokens = "
                f"{round(session_data['total_photons'], self.config.BILLING_PRECISION)} 光子 | "
                f"模型: {model}"
            )
        else:
            logger.info(
                f"💎 [计费] {tokens} tokens → {photons} 光子 (累计: "
                f"{round(session_data['total_photons'], self.config.BILLING_PRECISION)} 光子)"
            )
        
        return result
    
    def get_session_usage(self, session_id: str) -> Dict[str, Any]:
        """
        获取指定会话的使用统计
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话使用统计
        """
        if session_id not in self.session_usage:
            return {
                'session_id': session_id,
                'total_tokens': 0,
                'total_photons': 0.0,
                'requests_count': 0,
                'requests': []
            }
        
        session_data = self.session_usage[session_id]
        return {
            'session_id': session_id,
            'total_tokens': session_data['total_tokens'],
            'total_photons': round(session_data['total_photons'], self.config.BILLING_PRECISION),
            'requests_count': len(session_data['requests']),
            'requests': session_data['requests']
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        获取全局使用统计
        
        Returns:
            全局统计信息
        """
        return {
            'total_tokens': self.global_stats['total_tokens'],
            'total_photons': round(self.global_stats['total_photons'], self.config.BILLING_PRECISION),
            'total_requests': self.global_stats['total_requests'],
            'total_sessions': len(self.session_usage),
            'start_time': self.global_stats['start_time'],
            'current_time': datetime.now().isoformat(),
            'billing_config': {
                'tokens_per_photon': self.config.TOKENS_PER_PHOTON,
                'billing_enabled': self.config.BILLING_ENABLED,
                'precision': self.config.BILLING_PRECISION
            }
        }
    
    def reset_session(self, session_id: str) -> None:
        """
        重置指定会话的统计
        
        Args:
            session_id: 会话 ID
        """
        if session_id in self.session_usage:
            del self.session_usage[session_id]
            logger.info(f"💎 [计费] 已重置会话 {session_id[:8]}... 的统计")
    
    def reset_all(self) -> None:
        """重置所有统计"""
        self.session_usage.clear()
        self.global_stats = {
            'total_tokens': 0,
            'total_photons': 0.0,
            'total_requests': 0,
            'start_time': datetime.now().isoformat()
        }
        logger.info("💎 [计费] 已重置所有统计数据")


# 全局单例
_billing_service: Optional[PhotonBillingService] = None


def get_billing_service() -> PhotonBillingService:
    """获取全局计费服务实例"""
    global _billing_service
    if _billing_service is None:
        _billing_service = PhotonBillingService()
    return _billing_service

