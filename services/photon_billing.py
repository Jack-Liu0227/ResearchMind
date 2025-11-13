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

    # Bohrium 平台配置
    # ⚠️ 注意：AccessKey 和 ClientName 不从环境变量读取
    # 它们必须从用户的 Cookie 或前端传递获取，确保每个用户使用自己的凭证
    BOHRIUM_SKU_ID = os.getenv('BOHRIUM_SKU_ID', '10048')  # SKU ID 可以有默认值

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

        # 🔧 优化：移除全局锁和全局统计，改为从 ConversationBillingContext 聚合
        # 保留 start_time 用于统计服务启动时间
        self.global_stats = {
            'start_time': datetime.now().isoformat()
        }

        # 验证配置
        # ⚠️ 注意：不再检查 BOHRIUM_ACCESS_KEY，因为它从用户 Cookie 获取
        logger.info(
            f"💎 光子计费服务已启动 - "
            f"SKU ID: {self.config.BOHRIUM_SKU_ID}, "
            f"收费标准: {self.config.TOKENS_PER_PHOTON} tokens/光子, "
            f"计费状态: {'启用' if self.config.BILLING_ENABLED else '禁用'}, "
            f"认证方式: Cookie (用户凭证)"
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
        metadata: Optional[Dict[str, Any]] = None,
        fallback_user_id: str = None,
        client_id: str = None
    ) -> Dict[str, Any]:
        """
        使用隔离上下文记录 token 使用（推荐方法）

        这个方法确保每个对话的计费数据完全隔离，防止并发时的数据混乱

        新的扣费逻辑：
        - 每累计 5000 tokens 扣费 1 个光子
        - 优先使用用户的 appAccessKey 和 clientName（从数据库获取）
        - 通过 client_id 从 WebSocket 会话上下文获取已认证的用户 ID

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID（可能是 session_id 或数据库用户 ID）
            tokens: 使用的 token 数量
            model: 使用的模型名称
            metadata: 额外的元数据
            fallback_user_id: 回退用户 ID（可选，通常是 client_id，用于查找旧配置）
            client_id: WebSocket 客户端 ID（用于从会话上下文获取已认证用户）

        Returns:
            包含本次使用和累计统计的字典
        """
        if not self.config.BILLING_ENABLED:
            return {
                'billing_enabled': False,
                'message': '计费功能已禁用'
            }

        # 🔍 详细日志：记录每次 token 使用
        if self.config.VERBOSE_LOGGING:
            logger.info(f"🔍 [TOKEN 记录] conversation_id={conversation_id}, user_id={user_id}, tokens={tokens}, model={model}")

        # 计算光子消耗（不再实时扣费，而是累计到阈值时扣费）
        photons = self.calculate_photons(tokens)

        # 获取或创建隔离的计费上下文
        from .user_billing_config import get_billing_context_manager
        context_manager = get_billing_context_manager()
        context = context_manager.get_or_create_context(conversation_id, user_id)

        # 在隔离上下文中更新使用
        context.update_token_usage(tokens, photons, model, metadata)

        # 🔧 优化：移除全局统计更新以减少锁竞争
        # 全局统计现在通过聚合所有 ConversationBillingContext 来计算
        # 这样避免了每次 LLM 调用都需要获取全局锁

        # 新的扣费逻辑：每累计达到阈值时扣费
        charge_result = None
        snapshot = context.get_snapshot()
        total_tokens = snapshot['total_tokens']

        # 检查是否达到扣费阈值
        tokens_threshold = self.config.TOKENS_PER_PHOTON
        photons_to_charge = total_tokens // tokens_threshold  # 应该扣费的光子数

        # 获取已扣费的光子数（从上下文中）
        charged_photons = getattr(context, 'charged_photons', 0)

        # 计算需要扣费的光子数
        photons_need_charge = photons_to_charge - charged_photons

        # 🔍 详细日志：阈值检查
        if self.config.VERBOSE_LOGGING:
            logger.info(f"🔍 [阈值检查] total_tokens={total_tokens}, threshold={tokens_threshold}")
            logger.info(f"🔍 [阈值检查] photons_to_charge={photons_to_charge}, charged_photons={charged_photons}, need_charge={photons_need_charge}")

        if self.config.BILLING_ENABLED and photons_need_charge > 0:
            # 🔒 将计费逻辑包装在 try-except 中，确保计费失败不阻塞主流程
            try:
                # 🆕 优先从 WebSocket 会话上下文获取已认证的用户 ID
                authenticated_user_id = None
                if client_id:
                    try:
                        from .websocket_server import WebSocketServer
                        ws_server = WebSocketServer.get_instance()
                        if ws_server and client_id in ws_server.client_sessions:
                            session_info = ws_server.client_sessions[client_id]
                            authenticated_user_id = session_info.get("authenticated_user_id")
                            if authenticated_user_id:
                                logger.info(f"🔍 [计费追踪] 从 WebSocket 会话获取已认证用户 ID: {authenticated_user_id}")
                    except Exception as e:
                        logger.debug(f"📝 [计费] 从 WebSocket 会话获取用户 ID 失败: {e}")

                # 🔍 添加详细日志，追踪扣费流程
                logger.info(f"🔍 [计费追踪] user_id={user_id}, authenticated_user_id={authenticated_user_id}, conversation_id={conversation_id}")

                # ✅ 优先从 WebSocket 会话中获取 Cookie 凭证
                user_access_key = None
                user_sku_id = None
                user_client_name = None
                credentials_source = None

                if authenticated_user_id:
                    try:
                        from .websocket_server import WebSocketServer
                        ws_server = WebSocketServer.get_instance()
                        if ws_server and client_id in ws_server.client_sessions:
                            session_info = ws_server.client_sessions[client_id]
                            cookie_creds = session_info.get("cookie_credentials", {})

                            # ✅ 优先使用 Cookie 凭证
                            if cookie_creds.get("source") == "cookie":
                                user_access_key = cookie_creds.get("access_key")
                                user_sku_id = cookie_creds.get("sku_id")
                                user_client_name = cookie_creds.get("client_name")
                                credentials_source = "Cookie"
                                logger.info(f"✅ [计费追踪] 使用 Cookie 凭证: AK={user_access_key[:8]}...{user_access_key[-4:]}")
                            else:
                                # ⚠️ Cookie 不存在，不使用数据库凭证，而是返回错误提示用户输入
                                logger.warning(f"⚠️ [计费追踪] Cookie 凭证不存在，需要用户输入 AccessKey")
                                credentials_source = "none"
                    except Exception as e:
                        logger.error(f"❌ [计费追踪] 从 WebSocket 会话获取凭证失败: {e}")

                # 🔍 记录使用的凭证（脱敏）
                if not user_access_key:
                    logger.warning(f"⚠️ [计费追踪] 未找到 Cookie 凭证，user_id={user_id}, authenticated_user_id={authenticated_user_id}")

                # 调用扣费 API
                charge_result = self.charge_photons(
                    photons=photons_need_charge,
                    session_id=conversation_id,
                    user_id=str(authenticated_user_id) if authenticated_user_id else user_id,  # 🆕 优先使用已认证的用户 ID
                    user_access_key=user_access_key,
                    user_sku_id=user_sku_id,
                    user_client_name=user_client_name,
                    fallback_user_id=fallback_user_id  # 🔧 传递 fallback_user_id 用于回退查找配置
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
                # 🔧 修复：传入本次扣费的光子数，让 mark_charged 方法累加
                context.mark_charged(charge_result, photons_charged=photons_need_charge)

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

        🔧 优化：通过聚合所有 ConversationBillingContext 来计算全局统计
        避免了每次 LLM 调用都需要更新全局锁保护的统计数据

        Returns:
            全局统计信息
        """
        from .user_billing_config import get_billing_context_manager

        # 从所有会话上下文聚合统计
        context_manager = get_billing_context_manager()
        all_contexts = context_manager._contexts.values()

        total_tokens = sum(ctx.total_tokens for ctx in all_contexts)
        total_photons = sum(ctx.total_photons for ctx in all_contexts)
        total_requests = sum(ctx.request_count for ctx in all_contexts)
        total_sessions = len(all_contexts)

        return {
            'total_tokens': total_tokens,
            'total_photons': round(total_photons, self.config.BILLING_PRECISION),
            'total_requests': total_requests,
            'total_sessions': total_sessions,
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
        user_client_name: str = None,
        fallback_user_id: str = None
    ) -> Dict[str, Any]:
        """
        实际扣除光子（调用 Bohrium API）

        参考 Flask 示例的逻辑：
        1. 优先使用用户提供的 AK 和 Client Name（从 Cookie 获取）
        2. 回退到用户配置文件（使用 user_id 查找）
        3. 如果没有找到，尝试使用 fallback_user_id 查找配置
        4. 最后返回错误（不再提供开发者 AK 作为后备）

        Args:
            photons: 要扣除的光子数
            session_id: 会话 ID（用于生成唯一的 bizNo）
            user_id: 用户 ID（用于查找用户配置文件，通常是 session_id）
            user_access_key: 用户的 AccessKey（可选，优先级最高，从 Cookie 的 appAccessKey 获取）
            user_sku_id: 用户的 SKU ID（可选）
            user_client_name: 用户的 Client Name（可选，从 Cookie 的 clientName 获取）
            fallback_user_id: 回退用户 ID（可选，通常是 client_id，用于查找旧配置）

        Returns:
            扣费结果
        """
        if not self.config.BILLING_ENABLED:
            return {
                'success': False,
                'message': '计费未启用',
                'photons': photons
            }

        # ✅ 优先级：Cookie（必须） > 提示用户输入
        # ⚠️ 不再从数据库读取凭证用于计费
        access_key = None
        sku_id = None
        client_name = None
        source = None

        # 🔍 记录扣费请求参数
        logger.info(f"🔍 [扣费请求] user_id={user_id}, session_id={session_id}, photons={photons}")
        logger.info(f"🔍 [扣费请求] user_access_key={'已提供' if user_access_key else '未提供'}")

        # 1. ✅ 必须使用参数传入的用户 AK（从 Cookie 获取）
        if user_access_key:
            access_key = user_access_key
            sku_id = user_sku_id or self.config.BOHRIUM_SKU_ID  # SKU ID 可以有默认值
            client_name = user_client_name or "researchmind-uuid1759932177"  # 默认客户端名称
            source = "Cookie"
            logger.info(f"✅ [扣费] 使用 Cookie 凭证: AK={access_key[:8]}...{access_key[-4:]}, client_name={client_name}")
        else:
            # 2. ⚠️ Cookie 不存在，返回错误提示用户输入
            logger.error(f"❌ [计费] Cookie 中未找到 AccessKey，请确保已登录 Bohrium 平台")
            return {
                'success': False,
                'message': '未检测到 Bohrium Cookie，请在浏览器中登录 Bohrium 平台后刷新页面',
                'error_code': 'NO_COOKIE_ACCESS_KEY',
                'photons': photons,
                'user_id': user_id,
                'hint': '请访问 https://bohrium.dp.tech 登录后重试'
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

        # 重要：accessKey 必须在 header 中携带（参考官方 API 文档）
        # 注意：不要手动设置 Host 和 Connection，让 requests 库自动处理
        # ⚠️ 重要：根据 Flask 示例，需要同时提供 accessKey 和 x-app-key
        headers = {
            "accessKey": access_key,      # 用户的 AccessKey（header 中携带）
            "x-app-key": client_name,     # 客户端名称（可能是必需的）
            "Content-Type": "application/json",
            "Accept": "*/*"
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

                # 特殊处理 401 错误（认证失败）
                if resp.status_code == 401:
                    logger.error(f"❌ [计费] 认证失败 (401): AccessKey 可能无效或已过期")
                    logger.error(f"🔍 [调试] 使用的 AccessKey: {access_key[:8]}...{access_key[-4:]}")
                    logger.error(f"🔍 [调试] 请求头: {headers}")
                    logger.error(f"🔍 [调试] 请求体: {payload}")
                    logger.error(f"🔍 [调试] 响应内容: {resp.text}")

                    return {
                        'success': False,
                        'message': 'AccessKey 认证失败，请检查 AccessKey 是否正确或已过期',
                        'error_code': 'INVALID_ACCESS_KEY',
                        'photons': photons,
                        'hint': '请访问 https://bohrium.dp.tech 重新获取 AccessKey'
                    }

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

