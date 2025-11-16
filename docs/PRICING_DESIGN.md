# ResearchMind 收费标准设计方案（简化版）

## 📋 文档概述

本文档说明 ResearchMind 项目的核心收费功能：
1. **前端展示定价信息**
2. **后端指定功能扣费固定光子数量**
3. **前端展示邀新规则**（平台奖励，不涉及后端实现）

**版本**：v1.0（简化版）
**更新日期**：2025-11-16

---

## 💰 定价模型

### 核心原则

- ✅ **基础功能永久免费**：文献搜索、数据库查询等基础功能不消耗光子
- ✅ **智能体对话按需计费**：仅在调用 AI 智能体时消耗光子
- ✅ **固定扣费**：每个功能扣费固定光子数量

---

## 🎯 功能模块与光子消耗

### 功能分类说明

ResearchMind 提供三大类功能：**永久免费功能**、**智能体对话功能**、**高级计算功能**

### 详细功能对照表

| 功能模块 | 功能简介 | 光子消耗 | 免费额度 | 备注 |
|---------|---------|---------|---------|------|
| **📚 文献搜索** | ArXiv 论文搜索、Google Scholar 检索、Tavily 网络搜索 | **永久免费** | 无限制 | 基础检索功能 |
| **🗄️ 数据库查询** | Materials Project、OQMD、COD、AFLOW 数据库查询 | **永久免费** | 无限制 | 结构数据获取 |
| **📄 文件导出** | 计算结果 CSV、CIF 文件导出 | **永久免费** | 无限制 | 数据导出服务 |
| **💬 Agent 对话** | Deep Research / Database / Simulation Agent 智能对话 | **1 光子/次** | 无 | 每次发送消息计费 |
| **📊 文献调研报告** | 全文报告分析 + Markdown 报告生成 | **30 光子/次** | 无 | 深度分析功能 |
| **📝 文献分析报告** | 摘要简单分析 + Markdown 报告生成 | **15 光子/次** | 无 | 快速分析功能 |
| **🧪 结构生成** | CrystaLLM 晶体结构生成（基于化学式） | **10 光子/次** | 无 | AI 生成结构 |
| **⚡ 结构弛豫** | MatterSim 结构优化与能量最小化 | **5 光子/次** | 无 | 计算密集型 |
| **🎵 声子谱计算** | 声子色散关系图 + 声子态密度（DOS） | **5 光子/次** | 无 | 包含可视化 |
| **🔥 热导率计算** | AI4Kappa 热导率预测（Slack 模型 + ML 模型） | **5 光子/次** | 无 | 高级计算功能 |
| **📦 批量热导率计算** | 批量热导率计算（多个结构） | **4 光子/结构** | 无 | 批量优惠 20% |

### 功能使用说明

#### 永久免费功能（无需光子）

1. **文献搜索**
   - ArXiv 论文搜索（按关键词、作者、分类）
   - Google Scholar 检索
   - Tavily 学术网络搜索
   - 向量数据库语义搜索

2. **数据库查询**
   - Materials Project 材料数据库
   - OQMD 开放量子材料数据库
   - COD 晶体学开放数据库
   - AFLOW 自动流程材料数据库

3. **文件导出**
   - CIF 结构文件导出
   - CSV 数据导出
   - 计算结果图表导出

#### Agent 对话功能（1 光子/次）

- **Deep Research Agent**：文献调研与分析
- **Database Agent**：材料数据库智能查询
- **Simulation Agent**：仿真计算任务规划
- **Research Coordinator**：多智能体协作调度

> 💡 **提示**：
> - 每次发送消息计为 1 次使用，消耗 1 光子
> - 支持多轮对话，建议在一次对话中完成完整的研究任务
> - Agent 会自动调用相应的 MCP 服务器（Paper Search、Database、Simulation）

#### 高级计算功能（按次计费）

- **文献调研报告**（30 光子）：全文报告分析，生成结构化研究报告（Markdown 格式）
- **文献分析报告**（15 光子）：摘要简单分析，生成快速分析报告（Markdown 格式）
- **结构生成**（10 光子）：基于化学式生成晶体结构（CrystaLLM）
- **结构弛豫**（5 光子）：优化晶体结构，最小化能量（MatterSim）
- **声子谱计算**（5 光子）：计算声子色散和态密度
- **热导率计算**（5 光子）：预测材料热导率（AI4Kappa）
- **批量热导率计算**（4 光子/结构）：批量处理多个结构，享受 20% 折扣

> 💡 **提示**：
> - 所有计算功能均基于 ResearchMind 的三大智能体（Deep Research、Database、Simulation）
> - 批量计算享受折扣优惠，适合大规模材料筛选场景
> - 计算结果文件（CSV、CIF、图表）和分析报告（Markdown）导出永久免费

---

## 🎁 邀请奖励机制（仅前端展示）

> **重要说明**：邀请奖励功能由 **Bohrium 平台**提供和管理（活动 ID: 1200000），ResearchMind **仅在前端展示规则说明**，不涉及邀请码生成、奖励发放等后端实现。

### 前端展示内容

**邀请人奖励**：
- 每邀请 1 人获得 **7 日体验会员**（1000 光子 + 10GB 云盘）
- 会员时长**向后延续累加**

**受邀请人奖励**：
- 填写学术码后获得 **500 光子**（有效期 30 天）
- 必须在注册后 **72 小时内**完成填写

### 前端实现要点

1. **仅展示规则**：在前端页面展示邀请奖励规则说明
2. **不涉及后端**：不实现邀请码生成、邀请统计、奖励发放等后端逻辑
3. **引导到平台**：引导用户到 Bohrium 平台完成邀请操作

---

## 💳 支付方式

ResearchMind 使用 **Bohrium 平台的光子体系**：

1. 用户在 Bohrium 平台充值光子
2. 在 ResearchMind 中使用 Bohrium AccessKey 登录
3. 系统通过 Bohrium API 自动扣除光子

> **说明**：充值功能由 Bohrium 平台提供，ResearchMind 不需要额外开发充值功能。

---

## 🔌 API 接口设计（核心功能）

### 1. 查询定价配置

**端点**：`GET /api/billing/pricing/config`

**描述**：获取当前的定价配置（用于前端展示）

**响应**：
```json
{
  "success": true,
  "version": "v1.0",
  "feature_pricing": {
    "search": 0,
    "database": 0,
    "export": 0,
    "chat": 1,
    "report": 30,
    "analysis": 15,
    "structure_gen": 10,
    "relaxation": 5,
    "phonon": 5,
    "kappa": 5,
    "batch_kappa": 4
  },
  "invitation_rewards": {
    "inviter": {
      "membership_days": 7,
      "photons_per_membership": 1000
    },
    "invitee": {
      "photons": 500,
      "photons_validity_days": 30
    }
  }
}
```

> **说明**：邀请奖励信息仅用于前端展示，不涉及后端实现。

---

## ⚙️ 收费标准配置文件（核心）

### 配置文件位置

**主配置文件**：`services/pricing_config.py`

### 配置文件结构

```python
"""
ResearchMind 收费标准配置文件（简化版）

版本：v1.0
最后更新：2025-11-16
"""

from typing import Dict

# 功能光子消耗配置
FEATURE_PRICING: Dict[str, int] = {
    # 永久免费功能
    'search': 0,
    'database': 0,
    'export': 0,

    # Agent 对话功能
    'chat': 1,

    # 高级计算功能
    'report': 30,
    'analysis': 15,
    'structure_gen': 10,
    'relaxation': 5,
    'phonon': 5,
    'kappa': 5,
    'batch_kappa': 4,
}

# 邀请奖励配置（仅用于前端展示）
INVITATION_REWARDS_INVITER = {
    'membership_days': 7,
    'photons_per_membership': 1000,
}

INVITATION_REWARDS_INVITEE = {
    'photons': 500,
    'photons_validity_days': 30,
}

def get_feature_photons(feature_type: str) -> int:
    """获取功能所需光子数"""
    return FEATURE_PRICING.get(feature_type, 0)
```

---

## 🎨 前端展示方案

### 收费标准展示页面

**位置**：`ui/src/pages/PricingPage.tsx`

**功能**：
- 展示所有功能模块的光子消耗
- 展示邀请奖励规则说明（仅展示，不涉及后端）
- 引导用户前往 Bohrium 平台充值

---

## 🎯 核心功能总结

### 1. 前端展示定价信息
- 从 `/api/billing/pricing/config` 获取定价配置
- 在前端页面展示各功能的光子消耗

### 2. 后端指定功能扣费
- 通过 `services/pricing_config.py` 配置固定光子数量
- 调用 Bohrium API 扣除光子

### 3. 前端展示邀新规则
- 展示 Bohrium 平台的邀请奖励规则
- 不实现邀请码生成、奖励发放等后端逻辑

---

**文档版本**：v1.0（简化版）
**最后更新**：2025-11-16
**维护者**：ResearchMind Team
