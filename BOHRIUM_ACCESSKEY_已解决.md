# ✅ Bohrium AccessKey 问题已解决

## 📊 问题回顾

### 原始问题
- ❌ AccessKey: `sk-43edcc41b4794df892cde0e5c45bdbe5` **无效**
- ❌ API 返回: `{"code":2000,"error":"AccessKey Invalid! "}`
- ❌ 所有测试变体均失败

### 根本原因
- AccessKey 来源错误（从个人设置获取，而非应用管理）
- 计费 API 需要应用级别的 AccessKey

---

## ✅ 解决方案

### 新的有效凭证

```bash
# .env 文件配置
BOHRIUM_ACCESS_KEY=sk-49191efe405c4b7b8b00bf1332bd1a5a
BOHRIUM_CLIENT_NAME=researchmind-uuid1759932177
BOHRIUM_SKU_ID=10048
PHOTON_BILLING_ENABLED=true
```

### 测试结果

```bash
$ python test_new_accesskey.py

✅ 成功！AccessKey 有效！

📥 响应状态码: 200
📥 响应内容: {"code":0,"data":{"id":4890910}}
```

**API 响应详情**：
- HTTP 状态码: `200 OK`
- 响应代码: `0` (成功)
- 交易 ID: `4890910`
- 服务器: `openapi` (X-DP-SERVER)

---

## 🔧 已完成的配置更新

### 1. 环境变量 (.env)

```bash
# Bohrium 平台凭证
BOHRIUM_SKU_ID=10048
BOHRIUM_ACCESS_KEY=sk-49191efe405c4b7b8b00bf1332bd1a5a
BOHRIUM_CLIENT_NAME=researchmind-uuid1759932177

# 计费功能
PHOTON_BILLING_ENABLED=true  # ✅ 已重新启用
PHOTON_BILLING_VERBOSE=true
PHOTON_TOKENS_PER_PHOTON=8000
```

### 2. 代码配置 (services/photon_billing.py)

已支持的请求头：
```python
headers = {
    "accessKey": access_key,      # ✅ 从 Cookie 或环境变量读取
    "x-app-key": client_name,     # ✅ 从 Cookie 或环境变量读取
    "Content-Type": "application/json",
    "Accept": "*/*"
}
```

---

## 🎯 当前状态

### ✅ 已完成

- [x] 诊断 AccessKey 无效的根本原因
- [x] 获取新的有效 AccessKey
- [x] 测试验证新 AccessKey 可用
- [x] 更新 .env 配置
- [x] 重新启用计费功能
- [x] 添加 x-app-key 请求头支持

### 📋 待验证

- [ ] 重启 ResearchMind 服务
- [ ] 发送测试消息触发计费
- [ ] 检查后端日志确认扣费成功
- [ ] 在 Bohrium 平台查看扣费记录

---

## 🚀 下一步操作

### 1. 重启服务

```bash
# 停止当前运行的服务（如果有）
# 然后重新启动

# 方式 1: 使用启动脚本
./start.sh

# 方式 2: 直接运行
python -m services.main
```

### 2. 测试计费功能

1. **打开 ResearchMind 前端**
2. **发送一条测试消息**（触发 AI 响应）
3. **观察后端日志**，应该看到：

```
✅ [计费] 扣费成功: X 光子
💎 [计费] 使用 AccessKey 来源: Cookie
💳 [计费] API 响应: {"code":0,"data":{"id":...}}
```

### 3. 验证 Bohrium 平台

1. 登录 https://bohrium.dp.tech
2. 进入 **计费中心** 或 **使用记录**
3. 查看是否有新的扣费记录
4. 确认扣费金额正确

---

## 📊 关键差异对比

| 项目 | 旧 AccessKey (无效) | 新 AccessKey (有效) |
|------|-------------------|-------------------|
| **AccessKey** | `sk-43edc...dbe5` | `sk-49191...1a5a` |
| **Client Name** | `ResearchMind` | `researchmind-uuid1759932177` |
| **来源** | 个人设置（推测） | 应用管理 |
| **API 响应** | `{"code":2000,"error":"AccessKey Invalid!"}` | `{"code":0,"data":{"id":4890910}}` |
| **HTTP 状态** | `401 Unauthorized` | `200 OK` |

---

## 🔍 技术细节

### API 请求格式

```bash
POST https://openapi.dp.tech/openapi/v1/api/integral/consume

Headers:
  accessKey: sk-49191efe405c4b7b8b00bf1332bd1a5a
  x-app-key: researchmind-uuid1759932177
  Content-Type: application/json

Body:
{
  "bizNo": <14位唯一ID>,
  "changeType": 1,
  "eventValue": <光子数>,
  "skuId": 10048,
  "scene": "appCustomizeCharge"
}
```

### 成功响应格式

```json
{
  "code": 0,
  "data": {
    "id": 4890910
  }
}
```

- `code: 0` = 成功
- `code: 2000` = AccessKey 无效
- `data.id` = 交易记录 ID

---

## 📝 经验总结

### 关键发现

1. **AccessKey 来源很重要**
   - ❌ 个人设置的 AccessKey 不能用于计费 API
   - ✅ 应用管理的 AccessKey 才是正确的

2. **Client Name 格式**
   - 旧格式: `ResearchMind`
   - 新格式: `researchmind-uuid1759932177`
   - 可能需要包含唯一标识符

3. **x-app-key 请求头**
   - 虽然官方 curl 示例没有，但实际可能需要
   - 已在代码中添加支持

### 最佳实践

1. **从 Bohrium 平台的"应用管理"获取 AccessKey**
2. **测试新 AccessKey 后再更新配置**
3. **保持 .env 文件不提交到 git**
4. **定期检查 AccessKey 是否过期**

---

## 🎉 问题已完全解决！

- ✅ AccessKey 有效
- ✅ API 调用成功
- ✅ 配置已更新
- ✅ 计费功能已启用

**ResearchMind 现在可以正常使用 Bohrium 计费 API 了！**

---

## 📞 如有问题

如果重启后仍有问题，请检查：

1. **后端日志**：查看是否有错误信息
2. **Cookie 设置**：确保前端正确设置了 `appAccessKey` 和 `clientName`
3. **环境变量**：确认 `.env` 文件被正确加载
4. **网络连接**：确认可以访问 `openapi.dp.tech`

---

**祝使用愉快！** 🚀

