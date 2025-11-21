# 前端期刊信息显示问题修复总结

## 📋 发现的问题

### 1. **RightPanel.tsx 中的 API 调用错误**
- **位置**：`ui/src/components/RightPanel.tsx` 第 1242 行
- **错误**：调用了不存在的 `/api/mcp/call_tool` 接口，并尝试使用 `get_paper_info` 工具
- **现象**：浏览器控制台显示 `POST http://localhost:50001/api/mcp/call_tool 404 (Not Found)`
- **原因**：后端的 `/api/mcp/call_tool` 接口只支持 `list_papers_from_csv` 和 `select_papers` 两个工具，不支持 `get_paper_info`

### 2. **easyScholarService.ts 中的 URL 路径重复**
- **位置**：`ui/src/services/easyScholarService.ts` 第 512 行和第 578 行（已在之前修复）
- **错误**：URL 中出现 `/api/api` 重复路径
- **现象**：浏览器控制台显示 `GET http://localhost:50001/api/api/journal/pii-to-doi?pii=... 404 (Not Found)`
- **原因**：`API_BASE_URL` 已经包含 `/api` 前缀，但代码中又添加了一次 `/api`
- **状态**：✅ 已修复

### 3. **RightPanel.tsx 中的语法错误**
- **位置**：`ui/src/components/RightPanel.tsx` 第 1240 行
- **错误**：对象字面量中重复的属性定义，缺少逗号
- **现象**：Vite 编译错误 `Unexpected token, expected ","`
- **原因**：在之前的编辑中，`setDetailedInfo` 对象的属性被重复添加了两次
- **状态**：✅ 已修复

## ✅ 修复方案

### 修复 1: 简化 `fetchDetails` 函数

**修改文件**：`ui/src/components/RightPanel.tsx`

**修改内容**：
- 移除对 `/api/mcp/call_tool` 的调用
- 直接使用 `paper` 对象中的数据填充 `detailedInfo`
- 简化错误处理逻辑
- 修复重复的对象属性定义

**修改前**（第 1220-1285 行）：
```typescript
// 获取详细信息（通过 MCP API）
const fetchDetails = async () => {
  if (detailedInfo) return

  // ... 省略部分代码 ...

  // 调用 MCP API 获取详细信息
  const response = await fetch(`${API_CONFIG.BASE_URL}/api/mcp/call_tool`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      server_name: 'paper_search',
      tool_name: 'get_paper_info',
      arguments: {
        paper_id: paperId,
        source: source
      }
    })
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const result = await response.json()
  // ... 处理结果 ...
}
```

**修改后**（第 1220-1257 行）：
```typescript
// 获取详细信息（直接使用 paper 对象中的数据）
const fetchDetails = async () => {
  if (detailedInfo) return

  console.log('📖 加载文献详细信息:', {
    paper_id: paper.paper_id || paper.id,
    source: paper.source,
    has_abstract: !!paper.abstract
  })

  // 直接使用 paper 对象中的数据，不调用 API
  setLoadingDetails(true)
  try {
    setDetailedInfo({
      fullAbstract: paper.abstract || '暂无摘要',
      authors: paper.authors || [],
      published: paper.published || paper.publication_date || '未知',
      categories: paper.categories || [],
      doi: paper.doi,
      citations: paper.citations
    })
    console.log('✅ 文献详细信息加载成功')
  } catch (error: any) {
    console.error('❌ 加载文献详细信息失败:', error)
    // 失败时也设置基本信息
    setDetailedInfo({
      fullAbstract: paper.abstract || '暂无摘要',
      authors: paper.authors || [],
      published: paper.published || paper.publication_date || '未知'
    })
  } finally {
    setLoadingDetails(false)
  }
}
```

### 修复 2: 移除重复的 `/api` 前缀（已在之前修复）

**修改文件**：`ui/src/services/easyScholarService.ts`

**修改位置 1**：第 512 行（PII 转 DOI 接口）
```typescript
// 修改前
const response = await fetch(`${API_BASE_URL}/api/journal/pii-to-doi?pii=${pii}`)

// 修改后
const response = await fetch(`${API_BASE_URL}/journal/pii-to-doi?pii=${pii}`)
```

**修改位置 2**：第 578 行（Springer 期刊信息接口）
```typescript
// 修改前
const response = await fetch(`${API_BASE_URL}/api/journal/springer-journal-info?journal_id=${journalId}`)

// 修改后
const response = await fetch(`${API_BASE_URL}/journal/springer-journal-info?journal_id=${journalId}`)
```

**状态**：✅ 已完成

## 🧪 测试步骤

### 1. 刷新前端页面
```bash
# 在浏览器中访问
http://localhost:50001
```

### 2. 加载 CSV 文件
```
session_data/papers/session_1763649897080_fszhlfz5/all_papers.csv
```

### 3. 测试 Semantic Scholar 来源文献
- 点击任意 `semantic_scholar` 来源的文献
- 观察浏览器控制台，应该**不再出现** `404 Not Found` 错误
- 验证文献详细信息（摘要、作者、发表日期）正确显示

### 4. 测试 Tavily 来源文献
- 点击 Tavily 来源的 ScienceDirect 文献
- 观察浏览器控制台，应该**不再出现** `/api/api` 路径错误
- 验证期刊信息（影响因子、JCR 分区、中科院分区）正确显示

## 📊 预期效果

### Semantic Scholar 来源
- ✅ 文献详细信息正确加载
- ✅ 不再出现 404 错误
- ✅ 期刊信息正确显示（如果有）

### Tavily 来源
- ✅ ScienceDirect 文献：PII → DOI → 期刊信息 → 显示分区
- ✅ Springer 期刊主页：期刊 ID → 期刊名称 → 显示分区
- ✅ arXiv 文献：正确识别为预印本，跳过期刊信息获取

## 🔍 验证清单

- [ ] 浏览器控制台不再出现 `404 Not Found` 错误
- [ ] 浏览器控制台不再出现 `/api/api` 路径错误
- [ ] Semantic Scholar 文献的详细信息正确显示
- [ ] Tavily 来源的期刊信息正确显示
- [ ] arXiv 文献正确显示"预印本"标识

## 📝 相关文件

- `ui/src/components/RightPanel.tsx` - 文献详情面板组件
- `ui/src/services/easyScholarService.ts` - 期刊信息服务
- `ui/src/constants/index.ts` - API 配置常量
- `services/journal_api.py` - 后端期刊信息 API

## 🎯 下一步

如果测试通过，可以考虑：
1. 添加更多期刊数据源的支持
2. 优化期刊信息缓存机制
3. 改进错误提示的用户体验

