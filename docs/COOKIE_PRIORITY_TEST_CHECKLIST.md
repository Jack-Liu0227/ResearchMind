# Cookie 优先认证测试清单

## 📋 测试场景

### 场景 1: Cookie 存在（正常流程）

**前置条件：**
- 用户已在浏览器中登录 Bohrium 平台
- Cookie 中存在 `appAccessKey` 和 `clientName`

**测试步骤：**
1. 打开浏览器控制台，执行：
   ```javascript
   document.cookie.split(';').forEach(c => console.log(c.trim()))
   ```
   确认存在 `appAccessKey` 和 `clientName`

2. 访问应用登录页面
   - 应该自动从 Cookie 登录
   - 跳转到主页

3. 打开控制台，查看日志：
   ```
   ✅ 应该看到：
   🍪 Cookie 凭证: { appAccessKey: '12345678...', clientName: 'ResearchMind' }
   🔐 已发送 JWT Token 进行认证 (Cookie凭证: 已提供)
   ```

4. 发送一条消息，触发计费
   - 查看后端日志，应该看到：
   ```
   ✅ [计费追踪] 使用 Cookie 凭证: AK=12345678...abcd
   ✅ [扣费] 使用 Cookie 凭证: AK=12345678...abcd
   💳 [计费] 使用 AccessKey 来源: Cookie
   ```

5. 检查 UI 状态指示器
   - 应该显示：`✅ Bohrium 已连接`（绿色）

**预期结果：**
- ✅ 自动登录成功
- ✅ 计费使用 Cookie 凭证
- ✅ 状态指示器显示绿色

---

### 场景 2: Cookie 不存在（需要手动输入）

**前置条件：**
- 用户未登录 Bohrium 平台
- Cookie 中不存在 `appAccessKey`

**测试步骤：**
1. 清除 Cookie：
   ```javascript
   document.cookie = 'appAccessKey=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'
   document.cookie = 'clientName=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'
   ```

2. 刷新页面
   - 应该显示登录表单
   - 提示用户输入 AccessKey

3. 输入 AccessKey 并登录
   - 应该登录成功
   - 跳转到主页

4. 发送一条消息，触发计费
   - 查看后端日志，应该看到：
   ```
   ⚠️ [计费追踪] Cookie 凭证不存在，需要用户输入 AccessKey
   ❌ [计费] Cookie 中未找到 AccessKey，请确保已登录 Bohrium 平台
   ```

5. 检查 UI 状态指示器
   - 应该显示：`⚠️ 未检测到 Cookie`（黄色）

**预期结果：**
- ✅ 显示登录表单
- ✅ 手动登录成功
- ⚠️ 计费失败，提示用户登录 Bohrium
- ⚠️ 状态指示器显示黄色警告

---

### 场景 3: Cookie 过期或无效

**前置条件：**
- Cookie 中存在 `appAccessKey`，但已过期或无效

**测试步骤：**
1. 设置一个无效的 Cookie：
   ```javascript
   document.cookie = 'appAccessKey=invalid_key; path=/'
   ```

2. 刷新页面并登录

3. 发送一条消息，触发计费
   - 查看后端日志，应该看到：
   ```
   ❌ Bohrium API 返回错误: 401 Unauthorized
   ```

**预期结果：**
- ⚠️ 计费失败，提示 AccessKey 无效
- 建议用户重新登录 Bohrium

---

### 场景 4: 数据库中有凭证，但 Cookie 不存在

**前置条件：**
- 用户之前登录过，数据库中存在用户记录
- Cookie 已清除

**测试步骤：**
1. 清除 Cookie（保留 localStorage 中的 auth_token）
   ```javascript
   document.cookie = 'appAccessKey=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'
   ```

2. 刷新页面
   - 应该仍然通过 JWT Token 认证成功

3. 发送一条消息，触发计费
   - 查看后端日志，应该看到：
   ```
   ⚠️ [计费追踪] Cookie 凭证不存在，需要用户输入 AccessKey
   ❌ [计费] Cookie 中未找到 AccessKey
   ```

**预期结果：**
- ✅ JWT Token 认证成功（用户仍然登录）
- ⚠️ 计费失败，提示需要 Cookie
- ⚠️ 状态指示器显示黄色警告

---

## 🔍 调试命令

### 前端调试

```javascript
// 1. 查看所有 Cookie
document.cookie.split(';').forEach(c => console.log(c.trim()))

// 2. 查看 Bohrium 凭证
import { debugCookies } from './utils/cookieHelper'
debugCookies()

// 3. 查看 localStorage
console.log('auth_token:', localStorage.getItem('auth_token'))
console.log('user_info:', localStorage.getItem('user_info'))

// 4. 手动设置 Cookie（测试用）
document.cookie = 'appAccessKey=your_access_key; path=/'
document.cookie = 'clientName=ResearchMind; path=/'
```

### 后端日志关键字

```bash
# 查看 Cookie 凭证使用情况
grep "Cookie 凭证" logs/app.log

# 查看计费来源
grep "使用 AccessKey 来源" logs/app.log

# 查看计费错误
grep "NO_COOKIE_ACCESS_KEY" logs/app.log
```

---

## ✅ 验证清单

- [ ] 场景 1: Cookie 存在时，计费使用 Cookie 凭证
- [ ] 场景 2: Cookie 不存在时，提示用户输入
- [ ] 场景 3: Cookie 无效时，返回明确错误
- [ ] 场景 4: 数据库有凭证但 Cookie 不存在时，不使用数据库凭证
- [ ] 前端正确读取并发送 Cookie 凭证
- [ ] 后端正确接收并存储 Cookie 凭证到会话上下文
- [ ] 计费时优先使用 Cookie 凭证
- [ ] 状态指示器正确显示 Cookie 状态
- [ ] 日志中明确标注凭证来源

---

## 🐛 常见问题排查

### 问题 1: 计费仍然使用数据库凭证

**排查步骤：**
1. 检查后端日志，搜索 `数据库用户配置`
2. 如果看到此日志，说明代码未正确修改
3. 确认 `photon_billing.py` 中已移除数据库凭证读取逻辑

### 问题 2: Cookie 存在但未发送到后端

**排查步骤：**
1. 检查前端日志，搜索 `🍪 Cookie 凭证`
2. 确认 `websocket.ts` 中的 `sendAuthToken` 方法正确读取 Cookie
3. 检查 WebSocket 消息，确认 `appAccessKey` 字段存在

### 问题 3: 后端未存储 Cookie 凭证到会话上下文

**排查步骤：**
1. 检查后端日志，搜索 `使用 Cookie 凭证`
2. 确认 `message_handler.py` 中的 `handle_auth` 方法正确存储凭证
3. 检查 `cookie_credentials` 字段是否存在于会话上下文中

