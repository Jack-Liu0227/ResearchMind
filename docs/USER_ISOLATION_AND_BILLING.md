# 用户认证与计费机制

## 概述

ResearchMind 实现了基于 Cookie 的用户认证和计费机制：
- **每次都从 Cookie 读取** `appAccessKey` 和 `clientName`
- **如果 Cookie 不存在**，要求用户手动输入 AccessKey
- **用户配置存储在数据库中**，确保数据持久化和隔离

## 核心原则

1. **Cookie 优先**：每次请求都尝试从 Cookie 读取用户凭证
2. **手动输入备选**：Cookie 不存在时，提供登录页面让用户输入
3. **数据库存储**：用户配置（AccessKey、ClientName、SKU ID）存储在数据库 User 表中
4. **完全隔离**：每个用户的计费数据完全独立，使用自己的 AccessKey 扣费

## 认证流程

### 方式 1：Cookie 自动登录（推荐）

```
1. 用户访问应用
   ↓
2. 前端检测 Cookie 中的 appAccessKey
   ↓
3. 调用 /api/auth/login-from-cookie
   - 后端自动从 Cookie 读取 appAccessKey 和 clientName
   - 创建/更新数据库用户记录
   - 返回 JWT Token
   ↓
4. 前端保存 Token 到 localStorage
   ↓
5. WebSocket 连接时发送 Token 认证
   - 后端验证 Token
   - 保存 authenticated_user_id 到会话上下文
```

### 方式 2：手动登录（Cookie 不存在时）

```
1. 用户访问应用，Cookie 中无 appAccessKey
   ↓
2. 前端跳转到登录页面
   ↓
3. 用户手动输入 AccessKey 和 ClientName
   ↓
4. 调用 /api/auth/login
   - 验证 AccessKey 有效性
   - 创建/更新数据库用户记录
   - 返回 JWT Token
   ↓
5. 前端保存 Token 到 localStorage
   ↓
6. WebSocket 连接时发送 Token 认证
```

## 数据存储

#### 数据库（User 表）
```python
class User(Base):
    id = Column(Integer, primary_key=True)
    access_key = Column(String(64), unique=True)  # Bohrium AccessKey
    client_name = Column(String(100))              # 客户端名称
    sku_id = Column(String(20), default="10048")   # SKU ID
    total_photons_used = Column(Float)             # 累计使用光子数
    total_tokens_used = Column(Integer)            # 累计使用 Token 数
```

#### WebSocket 会话上下文
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

### 3. 计费隔离机制

#### 对话级别隔离
每个对话（conversation/session）有独立的计费上下文：

```python
class ConversationBillingContext:
    conversation_id: str          # 对话 ID
    user_id: str                  # 用户 ID
    total_tokens: int             # 累计 tokens
    total_photons: float          # 累计光子数
    charged_photons: int          # 已扣费光子数
```

#### 扣费流程

```
┌─────────────────────────────────┐
│ LLM 调用完成                     │
│ - 获取 token 使用量              │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ record_usage_isolated()          │
│ 1. 从 client_id 获取             │
│    authenticated_user_id         │
│ 2. 从数据库查询用户配置          │
│ 3. 累计 token 使用量             │
│ 4. 检查是否达到扣费阈值          │
└──────┬──────────────────────────┘
       │ 达到阈值（如 8000 tokens）
       ▼
┌─────────────────────────────────┐
│ charge_photons()                 │
│ 1. 使用用户的 access_key         │
│ 2. 调用 Bohrium API 扣费         │
│ 3. 更新 charged_photons          │
└─────────────────────────────────┘
```

## 关键代码位置

### 1. 用户认证
- **登录端点**: `services/auth_api.py`
  - `/api/auth/login` - 手动登录
  - `/api/auth/login-from-cookie` - Cookie 自动登录

- **JWT 处理**: `services/auth/jwt_handler.py`
  - `create_access_token()` - 创建 Token
  - `verify_token()` - 验证 Token

- **WebSocket 认证**: `services/message_handler.py`
  - `handle_auth()` - 处理 WebSocket 认证消息

### 2. 计费系统
- **计费服务**: `services/photon_billing.py`
  - `record_usage_isolated()` - 记录使用量（隔离）
  - `charge_photons()` - 实际扣费

- **计费上下文**: `services/user_billing_config.py`
  - `ConversationBillingContext` - 对话计费上下文
  - `ConversationBillingContextManager` - 上下文管理器

- **LLM 回调**: `agents/callbacks.py`
  - `record_llm_usage()` - LLM 调用后记录使用量

## 用户隔离保证

### 1. 认证隔离
- 每个用户有唯一的 `access_key`（数据库唯一索引）
- JWT Token 包含 `user_id`，确保身份唯一性
- WebSocket 会话绑定 `authenticated_user_id`

### 2. 数据隔离
- 每个对话有独立的 `ConversationBillingContext`
- 使用线程锁（`threading.RLock()`）保护并发访问
- 对话 ID 作为隔离键，确保数据不混淆

### 3. 扣费隔离
- 优先从 WebSocket 会话获取 `authenticated_user_id`
- 从数据库查询用户的 `access_key`
- 使用用户自己的 `access_key` 调用 Bohrium API
- 每个用户的扣费记录独立存储

## 配置说明

### 环境变量
```bash
# 计费阈值（多少 tokens = 1 光子）
PHOTON_TOKENS_PER_PHOTON=8000

# 是否启用计费
PHOTON_BILLING_ENABLED=true

# JWT 密钥
JWT_SECRET_KEY=your_secret_key_here
```

### 前端配置
```typescript
// localStorage 存储
- auth_token: JWT Token
- researchmind_client_id: WebSocket 客户端 ID
- researchmind_session_id: 会话 ID
```

## 测试验证

### 1. 多用户测试
```bash
# 用户 A 登录
curl -X POST http://localhost:50002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"access_key": "user_a_key", "client_name": "UserA"}'

# 用户 B 登录
curl -X POST http://localhost:50002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"access_key": "user_b_key", "client_name": "UserB"}'
```

### 2. 验证隔离
- 观察日志中的 `authenticated_user_id`
- 检查数据库中的用户记录
- 验证扣费时使用的 `access_key`

## 常见问题

### Q: 如何确保用户 A 的使用不会扣到用户 B 的账户？
A: 系统通过以下机制保证：
1. WebSocket 认证时绑定 `authenticated_user_id`
2. 计费时从会话上下文获取用户 ID
3. 从数据库查询用户的 `access_key`
4. 使用用户自己的 `access_key` 扣费

### Q: 如果用户未登录会怎样？
A: 
- WebSocket 连接正常，但 `authenticated_user_id` 为 `None`
- 计费时无法获取用户配置，扣费失败
- 返回错误：`未配置 Bohrium AccessKey`

### Q: Cookie 登录和手动登录有什么区别？
A:
- Cookie 登录：跳过 AccessKey 验证（提升性能）
- 手动登录：验证 AccessKey 有效性（首次登录推荐）
- 两者都会创建/更新用户记录并返回 JWT Token

