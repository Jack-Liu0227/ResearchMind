# EasyScholar API 集成调试指南

## 问题排查步骤

### 1. 检查浏览器控制台

打开浏览器开发者工具（F12），查看 Console 标签页，应该能看到以下日志：

#### 文献数据字段检查
```
🔍 [调试] 文献数据完整字段: {
  paper_id: "...",
  title: "...",
  journal_name: "...",  // ← 检查这个字段是否存在
  source: "...",
  url: "...",
  doi: "...",
  all_fields: [...]
}
```

**关键检查点**：
- ✅ 如果有 `journal_name` 字段，会直接使用
- ⚠️ 如果没有 `journal_name`，会尝试使用 `source` 字段
- ⚠️ 如果都没有，会尝试从 `url` 提取（通过 DOI/CrossRef）

#### 期刊名称提取日志
```
📚 [期刊信息] 期刊名称: Nature （来源: journal_name 字段）
```
或
```
📚 [期刊信息] 期刊名称: Nature （来源: URL 提取（通过 DOI/CrossRef））
```

#### API 调用日志
```
📡 [API] 调用 EasyScholar API...
📚 [EasyScholar] 查询期刊信息: Nature
🔧 [EasyScholar] API 配置: {
  base: "https://easyscholar.cc/open/getPublicationRank",
  key: "20bdbb85..."
}
📡 [EasyScholar] 请求 URL: https://easyscholar.cc/open/getPublicationRank?publicationName=Nature&apiKey=***
📥 [EasyScholar] 响应状态: 200 OK
✅ [EasyScholar] API 原始响应数据: {...}
✅ [EasyScholar] 解析后的期刊信息: {...}
```

### 2. 常见问题和解决方案

#### 问题 1：无法获取期刊名称
**症状**：
```
⚠️ [期刊信息] 无法获取期刊名称，已尝试的字段: {
  journal_name: undefined,
  source: "tavily_academic",
  url: "https://..."
}
```

**原因**：CSV 文件中缺少 `journal_name` 字段

**解决方案**：
1. **方案 A**：在 CSV 文件中添加 `journal_name` 列
2. **方案 B**：如果 `url` 是 DOI 链接，系统会自动从 CrossRef 获取期刊名称
3. **方案 C**：手动点击"重试获取期刊信息"按钮

#### 问题 2：API 请求失败
**症状**：
```
❌ [EasyScholar] API 请求失败: 401 Unauthorized
```

**原因**：API Key 无效或过期

**解决方案**：
1. 检查 `ui/.env` 文件中的 `VITE_EASYSCHOLAR_API_KEY`
2. 确认 API Key 是否正确：`20bdbb8588cd469d9af25d1cd6ae7640`
3. 重启开发服务器（`npm run dev`）

#### 问题 3：未找到期刊信息
**症状**：
```
⚠️ [API] 未找到期刊信息，期刊名称: Nature Communications
```

**原因**：
- 期刊名称拼写错误
- EasyScholar 数据库中没有该期刊
- 期刊名称格式不匹配（如缩写 vs 全称）

**解决方案**：
1. 尝试使用期刊的完整名称
2. 尝试使用期刊的缩写
3. 检查 API 原始响应数据，确认返回了什么

#### 问题 4：CORS 错误
**症状**：
```
Access to fetch at 'https://easyscholar.cc/...' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**原因**：EasyScholar API 不允许跨域请求

**解决方案**：
需要通过后端代理 API 请求（待实现）

### 3. 测试 API 调用

#### 手动测试 API
在浏览器控制台中运行：

```javascript
// 测试 EasyScholar API
const testJournal = async (name) => {
  const apiKey = '20bdbb8588cd469d9af25d1cd6ae7640'
  const url = `https://easyscholar.cc/open/getPublicationRank?publicationName=${encodeURIComponent(name)}&apiKey=${apiKey}`
  
  console.log('测试 URL:', url)
  
  const response = await fetch(url)
  const data = await response.json()
  
  console.log('响应数据:', data)
  return data
}

// 测试几个常见期刊
testJournal('Nature')
testJournal('Science')
testJournal('Cell')
```

#### 测试 DOI 提取
```javascript
// 测试从 DOI 获取期刊名称
const testDOI = async (doi) => {
  const url = `https://api.crossref.org/works/${encodeURIComponent(doi)}`
  const response = await fetch(url)
  const data = await response.json()
  
  console.log('期刊名称:', data?.message?.['container-title']?.[0])
  return data
}

// 测试
testDOI('10.1038/s41586-021-03428-z')
```

### 4. UI 功能说明

#### 期刊信息显示位置
- **紧凑视图**（未展开）：显示核心信息（IF、JCR分区、中科院分区、Top标识）
- **展开视图**：显示完整的期刊信息（5年IF、收录索引、ISSN、出版商等）

#### 状态指示
- **加载中**：显示旋转图标 + "获取期刊信息中..."
- **成功**：显示期刊信息标签（蓝色、红色、黄色等）
- **失败**：显示"重试获取期刊信息"按钮（橙色）
- **无数据**：显示"无期刊信息"标签（灰色）

#### 重试功能
点击"重试获取期刊信息"按钮可以重新尝试获取期刊信息。

### 5. 数据流程图

```
文献数据 (CSV)
    ↓
检查 journal_name 字段
    ↓
    ├─ 有 → 直接使用
    ├─ 无 → 检查 source 字段
    │       ↓
    │       ├─ 有 → 使用 source
    │       └─ 无 → 检查 url 字段
    │               ↓
    │               ├─ DOI 链接 → CrossRef API → 期刊名称
    │               └─ 其他 → 失败
    ↓
调用 EasyScholar API
    ↓
解析响应数据
    ↓
显示期刊信息
```

### 6. 下一步改进

#### 短期改进
- [ ] 添加后端代理，解决 CORS 问题
- [ ] 缓存期刊信息，避免重复请求
- [ ] 支持更多期刊名称格式（缩写、全称、别名）

#### 长期改进
- [ ] 支持从 PubMed、IEEE 等数据库提取期刊信息
- [ ] 批量获取期刊信息（优化性能）
- [ ] 离线期刊数据库（减少 API 依赖）
- [ ] 用户自定义期刊信息

## 联系支持

如果以上步骤都无法解决问题，请提供以下信息：
1. 浏览器控制台的完整日志（包括所有 `[EasyScholar]` 开头的日志）
2. 一条示例文献数据的完整字段（`console.log` 输出）
3. API 响应的原始数据（如果有）
4. 错误截图

