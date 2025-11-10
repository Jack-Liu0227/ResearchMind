# 认证架构迁移总结

## 📋 迁移概述

**日期**: 2025-11-09  
**方案**: 选项 3 - 混合方案（Cookie 认证 + 数据库统计）  
**目标**: 简化认证架构，完全基于 Cookie，移除 JWT Token

---

## ✅ 已完成的修改

### 前端修改（7 个文件）

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `ui/src/App.tsx` | ✅ 移除 `ProtectedRoute` 组件<br>✅ 移除 `LoginPage` 路由<br>✅ 移除 JWT Token 认证检查<br>✅ 所有页面直接可访问 | ✅ 完成 |
| `ui/src/services/websocket.ts` | ✅ 移除 JWT Token 发送<br>✅ 仅发送 Cookie 凭证<br>✅ 更新日志提示 | ✅ 完成 |
| `ui/src/services/api.ts` | ✅ 移除 JWT Token 请求拦截器<br>✅ 不再添加 Authorization 头 | ✅ 完成 |
| `ui/src/components/CookieWarningBanner.tsx` | ✅ 直接设置 Cookie（不调用后端）<br>✅ 移除 JWT Token 逻辑<br>✅ 30 天有效期 | ✅ 完成 |
| `ui/src/components/Layout.tsx` | ✅ 添加 `CookieWarningBanner` 组件<br>✅ 在顶部显示警告横幅 | ✅ 完成 |
| `ui/src/pages/UserProfilePage.tsx` | ✅ 移除 JWT Token 检查<br>✅ 使用 Cookie 认证（`credentials: 'include'`） | ✅ 完成 |

### 后端修改（2 个文件）

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `services/message_handler.py` | ✅ 移除 JWT Token 验证<br>✅ 仅接收 Cookie 凭证<br>✅ 保存到 WebSocket 会话上下文<br>✅ 简化认证逻辑 | ✅ 完成 |
| `services/user_billing_config.py` | ✅ 添加 `get_global_total_usage()` 方法<br>✅ 修复 AttributeError | ✅ 完成 |

### 文档更新（3 个文件）

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `docs/COOKIE_PRIORITY_AUTHENTICATION.md` | ✅ 更新认证优先级<br>✅ 说明架构变更<br>✅ 更新认证流程 | ✅ 完成 |
| `docs/ARCHITECTURE_SIMPLIFICATION.md` | ✅ 新建：详细说明架构简化<br>✅ 对比之前和现在的架构 | ✅ 完成 |
| `docs/MIGRATION_SUMMARY.md` | ✅ 新建：迁移总结文档 | ✅ 完成 |

---

## 🎯 架构变更对比

### 之前（复杂）

```
用户登录
  ↓
输入 AccessKey
  ↓
调用 /api/auth/login
  ↓
后端验证 + 保存到数据库
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

**问题**:
- ❌ 需要维护 JWT Token、数据库、Cookie 三套系统
- ❌ Cookie 和数据库可能不同步
- ❌ 用户更新 AccessKey 后需要重新登录

### 现在（简单）

```
用户访问应用
  ↓
检查 Cookie 中的 appAccessKey
  ↓ 如果存在
✅ 直接使用（显示绿色状态）
  ↓
WebSocket 连接时发送 Cookie 凭证
  ↓
后端保存到会话上下文
  ↓
计费时从会话上下文读取
  ↓ 如果不存在
⚠️ 显示黄色警告横幅
  ↓
用户输入 AccessKey → 设置 Cookie
  ↓
刷新页面 → 自动使用 Cookie
```

**优点**:
- ✅ 仅依赖 Cookie，架构简单
- ✅ Cookie 更新立即生效
- ✅ 单一数据源，避免不一致
- ✅ 无需服务器端会话管理

---

## 🔍 关键代码变更

### 1. 前端 WebSocket 认证（`ui/src/services/websocket.ts`）

**之前**:
```typescript
const token = localStorage.getItem('auth_token')
this.send({
  type: 'auth',
  data: {
    token,  // ❌ JWT Token
    appAccessKey: getCookie('appAccessKey'),
    clientName: getCookie('clientName')
  }
})
```

**现在**:
```typescript
// ✅ 仅发送 Cookie 凭证
this.send({
  type: 'auth',
  data: {
    timestamp: Date.now(),
    appAccessKey: getCookie('appAccessKey'),
    clientName: getCookie('clientName')
  },
  sessionId
})
```

### 2. 后端认证处理（`services/message_handler.py`）

**之前**:
```python
# ❌ 验证 JWT Token
token = auth_data.get("token")
payload = verify_token(token)
user_id = payload.get("user_id")

# ❌ 从数据库读取用户
user = db.query(User).filter(User.id == user_id).first()
effective_access_key = cookie_access_key or user.access_key
```

**现在**:
```python
# ✅ 仅接收 Cookie 凭证
cookie_access_key = auth_data.get("appAccessKey")
cookie_client_name = auth_data.get("clientName") or "ResearchMind"

# ✅ 直接保存到会话上下文
ws_server.client_sessions[client_id].update({
    "authenticated": True,
    "cookie_credentials": {
        "access_key": cookie_access_key,
        "client_name": cookie_client_name,
        "source": "cookie" if cookie_access_key else "none"
    }
})
```

---

## 📝 待清理（可选）

以下文件/代码已不再使用，可以删除：

### 前端
- [ ] `ui/src/pages/LoginPage.tsx`（已不使用）
- [ ] `ui/src/hooks/useLocalStorage.ts` 中的 `auth_token` 相关代码

### 后端
- [ ] `services/auth_api.py` 中的 `/api/auth/login` 接口
- [ ] `services/auth_api.py` 中的 `/api/auth/login-from-cookie` 接口
- [ ] `services/auth/jwt_handler.py`（JWT Token 相关）
- [ ] 数据库中的 `User.access_key` 字段（可选）
- [ ] 数据库中的 `AuthToken` 表（可选）

---

## 🚀 测试清单

### 场景 1: Cookie 存在
- [ ] 页面加载时显示绿色状态指示器
- [ ] WebSocket 连接成功
- [ ] 计费功能正常工作
- [ ] 不显示警告横幅

### 场景 2: Cookie 不存在
- [ ] 页面加载时显示黄色警告横幅
- [ ] 点击"手动输入"可以输入 AccessKey
- [ ] 输入后 Cookie 设置成功
- [ ] 刷新页面后显示绿色状态

### 场景 3: Cookie 过期
- [ ] 显示黄色警告横幅
- [ ] 计费失败，提示需要 Cookie
- [ ] 用户可以重新输入 AccessKey

---

## ✅ 验证结果

- [x] 前端移除 JWT Token 认证
- [x] 前端移除 `ProtectedRoute` 组件
- [x] 前端添加 `CookieWarningBanner` 组件
- [x] WebSocket 仅发送 Cookie 凭证
- [x] 后端移除 JWT Token 验证
- [x] 后端仅接收 Cookie 凭证
- [x] 计费时从会话上下文读取 Cookie 凭证
- [x] 修复 `get_global_total_usage()` AttributeError
- [x] 更新文档说明新架构

---

## 📞 联系方式

如有问题，请查看：
- `docs/COOKIE_PRIORITY_AUTHENTICATION.md` - 认证机制详解
- `docs/ARCHITECTURE_SIMPLIFICATION.md` - 架构简化说明
- `docs/COOKIE_PRIORITY_TEST_CHECKLIST.md` - 测试清单

