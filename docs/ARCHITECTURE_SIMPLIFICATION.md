# 架构简化：选项 3（混合方案）

## 📋 变更摘要

**目标**：简化认证架构，完全基于 Cookie，数据库仅用于统计。

**方案**：选项 3 - 混合方案
- ✅ 认证：完全基于 Cookie（移除 JWT Token）
- ✅ 统计：使用数据库（仅记录历史）
- ✅ 计费：直接从 Cookie 读取
- ✅ 实时性：Cookie 更新立即生效

---

## 🔄 架构对比

### 之前（JWT Token + Cookie + 数据库）

```
用户登录
  ↓
输入 AccessKey
  ↓
调用 /api/auth/login
  ↓
后端验证 AccessKey
  ↓
保存到数据库（User 表）
  ↓
返回 JWT Token
  ↓
前端保存到 localStorage
  ↓
WebSocket 连接时发送 JWT Token
  ↓
后端验证 JWT Token
  ↓
从数据库读取用户信息
  ↓
计费时从数据库读取 AccessKey
```

**问题**：
- ❌ 复杂：需要维护 JWT Token、数据库、Cookie 三套系统
- ❌ 不一致：Cookie 和数据库可能不同步
- ❌ 延迟：用户更新 AccessKey 后需要重新登录

---

### 现在（仅 Cookie + 登录门户）

```
用户访问应用
  ↓
显示登录门户（全屏）
  ↓
检查 Cookie 中的 appAccessKey
  ↓ 如果存在
自动跳过门户，进入主界面
  ↓
WebSocket 连接时发送 Cookie 凭证
  ↓
后端保存到会话上下文
  ↓
计费时从会话上下文读取
  ↓ 如果不存在
阻塞在登录门户
  ↓
用户输入 AccessKey
  ↓
直接设置 Cookie（无需后端）
  ↓
进入主界面
```

**优点**：
- ✅ 简单：仅依赖 Cookie
- ✅ 实时：Cookie 更新立即生效
- ✅ 一致：单一数据源
- ✅ 无状态：不需要 JWT Token

---

## 📁 修改的文件

### 前端

| 文件 | 修改内容 |
|------|---------|
| `ui/src/App.tsx` | ✅ 移除 `ProtectedRoute` 组件<br>✅ 移除 `LoginPage` 路由<br>✅ 所有页面直接可访问 |
| `ui/src/services/websocket.ts` | ✅ 移除 JWT Token 发送<br>✅ 仅发送 Cookie 凭证 |
| `ui/src/components/CookieWarningBanner.tsx` | ✅ 直接设置 Cookie（不调用后端）<br>✅ 移除 JWT Token 逻辑 |
| `ui/src/components/Layout.tsx` | ✅ 添加 `CookieWarningBanner` 组件 |

### 后端

| 文件 | 修改内容 |
|------|---------|
| `services/message_handler.py` | ✅ 移除 JWT Token 验证<br>✅ 仅接收 Cookie 凭证<br>✅ 保存到会话上下文 |
| `services/photon_billing.py` | ✅ 从会话上下文读取 Cookie 凭证<br>✅ Cookie 不存在时返回错误 |

### 文档

| 文件 | 修改内容 |
|------|---------|
| `docs/COOKIE_PRIORITY_AUTHENTICATION.md` | ✅ 更新认证流程<br>✅ 说明架构变更 |
| `docs/ARCHITECTURE_SIMPLIFICATION.md` | ✅ 新建：架构简化说明 |

---

## 🎯 数据库用途（仅统计）

### 保留的表

1. **`BillingRecord` 表**
   - 用途：记录每次计费历史
   - 字段：`photons`, `tokens`, `biz_no`, `charge_result`, `created_at`
   - 查询：按时间范围统计使用量

2. **`Session` 表**（可选）
   - 用途：记录用户会话历史
   - 字段：`session_id`, `client_id`, `created_at`
   - 查询：按会话统计使用量

### 移除的字段

- ❌ `User.access_key`（不再存储明文）
- ❌ `User.client_name`（不再存储）
- ❌ `AuthToken` 表（不再需要 JWT Token）

### 可选保留

- ✅ `User.access_key_hash`（用于统计，按用户分组）
- ✅ `User.total_photons_used`（累计使用量）
- ✅ `User.total_tokens_used`（累计 Token 数）

---

## 🔍 认证流程详解

### 场景 1: 用户已登录 Bohrium

```
1. 用户在浏览器中登录 Bohrium 平台
   ↓
2. Bohrium 设置 Cookie: appAccessKey, clientName
   ↓
3. 用户访问 ResearchMind 应用
   ↓
4. 前端检测到 Cookie，显示绿色状态
   ↓
5. WebSocket 连接时发送 Cookie 凭证
   ↓
6. 后端保存到会话上下文
   ↓
7. 计费时从会话上下文读取
   ↓
8. 成功扣费
```

### 场景 2: 用户未登录 Bohrium

```
1. 用户访问 ResearchMind 应用
   ↓
2. 前端检测不到 Cookie，显示黄色警告
   ↓
3. 用户点击"手动输入"
   ↓
4. 输入 AccessKey 和 ClientName
   ↓
5. 前端直接设置 Cookie（30 天有效期）
   ↓
6. 刷新页面
   ↓
7. 前端检测到 Cookie，显示绿色状态
   ↓
8. 后续流程同场景 1
```

---

## ✅ 验证清单

- [x] 前端移除 JWT Token 认证
- [x] 前端移除 `ProtectedRoute` 组件
- [x] 前端移除 `LoginPage` 页面
- [x] 前端添加 `CookieWarningBanner` 组件
- [x] WebSocket 仅发送 Cookie 凭证
- [x] 后端移除 JWT Token 验证
- [x] 后端仅接收 Cookie 凭证
- [x] 计费时从会话上下文读取 Cookie 凭证
- [x] Cookie 不存在时返回明确错误
- [x] 更新文档说明新架构

---

## 🚀 下一步

1. **测试认证流程**
   - 测试 Cookie 存在时的流程
   - 测试 Cookie 不存在时的流程
   - 测试手动输入 AccessKey

2. **测试计费功能**
   - 测试 Cookie 凭证计费
   - 测试 Cookie 不存在时的错误提示

3. **清理代码**
   - 删除 `LoginPage.tsx`（已不使用）
   - 删除 `/api/auth/login` 接口（已不使用）
   - 删除 JWT Token 相关代码

4. **数据库迁移**（可选）
   - 移除 `User.access_key` 字段
   - 移除 `AuthToken` 表
   - 保留 `BillingRecord` 表用于统计

