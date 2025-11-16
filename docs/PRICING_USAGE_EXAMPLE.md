# 定价功能使用示例

**版本**：v1.0（简化版）
**更新日期**：2025-11-16

---

## 📋 概述

本文档说明如何在 ResearchMind 中使用简化后的定价功能：

1. **前端展示定价信息**
2. **后端固定扣费**
3. **前端展示邀新规则**

---

## 1️⃣ 前端展示定价信息

### 获取定价配置

前端通过 API 获取定价配置：

```typescript
// 获取定价配置
const response = await fetch('/api/billing/pricing/config')
const data = await response.json()

console.log(data.feature_pricing)
// {
//   'search': 0,
//   'database': 0,
//   'export': 0,
//   'chat': 1,
//   'report': 30,
//   'analysis': 15,
//   'structure_gen': 10,
//   'relaxation': 5,
//   'phonon': 5,
//   'kappa': 5,
//   'batch_kappa': 4,
// }
```

### 展示定价页面

访问 `/pricing` 路由查看完整的定价页面。

---

## 2️⃣ 后端固定扣费

### 方法 1：使用 PricingService（推荐）

```python
from services.pricing_service import PricingService

# 为指定功能扣费
result = PricingService.charge_for_feature(
    feature_type='report',          # 功能类型
    session_id='session_123',       # 会话 ID
    user_access_key='xxx',          # 从 Cookie 获取
    user_client_name='ResearchMind' # 从 Cookie 获取
)

if result['success']:
    print(f"✅ 扣费成功: {result['photons']} 光子")
else:
    print(f"❌ 扣费失败: {result['message']}")
```

### 方法 2：直接调用 PhotonBillingService

```python
from services.photon_billing import get_billing_service
from services.pricing_config import get_feature_photons

# 获取功能所需光子数
photons = get_feature_photons('structure_gen')  # 10 光子

# 调用扣费
billing_service = get_billing_service()
result = billing_service.charge_photons(
    photons=photons,
    session_id='session_123',
    user_access_key='xxx',  # 从 Cookie 获取
    user_client_name='ResearchMind'
)
```

### 功能类型与光子消耗对照表

| 功能类型 | 光子消耗 | 说明 |
|---------|---------|------|
| `search` | 0 | 文献搜索（免费） |
| `database` | 0 | 数据库查询（免费） |
| `export` | 0 | 文件导出（免费） |
| `chat` | 1 | Agent 对话 |
| `report` | 30 | 文献调研报告 |
| `analysis` | 15 | 文献分析报告 |
| `structure_gen` | 10 | 结构生成 |
| `relaxation` | 5 | 结构弛豫 |
| `phonon` | 5 | 声子谱计算 |
| `kappa` | 5 | 热导率计算 |
| `batch_kappa` | 4 | 批量热导率计算（每个结构） |

---

## 3️⃣ 前端展示邀新规则

### 获取邀请奖励配置

```typescript
const response = await fetch('/api/billing/pricing/config')
const data = await response.json()

console.log(data.invitation_rewards)
// {
//   inviter: {
//     membership_days: 7,
//     photons_per_membership: 1000,
//     ...
//   },
//   invitee: {
//     photons: 500,
//     photons_validity_days: 30
//   }
// }
```

### 说明

- **邀请奖励由 Bohrium 平台提供和管理**（活动 ID: 1200000）
- ResearchMind **仅在前端展示规则**
- **不实现邀请码生成、奖励发放等后端逻辑**

---

## 🔧 配置文件

所有定价配置在 `services/pricing_config.py` 中管理：

```python
FEATURE_PRICING: Dict[str, int] = {
    'search': 0,
    'database': 0,
    'export': 0,
    'chat': 1,
    'report': 30,
    'analysis': 15,
    'structure_gen': 10,
    'relaxation': 5,
    'phonon': 5,
    'kappa': 5,
    'batch_kappa': 4,
}
```

修改价格只需修改此文件，无需改动业务代码。

---

**文档版本**：v1.0（简化版）
**最后更新**：2025-11-16

