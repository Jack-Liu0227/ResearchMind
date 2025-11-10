# 计费扣费修复

## 🐛 问题描述

### 问题 1：后端扣费失败

**症状**：
- 用户使用应用后，后端没有实际扣费
- 后端日志显示：`⚠️ [计费追踪] Cookie 凭证不存在，需要用户输入 AccessKey`
- 实际上用户已经通过登录门户输入了 AccessKey，Cookie 也存在

**影响**：
- 用户使用应用消耗了 tokens 和光子，但没有实际扣费
- 计费统计不准确
- 可能导致用户账户余额不一致

### 问题 2：前端显示"未扣费"

**症状**：
- 计费统计面板显示"是否已扣费：**未扣费**"
- 即使后端已经成功扣费，前端仍然显示"未扣费"

**影响**：
- 用户误以为没有扣费
- 计费统计显示不准确

---

## 🔍 根本原因

### 问题 1 的根本原因：后端未设置 authenticated_user_id

**文件**: `services/message_handler.py`
**行号**: 290

**问题代码位置**: `services/photon_billing.py` 第 196-217 行

### 问题 2 的根本原因：前端 updateBillingData 未保存 charged 字段

**文件**: `ui/src/store/useAppStore.ts`
**行号**: 487-504

**问题代码**：当 `billingData` 为 `null` 时，只设置了 3 个字段，缺少 `charged` 和 `billing_source`

### 问题 3 的根本原因：后端 mark_charged 未更新 charged_photons

**文件**: `services/user_billing_config.py`
**行号**: 65-78

**问题代码**：`mark_charged()` 方法只设置 `charged = True`，没有更新 `charged_photons`

```python
# ❌ 错误的逻辑
if authenticated_user_id:  # 这个条件永远不满足！
    try:
        from .websocket_server import WebSocketServer
        ws_server = WebSocketServer.get_instance()
        if ws_server and client_id in ws_server.client_sessions:
            session_info = ws_server.client_sessions[client_id]
            cookie_creds = session_info.get("cookie_credentials", {})
            
            if cookie_creds.get("source") == "cookie":
                user_access_key = cookie_creds.get("access_key")
                # ... 读取 Cookie 凭证
```

### 问题分析

1. **`photon_billing.py` 第 196 行**：代码检查 `if authenticated_user_id:`
2. **`message_handler.py` 第 290 行**：`handle_auth` 方法**没有设置 `authenticated_user_id`**
3. **结果**：`authenticated_user_id` 永远是 `None`，条件永远不满足
4. **后果**：Cookie 凭证永远不会被读取，扣费永远失败

---

## ✅ 修复方案

### 修复 1：后端设置 authenticated_user_id

**文件**: `services/message_handler.py`
**行号**: 292

**修改内容**：
```python
# ✅ 修复后的代码
ws_server.client_sessions[client_id].update({
    "authenticated": True,
    "authenticated_user_id": client_id,  # 🔧 新增：设置 authenticated_user_id
    "cookie_credentials": {
        "access_key": cookie_access_key,
        "client_name": cookie_client_name,
        "sku_id": "10048",
        "source": "cookie" if cookie_access_key else "none"
    }
})
```

**关键变更**：
- ✅ 添加 `"authenticated_user_id": client_id`
- ✅ 使用 `client_id` 作为用户 ID（WebSocket 客户端唯一标识）
- ✅ 确保 `photon_billing.py` 中的条件 `if authenticated_user_id:` 能够满足

---

### 修复 2：前端使用后端返回的 charged 状态

**文件 1**: `ui/src/store/useAppStore.ts`
**行号**: 22-31

**修改内容**：
```typescript
export interface BillingData {
  session_total_tokens: number
  session_total_photons: number
  requests_count: number
  current_tokens?: number
  current_photons?: number
  model_name?: string
  charged?: boolean  // 🔧 新增：是否已扣费
  billing_source?: string  // 🔧 新增：计费来源
}
```

**文件 2**: `ui/src/components/BillingStatsPanel.tsx`
**行号**: 88-89

**修改内容**：
```typescript
setConversationStats({
  conversation_id: currentSession.id,
  user_id: user?.id?.toString() || 'unknown',
  total_tokens: billingData.session_total_tokens,
  total_photons: billingData.session_total_photons,
  request_count: billingData.requests_count,
  charged: billingData.charged ?? false,  // 🔧 修复：使用后端返回的 charged 状态
  billing_source: billingData.billing_source,  // 🔧 添加：计费来源
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
})
```

**文件 3**: `services/agent_coordinator.py`
**行号**: 394-404

**修改内容**：
```python
# 发送完成状态（包含计费信息）
billing_data = {
    "session_total_tokens": session_usage.get('total_tokens', 0),
    "session_total_photons": session_usage.get('total_photons', 0.0),
    "requests_count": session_usage.get('requests_count', 0),
    "model_name": os.getenv('MODEL_USE', 'qwen-plus'),
    "charged": session_usage.get('charged', False),  # 🔧 新增：是否已扣费
    "billing_source": "Cookie"  # 🔧 新增：计费来源
}
```

**文件 4**: `ui/src/store/useAppStore.ts`
**行号**: 487-504

**修改内容**：
```typescript
updateBillingData: (data) => {
  const current = get().billingData
  set({
    billingData: current
      ? { ...current, ...data }
      : {
          session_total_tokens: data.session_total_tokens || 0,
          session_total_photons: data.session_total_photons || 0,
          requests_count: data.requests_count || 0,
          charged: data.charged ?? false,  // 🔧 修复：添加 charged 字段
          billing_source: data.billing_source,  // 🔧 修复：添加 billing_source 字段
          current_tokens: data.current_tokens,
          current_photons: data.current_photons,
          model_name: data.model_name,
        },
  })
}
```

**文件 5**: `services/user_billing_config.py`
**行号**: 65-78

**修改内容**：
```python
def mark_charged(self, result: Dict, photons_charged: int = 0) -> None:
    """
    线程安全地标记已扣费

    Args:
        result: 扣费结果
        photons_charged: 本次扣费的光子数（可选）
    """
    with self._lock:
        self.charged = True
        self.charge_result = result
        if photons_charged > 0:
            self.charged_photons += photons_charged  # 🔧 修复：累加已扣费光子数
        self.updated_at = datetime.now().isoformat()
```

**文件 6**: `services/photon_billing.py`
**行号**: 241-244

**修改内容**：
```python
# 标记上下文为已扣费
if charge_result.get('success'):
    # 🔧 修复：传入本次扣费的光子数，让 mark_charged 方法累加
    context.mark_charged(charge_result, photons_charged=photons_need_charge)
```

**关键变更**：
- ✅ 后端在 WebSocket 消息中返回 `charged` 和 `billing_source` 字段
- ✅ 前端 `BillingData` 类型添加 `charged` 和 `billing_source` 字段
- ✅ 前端使用后端返回的 `charged` 值，而不是硬编码 `false`
- ✅ **修复 `updateBillingData` 方法**：当 `current` 为 `null` 时，也要设置 `charged` 和 `billing_source` 字段
- ✅ **修复 `mark_charged` 方法**：累加 `charged_photons`，而不是直接赋值

---

## 🔄 修复后的工作流程

### 1. 用户登录

```
用户输入 AccessKey
  ↓
设置 Cookie（appAccessKey, clientName）
  ↓
WebSocket 连接
  ↓
发送 auth 消息（包含 Cookie 凭证）
  ↓
handle_auth() 处理
  ↓
✅ 设置 authenticated_user_id = client_id
✅ 设置 cookie_credentials = { access_key, client_name, sku_id, source }
```

### 2. 计费扣费

```
用户发送消息
  ↓
LLM 调用消耗 tokens
  ↓
record_usage_isolated() 记录使用
  ↓
检查是否达到扣费阈值（5000 tokens = 1 光子）
  ↓ 如果达到
从 WebSocket 会话获取 authenticated_user_id
  ↓
✅ authenticated_user_id 存在（= client_id）
  ↓
从 WebSocket 会话获取 cookie_credentials
  ↓
✅ cookie_credentials.source == "cookie"
  ↓
提取 access_key, sku_id, client_name
  ↓
调用 charge_photons()
  ↓
✅ 成功扣费！
```

---

## 🧪 验证方法

### 1. 检查 WebSocket 会话

```python
# 在 handle_auth() 后添加日志
logger.info(f"🔍 [调试] client_sessions[{client_id}] = {ws_server.client_sessions[client_id]}")
```

**预期输出**：
```json
{
  "authenticated": true,
  "authenticated_user_id": "client_abc123",
  "cookie_credentials": {
    "access_key": "your_access_key",
    "client_name": "ResearchMind",
    "sku_id": "10048",
    "source": "cookie"
  }
}
```

### 2. 检查计费日志

**修复前**：
```
⚠️ [计费追踪] Cookie 凭证不存在，需要用户输入 AccessKey
❌ [计费] Cookie 中未找到 AccessKey，请确保已登录 Bohrium 平台
```

**修复后**：
```
✅ [计费追踪] 使用 Cookie 凭证: AK=12345678...abcd
💎 [计费] 正在扣除 1 光子 (bizNo: 12345678901234)
✅ [自动扣费] 成功扣除 1 光子
```

### 3. 检查计费统计

**修复前**：
- 是否已扣费：**未扣费** ❌
- 计费来源：**未知**

**修复后**：
- 是否已扣费：**已扣费** ✅
- 计费来源：**Cookie**

---

## 📊 影响范围

### 受影响的功能

- ✅ 自动扣费（每 5000 tokens 扣 1 光子）
- ✅ 计费统计（当前会话、用户统计、全局统计）
- ✅ 计费历史记录

### 不受影响的功能

- ✅ WebSocket 认证（仍然正常工作）
- ✅ 消息发送和接收
- ✅ Agent 调用
- ✅ 文件上传

---

## 🎯 测试清单

### 功能测试

- [ ] **登录测试**
  - [ ] 输入 AccessKey 后设置 Cookie
  - [ ] WebSocket 认证成功
  - [ ] `authenticated_user_id` 正确设置

- [ ] **扣费测试**
  - [ ] 发送消息消耗 tokens
  - [ ] 达到 5000 tokens 阈值
  - [ ] 自动扣费成功
  - [ ] 计费统计显示"已扣费"

- [ ] **日志测试**
  - [ ] 查看后端日志
  - [ ] 确认显示：`✅ [计费追踪] 使用 Cookie 凭证`
  - [ ] 确认显示：`✅ [自动扣费] 成功扣除 X 光子`

### 边界测试

- [ ] **Cookie 不存在**
  - [ ] 清除 Cookie
  - [ ] 发送消息
  - [ ] 显示错误：`未检测到 Bohrium Cookie`

- [ ] **AccessKey 无效**
  - [ ] 输入无效的 AccessKey
  - [ ] 发送消息
  - [ ] 扣费失败，显示错误信息

---

## 📝 相关文件

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `services/message_handler.py` | 添加 `authenticated_user_id` 设置 | ✅ 已修复 |
| `services/photon_billing.py` | 无需修改（逻辑正确） | ✅ 正常 |
| `docs/BILLING_FIX.md` | 新建：修复说明文档 | ✅ 已创建 |

---

## 🚀 部署建议

### 1. 重启后端服务

```bash
# 停止后端
# Ctrl+C 或 kill 进程

# 重新启动
python main.py
```

### 2. 清除旧数据（可选）

```bash
# 清除旧的计费记录（如果需要）
rm -rf data/researchmind.db

# 或者仅清除 BillingRecord 表
# 使用 SQLite 工具手动清除
```

### 3. 测试验证

1. 清除浏览器 Cookie
2. 重新登录（输入 AccessKey）
3. 发送消息（消耗 tokens）
4. 查看计费统计（应显示"已扣费"）

---

## 📞 相关文档

- `docs/LOGIN_GATEWAY.md` - 登录门户说明
- `docs/ARCHITECTURE_SIMPLIFICATION.md` - 架构简化说明
- `docs/COOKIE_PRIORITY_AUTHENTICATION.md` - Cookie 认证机制

