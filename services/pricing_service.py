"""
定价服务类（简化版）

仅提供核心功能：
1. 获取功能所需光子数
2. 简单的权限检查（不涉及数据库）
3. 调用 Bohrium API 扣除固定光子数量
"""

import logging
from typing import Dict, Any, Optional

from services.pricing_config import get_feature_photons

logger = logging.getLogger(__name__)


class PricingService:
    """定价服务类（简化版）"""

    @staticmethod
    def check_permission(
        feature_type: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        检查功能所需光子数（简化版，不涉及用户数据库）

        Args:
            feature_type: 功能类型
            quantity: 数量（批量操作时使用）

        Returns:
            {
                "allowed": bool,
                "reason": str,
                "photons_required": int,
            }
        """
        # 获取功能所需光子数
        photons_per_unit = get_feature_photons(feature_type)
        total_photons = photons_per_unit * quantity

        # 免费功能（光子数为 0）
        if total_photons == 0:
            return {
                "allowed": True,
                "reason": "免费功能",
                "photons_required": 0,
            }

        # 需要消耗光子
        return {
            "allowed": True,
            "reason": f"需要消耗 {total_photons} 光子",
            "photons_required": total_photons,
        }

    @staticmethod
    def charge_for_feature(
        feature_type: str,
        session_id: str,
        user_id: Optional[str] = None,
        user_access_key: Optional[str] = None,
        user_sku_id: Optional[str] = None,
        user_client_name: Optional[str] = None,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        为指定功能扣除固定光子数量

        Args:
            feature_type: 功能类型（如 'report', 'structure_gen' 等）
            session_id: 会话 ID
            user_id: 用户 ID（可选）
            user_access_key: 用户的 AccessKey（从 Cookie 获取）
            user_sku_id: 用户的 SKU ID（可选）
            user_client_name: 用户的 Client Name（从 Cookie 获取）
            quantity: 数量（批量操作时使用）

        Returns:
            扣费结果
        """
        # 获取功能所需光子数
        photons_per_unit = get_feature_photons(feature_type)
        total_photons = photons_per_unit * quantity

        # 免费功能，无需扣费
        if total_photons == 0:
            logger.info(f"✅ 功能 {feature_type} 为免费功能，无需扣费")
            return {
                "success": True,
                "message": "免费功能，无需扣费",
                "photons": 0,
                "feature_type": feature_type,
            }

        # 调用 Bohrium API 扣费
        try:
            from services.photon_billing import get_billing_service
            billing_service = get_billing_service()

            result = billing_service.charge_photons(
                photons=total_photons,
                session_id=session_id,
                user_id=user_id,
                user_access_key=user_access_key,
                user_sku_id=user_sku_id,
                user_client_name=user_client_name,
            )

            if result.get("success"):
                logger.info(
                    f"✅ 功能 {feature_type} 扣费成功: {total_photons} 光子 "
                    f"(session_id={session_id})"
                )
            else:
                logger.warning(
                    f"⚠️ 功能 {feature_type} 扣费失败: {result.get('message')} "
                    f"(session_id={session_id})"
                )

            return {
                **result,
                "feature_type": feature_type,
                "photons": total_photons,
            }

        except Exception as e:
            logger.error(f"❌ 功能 {feature_type} 扣费异常: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"扣费异常: {str(e)}",
                "photons": total_photons,
                "feature_type": feature_type,
            }

    # ============================================================================
    # 辅助方法
    # ============================================================================

    @staticmethod
    def get_feature_name(feature_type: str) -> str:
        """获取功能的可读名称"""
        feature_names = {
            'search': '文献搜索',
            'database': '数据库查询',
            'export': '文件导出',
            'chat': 'Agent 对话',
            'report': '文献调研报告',
            'analysis': '文献分析报告',
            'structure_gen': '结构生成',
            'relaxation': '结构弛豫',
            'phonon': '声子谱计算',
            'kappa': '热导率计算',
            'batch_kappa': '批量热导率计算',
        }
        return feature_names.get(feature_type, feature_type)

