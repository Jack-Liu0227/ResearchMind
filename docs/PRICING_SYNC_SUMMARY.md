# ResearchMind 定价配置简化总结

**更新日期**：2025-11-16
**版本**：v1.0（简化版）
**状态**：✅ 已简化

---

## 📋 简化说明

本次简化删除了以下内容：
- ❌ 数据库表设计、数据模型、持久化相关内容
- ❌ 邀新奖励的后端实现逻辑
- ❌ 充值功能的开发内容
- ❌ 复杂的定价同步、动态计费等非必选功能

保留了以下核心功能：
- ✅ 前端展示定价信息
- ✅ 后端指定功能扣费固定光子数量
- ✅ 前端展示邀新规则（仅展示，说明这是平台奖励）

---

## 📊 核心定价配置

```python
FEATURE_PRICING = {
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

---

## 🎯 核心功能

1. **前端展示定价信息**
   - 从 `/api/billing/pricing/config` 获取定价配置
   - 在前端页面展示各功能的光子消耗

2. **后端固定扣费**
   - 通过 `services/pricing_config.py` 配置固定光子数量
   - 调用 Bohrium API 扣除光子

3. **前端展示邀新规则**
   - 展示 Bohrium 平台的邀请奖励规则
   - 不实现邀请码生成、奖励发放等后端逻辑

---

## 📝 简化内容清单

### 已删除内容

- ❌ 数据库表设计（User、FeatureUsage、Invitation 等）
- ❌ 数据库迁移脚本
- ❌ 邀请系统后端实现（邀请码生成、邀请统计、奖励发放）
- ❌ 充值功能开发内容
- ❌ 复杂的权限验证服务
- ❌ 使用历史记录功能
- ❌ 配置文件版本管理、环境变量覆盖等高级功能
- ❌ 实施计划、验收标准等项目管理内容

### 保留内容

- ✅ 核心定价配置（`services/pricing_config.py`）
- ✅ 定价配置 API（`/api/billing/pricing/config`）
- ✅ 前端展示页面（`ui/src/pages/PricingPage.tsx`）
- ✅ 邀请奖励规则展示（仅前端，不涉及后端）

---

## 📚 简化后的文档列表

1. **`docs/INVITATION_REWARDS_BOHRIUM.md`** - 简化为前端展示用
2. **`docs/INVITATION_REWARDS_GUIDE.md`** - 简化为前端展示用
3. **`docs/PRICING_DESIGN.md`** - 简化为核心功能说明
4. **`docs/PRICING_SUMMARY.md`** - 简化为快速参考
5. **`docs/PRICING_SYNC_SUMMARY.md`** - 本文件，简化说明
6. **`docs/progress.md`** - 保持原样

---

## ✅ 简化验收

- [x] 删除数据库相关内容
- [x] 删除邀请系统后端实现
- [x] 删除充值功能开发内容
- [x] 删除复杂的非必选功能
- [x] 保留核心功能：前端展示定价 + 后端固定扣费 + 前端展示邀新规则
- [x] 所有文档已简化并保持一致

