# 文献文件保存路径修复

## 问题描述

用户报告文献相关文件（CSV、MD）保存位置不正确：

**错误的保存位置：**
- `session_data/papers/analysis_results_20251120_002108.csv` ❌
- `mcp_servers/papers/analysis_20251120_002108.md` ❌

**正确的保存位置：**
- `session_data/papers/session_1763568795798_mdiyameq/analysis_results_20251120_002108.csv` ✅
- `session_data/papers/session_1763568795798_mdiyameq/analysis_20251120_002108.md` ✅

## 根本原因

在 `mcp_servers/paper_search/modules/paper_manager/export_tools.py` 中，4 个保存函数的目录选择逻辑有问题：

```python
# ❌ 错误逻辑
if session_id and topic:
    save_dir = get_session_folder(session_id, topic)
elif output_dir:
    save_dir = output_dir
else:
    save_dir = PAPER_DIR  # 后备目录
```

**问题：** 当 `session_id` 存在但 `topic` 为 `None` 时，会跳过 `get_session_folder()`，直接使用后备目录 `PAPER_DIR`（即 `session_data/papers/`），导致文件保存在错误位置。

## 解决方案

修改 4 个保存函数的目录选择逻辑：

```python
# ✅ 正确逻辑
if session_id:
    # 即使 topic 为 None，也使用 session_id 获取会话文件夹
    save_dir = get_session_folder(session_id, topic)
elif output_dir:
    save_dir = output_dir
else:
    save_dir = PAPER_DIR  # 后备目录
```

## 修改的函数

### 1. `save_summary_to_file` (Line 260-273)
- **用途：** 保存批量分析的 Markdown 报告
- **调用者：** `batch_paper_analysis` 工具
- **文件名：** `analysis_{timestamp}.md`

### 2. `save_report_to_file` (Line 360-374)
- **用途：** 保存研究报告的 Markdown 内容
- **调用者：** `generate_research_report` 工具
- **文件名：** `report_{timestamp}.md`

### 3. `save_papers_to_csv` (Line 584-596)
- **用途：** 保存论文列表到 CSV
- **调用者：** `search_papers` 工具
- **文件名：** `all_papers.csv`（追加模式）或 `{prefix}_{timestamp}.csv`

### 4. `save_analysis_results_to_csv` (Line 808-820)
- **用途：** 保存分析结果到 CSV
- **调用者：**
  - `batch_paper_analysis` 工具 → `analysis_results_{timestamp}.csv`
  - `generate_research_report` 工具 → `report_papers_{timestamp}.csv`
- **文件名：** 根据 `file_prefix` 参数决定

## 文件结构

修复后，所有文献相关文件都保存在会话文件夹中：

```
session_data/
└── papers/
    └── session_1763568795798_mdiyameq/
        ├── session_metadata.json
        ├── all_papers.csv                          # 所有检索的论文
        ├── analysis_20251120_002108.md             # 批量分析报告（MD）
        ├── analysis_results_20251120_002108.csv    # 批量分析结果（CSV）
        ├── report_20251120_002108.md               # 研究报告（MD）
        └── report_papers_20251120_002108.csv       # 研究报告论文数据（CSV）
```

## 下载 URL 生成

`get_download_url()` 函数会自动提取相对路径：

```python
# 输入：D:/XJTU/.../session_data/papers/session_xxx/file.csv
# 输出：/api/download/papers/session_xxx/file.csv
```

前端通过 `/api/download/` 端点访问文件，不会出现 404 错误。

## 测试步骤

1. **重启后端服务**（必须）
2. **搜索文献：**
   - 执行 `search_papers` 工具
   - 验证 `all_papers.csv` 保存在 `session_data/papers/session_xxx/`
3. **批量分析：**
   - 执行 `batch_paper_analysis` 工具
   - 验证生成 2 个文件：
     - `analysis_{timestamp}.md` - Markdown 报告
     - `analysis_results_{timestamp}.csv` - 结构化数据
4. **生成报告：**
   - 执行 `generate_research_report` 工具
   - 验证生成 2 个文件：
     - `report_{timestamp}.md` - Markdown 报告
     - `report_papers_{timestamp}.csv` - 论文数据
5. **下载文件：**
   - 点击前端的下载链接
   - 验证所有文件都返回 200 OK（无 404 错误）
6. **验证文件结构：**
   - 检查 `session_data/papers/session_xxx/` 目录
   - 确认所有文件都在同一会话文件夹中

## 影响范围

- ✅ 所有新生成的文件都会保存在正确位置
- ⚠️ 旧文件（已保存在错误位置）不会自动迁移
- ✅ 前端下载链接会正确工作
- ✅ 会话隔离正常工作

## 注意事项

1. **必须重启后端服务**才能生效
2. 旧的错误位置文件可以手动删除或保留（不影响新功能）
3. `get_session_folder()` 会自动创建会话文件夹（如果不存在）
4. 所有文件都使用 UTF-8 编码保存

