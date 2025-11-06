# Cookie 计费配置指南

## 概述

ResearchMind 支持通过浏览器 Cookie 自动获取用户的 Bohrium 计费配置，实现方式与 Flask 的 `request.cookies.get()` 完全一致。

## 工作原理

### 方案对比

| 特性 | Flask HTTP | FastAPI HTTP (我们的实现) |
|------|-----------|--------------------------|
| **获取方式** | `request.cookies.get("appAccessKey")` | `appAccessKey: str = Cookie(None)` |
| **代码复杂度** | 简单 | 简单 |
| **标准化** | ✅ | ✅ |
| **易维护性** | ✅ | ✅ |
| **自动解析** | ✅ | ✅ |

### 实现流程

```
1. 用户访问应用（浏览器携带 Cookie）
   Cookie: appAccessKey=xxx; clientName=yyy
   ↓
2. 前端 WebSocket 连接成功后
   调用 FastAPI 端点: POST /api/billing/config/save-from-cookie
   ↓
3. FastAPI 自动从 Cookie 读取配置
   appAccessKey: str = Cookie(None)
   clientName: str = Cookie(None)
   ↓
4. 保存到用户配置文件
   config_manager.save_user_config(user_id, access_key, sku_id, client_name)
   ↓
5. AI 调用时自动使用用户配置
   优先级: 用户 Cookie > 开发者默认配置
```

## 代码示例

### 后端：FastAPI 端点

```python
# services/billing_api.py

@router.post("/config/save-from-cookie")
async def save_billing_config_from_cookie(
    user_id: str = Query(..., description="用户会话 ID"),
    appAccessKey: Optional[str] = Cookie(None),  # 自动从 Cookie 读取
    clientName: Optional[str] = Cookie(None)     # 自动从 Cookie 读取
) -> BillingConfigResponse:
    """
    从 Cookie 中读取并保存用户的 Bohrium 计费配置
    
    就像 Flask 的 request.cookies.get() 一样简单！
    """
    if not appAccessKey:
        return BillingConfigResponse(
            success=True,
            message="未检测到用户 Cookie，将使用开发者默认配置",
            has_config=False
        )
    
    # 保存配置
    config_manager = get_config_manager()
    config_manager.save_user_config(
        user_id=user_id,
        access_key=appAccessKey,
        sku_id="10048",
        client_name=clientName or "ResearchMind"
    )
    
    return BillingConfigResponse(
        success=True,
        message="配置保存成功（来自用户 Cookie）",
        has_config=True
    )
```

### 前端：调用 FastAPI 端点

```typescript
// ui/src/services/websocket.ts

private async sendUserBohriumConfig(): Promise<void> {
  try {
    const sessionId = localStorage.getItem('researchmind_session_id') || this.clientId

    // 调用 FastAPI 端点，自动从 Cookie 读取配置
    const response = await fetch(
      `/api/billing/config/save-from-cookie?user_id=${sessionId}`,
      {
        method: 'POST',
        credentials: 'include'  // 重要：确保发送 Cookie
      }
    )

    if (response.ok) {
      const result = await response.json()
      
      if (result.has_config) {
        console.log('✅ 用户 Bohrium 配置已保存 (来自 Cookie)')
      } else {
        console.log('ℹ️ 将使用开发者默认配置')
      }
    }
  } catch (error) {
    console.error('❌ 保存配置失败:', error)
  }
}
```

## 使用说明

### 开发者测试

如果用户未提供 Cookie，系统会自动使用开发者配置：

```bash
# .env.remote
BOHRIUM_ACCESS_KEY=your_access_key_here
BOHRIUM_SKU_ID=10048
BOHRIUM_CLIENT_NAME=ResearchMind
```

### 用户使用

用户需要在浏览器中设置以下 Cookie：

```javascript
// 方式 1：通过 JavaScript 设置
document.cookie = "appAccessKey=your_access_key; path=/; max-age=86400";
document.cookie = "clientName=YourName; path=/; max-age=86400";

// 方式 2：通过 Bohrium OAuth 登录（自动设置）
window.location.href = '/api/auth/login?user_session_id=' + sessionId;
```

## 扣费逻辑

### 收费标准

- **5000 tokens = 1 光子**
- 累计扣费：每累计 5000 tokens 自动扣费 1 个光子
- 避免重复扣费：记录已扣费的光子数

### 配置优先级

```
1. 用户 Cookie (appAccessKey + clientName)
   ↓ 如果没有
2. 用户配置文件 (~/.researchmind/user_billing_configs/{user_id}.json)
   ↓ 如果没有
3. 开发者默认配置 (.env.remote)
```

### 自动扣费流程

```python
# services/photon_billing.py

def record_usage_isolated(conversation_id, user_id, tokens, model):
    # 1. 累计 token 使用量
    context.update_token_usage(tokens, photons, model)
    
    # 2. 检查是否达到扣费阈值
    total_tokens = context.total_tokens
    photons_to_charge = total_tokens // 5000  # 每 5000 tokens = 1 光子
    
    # 3. 计算需要扣费的光子数
    charged_photons = context.charged_photons
    photons_need_charge = photons_to_charge - charged_photons
    
    # 4. 如果需要扣费，调用 Bohrium API
    if photons_need_charge > 0:
        # 读取用户配置
        user_config = config_manager.get_user_config(user_id)
        user_access_key = user_config.get('access_key')
        
        # 调用扣费 API
        charge_result = self.charge_photons(
            photons=photons_need_charge,
            user_access_key=user_access_key  # 优先使用用户的 AK
        )
        
        # 更新已扣费光子数
        if charge_result.get('success'):
            context.charged_photons = photons_to_charge
```

## API 文档

### POST /api/billing/config/save-from-cookie

从 Cookie 中读取并保存用户的 Bohrium 计费配置。

**请求参数：**

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| user_id | string | Query | ✅ | 用户会话 ID |
| appAccessKey | string | Cookie | ❌ | Bohrium AccessKey（自动从 Cookie 读取） |
| clientName | string | Cookie | ❌ | 客户端名称（自动从 Cookie 读取） |

**请求示例：**

```bash
curl -X POST "http://localhost:50002/api/billing/config/save-from-cookie?user_id=session_123" \
  -H "Cookie: appAccessKey=e3a895e74d9a4c858b64bfd1d7343e02; clientName=ResearchMind" \
  --cookie-jar cookies.txt
```

**响应示例：**

```json
{
  "success": true,
  "message": "配置保存成功（来自用户 Cookie）",
  "has_config": true,
  "config": {
    "sku_id": "10048",
    "client_name": "ResearchMind",
    "access_key_masked": "e3a895e7...ce02",
    "source": "来自用户 Cookie"
  }
}
```

## 优势总结

### ✅ 与 Flask 方案完全等价

```python
# Flask
@app.route("/")
def index():
    access_key = request.cookies.get("appAccessKey") or DEV_ACCESS_KEY
    client_name = request.cookies.get("clientName") or CLIENT_NAME

# FastAPI (我们的实现)
@router.post("/config/save-from-cookie")
async def save_billing_config_from_cookie(
    appAccessKey: Optional[str] = Cookie(None),
    clientName: Optional[str] = Cookie(None)
):
    access_key = appAccessKey or DEV_ACCESS_KEY
    client_name = clientName or CLIENT_NAME
```

### ✅ 更简单、更标准

- 使用 FastAPI 原生的 `Cookie()` 参数
- 无需手动解析 Cookie 字符串
- 代码更清晰、更易维护

### ✅ 更灵活

- 可以随时调用，不依赖 WebSocket 连接
- 支持 HTTP 和 WebSocket 两种方式
- 易于测试和调试

## 测试

### 测试 1：有用户 Cookie

```bash
# 设置 Cookie
curl -X POST "http://localhost:50002/api/billing/config/save-from-cookie?user_id=test_user" \
  -H "Cookie: appAccessKey=test_key_123; clientName=TestUser"

# 预期输出
{
  "success": true,
  "message": "配置保存成功（来自用户 Cookie）",
  "has_config": true,
  "config": {
    "source": "来自用户 Cookie"
  }
}
```

### 测试 2：无用户 Cookie

```bash
# 不设置 Cookie
curl -X POST "http://localhost:50002/api/billing/config/save-from-cookie?user_id=test_user"

# 预期输出
{
  "success": true,
  "message": "未检测到用户 Cookie，将使用开发者默认配置",
  "has_config": false,
  "config": {
    "source": "开发者本地调试 AK"
  }
}
```

## 总结

这个方案完美实现了与 Flask `request.cookies.get()` 等价的功能，同时保持了代码的简洁性和可维护性。

**关键优势：**
1. ✅ 使用 FastAPI 原生 Cookie 支持
2. ✅ 代码简单、易懂、易维护
3. ✅ 与 Flask 方案完全等价
4. ✅ 支持自动回退到开发者配置
5. ✅ 完整的错误处理和日志记录

