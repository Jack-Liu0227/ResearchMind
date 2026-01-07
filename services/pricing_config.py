"""
ResearchMind 收费标准配置文件

⚠️ 重要说明：
1. 本文件是收费标准的唯一真相来源（Single Source of Truth）
2. 修改价格只需修改本文件，无需改动业务代码
3. 支持通过环境变量覆盖默认配置
4. 所有价格变更需要记录到 PRICING_CHANGELOG

版本：v1.0
最后更新：2025-11-14
"""

import os
from typing import Dict, Any

# ============================================================================
# 功能光子消耗配置（核心定价表）
# ============================================================================

FEATURE_PRICING: Dict[str, int] = {
    # ===== 永久免费功能 =====

    'export': 0,           # 文件导出（CIF、CSV、Markdown）

    # ===== Agent 对话功能 =====
    'chat': 0,             # Agent 对话（Deep Research / Database / Simulation Agent）
    'database': 1,         # 数据库查询（Materials Project、OQMD、COD、AFLOW）
    # ===== 高级计算功能 =====
    'search': 1,           # 文献搜索（ArXiv、semantic cholar、Tavily）
    'report': 30,          # 文献调研报告（全文报告分析 + Markdown 报告生成）
    'analysis': 15,        # 文献分析报告 （摘要简单分析+ Markdown 报告生成）
    'structure_gen': 10,   # 结构生成（CrystaLLM 晶体结构生成）
    'relaxation': 5,       # 结构弛豫（MatterSim 结构优化）
    'phonon': 5,           # 声子谱计算（声子色散 + 态密度）
    'kappa': 5,            # 热导率计算（AI4Kappa 预测）
}

# 全局价格倍率（用于统一调整价格）
PRICING_MULTIPLIER: float = 10
# ============================================================================
# 批量计算折扣配置
# ============================================================================

BATCH_DISCOUNT: Dict[str, float] = {
    'batch_phonon': 0.20,  # 批量声子谱计算享受 20% 折扣
    'batch_kappa': 0.20,   # 批量热导率计算享受 20% 折扣
}

# 自动计算批量功能价格
for batch_feature, discount in BATCH_DISCOUNT.items():
    base_feature = batch_feature.replace('batch_', '')
    if base_feature in FEATURE_PRICING:
        # 批量价格 = 单个价格 * (1 - 折扣率)
        # 注意：这里计算的是基础价格，get_feature_photons 会再乘上 PRICING_MULTIPLIER
        FEATURE_PRICING[batch_feature] = int(FEATURE_PRICING[base_feature] * (1 - discount))

# ============================================================================
# 免费额度配置
# ============================================================================

FREE_QUOTA_CONFIG: Dict[str, int] = {
    # 当前暂无免费额度功能
    # 如需添加，格式：'feature_type': quota_count
}

# ============================================================================
# 邀请奖励配置（严格遵循 Bohrium 平台规则）
# 参考：https://www.bohrium.com/activity-rules?activityId=1200000
# ============================================================================

# 邀请人奖励：7 日体验会员
INVITATION_REWARDS_INVITER: Dict[str, Any] = {
    'membership_days': 7,           # 每邀请 1 人获得 7 天体验会员
    'photons_per_membership': 1000, # 每个会员周期包含 1000 光子
    'photons_validity_days': 7,     # 光子有效期 7 天
    'cloud_storage_gb': 10,         # 10GB 玻尔云盘空间
    'cumulative': True,             # 邀请多人时会员时长累加
    'max_validity_years': 5,        # 体验会员最长存续期限 5 年
}

# 受邀请人奖励：500 光子
INVITATION_REWARDS_INVITEE: Dict[str, Any] = {
    'photons': 500,                 # 填写学术码后获得 500 光子
    'photons_validity_days': 30,    # 光子有效期 30 天
}

# 邀请有效期（小时）
INVITATION_VALID_HOURS: int = 72  # 新用户需在 72 小时内填写学术码

# ============================================================================
# 辅助函数
# ============================================================================

def get_feature_photons(feature_type: str) -> int:
    """
    获取功能所需光子数

    Args:
        feature_type: 功能类型（如 'report', 'structure_gen' 等）

    Returns:
        所需光子数（0 表示免费）
    """
    # 支持通过环境变量覆盖（格式：PRICING_<FEATURE_TYPE>=<PHOTONS>）
    env_key = f"PRICING_{feature_type.upper()}"
    env_value = os.getenv(env_key)

    if env_value is not None:
        try:
            return int(env_value)
        except ValueError:
            pass

    base_price = FEATURE_PRICING.get(feature_type, 0)
    return int(base_price * PRICING_MULTIPLIER)


def get_free_quota(feature_type: str) -> int:
    """
    获取功能的免费额度

    Args:
        feature_type: 功能类型

    Returns:
        免费额度数量（0 表示无免费额度）
    """
    return FREE_QUOTA_CONFIG.get(feature_type, 0)


def get_invitation_reward_inviter(invitation_count: int) -> Dict[str, Any]:
    """
    获取邀请人的奖励（体验会员）

    Args:
        invitation_count: 邀请人数

    Returns:
        奖励详情字典，包含会员天数、光子数、云盘空间等
    """
    membership_days = invitation_count * INVITATION_REWARDS_INVITER['membership_days']
    total_photons = invitation_count * INVITATION_REWARDS_INVITER['photons_per_membership']

    return {
        'membership_days': membership_days,
        'total_photons': total_photons,
        'photons_validity_days': INVITATION_REWARDS_INVITER['photons_validity_days'],
        'cloud_storage_gb': INVITATION_REWARDS_INVITER['cloud_storage_gb'],
    }


def get_invitation_reward_invitee() -> Dict[str, Any]:
    """
    获取受邀请人的奖励（500 光子）

    Returns:
        奖励详情字典
    """
    return {
        'photons': INVITATION_REWARDS_INVITEE['photons'],
        'photons_validity_days': INVITATION_REWARDS_INVITEE['photons_validity_days'],
    }


def get_batch_discount(feature_type: str) -> float:
    """
    获取批量计算折扣率

    Args:
        feature_type: 功能类型

    Returns:
        折扣率（0.0-1.0，如 0.20 表示 20% 折扣）
    """
    return BATCH_DISCOUNT.get(feature_type, 0.0)


# ============================================================================
# 价格变更日志（用于审计和回溯）
# ============================================================================

PRICING_CHANGELOG = [
    {
        'version': 'v1.0',
        'date': '2025-11-14',
        'description': '初始版本 - 定价配置详见 FEATURE_PRICING 字典',
        'author': 'ResearchMind Team',
    },
]


def get_latest_pricing_version() -> str:
    """获取当前定价版本"""
    if PRICING_CHANGELOG:
        return PRICING_CHANGELOG[-1]['version']
    return 'unknown'


# ============================================================================
# 配置验证（启动时自动检查）
# ============================================================================

def validate_pricing_config() -> bool:
    """
    验证配置文件的完整性和合法性

    Returns:
        配置是否有效
    """
    errors = []

    # 检查必需的功能类型
    required_features = ['search', 'database', 'export', 'chat', 'report',
                        'structure_gen', 'relaxation', 'phonon', 'kappa', 'batch_phonon', 'batch_kappa']

    for feature in required_features:
        if feature not in FEATURE_PRICING:
            errors.append(f"缺少功能定价配置: {feature}")
        elif FEATURE_PRICING[feature] < 0:
            errors.append(f"功能定价不能为负数: {feature} = {FEATURE_PRICING[feature]}")

    # 检查价格倍率
    if PRICING_MULTIPLIER < 0:
        errors.append(f"价格倍率不能为负数: {PRICING_MULTIPLIER}")

    # 检查邀请奖励配置
    if not INVITATION_REWARDS_INVITER or not INVITATION_REWARDS_INVITEE:
        errors.append("邀请奖励配置为空")

    # 检查批量折扣
    for feature, discount in BATCH_DISCOUNT.items():
        if not (0.0 <= discount <= 1.0):
            errors.append(f"批量折扣率必须在 0.0-1.0 之间: {feature} = {discount}")

    if errors:
        print("❌ 收费标准配置验证失败：")
        for error in errors:
            print(f"  - {error}")
        return False

    print(f"✅ 收费标准配置验证通过（版本：{get_latest_pricing_version()}）")
    return True


# 模块加载时自动验证
if __name__ != "__main__":
    validate_pricing_config()
