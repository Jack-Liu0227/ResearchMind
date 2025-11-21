# EasyScholar API 集成说明

## 概述

本项目已集成 EasyScholar API，用于为文献添加期刊信息（影响因子、JCR分区、中科院分区等）。

## 功能特性

- ✅ 侧边栏宽度可调整（支持拖拽调整，自动保存到 localStorage）
- ✅ 为文献自动添加期刊信息（影响因子、分区等）
- ✅ 使用真实的 EasyScholar API
- ✅ 美观的期刊信息展示界面（默认展开显示完整信息）
- ✅ 自动获取期刊信息（展开文献详情时自动查询）

## 使用方法

### 1. 调整侧边栏宽度

- 将鼠标悬停在左侧或右侧侧边栏的边缘
- 当鼠标变为调整大小图标时，按住并拖动
- 释放鼠标后，宽度会自动保存
- 下次打开时会保持上次的宽度设置

### 2. 查看期刊信息

1. 在文献列表中找到需要查看的文献
2. 点击文献卡片展开详细信息
3. 系统会**自动查询并显示**期刊信息，包括：
   - **影响因子（IF）**：当前年度影响因子
   - **5年影响因子**：近5年平均影响因子
   - **JCR 分区**：Journal Citation Reports 分区（Q1-Q4）
   - **中科院分区**：中国科学院文献情报中心分区（1-4区）
   - **Top 期刊标识**：是否为中科院 Top 期刊
   - **收录索引**：SCI、EI、SSCI、CSCD、北大核心、南大核心、科技核心等
   - **期刊详情**：ISSN、出版商、国家等信息

## 配置说明

### 当前状态：真实 API 模式

系统已配置使用**真实的 EasyScholar API**，API Key 已配置在环境变量中。

### API 配置

API 配置存储在 `ui/.env` 文件中：

```env
# EasyScholar API 配置
VITE_EASYSCHOLAR_API_KEY=20bdbb8588cd469d9af25d1cd6ae7640
VITE_EASYSCHOLAR_API_BASE=https://easyscholar.cc/open/getPublicationRank
```

### 更换 API Key

如果需要更换 API Key，只需修改 `ui/.env` 文件中的 `VITE_EASYSCHOLAR_API_KEY` 值：

```env
VITE_EASYSCHOLAR_API_KEY=你的新API_KEY
```

修改后需要重启前端开发服务器：

```bash
cd ui
npm run dev
```

## 技术实现

### API 调用方式

系统使用 EasyScholar 的公开 API 接口：

```
GET https://easyscholar.cc/open/getPublicationRank?publicationName={期刊名称}&apiKey={API_KEY}
```

### 自动获取机制

- 当用户展开文献详情时，系统会自动检测期刊名称
- 如果文献包含 `journal_name` 或 `source` 字段，会自动调用 API 获取期刊信息
- 每篇文献只会查询一次，避免重复请求
- 查询过程静默进行，不会打扰用户

### 数据缓存

- 期刊信息在组件状态中缓存，同一文献不会重复查询
- 未来可以扩展到 localStorage 或数据库缓存，进一步减少 API 调用

## 故障排查

### 问题 1：API 请求失败

**症状**：浏览器控制台显示 API 请求错误

**解决方法**：
1. 检查 `.env` 文件中的 API Key 是否正确
2. 检查网络连接是否正常
3. 打开浏览器开发者工具（F12），查看 Network 标签中的请求详情
4. 确认 API 端点 URL 是否正确
5. 检查 API Key 是否过期或被禁用

### 问题 2：期刊信息不显示

**症状**：展开文献详情后没有显示期刊信息

**可能原因**：
1. 文献数据中没有期刊名称（`source` 或 `journal_name` 字段为空）
2. API 返回的数据中没有找到该期刊
3. 文献来源不是期刊（如会议论文、预印本等）

**解决方法**：
1. 在浏览器控制台查看日志，确认是否发起了 API 请求
2. 检查 API 响应数据，确认是否返回了期刊信息
3. 对于非期刊文献，这是正常现象

### 问题 3：期刊信息显示不完整

**症状**：只显示部分期刊信息字段

**原因**：EasyScholar API 返回的数据可能不包含所有字段（取决于期刊本身）

**说明**：这是正常现象，不同期刊的可用信息不同。例如：
- 某些期刊可能没有中科院分区
- 某些期刊可能没有5年影响因子
- 新创刊的期刊可能还没有影响因子数据

## 技术架构

### 文件结构

```
ui/
├── .env                        # 环境变量配置（包含 API Key）
├── src/
│   ├── components/
│   │   ├── Layout.tsx          # 侧边栏宽度调整
│   │   └── RightPanel.tsx      # 文献列表和期刊信息展示
│   ├── services/
│   │   └── easyScholarService.ts  # EasyScholar API 服务
│   └── types/
│       └── index.ts            # Paper 类型定义（包含期刊信息字段）
```

### 数据流

```
用户展开文献详情
    ↓
RightPanel 组件检测到展开事件
    ↓
调用 fetchJournalInfo() 函数
    ↓
easyScholarService.getJournalInfo()
    ↓
发送 HTTP GET 请求到 EasyScholar API
    ↓
解析 API 响应数据
    ↓
更新组件状态，显示期刊信息
```

## 已实现的功能

✅ **侧边栏宽度调整**
- 左右侧边栏支持拖拽调整宽度
- 宽度自动保存到 localStorage
- 动态最小/最大宽度限制

✅ **期刊信息自动获取**
- 展开文献详情时自动查询
- 静默获取，不打扰用户
- 每篇文献只查询一次

✅ **完整的期刊信息展示**
- 影响因子和5年影响因子
- JCR 分区和类别
- 中科院分区和 Top 标识
- 收录索引（SCI、EI、SSCI、CSCD等）
- 核心期刊标识（北大核心、南大核心等）
- ISSN、出版商、国家等详细信息

✅ **美观的 UI 设计**
- 渐变背景色
- 卡片式布局
- 响应式设计
- 清晰的信息层次

## 下一步优化建议

### 短期优化

1. **本地缓存**：将查询结果保存到 localStorage，减少重复 API 调用
2. **错误重试**：添加自动重试机制处理临时网络错误
3. **加载动画**：优化加载状态的视觉反馈

### 中期优化

1. **后端代理**：将 API 调用移到后端，避免在前端暴露 API Key
2. **数据库缓存**：将期刊信息保存到数据库，永久缓存
3. **批量查询**：支持一次性为多篇文献获取期刊信息

### 长期优化

1. **智能识别**：在导入文献时自动获取期刊信息
2. **数据更新**：定期更新期刊信息（影响因子每年更新）
3. **自定义字段**：允许用户选择显示哪些期刊信息字段
4. **导出功能**：支持将期刊信息导出到 Excel/CSV

## 参考资源

- **EasyScholar 开放平台**：https://www.easyscholar.cc/console/user/open
- **当前 API Key**：`20bdbb8588cd469d9af25d1cd6ae7640`
- **API 端点**：`https://easyscholar.cc/open/getPublicationRank`

## 更新日志

### 2024-11-20
- ✅ 实现侧边栏宽度调整功能
- ✅ 集成 EasyScholar API
- ✅ 实现期刊信息自动获取和展示
- ✅ 移除模拟模式，使用真实 API
- ✅ 优化期刊信息展示界面
- ✅ 添加完整的文档说明

