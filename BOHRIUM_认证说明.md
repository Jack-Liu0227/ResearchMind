# Bohrium 认证说明

## ✅ 正确的认证方式

### 凭证来源

ResearchMind 使用**基于 Cookie 的用户认证**，每个用户使用自己的 Bohrium 凭证：

- ✅ **AccessKey**: 从用户浏览器 Cookie (`appAccessKey`) 获取
- ✅ **ClientName**: 从用户浏览器 Cookie (`clientName`) 获取
- ✅ **SKU ID**: 从环境变量 `.env` 获取（全局配置）

### 为什么不从 .env 读取 AccessKey？

1. **用户隔离**: 每个用户应该使用自己的 AccessKey，而不是共享一个
2. **安全性**: AccessKey 是用户的私密凭证，不应该存储在服务器配置中
3. **计费准确**: 每个用户的使用量应该扣除到自己的账户

---

## 🔧 配置说明

### .env 文件（服务器配置）

```bash
# Bohrium 平台配置
# ⚠️ 注意：AccessKey 和 ClientName 不在此配置
# 它们从用户的 Cookie 或前端传递获取，确保每个用户使用自己的凭证
BOHRIUM_SKU_ID=10048

# 计费设置
PHOTON_BILLING_ENABLED=true
PHOTON_TOKENS_PER_PHOTON=8000
PHOTON_BILLING_PRECISION=4
PHOTON_BILLING_VERBOSE=true
```

### 用户 Cookie（浏览器存储）

```javascript
// 用户登录时设置
document.cookie = `appAccessKey=sk-xxx...xxx; path=/; max-age=2592000`  // 30天
document.cookie = `clientName=researchmind-uuid1759932177; path=/; max-age=2592000`
```

---

## 🔄 认证流程

### 1. 用户登录

```
用户输入 AccessKey + ClientName
    ↓
前端设置 Cookie (appAccessKey, clientName)
    ↓
前端跳转到主界面
```

### 2. WebSocket 连接

```
前端建立 WebSocket 连接
    ↓
后端从 Cookie 读取 appAccessKey 和 clientName
    ↓
后端验证 AccessKey 并创建/查找用户
    ↓
后端绑定 authenticated_user_id 到 WebSocket 会话
```

### 3. 计费扣费

```
用户发送消息触发 AI 响应
    ↓
后端统计 token 使用量
    ↓
后端从 WebSocket 会话获取 authenticated_user_id
    ↓
后端从数据库查询用户的 access_key
    ↓
后端使用用户的 access_key 调用 Bohrium API 扣费
```

---

## 📝 代码示例

### 前端：设置 Cookie

```typescript
// ui/src/components/LoginGateway.tsx
const expiryDate = new Date()
expiryDate.setDate(expiryDate.getDate() + 30)  // 30天过期

document.cookie = `appAccessKey=${accessKey.trim()}; expires=${expiryDate.toUTCString()}; path=/`
document.cookie = `clientName=${clientName.trim()}; expires=${expiryDate.toUTCString()}; path=/`
```

### 后端：从 Cookie 读取

```python
# services/message_handler.py
cookies = dict(
    cookie.split('=', 1) 
    for cookie in headers.get('cookie', '').split('; ') 
    if '=' in cookie
)

user_access_key = cookies.get('appAccessKey')
client_name = cookies.get('clientName')
```

### 后端：使用用户凭证扣费

```python
# services/photon_billing.py
def charge_photons(
    self,
    user_id: int,
    session_id: str,
    photons: float,
    user_access_key: str = None,  # 从 Cookie 获取
    user_client_name: str = None,  # 从 Cookie 获取
    user_sku_id: str = None
):
    # 必须使用用户传入的 AccessKey
    if user_access_key:
        access_key = user_access_key
        client_name = user_client_name or "ResearchMind"
        # 调用 Bohrium API...
    else:
        # 返回错误：未检测到 Cookie
        return {'success': False, 'error_code': 'NO_COOKIE_ACCESS_KEY'}
```

---

## ✅ 测试验证

### 测试新的 AccessKey

```bash
# 使用测试脚本
python test_new_accesskey.py

# 或者手动测试
curl -X POST https://openapi.dp.tech/openapi/v1/api/integral/consume \
  -H "accessKey: sk-xxx...xxx" \
  -H "x-app-key: researchmind-uuid1759932177" \
  -H "Content-Type: application/json" \
  -d '{
    "bizNo": 12345678901234,
    "changeType": 1,
    "eventValue": 0,
    "skuId": 10048,
    "scene": "appCustomizeCharge"
  }'
```

### 预期响应

```json
{
  "code": 0,
  "data": {
    "id": 4890910
  }
}
```

---

## 🎯 关键要点

1. ✅ **AccessKey 从 Cookie 获取**，不从 .env 读取
2. ✅ **每个用户使用自己的凭证**，确保用户隔离
3. ✅ **SKU ID 可以有默认值**，从 .env 读取
4. ✅ **计费时必须检查 Cookie**，没有 Cookie 返回错误
5. ✅ **前端负责设置 Cookie**，后端负责读取和验证

---

## 📁 相关文件

| 文件 | 作用 |
|------|------|
| `services/photon_billing.py` | 计费服务（从 Cookie 获取凭证） |
| `services/message_handler.py` | WebSocket 处理（读取 Cookie） |
| `ui/src/components/LoginGateway.tsx` | 登录页面（设置 Cookie） |
| `ui/src/utils/cookieHelper.ts` | Cookie 工具函数 |
| `.env` | 服务器配置（不包含 AccessKey） |

---

**重要提醒**: 永远不要在 `.env` 或代码中硬编码 AccessKey！

