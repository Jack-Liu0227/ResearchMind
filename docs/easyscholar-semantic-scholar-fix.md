# Semantic Scholar 期刊信息获取修复

## 问题原因

您的文献数据来自 **Semantic Scholar**，但之前的实现没有从 Semantic Scholar API 获取期刊名称（`venue` 字段），导致 CSV 文件中缺少 `journal_name` 字段，无法调用 EasyScholar API 获取期刊信息。

## 解决方案

我已经修复了以下问题：

### 1. 后端修复 ✅

#### 修改文件：`mcp_servers/paper_search/modules/search/semantic_scholar.py`

**修改内容**：
1. **添加 `venue` 和 `journal` 字段到 API 请求**（第 60 行）：
   ```python
   fields = "paperId,title,authors,abstract,url,publicationDate,citationCount,publicationTypes,externalIds,openAccessPdf,fieldsOfStudy,venue,journal"
   ```

2. **提取期刊名称并映射为 `journal_name`**（第 163-173 行）：
   ```python
   # 提取期刊/会议名称
   journal_name = ''
   venue = paper.get('venue', '')
   journal = paper.get('journal')
   
   if venue and isinstance(venue, str):
       journal_name = venue
   elif journal and isinstance(journal, dict):
       journal_name = journal.get('name', '')
   ```

3. **添加 `journal_name` 到返回数据**（第 189 行）：
   ```python
   normalized = {
       # ... 其他字段
       'journal_name': journal_name,
   }
   ```

#### 修改文件：`mcp_servers/paper_search/modules/paper_manager/export_tools.py`

**修改内容**：
1. **添加 `JournalName` 列到 CSV 导出**（第 610 行）：
   ```python
   row = {
       'ID': paper_id,
       'Topic': simplified_topic,
       'Title': title,
       'Authors': authors_str,
       'Abstract': abstract,
       'URL': download_url,
       'PDF_URL': pdf_url,
       'Published': published,
       'Source': paper.get('source', 'unknown'),
       'JournalName': journal_name,  # 🆕 期刊名称
       'Categories': categories_str,
       'DOI': doi,
       'CitationCount': citation_count,
       'FullText': full_text,
       'LocalFile': local_file,
   }
   ```

2. **添加 `JournalName` 字段映射**（第 135-137 行）：
   ```python
   elif key == 'JournalName':
       paper['journal_name'] = paper.pop('JournalName')
   ```

### 2. 前端改进 ✅

#### 修改文件：`ui/src/components/RightPanel.tsx`

**修改内容**：
- 过滤数据源名称，避免将 `semantic_scholar` 误认为期刊名称（第 1312-1325 行）

## 如何使用

### 方案 A：重新搜索文献（推荐）

**步骤**：
1. 在聊天界面中，重新执行之前的文献搜索命令
2. 例如：`请使用 Semantic Scholar 搜索关于 "Agentic AI Systems" 的文献`
3. 新搜索的文献将自动包含期刊名称
4. 期刊信息将自动显示在文献卡片上

**优点**：
- ✅ 自动获取最新的期刊信息
- ✅ 无需手动操作
- ✅ 数据完整且准确

### 方案 B：手动添加期刊名称到现有 CSV

如果您不想重新搜索，可以手动编辑 CSV 文件：

**步骤**：
1. 找到您的 CSV 文件（通常在 `sessions/<session_id>/<topic>/papers.csv`）
2. 在 Excel 或文本编辑器中打开
3. 在 `Source` 列后面添加一个新列 `JournalName`
4. 手动填写每篇文献的期刊名称（可以从文献的 URL 或标题中查找）
5. 保存文件
6. 刷新前端页面

**示例 CSV 结构**：
```csv
ID,Topic,Title,Authors,Abstract,URL,PDF_URL,Published,Source,JournalName,Categories,DOI,CitationCount
s2_abc123,Agentic AI,Practices for Governing Agentic AI Systems,Yonadav Shavit,...,https://...,,...,2024-01-01,semantic_scholar,Nature,AI; Machine Learning,10.1038/...,42
```

**缺点**：
- ⚠️ 需要手动查找期刊名称（耗时）
- ⚠️ 可能不准确
- ⚠️ 对于大量文献不现实

### 方案 C：使用 DOI 自动提取（部分文献）

如果您的文献有 DOI，前端会自动尝试从 CrossRef API 提取期刊名称。

**适用条件**：
- ✅ 文献有 `DOI` 字段
- ✅ DOI 有效且可以在 CrossRef 查询到

**自动流程**：
1. 前端检测到没有 `journal_name`
2. 检查是否有 `url` 字段且包含 DOI
3. 调用 CrossRef API 获取期刊名称
4. 调用 EasyScholar API 获取期刊信息

## 测试步骤

### 1. 重启后端服务

修改了后端代码后，需要重启 MCP 服务器：

```powershell
# 如果使用 uv 运行
cd mcp_servers/paper_search
uv run python server.py

# 或者重启整个应用
```

### 2. 重新搜索文献

在聊天界面中执行：
```
请使用 Semantic Scholar 搜索关于 "Agentic AI Systems" 的 5 篇文献
```

### 3. 检查 CSV 文件

查看生成的 CSV 文件，确认是否包含 `JournalName` 列：
```powershell
# 查看 CSV 文件的列名
Get-Content "sessions/<session_id>/<topic>/papers.csv" -First 1
```

应该看到类似这样的输出：
```
ID,Topic,Title,Authors,Abstract,URL,PDF_URL,Published,Source,JournalName,Categories,DOI,CitationCount,FullText,LocalFile
```

### 4. 检查前端显示

1. 打开浏览器控制台（F12）
2. 查看文献列表
3. 查找日志：
   ```
   🔍 [调试] 文献数据完整字段: { ..., journal_name: "Nature", ... }
   📚 [期刊信息] 期刊名称: Nature （来源: journal_name 字段）
   ```
4. 确认期刊信息标签是否显示

## 常见问题

### Q1: 重新搜索后仍然没有期刊信息

**可能原因**：
1. Semantic Scholar API 没有返回 `venue` 字段（某些文献可能没有期刊信息）
2. 后端服务没有重启
3. 前端缓存了旧数据

**解决方案**：
1. 检查后端日志，确认是否提取到 `journal_name`
2. 重启后端服务
3. 清除浏览器缓存或使用无痕模式

### Q2: 只有部分文献有期刊信息

**原因**：
- Semantic Scholar 数据库中，并非所有文献都有期刊信息
- 预印本（arXiv）、会议论文可能没有期刊名称

**解决方案**：
- 这是正常现象
- 对于没有期刊信息的文献，前端会显示"无期刊信息"标签

### Q3: 期刊名称不准确

**原因**：
- Semantic Scholar 的 `venue` 字段可能包含会议名称而非期刊名称
- 某些文献的元数据可能不完整

**解决方案**：
- 使用 DOI 提取（更准确）
- 手动修正 CSV 文件中的期刊名称

## 技术细节

### Semantic Scholar API 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `venue` | string | 期刊或会议名称（简单字符串） |
| `journal` | object | 期刊详细信息（包含 `name`、`pages`、`volume` 等） |

**示例响应**：
```json
{
  "paperId": "abc123",
  "title": "Example Paper",
  "venue": "Nature",
  "journal": {
    "name": "Nature",
    "pages": "1-10",
    "volume": "600"
  }
}
```

### 字段映射关系

| Semantic Scholar | CSV 列名 | 前端字段 | EasyScholar API |
|------------------|----------|----------|-----------------|
| `venue` 或 `journal.name` | `JournalName` | `journal_name` | `publicationName` |

## 相关文档

- 📖 [EasyScholar API 集成调试指南](./easyscholar-debugging.md)
- 📖 [EasyScholar 修复总结](./easyscholar-fix-summary.md)
- 📖 [Bug 修复报告](./bug-fixes-2024-11-20.md)
- 🔗 [Semantic Scholar API 文档](https://api.semanticscholar.org/api-docs/)

