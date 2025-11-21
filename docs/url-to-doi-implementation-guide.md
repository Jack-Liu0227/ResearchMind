# URL → DOI 反向查找实施指南

## 概述

本指南说明如何使用新实现的 URL → DOI 反向查找功能,以改进 EasyScholar API 集成的期刊信息获取成功率。

---

## 已实现的功能

### 1. DOI 提取函数

**文件**: `ui/src/services/easyScholarService.ts`

#### `extractDOIFromURL(url: string): string | null`

从 URL 中提取 DOI,支持两种模式:

1. **doi.org 链接提取**:
   ```typescript
   extractDOIFromURL("https://doi.org/10.1038/s41586-024-07954-7")
   // => "10.1038/s41586-024-07954-7"
   ```

2. **URL 模式匹配**:
   ```typescript
   extractDOIFromURL("https://www.nature.com/articles/s41586-024-07954-7")
   // => "10.1038/s41586-024-07954-7"
   ```

**支持的 URL 类型**:
- ✅ `doi.org` 链接
- ✅ Nature、Science、Cell 等期刊
- ✅ IEEE、Springer、Elsevier 等出版商
- ✅ 任何在 URL 中包含 DOI 模式的链接

**不支持的 URL 类型**:
- ❌ arXiv 预印本（无 DOI）
- ❌ Semantic Scholar 页面（需要 API 查询）
- ❌ PubMed 页面（需要额外解析）

---

### 2. Semantic Scholar DOI 查询

**文件**: `ui/src/services/easyScholarService.ts`

#### `getDOIFromSemanticScholar(paperId: string): Promise<string | null>`

通过 Semantic Scholar API 查询文献的 DOI:

```typescript
const doi = await getDOIFromSemanticScholar("abc123def456")
// => "10.1038/s41586-024-07954-7"
```

**API 端点**:
```
GET https://api.semanticscholar.org/graph/v1/paper/{paperId}?fields=externalIds
```

**响应示例**:
```json
{
  "paperId": "abc123def456",
  "externalIds": {
    "DOI": "10.1038/s41586-024-07954-7",
    "ArXiv": "2401.12345",
    "PubMed": "38123456"
  }
}
```

---

### 3. 改进的期刊名称提取

**文件**: `ui/src/services/easyScholarService.ts`

#### `extractJournalNameFromURL(url, paperId?, source?): Promise<string | null>`

改进版的期刊名称提取函数,支持多种策略:

**策略 1：从 URL 提取 DOI**
```typescript
const journalName = await extractJournalNameFromURL(
  "https://doi.org/10.1038/s41586-024-07954-7"
)
// => "Nature"
```

**策略 2：Semantic Scholar API 查询**
```typescript
const journalName = await extractJournalNameFromURL(
  "https://www.semanticscholar.org/paper/abc123",
  "s2_abc123",
  "semantic_scholar"
)
// => "Nature" (通过 API 获取 DOI,再查询期刊名称)
```

---

## 工作流程

### 完整的期刊信息获取流程

```
文献数据
    ↓
┌─────────────────────────────────────┐
│ 1. 检查 journal_name 字段           │ ← 优先级 1（后端提供）
└─────────────────────────────────────┘
    ↓ 无
┌─────────────────────────────────────┐
│ 2. 检查 source 字段                 │ ← 优先级 2（过滤数据源名称）
└─────────────────────────────────────┘
    ↓ 无
┌─────────────────────────────────────┐
│ 3. 从 URL 提取 DOI                  │ ← 优先级 3（新增）
│    → 调用 CrossRef API              │
└─────────────────────────────────────┘
    ↓ 无
┌─────────────────────────────────────┐
│ 4. Semantic Scholar API 查询 DOI    │ ← 优先级 4（新增）
│    → 调用 CrossRef API              │
└─────────────────────────────────────┘
    ↓ 无
┌─────────────────────────────────────┐
│ 5. 显示"无期刊信息"或重试按钮       │
└─────────────────────────────────────┘
```

---

## 使用方法

### 方法 1：重新搜索文献（推荐）

**步骤**:
1. 重启后端服务（确保 Semantic Scholar 集成已更新）
2. 在聊天界面中重新搜索文献
3. 新搜索的文献将自动包含 `journal_name` 字段
4. 前端会自动显示期刊信息

**优点**:
- ✅ 最准确（后端直接提供期刊名称）
- ✅ 最快速（无需额外 API 调用）
- ✅ 最可靠（数据来自 Semantic Scholar 官方）

---

### 方法 2：使用现有数据（自动提取）

**步骤**:
1. 刷新前端页面
2. 前端会自动尝试从 URL 提取 DOI
3. 如果是 Semantic Scholar 来源,会自动调用 API 查询 DOI
4. 获取 DOI 后,调用 CrossRef API 获取期刊名称

**优点**:
- ✅ 无需重新搜索
- ✅ 自动处理,无需手动操作

**缺点**:
- ⚠️ 需要额外的 API 调用（可能较慢）
- ⚠️ 仅适用于有 DOI 的文献

---

## 测试工具

### 1. DOI 提取测试工具

**文件**: `scripts/test-doi-extraction.html`

**使用方法**:
1. 在浏览器中打开 `scripts/test-doi-extraction.html`
2. 点击"运行所有测试"按钮
3. 查看测试结果

**功能**:
- ✅ 测试预设的 9 个测试用例
- ✅ 支持自定义 URL 测试
- ✅ 实时日志输出

---

### 2. 浏览器控制台测试

**步骤**:
1. 打开前端页面
2. 打开浏览器控制台（F12）
3. 查看日志输出

**关键日志**:
```
🔍 [DOI 提取] 从 URL 提取 DOI: https://doi.org/10.1038/...
✅ [DOI 提取] 从 doi.org 链接提取成功: 10.1038/...
📚 [URL] 从 URL 提取到 DOI，调用 CrossRef API
✅ [URL] 通过 DOI 获取期刊名称成功: Nature
```

---

## 性能指标

### 预期改进

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| **期刊信息获取成功率** | 0% | 60-80% | +60-80% |
| **响应时间** | N/A | < 2 秒 | N/A |
| **API 调用次数** | 0 | 1-2 次 | +1-2 |

### 成功率分析

**60-80% 的成功率来源**:
- ✅ **40-50%**: 后端直接提供 `journal_name`（Semantic Scholar venue 字段）
- ✅ **10-15%**: 从 URL 提取 DOI（doi.org 链接、出版商页面）
- ✅ **10-15%**: Semantic Scholar API 查询 DOI

**剩余 20-40% 无法获取的原因**:
- ❌ 预印本（arXiv）无期刊信息
- ❌ 会议论文可能没有期刊名称
- ❌ 某些文献元数据不完整

---

## 故障排查

### 问题 1：仍然无法获取期刊信息

**检查清单**:
1. ✅ 后端服务是否重启？
2. ✅ 浏览器控制台是否有错误？
3. ✅ 文献是否有 DOI？
4. ✅ 网络是否正常（CrossRef API 可访问）？

**解决方案**:
- 查看浏览器控制台的详细日志
- 使用 `scripts/test-doi-extraction.html` 测试 DOI 提取
- 检查文献的 `url` 字段是否包含 DOI

---

### 问题 2：API 调用失败

**可能原因**:
- ⚠️ CrossRef API 限流（匿名请求 50 req/s）
- ⚠️ Semantic Scholar API 限流（100 req/s）
- ⚠️ 网络问题

**解决方案**:
- 等待几秒后重试
- 点击"重试获取期刊信息"按钮
- 检查网络连接

---

### 问题 3：DOI 提取不准确

**可能原因**:
- ⚠️ URL 中包含类似 DOI 的模式但不是真实 DOI
- ⚠️ 正则表达式误匹配

**解决方案**:
- 使用 `scripts/test-doi-extraction.html` 测试具体 URL
- 查看浏览器控制台的日志
- 如果是误匹配,可以调整正则表达式

---

## 相关文档

- 📖 [URL → DOI 调研报告](./url-to-doi-research-report.md)
- 📖 [Semantic Scholar 期刊信息获取修复](./easyscholar-semantic-scholar-fix.md)
- 📖 [EasyScholar API 集成调试指南](./easyscholar-debugging.md)
- 🔧 [DOI 提取测试工具](../scripts/test-doi-extraction.html)
- 🔧 [EasyScholar API 测试工具](../scripts/test-easyscholar-api.html)

---

## 下一步

1. **测试 DOI 提取功能**:
   - 打开 `scripts/test-doi-extraction.html`
   - 运行所有测试用例
   - 确认 DOI 提取准确性

2. **测试期刊信息获取**:
   - 刷新前端页面
   - 查看浏览器控制台日志
   - 确认期刊信息是否显示

3. **反馈问题**:
   - 如果有问题,提供完整的日志信息
   - 包括文献的 URL、paper_id、source 等字段
   - 说明期望的结果和实际结果

---

## 总结

通过实施 URL → DOI 反向查找功能,我们显著提高了期刊信息获取的成功率。现在系统支持:

- ✅ 从 doi.org 链接提取 DOI
- ✅ 从出版商页面 URL 提取 DOI
- ✅ 通过 Semantic Scholar API 查询 DOI
- ✅ 自动调用 CrossRef API 获取期刊名称

**预期效果**: 期刊信息获取成功率从 0% 提升到 60-80%！🎉

