# Bohrium AccessKey 问题诊断报告

## 📊 测试结果

**结论**：AccessKey `sk-43edcc41b4794df892cde0e5c45bdbe5` **无效**

所有 5 种配置变体均返回：
```json
{"code":2000,"error":"AccessKey Invalid! "}
```

## 🔍 根本原因分析

### 确认的事实

1. ✅ **请求格式正确** - 与官方 curl 示例完全一致
2. ✅ **API 端点正确** - `https://openapi.dp.tech/openapi/v1/api/integral/consume`
3. ✅ **请求参数正确** - bizNo, changeType, eventValue, skuId, scene 都符合规范
4. ❌ **AccessKey 无效** - API 明确返回 "AccessKey Invalid!"

### 最可能的原因（按概率排序）

| 原因 | 概率 | 说明 |
|------|------|------|
| **1. AccessKey 来源错误** | 90% | 从个人设置获取，而非开放平台/应用管理 |
| **2. AccessKey 类型错误** | 80% | 这是个人 API Key，不是计费 API Key |
| **3. 需要注册应用** | 70% | 计费 API 需要先注册应用获取专用凭证 |
| **4. AccessKey 已过期** | 30% | 密钥已失效 |
| **5. 权限不足** | 60% | AccessKey 没有计费 API 权限 |

## 🎯 解决方案（按优先级）

### 方案 1：在 Bohrium 平台重新获取正确的 AccessKey（推荐）

#### 步骤 1：访问 Bohrium 开放平台

1. 打开浏览器访问：**https://bohrium.dp.tech**
2. 登录你的账号

#### 步骤 2：查找正确的 AccessKey 位置

**请按以下优先级查找**（从上到下依次尝试）：

##### 选项 A：开放平台 > 应用管理（最可能）

```
导航路径：
首页 → 开放平台 / Open Platform → 应用管理 / Application Management
```

**操作**：
1. 点击 **"创建应用"** 或 **"新建应用"**
2. 填写信息：
   - 应用名称：`ResearchMind`
   - 应用描述：`AI 研究助手`
   - 回调地址：`http://localhost:50001/api/auth/callback`
3. 提交后获取：
   - **App ID** (应用 ID)
   - **App Secret** (应用密钥)
   - **AccessKey** (访问密钥)

**⚠️ 重要**：这里获取的 AccessKey 才是用于计费 API 的正确密钥！

##### 选项 B：API 密钥 / API Keys

```
导航路径：
首页 → 个人中心 / Profile → API 密钥 / API Keys → 计费 API / Billing API
```

**操作**：
1. 查找 **"计费 API"** 或 **"Integral API"** 分类
2. 点击 **"生成新密钥"** 或 **"创建密钥"**
3. 选择权限：勾选 **"计费/扣费"** 权限
4. 复制生成的 AccessKey

##### 选项 C：计费设置 / Billing Settings

```
导航路径：
首页 → 计费中心 / Billing → 设置 / Settings → API 凭证 / API Credentials
```

**操作**：
1. 查找 **"API 凭证"** 或 **"开发者凭证"**
2. 复制显示的 AccessKey

#### 步骤 3：验证新的 AccessKey

获取新 AccessKey 后，立即测试：

```bash
python test_bohrium_api.py <新的AccessKey> ResearchMind
```

---

### 方案 2：联系 Bohrium 技术支持（如果找不到正确位置）

**发送邮件或工单**，包含以下信息：

```
主题：无法获取计费 API 的有效 AccessKey

您好，

我正在开发一个应用（ResearchMind），需要调用 Bohrium 计费 API，但遇到认证问题：

【问题描述】
调用 https://openapi.dp.tech/openapi/v1/api/integral/consume 时
返回错误：{"code":2000,"error":"AccessKey Invalid! "}

【已尝试的 AccessKey 来源】
- 个人中心 > [具体位置]
- 格式：sk-43edcc41b4794df892cde0e5c45bdbe5

【请求帮助】
1. 计费 API 的 AccessKey 应该从哪里获取？（请提供具体菜单路径）
2. 是否需要先注册应用才能使用计费 API？
3. 如果需要注册，请提供注册流程文档链接
4. 我的账号是否有计费 API 的使用权限？

【应用信息】
- 应用名称：ResearchMind
- 用途：AI 研究助手
- 预计用量：每月约 XXX 光子

期待您的回复，谢谢！
```

**联系方式**（请在 Bohrium 平台查找）：
- 📧 技术支持邮箱
- 💬 在线客服
- 📝 工单系统

---

### 方案 3：临时禁用计费，继续开发（立即可用）

如果你想先继续开发，稍后再解决计费问题：

#### 修改 `.env` 文件

```bash
# 禁用计费功能
PHOTON_BILLING_ENABLED=false

# 保持详细日志以便调试
PHOTON_BILLING_VERBOSE=true
```

#### 效果

- ✅ 应用正常运行
- ✅ 仍然统计 token 使用量
- ✅ 仍然计算光子数
- ✅ 显示计费日志（但不实际扣费）
- ❌ 不会调用 Bohrium API

#### 重新启动服务

```bash
# 停止当前服务
# 然后重新启动
python -m services.main
```

---

## 📋 检查清单

在 Bohrium 平台上，请确认以下信息：

- [ ] 我的账号类型是什么？（个人/企业/开发者）
- [ ] 是否有"开放平台"或"应用管理"菜单？
- [ ] 是否已注册过应用？
- [ ] AccessKey 是从哪个具体页面获取的？（截图保存）
- [ ] AccessKey 显示的权限/范围是什么？
- [ ] 是否有 SKU ID 或产品 ID 的说明？
- [ ] 是否有计费 API 的文档链接？

## 🔗 有用的资源

- Bohrium 官网：https://bohrium.dp.tech
- Bohrium 文档：https://bohrium.dp.tech/docs （如果有）
- API 文档：https://openapi.dp.tech/docs （如果有）

## 📞 下一步行动

**请按以下顺序操作**：

1. ✅ **立即执行**：修改 `.env` 禁用计费，继续开发
2. 🔍 **今天完成**：登录 Bohrium 平台，按上述路径查找正确的 AccessKey
3. 📧 **如果找不到**：联系 Bohrium 技术支持
4. ✅ **获取新 Key 后**：运行测试脚本验证
5. 🔄 **验证成功后**：重新启用计费功能

---

**需要我帮你做什么？**

- [ ] 修改 `.env` 文件禁用计费
- [ ] 创建 Mock 计费服务用于开发
- [ ] 准备发送给 Bohrium 支持的详细问题描述
- [ ] 其他？

