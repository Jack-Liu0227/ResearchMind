# Cookie 优先认证机制（选项 3：混合方案）

## 📋 认证优先级（最终版本）

```
优先级 1: Cookie（实时、最新）
    ↓ 每次都从浏览器 Cookie 读取 appAccessKey 和 clientName
    ↓ 如果 Cookie 不存在
优先级 2: 提示用户输入
    ↓ 显示警告横幅，要求用户输入 AccessKey
    ↓ 用户输入后，直接设置 Cookie（不调用后端）
    ↓ 或提示用户访问 Bohrium 平台登录
优先级 3: 数据库（仅用于统计和历史记录）
    ↓ 记录计费历史（BillingRecord 表）
    ↓ 统计用户使用量（按 access_key 哈希值分组）
    ⚠️ 不存储 access_key（已移除）
    ⚠️ 不用于认证（已移除 JWT Token）
```

## 🎯 架构变更（选项 3）

### ✅ 已移除
- ❌ JWT Token 认证
- ❌ `/api/auth/login` 接口
- ❌ `/api/auth/login-from-cookie` 接口
- ❌ `ProtectedRoute` 组件
- ❌ `LoginPage` 页面
- ❌ `localStorage.getItem('auth_token')`
- ❌ 数据库中的 `User.access_key` 字段（仅保留哈希值用于统计）

### ✅ 保留
- ✅ Cookie 认证（唯一认证方式）
- ✅ 数据库统计（`BillingRecord` 表）
- ✅ WebSocket 会话管理
- ✅ 计费历史记录

## 🔑 核心原则

1. **Cookie 是唯一的计费凭证来源**
   - 每次计费时必须从 Cookie 读取 `appAccessKey` 和 `clientName`
   - 如果 Cookie 不存在，返回错误提示用户登录

2. **数据库不作为凭证来源**
   - 数据库中的 `access_key` 仅用于：
     - 用户身份验证（JWT Token 验证）
     - 计费历史记录（`total_photons_used`, `total_tokens_used`）
     - 用户输入后的持久化存储
   - ⚠️ **不用于计费时的 AccessKey 来源**

3. **实时性保证**
   - 用户在 Bohrium 平台更新 AccessKey 后，立即生效
   - 无需手动更新应用中的配置

## 🔄 认证流程（简化版）

### 1. 页面加载

```typescript
// 前端：App.tsx + CookieWarningBanner.tsx
1. 检测 Cookie 中的 appAccessKey
   ↓ 如果存在
2. 直接使用 Cookie 凭证（无需后端验证）
   - 显示绿色状态指示器
   - WebSocket 连接时发送 Cookie 凭证
   ↓ 如果不存在
3. 显示黄色警告横幅
   - 提示用户登录 Bohrium 或手动输入
   - 用户输入后，直接设置 Cookie
   - 刷新页面，自动使用 Cookie
```

### 2. WebSocket 认证（简化版）

```typescript
// 前端：websocket.ts
1. WebSocket 连接成功后
   ↓
2. 从 Cookie 读取 appAccessKey 和 clientName
   ↓
3. 发送认证消息（不包含 JWT Token）
   {
     type: 'auth',
     data: {
       timestamp: Date.now(),
       appAccessKey: '<from Cookie>',  // ✅ 唯一认证来源
       clientName: '<from Cookie>'
     },
     sessionId: '<client_id>'
   }
   ↓
4. 后端保存到 WebSocket 会话上下文
   - cookie_credentials.access_key
   - cookie_credentials.client_name
   - cookie_credentials.source = "cookie" or "none"
```

### 3. 计费扣费

```python
# 后端：photon_billing.py
1. 从 WebSocket 会话上下文读取 cookie_credentials
   ↓ 如果 source == "cookie"
2. 使用 Cookie 凭证扣费
   - access_key = cookie_credentials.access_key
   - client_name = cookie_credentials.client_name
   ↓ 如果 Cookie 不存在
3. 返回错误
   {
     'success': False,
     'error_code': 'NO_COOKIE_ACCESS_KEY',
     'message': '未检测到 Bohrium Cookie，请登录后重试'
   }
```

## 📁 修改的文件

| 文件 | 修改内容 |
|------|---------|
| `ui/src/services/websocket.ts` | ✅ 添加从 Cookie 读取凭证并发送到后端 |
| `ui/src/components/BohriumAuthButton.tsx` | ✅ 优先检查 Cookie，移除数据库检查 |
| `ui/src/utils/cookieHelper.ts` | ✅ 添加调试日志 |
| `services/message_handler.py` | ✅ 接收并存储 Cookie 凭证到会话上下文 |
| `services/photon_billing.py` | ✅ 优先使用 Cookie 凭证，移除数据库凭证读取 |

## 🔍 调试方法

### 前端调试

```javascript
// 在浏览器控制台执行
import { debugCookies } from './utils/cookieHelper'
debugCookies()

// 输出：
// 🍪 Cookie 信息
//   所有 Cookie: { appAccessKey: '...', clientName: '...' }
//   appAccessKey: 'xxx...'
//   clientName: 'ResearchMind'
//   是否存在 Bohrium Cookie: true
```

### 后端日志

```
✅ 使用 Cookie 凭证: AK=12345678...abcd
💳 [计费] 使用 AccessKey 来源: Cookie | AK: 12345678...abcd
```

## ⚠️ 常见问题

### Q1: Cookie 不存在怎么办？

**A:** 系统会返回错误提示用户登录：
```json
{
  "success": false,
  "error_code": "NO_COOKIE_ACCESS_KEY",
  "message": "未检测到 Bohrium Cookie，请在浏览器中登录 Bohrium 平台后刷新页面",
  "hint": "请访问 https://bohrium.dp.tech 登录后重试"
}
```

### Q2: 数据库中的 access_key 还有用吗？

**A:** 有用，但仅用于：
- JWT Token 验证（用户身份认证）
- 计费历史记录
- 用户输入后的持久化存储

⚠️ **不用于计费时的 AccessKey 来源**

### Q3: 如何确保每次都从 Cookie 读取？

**A:** 
1. 前端：WebSocket 认证时从 Cookie 读取并发送
2. 后端：优先使用前端发送的 Cookie 凭证
3. 计费：从 WebSocket 会话上下文读取 Cookie 凭证
4. 如果 Cookie 不存在，返回错误（不回退到数据库）

## 🎯 验证清单

- [x] 前端从 Cookie 读取凭证并发送到后端
- [x] 后端接收并存储 Cookie 凭证到会话上下文
- [x] 计费时优先使用 Cookie 凭证
- [x] Cookie 不存在时返回明确错误
- [x] 移除数据库凭证作为计费来源
- [x] 添加调试日志
- [x] 更新 UI 显示（Cookie 状态指示器）

