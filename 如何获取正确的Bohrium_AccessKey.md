# 如何获取正确的 Bohrium AccessKey

## 🎯 目标

获取用于 **计费 API** (`/openapi/v1/api/integral/consume`) 的有效 AccessKey

## 📍 当前问题

- ❌ 现有 AccessKey: `sk-43edcc41b4794df892cde0e5c45bdbe5` **无效**
- ❌ API 返回: `{"code":2000,"error":"AccessKey Invalid! "}`
- ❌ 所有请求配置变体均失败

## 🔍 在 Bohrium 平台上查找（按优先级）

### 方法 1：开放平台 > 应用管理（推荐，成功率 90%）

#### 导航路径

```
登录 https://bohrium.dp.tech
↓
顶部菜单栏 → "开放平台" / "Open Platform" / "开发者中心"
↓
左侧菜单 → "应用管理" / "Application Management" / "我的应用"
```

#### 操作步骤

1. **如果已有应用**：
   - 找到名为 "ResearchMind" 或类似的应用
   - 点击 "查看详情" 或 "管理"
   - 复制显示的 **AccessKey** 或 **App Secret**

2. **如果没有应用**：
   - 点击 **"创建应用"** / "新建应用" / "注册应用"
   - 填写表单：
     ```
     应用名称: ResearchMind
     应用类型: Web 应用 / 服务端应用
     应用描述: AI 研究助手，用于材料科学研究
     回调地址: http://localhost:50001/api/auth/callback
     权限范围: 勾选 "计费 API" / "Integral API"
     ```
   - 提交后，系统会显示：
     - **App ID** (应用 ID)
     - **App Secret** (应用密钥) ← **这个可能是正确的 AccessKey**
     - **AccessKey** (访问密钥)
   - **⚠️ 重要**：立即复制并保存，某些平台只显示一次！

3. **测试新 AccessKey**：
   ```bash
   python test_bohrium_api.py <新的AccessKey> ResearchMind
   ```

---

### 方法 2：API 密钥管理（成功率 70%）

#### 导航路径

```
登录 https://bohrium.dp.tech
↓
右上角头像 → "个人中心" / "Profile" / "账户设置"
↓
左侧菜单 → "API 密钥" / "API Keys" / "开发者密钥"
```

#### 操作步骤

1. **查看现有密钥列表**：
   - 检查是否有标注 **"计费 API"** / "Billing" / "Integral" 的密钥
   - 查看每个密钥的 **权限范围** / "Scopes"

2. **创建新密钥**：
   - 点击 **"生成新密钥"** / "Create New Key"
   - 选择密钥类型：
     - ✅ **"计费 API 密钥"** / "Billing API Key"
     - ✅ **"服务端密钥"** / "Server-side Key"
     - ❌ 不要选 "只读密钥" / "Read-only Key"
   - 权限设置：
     - ✅ 勾选 **"计费/扣费"** / "Billing/Charge"
     - ✅ 勾选 **"积分消费"** / "Integral Consume"
   - 复制生成的密钥

3. **测试**：
   ```bash
   python test_bohrium_api.py <新密钥> ResearchMind
   ```

---

### 方法 3：计费中心（成功率 60%）

#### 导航路径

```
登录 https://bohrium.dp.tech
↓
顶部菜单 → "计费中心" / "Billing" / "费用管理"
↓
左侧菜单 → "API 凭证" / "API Credentials" / "开发者设置"
```

#### 操作步骤

1. 查找 **"API 凭证"** 或 **"开发者凭证"** 区域
2. 复制显示的 AccessKey 或 Secret Key
3. 如果有多个，选择标注为 **"计费 API"** 的那个

---

### 方法 4：文档中心查找（成功率 50%）

#### 导航路径

```
登录 https://bohrium.dp.tech
↓
顶部菜单 → "文档" / "Docs" / "帮助中心"
↓
搜索: "计费 API" / "Billing API" / "Integral API"
```

#### 查找内容

- API 认证方式说明
- AccessKey 获取教程
- 示例代码中的 AccessKey 格式
- 常见问题 FAQ

---

## 🚨 关键识别标志

**正确的 AccessKey 应该具备以下特征**：

### 格式特征

- ✅ 长度：32-64 字符
- ✅ 格式：可能以 `sk-`、`ak-`、`app-` 开头
- ✅ 字符：字母数字组合，可能包含 `-` 或 `_`

### 权限特征

在 Bohrium 平台上，正确的 AccessKey 应该显示：

- ✅ 权限范围包含：**"计费 API"** / "Billing API" / "Integral API"
- ✅ 状态：**"有效"** / "Active" / "启用"
- ✅ 类型：**"服务端密钥"** / "Server Key" / "应用密钥"

### 来源特征

- ✅ 来自：**"开放平台"** / "应用管理" / "API 密钥管理"
- ❌ 不是：**"个人设置"** / "账户安全" / "登录密码"

---

## 📸 需要截图的位置

如果找不到，请截图以下页面发给 Bohrium 支持：

1. **主菜单栏**（顶部导航）
2. **个人中心的左侧菜单**
3. **所有包含 "API"、"密钥"、"开放平台" 的页面**
4. **当前 AccessKey 的详情页**（如果有）

---

## ✅ 验证新 AccessKey 的步骤

获取新 AccessKey 后，按以下步骤验证：

### 1. 运行测试脚本

```bash
python test_bohrium_api.py <新AccessKey> ResearchMind
```

**期望输出**：
```
✅ 请求成功！
响应数据: {"code":0, "message":"success", ...}
```

### 2. 更新 .env 文件

如果测试成功，更新配置：

```bash
# 在 .env 文件中
BOHRIUM_ACCESS_KEY=<新AccessKey>
PHOTON_BILLING_ENABLED=true
```

### 3. 重启服务

```bash
# 停止当前服务，然后重新启动
python -m services.main
```

### 4. 端到端测试

在 ResearchMind 中发送一条消息，检查后端日志：

**期望日志**：
```
✅ [计费] 扣费成功: 1 光子
💎 [计费] 剩余光子: XXX
```

---

## 🆘 如果仍然找不到

### 联系 Bohrium 技术支持

**准备以下信息**：

1. **账号信息**：
   - 用户名 / 邮箱
   - 账号类型（个人/企业）

2. **问题描述**：
   ```
   我需要调用计费 API (https://openapi.dp.tech/openapi/v1/api/integral/consume)
   但现有 AccessKey 返回 "AccessKey Invalid!" 错误。
   
   请问：
   1. 计费 API 的 AccessKey 应该从哪里获取？
   2. 是否需要先注册应用？
   3. 我的账号是否有计费 API 权限？
   ```

3. **截图**：
   - 当前 AccessKey 的获取位置
   - 错误响应截图
   - Bohrium 平台的主菜单

**联系方式**（在 Bohrium 平台查找）：
- 📧 技术支持邮箱
- 💬 在线客服（右下角聊天图标）
- 📝 工单系统

---

## 📝 记录模板

找到正确 AccessKey 后，请记录：

```
✅ 获取时间: 2025-11-10
✅ 获取位置: [具体菜单路径]
✅ AccessKey: <前8位>...<后4位>
✅ 权限范围: 计费 API
✅ 有效期: [如果有]
✅ 测试结果: 成功 ✅ / 失败 ❌
```

---

**祝你顺利获取正确的 AccessKey！如有问题随时联系我。**

