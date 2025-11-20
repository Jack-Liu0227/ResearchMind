# 文献标题点击跳转修复

## 问题描述

**现象：** 文献卡片中的标题无法点击跳转到论文原文链接

**根本原因：** 后端返回的文献数据中缺少 `url` 字段

## 问题分析

### 1. 前端实现正确

前端代码已经正确实现了标题点击功能：

```typescript
// ui/src/components/RightPanel.tsx
{paper.url ? (
  <a
    href={paper.url}
    target="_blank"
    rel="noopener noreferrer"
    className="... hover:text-blue-600 hover:underline ..."
  >
    {paper.title}
  </a>
) : (
  <h4>{paper.title}</h4>
)}
```

### 2. 后端缺少 url 字段

**问题 1：HTTP Server 默认字段列表缺少 url**

```python
# services/http_server.py (修复前)
if fields is None:
    fields = ["paper_id", "title", "authors", "published", "source", "score", "abstract"]
    # ❌ 缺少 "url" 字段
```

**问题 2：MCP Server 默认字段列表缺少 url**

```python
# mcp_servers/paper_search/server.py (修复前)
if fields is None:
    fields = ["paper_id", "title", "authors", "published", "source", "score", "abstract"]
    # ❌ 缺少 "url" 字段
```

## 解决方案

### 1. 修改 HTTP Server

```python
# services/http_server.py
# Default fields (包含 url 字段用于前端点击跳转)
if fields is None:
    fields = ["paper_id", "title", "authors", "published", "source", "score", "abstract", "url"]
    # ✅ 添加 "url" 字段
```

### 2. 修改 MCP Server

```python
# mcp_servers/paper_search/server.py
# 默认返回字段（包含 url 字段用于前端点击跳转）
if fields is None:
    fields = ["paper_id", "title", "authors", "published", "source", "score", "abstract", "url"]
    # ✅ 添加 "url" 字段
```

### 3. 前端添加调试和事件处理

```typescript
// ui/src/components/RightPanel.tsx

// 1. 添加点击事件处理（阻止冒泡）
<a
  href={paper.url}
  onClick={(e) => {
    e.stopPropagation() // 阻止事件冒泡到父元素
    console.log('📖 打开文献链接:', paper.url)
  }}
  ...
>
  {paper.title}
</a>

// 2. 添加加载调试日志
if (papers.length > 0) {
  console.log('📚 加载文献示例:', {
    title: papers[0].title,
    url: papers[0].url,
    hasUrl: !!papers[0].url,
    allFields: Object.keys(papers[0])
  })
}
```

## 修改的文件

1. ✅ `services/http_server.py` - 添加 `url` 到默认字段列表
2. ✅ `mcp_servers/paper_search/server.py` - 添加 `url` 到默认字段列表，更新文档
3. ✅ `ui/src/components/RightPanel.tsx` - 添加点击事件处理和调试日志

## 测试步骤

### 1. 重启后端服务

```bash
# 重启后端服务以加载新的字段配置
# 如果使用 systemd 或其他进程管理器，请重启相应的服务
```

### 2. 测试文献加载

1. 搜索文献
2. 切换到"文献"标签页
3. 打开浏览器控制台（F12）
4. 查看调试日志，确认 `url` 字段存在：

```
📚 加载文献示例: {
  title: "...",
  url: "https://arxiv.org/abs/...",
  hasUrl: true,
  allFields: ["paper_id", "title", "authors", "published", "source", "score", "abstract", "url"]
}
```

### 3. 测试标题点击

1. 点击文献标题
2. 验证是否在新标签页打开论文原文链接
3. 查看控制台日志：`📖 打开文献链接: https://...`

### 4. 测试外部链接图标

1. 点击标题右侧的外部链接图标（ExternalLink）
2. 验证是否在新标签页打开论文原文链接
3. 查看控制台日志：`🔗 打开文献链接（图标）: https://...`

## 数据流

```
1. 用户搜索文献 → search_papers 工具执行
2. 后端保存文献到 CSV（包含 url 字段）
3. 前端调用 /api/mcp/call_tool (list_papers_from_csv)
4. HTTP Server 读取 CSV，返回包含 url 的文献列表
5. 前端渲染文献卡片
6. 用户点击标题 → 打开 paper.url ✅
```

## 关键点

1. **字段一致性**：HTTP Server 和 MCP Server 的默认字段列表保持一致
2. **事件冒泡**：使用 `e.stopPropagation()` 阻止点击事件冒泡到父元素
3. **调试日志**：添加日志帮助排查问题
4. **用户体验**：
   - 标题可点击（悬停显示下划线和蓝色文字）
   - 外部链接图标可点击
   - 如果 `url` 不存在，标题显示为普通文本

## 注意事项

1. **需要重启后端**：修改了 Python 代码，需要重启后端服务
2. **CSV 文件格式**：确保 CSV 文件中包含 `url` 列
3. **数据来源**：不同来源（arXiv、Semantic Scholar 等）的 URL 格式可能不同
4. **错误处理**：如果 `url` 为空或无效，标题显示为普通文本（不可点击）

## 与其他功能的关系

- ✅ 文献选择功能 - 不受影响
- ✅ 批量分析功能 - 不受影响
- ✅ 生成报告功能 - 不受影响
- ✅ 文献持久化 - 不受影响
- ✅ 展开详情功能 - 可以通过 URL 获取更多信息

