# 认证与计费系统

## 📋 概述

ResearchMind 使用基于 Cookie 的认证系统，每次都从用户的 Cookie 中读取 `appAccessKey` 和 `clientName`。如果 Cookie 不存在，则要求用户手动输入。

## 🔑 认证方式

### 1. Cookie 自动登录（推荐）

**前端代码**：
```typescript
// 页面加载时自动尝试 Cookie 登录
const response = await fetch('/api/auth/login-from-cookie', {
  method: 'POST',
  credentials: 'include'  // 重要：发送 Cookie
})

if (response.ok) {
  const result = await response.json()
  localStorage.setItem('auth_token', result.token)
  // 登录成功，跳转到主页
}
```

**后端处理**：
```python
@router.post("/login-from-cookie")
async def login_from_cookie(
    appAccessKey: Optional[str] = Cookie(None),
    clientName: Optional[str] = Cookie(None),
    db: DBSession = Depends(get_db)
):
    # 从 Cookie 读取凭证
    # 创建/更新用户记录
    # 返回 JWT Token
```

### 2. 手动登录（Cookie 不存在时）

**前端代码**：
```typescript
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    access_key: accessKey,
    client_name: clientName,
    sku_id: '10048'
  })
})
```

## 💾 数据存储

### 数据库（User 表）

```python
class User(Base):
    id = Column(Integer, primary_key=True)
    access_key = Column(String(64), unique=True)  # Bohrium AccessKey
    client_name = Column(String(100))              # 客户端名称
    sku_id = Column(String(20), default="10048")   # SKU ID
    total_photons_used = Column(Float)             # 累计使用光子数
    total_tokens_used = Column(Integer)            # 累计使用 Token 数
```

### WebSocket 会话上下文

```python
client_sessions[client_id] = {
    "authenticated": True,
    "authenticated_user_id": 123,  # 数据库用户 ID
    "user": {
        "id": 123,
        "client_name": "ResearchMind",
        "sku_id": "10048"
    }
}
```

## 💰 计费机制

### 计费流程

```
1. LLM 调用完成
   ↓
2. 记录 token 使用量（record_usage_isolated）
   - 从 WebSocket 会话获取 authenticated_user_id
   - 从数据库查询用户的 access_key
   ↓
3. 累计到阈值时自动扣费
   - 默认：8000 tokens = 1 光子
   - 使用用户自己的 access_key 调用 Bohrium API
   ↓
4. 更新数据库用户统计
   - total_photons_used
   - total_tokens_used
```

### 用户隔离保证

1. **认证隔离**：每个用户有唯一的 `access_key`（数据库唯一索引）
2. **会话隔离**：WebSocket 会话绑定 `authenticated_user_id`
3. **计费隔离**：每个对话有独立的 `ConversationBillingContext`
4. **扣费隔离**：使用用户自己的 `access_key` 扣费

## 📁 关键文件

| 文件 | 作用 |
|------|------|
| `services/auth_api.py` | 认证 API（登录端点） |
| `services/auth/jwt_handler.py` | JWT Token 生成和验证 |
| `services/auth/bohrium_oauth.py` | Bohrium AccessKey 验证 |
| `services/message_handler.py` | WebSocket 认证处理 |
| `services/photon_billing.py` | 计费服务 |
| `services/user_billing_config.py` | 对话计费上下文管理 |
| `services/database/models.py` | 数据库模型（User 表） |
| `ui/src/pages/LoginPage.tsx` | 前端登录页面 |
| `ui/src/utils/cookieHelper.ts` | Cookie 工具函数 |

## 🔧 环境变量

```bash
# JWT 密钥（必须）
JWT_SECRET_KEY=your_secret_key_here

# 计费配置
PHOTON_TOKENS_PER_PHOTON=8000  # 多少 tokens = 1 光子
PHOTON_BILLING_ENABLED=true     # 是否启用计费
```

## 🧪 测试

### 测试 Cookie 登录

```bash
# 设置 Cookie
curl -X POST "http://localhost:50002/api/auth/login-from-cookie" \
  -H "Cookie: appAccessKey=your_key; clientName=YourName" \
  --cookie-jar cookies.txt
```

### 测试手动登录

```bash
curl -X POST "http://localhost:50002/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"access_key": "your_key", "client_name": "YourName", "sku_id": "10048"}'
```

## ❓ 常见问题

### Q: 如何确保每次都从 Cookie 读取？
A: 前端在页面加载时调用 `/api/auth/login-from-cookie`，后端自动从 Cookie 读取。

### Q: Cookie 不存在怎么办？
A: 前端检测到 Cookie 登录失败后，跳转到登录页面让用户手动输入。

### Q: 用户配置存储在哪里？
A: 存储在数据库 `users` 表中，不再使用文件配置。

### Q: 如何保证用户隔离？
A: 通过数据库唯一索引、WebSocket 会话绑定、对话计费上下文隔离三层机制保证。

