"""
光子计费服务 (Photon Billing Service)

根据 token 使用量计算光子消耗
默认收费标准：5000 tokens = 1 光子（可通过环境变量 PHOTON_TOKENS_PER_PHOTON 配置）
"""

import os
import logging
import requests
import time
import secrets
import threading
from typing import Dict, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量（从 .env 文件）
load_dotenv()

logger = logging.getLogger(__name__)


class PhotonBillingConfig:
    """光子计费配置"""

    # Bohrium 平台凭证（开发者默认配置，用于测试）
    BOHRIUM_SKU_ID = os.getenv('BOHRIUM_SKU_ID', '10048')
    BOHRIUM_ACCESS_KEY = os.getenv('BOHRIUM_ACCESS_KEY', '')
    BOHRIUM_CLIENT_NAME = os.getenv('BOHRIUM_CLIENT_NAME', 'ResearchMind')

    # 从环境变量读取收费标准，默认 5000 tokens = 1 光子
    TOKENS_PER_PHOTON = int(os.getenv('PHOTON_TOKENS_PER_PHOTON', '5000'))

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
        self._global_lock = threading.RLock()

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
    
    def record_usage_isolated(
        self,
        conversation_id: str,
        user_id: str,
        tokens: int,
        model: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用隔离上下文记录 token 使用（推荐方法）

        这个方法确保每个对话的计费数据完全隔离，防止并发时的数据混乱

        新的扣费逻辑：
        - 每累计 5000 tokens 扣费 1 个光子
        - 优先使用用户的 appAccessKey 和 clientName（从 Cookie 获取）
        - 如果未获取到用户的，则使用开发者的 AK 进行测试

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID
            tokens: 使用的 token 数量
            model: 使用的模型名称
            metadata: 额外的元数据

        Returns:
            包含本次使用和累计统计的字典
        """
        if not self.config.BILLING_ENABLED:
            return {
                'billing_enabled': False,
                'message': '计费功能已禁用'
            }

        # 计算光子消耗（不再实时扣费，而是累计到5000 tokens时扣费）
        photons = self.calculate_photons(tokens)

        # 获取或创建隔离的计费上下文
        from .user_billing_config import get_billing_context_manager
        context_manager = get_billing_context_manager()
        context = context_manager.get_or_create_context(conversation_id, user_id)

        # 在隔离上下文中更新使用
        context.update_token_usage(tokens, photons, model, metadata)

        # 同时更新全局统计（用于向后兼容）
        with self._global_lock:
            self.global_stats['total_tokens'] += tokens
            self.global_stats['total_photons'] += photons
            self.global_stats['total_requests'] += 1

        # 新的扣费逻辑：每累计 5000 tokens 扣费 1 个光子
        charge_result = None
        snapshot = context.get_snapshot()
        total_tokens = snapshot['total_tokens']

        # 检查是否达到扣费阈值（5000 tokens = 1 光子）
        tokens_threshold = self.config.TOKENS_PER_PHOTON
        photons_to_charge = total_tokens // tokens_threshold  # 应该扣费的光子数

        # 获取已扣费的光子数（从上下文中）
        charged_photons = getattr(context, 'charged_photons', 0)

        # 计算需要扣费的光子数
        photons_need_charge = photons_to_charge - charged_photons

        if self.config.BILLING_ENABLED and photons_need_charge > 0:
            # 🔒 将计费逻辑包装在 try-except 中，确保计费失败不阻塞主流程
            try:
                # 获取用户的计费配置
                from .user_billing_config import get_config_manager
                user_config_manager = get_config_manager()
                user_config = user_config_manager.get_user_config(user_id)

                # 🔍 添加详细日志，追踪扣费流程
                logger.info(f"🔍 [计费追踪] user_id={user_id}, conversation_id={conversation_id}")
                logger.info(f"🔍 [计费追踪] 用户配置: {user_config}")

                # 使用用户配置的 AK 和 SKU，如果没有则使用默认配置
                user_access_key = user_config.get('access_key') if user_config else None
                user_sku_id = user_config.get('sku_id') if user_config else None
                user_client_name = user_config.get('client_name') if user_config else None

                # 🔍 记录使用的凭证（脱敏）
                if user_access_key:
                    logger.info(f"🔍 [计费追踪] 使用用户 AK: {user_access_key[:8]}...{user_access_key[-4:]}")
                else:
                    logger.warning(f"⚠️ [计费追踪] 未找到用户 AK，user_id={user_id}")

                # 调用扣费 API
                charge_result = self.charge_photons(
                    photons=photons_need_charge,
                    session_id=conversation_id,
                    user_id=user_id,  # 🆕 传递 user_id 用于查找用户配置
                    user_access_key=user_access_key,
                    user_sku_id=user_sku_id,
                    user_client_name=user_client_name
                )
            except Exception as billing_error:
                # 🔒 计费异常不应阻塞主流程，记录错误并继续
                logger.error(f"❌ [计费异常] 扣费过程发生异常: {billing_error}", exc_info=True)
                charge_result = {
                    'success': False,
                    'message': f'计费异常: {str(billing_error)}',
                    'photons': photons_need_charge
                }

            # 标记上下文为已扣费
            if charge_result.get('success'):
                # 更新已扣费的光子数
                context.charged_photons = photons_to_charge
                context.mark_charged(charge_result)

                # 🔒 生产模式：简化日志输出
                if self.config.VERBOSE_LOGGING:
                    logger.info(
                        f"✅ [自动扣费] 对话 {conversation_id[:8]}... 累计 {total_tokens} tokens，"
                        f"成功扣除 {photons_need_charge} 光子 (已扣费: {photons_to_charge} 光子)"
                    )
                else:
                    logger.info(f"✅ [自动扣费] 成功扣除 {photons_need_charge} 光子")
            else:
                error_msg = charge_result.get('message', '未知错误')

                # 🔒 生产模式：简化错误日志
                if self.config.VERBOSE_LOGGING:
                    logger.warning(f"⚠️ [自动扣费] 对话 {conversation_id[:8]}... 扣费失败: {error_msg}")
                else:
                    logger.warning(f"⚠️ [自动扣费] 扣费失败: {error_msg}")

                # 如果是余额不足，给出友好提示
                if '余额不足' in error_msg or 'insufficient' in error_msg.lower():
                    logger.warning(f"💡 [提示] 请充值光子余额或配置用户的 Bohrium AccessKey")

        # 构建返回结果
        result = {
            'billing_enabled': True,
            'current_request': {
                'tokens': tokens,
                'photons': photons,
                'model': model
            },
            'conversation_total': {
                'tokens': snapshot['total_tokens'],
                'photons': snapshot['total_photons'],
                'requests_count': snapshot['request_count'],
                'charged_photons': charged_photons,  # 已扣费的光子数
                'pending_tokens': total_tokens % tokens_threshold  # 待扣费的 tokens
            },
            'billing_config': {
                'tokens_per_photon': self.config.TOKENS_PER_PHOTON,
                'precision': self.config.BILLING_PRECISION
            },
            'charge_result': charge_result  # 添加扣费结果
        }

        # 详细日志
        if self.config.VERBOSE_LOGGING:
            logger.info(
                f"💎 [隔离计费] 对话 {conversation_id[:8]}... (用户: {user_id[:8]}...) | "
                f"本次: {tokens} tokens = {photons} 光子 | "
                f"累计: {snapshot['total_tokens']} tokens = {snapshot['total_photons']} 光子 | "
                f"已扣费: {charged_photons} 光子 | "
                f"待扣费: {total_tokens % tokens_threshold} tokens | "
                f"模型: {model} | "
                f"扣费: {'成功' if charge_result and charge_result.get('success') else ('失败' if charge_result else '未达阈值')}"
            )
        else:
            logger.info(
                f"💎 [隔离计费] {tokens} tokens → {photons} 光子 "
                f"(累计: {snapshot['total_photons']} 光子, 已扣费: {charged_photons} 光子)"
            )

        return result

    def get_global_stats(self) -> Dict[str, Any]:
        """
        获取全局使用统计

        Returns:
            全局统计信息
        """
        with self._global_lock:
            return {
                'total_tokens': self.global_stats['total_tokens'],
                'total_photons': round(self.global_stats['total_photons'], self.config.BILLING_PRECISION),
                'total_requests': self.global_stats['total_requests'],
                'start_time': self.global_stats['start_time'],
                'current_time': datetime.now().isoformat(),
                'billing_config': {
                    'tokens_per_photon': self.config.TOKENS_PER_PHOTON,
                    'billing_enabled': self.config.BILLING_ENABLED,
                    'precision': self.config.BILLING_PRECISION
                }
            }

    def charge_photons(
        self,
        photons: float,
        session_id: str = "default",
        user_id: str = None,
        user_access_key: str = None,
        user_sku_id: str = None,
        user_client_name: str = None
    ) -> Dict[str, Any]:
        """
        实际扣除光子（调用 Bohrium API）

        参考 Flask 示例的逻辑：
        1. 优先使用用户提供的 AK 和 Client Name（从 Cookie 获取）
        2. 回退到用户配置文件（使用 user_id 查找）
        3. 最后回退到开发者的 AK（用于测试和未认证用户）

        Args:
            photons: 要扣除的光子数
            session_id: 会话 ID（用于生成唯一的 bizNo）
            user_id: 用户 ID（用于查找用户配置文件）
            user_access_key: 用户的 AccessKey（可选，优先级最高，从 Cookie 的 appAccessKey 获取）
            user_sku_id: 用户的 SKU ID（可选）
            user_client_name: 用户的 Client Name（可选，从 Cookie 的 clientName 获取）

        Returns:
            扣费结果
        """
        if not self.config.BILLING_ENABLED:
            return {
                'success': False,
                'message': '计费未启用',
                'photons': photons
            }

        # 优先级：参数（Cookie） > 用户配置文件
        access_key = None
        sku_id = None
        client_name = None
        source = None

        # 🔍 记录扣费请求参数
        logger.info(f"🔍 [扣费请求] user_id={user_id}, session_id={session_id}, photons={photons}")
        logger.info(f"🔍 [扣费请求] user_access_key={'已提供' if user_access_key else '未提供'}")

        # 1. 优先使用参数传入的用户 AK（从 Cookie 获取）
        if user_access_key:
            access_key = user_access_key
            sku_id = user_sku_id or self.config.BOHRIUM_SKU_ID
            client_name = user_client_name or self.config.BOHRIUM_CLIENT_NAME
            source = "来自用户 Cookie"
            logger.info(f"✅ [扣费] 使用来自 Cookie 的 AK: {access_key[:8]}...{access_key[-4:]}")

        # 2. 尝试从用户配置文件读取（使用 user_id）
        if not access_key and user_id:
            try:
                from .user_billing_config import get_config_manager
                config_manager = get_config_manager()
                user_config = config_manager.get_user_config(user_id)
                logger.info(f"🔍 [扣费] 从配置文件读取 user_id={user_id} 的配置: {user_config}")
                if user_config.get('access_key'):
                    access_key = user_config.get('access_key')
                    sku_id = user_config.get('sku_id')
                    client_name = user_config.get('client_name', self.config.BOHRIUM_CLIENT_NAME)
                    source = "用户配置文件"
                    logger.info(f"✅ [扣费] 使用来自配置文件的 AK: {access_key[:8]}...{access_key[-4:]}")
            except Exception as e:
                logger.debug(f"📝 [计费] 未找到用户配置: {e}")

        # 3. 如果没有找到用户凭证，返回错误
        if not access_key:
            logger.error(f"❌ [计费] 未配置用户 AccessKey (user_id={user_id})，请前往设置页面配置您的 Bohrium 凭证")
            return {
                'success': False,
                'message': '未配置 Bohrium AccessKey，请前往设置页面配置您的凭证',
                'error_code': 'NO_ACCESS_KEY',
                'photons': photons,
                'user_id': user_id  # 🔍 返回 user_id 用于调试
            }

        # 🔒 生产模式：仅记录关键信息，不输出敏感数据
        # 🔍 始终记录 AK 来源和脱敏后的 AK，用于追踪扣费问题
        logger.info(
            f"💳 [计费] 使用 AccessKey 来源: {source} | "
            f"AK: {access_key[:8]}...{access_key[-4:]} | "
            f"user_id: {user_id} | "
            f"session_id: {session_id[:8]}..."
        )

        # 生成唯一的 bizNo（使用时间戳 + 随机数，确保不超过 int 范围）
        # 使用毫秒时间戳的后 10 位 + 4 位随机数
        timestamp_ms = int(time.time() * 1000)
        rand_part = secrets.randbelow(10000)  # 0-9999 的随机数
        biz_no = (timestamp_ms % 10000000000) * 10000 + rand_part  # 确保是 14 位数字

        # Bohrium API 配置
        # 参考官方文档：https://openapi.dp.tech/openapi/v1/api/integral/consume
        url = "https://openapi.dp.tech/openapi/v1/api/integral/consume"

        # 重要：accessKey 必须在 header 中携带
        headers = {
            "accessKey": access_key,  # 用户的 AccessKey（header 中携带）
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": f"ResearchMind/{client_name}"
        }

        # eventValue：扣费数额（光子数），类型为 int
        # 根据文档，eventValue 就是光子数，不需要乘以 10000
        event_value = int(photons)  # 直接使用光子数（整数）

        # 请求体参数
        payload = {
            "bizNo": biz_no,           # 请求唯一 ID（int）
            "changeType": 1,           # 扣费类型，默认值 1
            "eventValue": event_value, # 扣费数额（光子数）
            "skuId": int(sku_id),      # SKU ID
            "scene": "appCustomizeCharge"  # 扣费场景，默认值
        }

        try:
            logger.info(f"💎 [计费] 正在扣除 {photons} 光子 (bizNo: {biz_no})")

            # 🔒 生产模式：仅在详细日志模式下输出请求详情
            if self.config.VERBOSE_LOGGING:
                logger.debug(f"📤 [计费] 请求 URL: {url}")
                logger.debug(f"📤 [计费] 请求头: {headers}")
                logger.debug(f"📤 [计费] 请求体: {payload}")

            # 🔒 生产模式：启用 SSL 验证，添加重试机制
            max_retries = 3
            retry_delay = 1  # 秒
            last_error = None

            for attempt in range(max_retries):
                try:
                    resp = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=(10, 30),  # (连接超时, 读取超时)
                        verify=True  # 启用 SSL 验证（生产模式）
                    )
                    break  # 成功则跳出重试循环
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ [计费] 请求失败（尝试 {attempt + 1}/{max_retries}），{retry_delay}秒后重试: {e}")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        logger.error(f"❌ [计费] 请求失败（已重试 {max_retries} 次）: {e}")
                        raise
            else:
                # 如果循环正常结束（没有 break），说明所有重试都失败了
                if last_error:
                    raise last_error

            if resp.status_code == 200:
                result = resp.json()

                # 🔒 生产模式：仅在详细日志模式下输出完整响应
                if self.config.VERBOSE_LOGGING:
                    logger.debug(f"📥 [计费] Bohrium API 响应: {result}")

                # Bohrium API 响应格式：
                # 成功: {'success': true, ...} 或 {'code': 0, ...}
                # 失败: {'code': xxx, 'error': {'msg': '...'}}

                # 检查是否成功
                is_success = result.get('success') or (result.get('code') == 0)

                if is_success:
                    logger.info(f"✅ [计费] 成功扣除 {photons} 光子")
                    return {
                        'success': True,
                        'message': '扣费成功',
                        'photons': photons,
                        'bizNo': biz_no,
                        'response': result
                    }
                else:
                    # 提取错误信息
                    error_msg = '未知错误'
                    if 'error' in result and isinstance(result['error'], dict):
                        error_msg = result['error'].get('msg') or result['error'].get('message') or error_msg
                    elif 'message' in result:
                        error_msg = result['message']
                    elif 'msg' in result:
                        error_msg = result['msg']

                    logger.error(f"❌ [计费] 扣费失败: {error_msg} (code: {result.get('code')})")

                    # 🔒 生产模式：仅在详细日志模式下输出完整响应
                    if self.config.VERBOSE_LOGGING:
                        logger.debug(f"❌ [计费] 完整响应: {result}")

                    return {
                        'success': False,
                        'message': error_msg,
                        'photons': photons,
                        'response': result
                    }
            else:
                logger.error(f"❌ [计费] API 请求失败: HTTP {resp.status_code}")

                # 🔒 生产模式：仅在详细日志模式下输出响应内容
                if self.config.VERBOSE_LOGGING:
                    logger.debug(f"❌ [计费] 响应内容: {resp.text}")

                return {
                    'success': False,
                    'message': f'API 请求失败: {resp.status_code}',
                    'photons': photons
                }

        except requests.exceptions.SSLError as e:
            # 🔒 SSL 错误特殊处理
            logger.error(f"❌ [计费] SSL 验证失败: {str(e)}")
            logger.error(f"💡 [提示] 请检查网络连接或联系管理员")
            return {
                'success': False,
                'message': f'SSL 验证失败: {str(e)}',
                'photons': photons
            }
        except Exception as e:
            logger.error(f"❌ [计费] 扣费异常: {e}", exc_info=self.config.VERBOSE_LOGGING)
            return {
                'success': False,
                'message': f'扣费异常: {str(e)}',
                'photons': photons
            }


# 全局单例
_billing_service: Optional[PhotonBillingService] = None


def get_billing_service() -> PhotonBillingService:
    """获取全局计费服务实例"""
    global _billing_service
    if _billing_service is None:
        _billing_service = PhotonBillingService()
    return _billing_service

