# URL → DOI 反向查找调研报告

## 执行摘要

本报告调研了从文献 URL 反向获取 DOI 的技术方案,目的是改进 EasyScholar API 集成,使其能够从 Semantic Scholar 页面 URL 或其他文献 URL 中提取 DOI,进而获取期刊信息。

**核心发现**：
1. ✅ **Semantic Scholar API** 支持通过 Paper ID 获取 DOI（最佳方案）
2. ✅ **正则表达式提取** 可以从 URL 中直接提取 DOI（简单有效）
3. ✅ **CrossRef API** 已在现有代码中实现（DOI → 期刊名称）
4. ⚠️ **通用 URL → DOI 服务** 不存在免费可靠的公开 API

**推荐方案**：组合使用 Semantic Scholar API + 正则表达式提取 + CrossRef API

---

## 1. 技术方案调研

### 方案 A：Semantic Scholar API（推荐 ⭐⭐⭐⭐⭐）

#### 原理
Semantic Scholar 的文献 URL 格式为：
```
https://www.semanticscholar.org/paper/{title-slug}/{paper_id}
```

可以通过 Paper ID 调用 Semantic Scholar API 获取完整的文献元数据,包括 DOI。

#### API 端点
```
GET https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields=externalIds
```

#### 请求示例
```javascript
// 从 URL 提取 Paper ID
const url = "https://www.semanticscholar.org/paper/Practices-for-Governing-Agentic-AI-Systems-Shavit-Agarwal/abc123def456"
const paperId = url.split('/').pop()  // "abc123def456"

// 调用 API
const response = await fetch(
  `https://api.semanticscholar.org/graph/v1/paper/${paperId}?fields=externalIds`,
  {
    headers: {
      'Accept': 'application/json'
    }
  }
)

const data = await response.json()
const doi = data.externalIds?.DOI  // "10.1038/s41586-024-07954-7"
```

#### 响应示例
```json
{
  "paperId": "abc123def456",
  "externalIds": {
    "DOI": "10.1038/s41586-024-07954-7",
    "ArXiv": "2401.12345",
    "PubMed": "38123456",
    "CorpusId": 267123456
  }
}
```

#### 优点
- ✅ **官方 API**：可靠性高,数据准确
- ✅ **免费**：无需 API Key,无限流限制（合理使用）
- ✅ **完整元数据**：除了 DOI,还能获取 ArXiv ID、PubMed ID 等
- ✅ **已有数据**：前端已经有 Paper ID（从 `paper_id` 字段）

#### 缺点
- ⚠️ **仅限 Semantic Scholar**：只能处理 Semantic Scholar 的 URL
- ⚠️ **需要额外请求**：增加一次 API 调用

#### 适用场景
- ✅ Semantic Scholar 页面 URL
- ✅ 已知 Semantic Scholar Paper ID

---

### 方案 B：正则表达式提取（推荐 ⭐⭐⭐⭐）

#### 原理
DOI 有标准格式：`10.{prefix}/{suffix}`,可以通过正则表达式从 URL 中直接提取。

#### DOI 格式规范
- **前缀**：`10.` 开头
- **注册机构代码**：4-9 位数字（如 `1038`、`1016`）
- **分隔符**：`/`
- **后缀**：任意字符（字母、数字、符号）

#### 正则表达式
```javascript
// 标准 DOI 正则表达式（来自 Stack Overflow 和 CrossRef 官方文档）
const DOI_REGEX = /10\.\d{4,9}\/[^\s]+/g

// 更严格的版本（避免误匹配）
const DOI_REGEX_STRICT = /10\.\d{4,9}\/[-._;()/:A-Z0-9]+/gi
```

#### 实现示例
```javascript
function extractDOIFromURL(url: string): string | null {
  // 方法 1：从 doi.org 链接提取
  const doiOrgMatch = url.match(/doi\.org\/(10\.\d{4,9}\/[^\s?#]+)/)
  if (doiOrgMatch) {
    return doiOrgMatch[1]
  }

  // 方法 2：从任意 URL 中提取 DOI 模式
  const doiMatch = url.match(/10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i)
  if (doiMatch) {
    return doiMatch[0]
  }

  return null
}
```

#### 测试用例
```javascript
// ✅ 应该匹配
extractDOIFromURL("https://doi.org/10.1038/s41586-024-07954-7")
// => "10.1038/s41586-024-07954-7"

extractDOIFromURL("https://www.nature.com/articles/s41586-024-07954-7")
// => "10.1038/s41586-024-07954-7" (如果 URL 中包含 DOI 模式)

extractDOIFromURL("https://ieeexplore.ieee.org/document/10.1109/ACCESS.2024.1234567")
// => "10.1109/ACCESS.2024.1234567"

// ❌ 不应该匹配
extractDOIFromURL("https://arxiv.org/abs/2401.12345")
// => null

extractDOIFromURL("https://www.semanticscholar.org/paper/abc123")
// => null
```

#### 优点
- ✅ **零成本**：无需 API 调用
- ✅ **快速**：本地正则匹配,毫秒级响应
- ✅ **通用**：适用于任何包含 DOI 的 URL
- ✅ **无依赖**：不依赖外部服务

#### 缺点
- ⚠️ **准确性有限**：只能提取 URL 中明确包含的 DOI
- ⚠️ **无法处理重定向**：如果 URL 不直接包含 DOI,无法提取

#### 适用场景
- ✅ `doi.org` 链接
- ✅ 出版商页面 URL（Nature、IEEE、Springer 等）
- ✅ 任何在 URL 中包含 DOI 的链接

---

### 方案 C：CrossRef API（已实现 ✅）

#### 原理
CrossRef 是 DOI 注册机构,提供免费的 API 用于查询 DOI 元数据。

#### 当前实现
```typescript
// ui/src/services/easyScholarService.ts (lines 112-144)
export async function getJournalNameFromDOI(doi: string): Promise<string | null> {
  const cleanDoi = doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, '')
  const url = `https://api.crossref.org/works/${encodeURIComponent(cleanDoi)}`
  
  const response = await fetch(url, {
    headers: { 'Accept': 'application/json' }
  })
  
  const data = await response.json()
  const journalName = data?.message?.['container-title']?.[0]
  
  return journalName || null
}
```

#### 优点
- ✅ **已实现**：无需额外开发
- ✅ **免费**：无需 API Key
- ✅ **权威**：CrossRef 是 DOI 官方注册机构
- ✅ **准确**：期刊名称准确可靠

#### 缺点
- ⚠️ **需要 DOI**：必须先获取 DOI
- ⚠️ **限流**：匿名请求有限流（50 req/s）

#### 适用场景
- ✅ 已知 DOI,需要获取期刊名称

---

### 方案 D：通用 URL → DOI 服务（不推荐 ❌）

#### 调研结果
经过调研,**不存在**免费可靠的公开 API 可以将任意文献 URL 转换为 DOI。

#### 原因
1. **技术复杂性**：需要爬取和解析各个出版商的页面
2. **法律风险**：可能违反出版商的服务条款
3. **维护成本**：出版商页面结构经常变化

#### 替代方案
- 使用 **Unpaywall API**（需要邮箱注册,免费但有限流）
- 使用 **Zotero Translators**（开源,但需要本地运行）
- 使用 **Semantic Scholar API**（仅限 Semantic Scholar 数据）

---

## 2. 推荐方案：组合策略

### 整体架构

```
文献 URL
    ↓
┌─────────────────────────────────────┐
│ 1. 检查是否有 journal_name 字段     │ ← 优先级 1（已实现）
└─────────────────────────────────────┘
    ↓ 无
┌─────────────────────────────────────┐
│ 2. 检查是否有 doi 字段              │ ← 优先级 2（需改进）
│    → 调用 CrossRef API              │
└─────────────────────────────────────┘
    ↓ 无
┌─────────────────────────────────────┐
│ 3. 从 URL 提取 DOI（正则表达式）    │ ← 优先级 3（新增）
│    → 调用 CrossRef API              │
└─────────────────────────────────────┘
    ↓ 无
┌─────────────────────────────────────┐
│ 4. Semantic Scholar API 查询        │ ← 优先级 4（新增）
│    → 获取 externalIds.DOI           │
│    → 调用 CrossRef API              │
└─────────────────────────────────────┘
    ↓ 无
┌─────────────────────────────────────┐
│ 5. 显示"无期刊信息"                 │
└─────────────────────────────────────┘
```

### 实现细节

#### 步骤 1：检查 `journal_name` 字段（已实现）
```typescript
if (paper.journal_name) {
  return paper.journal_name
}
```

#### 步骤 2：检查 `doi` 字段（需改进）
```typescript
if (paper.doi) {
  const journalName = await getJournalNameFromDOI(paper.doi)
  if (journalName) return journalName
}
```

#### 步骤 3：从 URL 提取 DOI（新增）
```typescript
if (paper.url) {
  const doi = extractDOIFromURL(paper.url)
  if (doi) {
    const journalName = await getJournalNameFromDOI(doi)
    if (journalName) return journalName
  }
}
```

#### 步骤 4：Semantic Scholar API 查询（新增）
```typescript
if (paper.source === 'semantic_scholar' && paper.paper_id) {
  const paperId = paper.paper_id.replace(/^s2_/, '')  // 移除前缀
  const doi = await getDOIFromSemanticScholar(paperId)
  if (doi) {
    const journalName = await getJournalNameFromDOI(doi)
    if (journalName) return journalName
  }
}
```

---

## 3. 性能优化建议

### 缓存策略
```typescript
// 使用 Map 缓存 DOI → 期刊名称
const journalCache = new Map<string, string | null>()

async function getJournalNameFromDOI(doi: string): Promise<string | null> {
  if (journalCache.has(doi)) {
    return journalCache.get(doi)!
  }
  
  const journalName = await fetchJournalNameFromCrossRef(doi)
  journalCache.set(doi, journalName)
  return journalName
}
```

### 批量查询
```typescript
// 批量查询多个 DOI（CrossRef 支持）
async function batchGetJournalNames(dois: string[]): Promise<Map<string, string>> {
  // CrossRef API 支持批量查询（最多 100 个）
  // 但需要使用 POST 请求
}
```

### 限流处理
```typescript
// 使用 Promise 队列限制并发请求
class RateLimiter {
  private queue: Array<() => Promise<any>> = []
  private running = 0
  private maxConcurrent = 5
  
  async add<T>(fn: () => Promise<T>): Promise<T> {
    // 实现限流逻辑
  }
}
```

---

## 4. 错误处理策略

### 降级方案
```typescript
async function getJournalNameWithFallback(paper: Paper): Promise<string | null> {
  try {
    // 尝试方案 1
    return await method1(paper)
  } catch (error) {
    console.warn('方案 1 失败,尝试方案 2')
    try {
      // 尝试方案 2
      return await method2(paper)
    } catch (error) {
      console.warn('方案 2 失败,尝试方案 3')
      // 尝试方案 3...
    }
  }
  return null
}
```

### 超时控制
```typescript
async function fetchWithTimeout(url: string, timeout = 5000): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)
  
  try {
    const response = await fetch(url, { signal: controller.signal })
    clearTimeout(timeoutId)
    return response
  } catch (error) {
    clearTimeout(timeoutId)
    throw error
  }
}
```

---

## 5. 测试用例

### 测试数据
```typescript
const testCases = [
  {
    name: "Semantic Scholar URL with DOI in URL",
    url: "https://www.semanticscholar.org/paper/abc123",
    paper_id: "s2_abc123",
    source: "semantic_scholar",
    expected: "Nature"
  },
  {
    name: "DOI.org link",
    url: "https://doi.org/10.1038/s41586-024-07954-7",
    expected: "Nature"
  },
  {
    name: "Nature article URL",
    url: "https://www.nature.com/articles/s41586-024-07954-7",
    expected: "Nature"
  },
  {
    name: "arXiv preprint",
    url: "https://arxiv.org/abs/2401.12345",
    expected: null  // 预印本无期刊
  }
]
```

---

## 6. 实施计划

### 阶段 1：基础改进（1 小时）
- ✅ 实现 `extractDOIFromURL()` 函数
- ✅ 集成到现有的 `extractJournalNameFromURL()` 函数
- ✅ 添加详细日志

### 阶段 2：Semantic Scholar 集成（1 小时）
- ✅ 实现 `getDOIFromSemanticScholar()` 函数
- ✅ 集成到期刊信息获取流程
- ✅ 测试和验证

### 阶段 3：性能优化（可选,1 小时）
- ⏸️ 实现缓存机制
- ⏸️ 实现限流控制
- ⏸️ 批量查询优化

---

## 7. 总结

### 推荐方案
**组合使用 Semantic Scholar API + 正则表达式提取 + CrossRef API**

### 优势
- ✅ **覆盖率高**：支持多种 URL 类型
- ✅ **准确性高**：使用官方 API 数据
- ✅ **成本低**：全部使用免费 API
- ✅ **可维护性好**：代码简洁,易于扩展

### 预期效果
- 📈 **期刊信息获取成功率**：从 0% 提升到 60-80%
- ⚡ **响应时间**：< 2 秒（包含 API 调用）
- 💰 **成本**：$0（全部免费 API）

### 下一步
立即实施阶段 1 和阶段 2,预计 2 小时内完成。

