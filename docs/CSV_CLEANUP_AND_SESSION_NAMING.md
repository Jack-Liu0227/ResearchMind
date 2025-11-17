# CSV 数据清理与会话命名规范

## 概述

本文档说明了 MCP Paper Search Server 的两个重要功能：
1. **CSV 数据清理**：自动清理 CSV 文件中的无效数据行
2. **统一会话命名**：使用统一的 `session_{timestamp}_{random_id}` 格式

---

## 1. CSV 数据清理

### 功能说明

CSV 数据清理功能可以自动识别并移除以下类型的无效数据行：

- **ID 包含 "unknown"**：如 `unknown_unknown`、`unknown_123` 等
- **Title 为 "Unknown Title" 且 Abstract 为空**：通常是解析失败的结果
- **Source 为 "unknown" 且其他关键字段为空**：数据源错误
- **所有关键字段都为空**：完全无效的行

### 自动清理机制 ⭐

**重要更新**：CSV 清理功能已集成到 `save_papers_to_csv()` 函数中，**每次保存时自动执行清理**。

- ✅ **保存前自动清理**：在保存新数据前，自动移除无效行
- ✅ **追加模式自动清理**：在合并现有数据后，自动清理所有无效行
- ✅ **无需手动调用**：`search_papers()` 等函数保存 CSV 时会自动清理
- ✅ **日志记录**：清理操作会记录在日志中，方便追踪

**示例日志输出**：
```
2025-11-16 23:56:46 [info] 清理前共 5 行数据
2025-11-16 23:56:46 [info] 清理了 2 个无效行
2025-11-16 23:56:46 [info] 成功保存CSV到文件: .../all_papers.csv
```

### 手动清理方法

#### 方法 1: 通过 MCP 工具调用

```python
# 清理指定会话的 CSV 文件
result = await clean_csv_data(
    session_id="session_1763305049955_zs3m2y8m",
    backup=True,      # 是否备份原文件
    dry_run=False     # False=实际清理，True=只检查不修改
)

# 清理指定的 CSV 文件
result = await clean_csv_data(
    csv_path="session_data/papers/session_xxx/all_papers.csv",
    backup=True,
    dry_run=False
)

# 清理所有会话的 CSV 文件
result = await clean_csv_data(
    backup=True,
    dry_run=False
)
```

#### 方法 2: 直接调用函数

```python
from mcp_servers.paper_search.modules.paper_manager.export_tools import (
    clean_csv_file,
    clean_all_csv_files
)

# 清理单个文件
result = clean_csv_file(
    csv_path="session_data/papers/session_xxx/all_papers.csv",
    backup=True,
    dry_run=False
)

# 批量清理所有文件
result = clean_all_csv_files(
    session_dir=None,  # None=清理所有会话，或指定会话目录
    backup=True,
    dry_run=False
)
```

### 返回结果

```python
{
    'status': 'success',
    'message': '清理完成',
    'original_count': 100,      # 原始行数
    'valid_count': 95,          # 有效行数
    'invalid_count': 5,         # 无效行数
    'invalid_rows_sample': [...],  # 无效行示例（最多10个）
    'backup_path': '...'        # 备份文件路径
}
```

### 备份机制

- 清理前会自动创建 `.backup` 文件（如 `all_papers.csv.backup`）
- 可以通过 `backup=False` 禁用备份
- 建议首次使用时启用 `dry_run=True` 预览结果

---

## 2. 统一会话命名规范

### 命名格式

所有会话文件夹统一使用以下格式：

```
session_{timestamp}_{random_id}
```

**示例**：
- `session_1763305049955_zs3m2y8m`
- `session_1763307504373_bh95f9fe`

**格式说明**：
- `timestamp`：13位毫秒级时间戳
- `random_id`：8位随机字符串（小写字母+数字）

### 会话元数据 ⭐

**重要更新**：会话元数据创建已集成到 `storage_manager.py` 和 `session_folder_manager.py` 中，**所有会话（搜索、上传、测试）都会自动创建元数据文件**。

每个会话文件夹都包含 `session_metadata.json` 文件，记录以下信息：

```json
{
  "session_id": "session_1763305049955_zs3m2y8m",
  "topic": "machine learning",
  "session_type": "search",
  "created_by": "system",
  "created_at": "2025-11-16T23:38:24.373000",
  "folder_path": "D:\\...\\session_data\\papers\\session_1763305049955_zs3m2y8m",
  "folder_name": "session_1763305049955_zs3m2y8m"
}
```

**字段说明**：
- `session_id`：会话唯一标识符
- `topic`：会话主题（搜索关键词或上传文件描述）
- `session_type`：会话类型
  - `search`：关键词搜索创建
  - `upload`：文件上传创建
  - `simulation`：模拟计算创建
  - `test`：测试创建
- `created_by`：创建方式
  - `system`：系统自动创建（如搜索）
  - `user`：用户手动创建（如上传）
  - `api`：API 调用创建
- `created_at`：创建时间（ISO 8601 格式）
- `folder_path`：文件夹完整路径
- `folder_name`：文件夹名称

### 自动创建机制

**搜索操作**（`search_papers()`）：
- 在 `server.py` 中生成 session_id
- 调用 `session_folder_manager.get_session_folder()` 创建会话
- 自动设置 `session_type="search"`, `created_by="system"`

**上传操作**（文件上传）：
- 在 `agent_coordinator.py` 中生成 session_id
- 调用 `storage_manager.get_session_storage_path()` 创建会话
- 自动设置 `session_type="upload"`, `created_by="user"`

**元数据保护**：
- 如果元数据文件已存在，不会被覆盖
- 确保会话信息的一致性和可追溯性

### 兼容性

- **搜索操作**：自动生成 `session_{timestamp}_{id}` 格式
- **上传操作**：自动生成 `session_{timestamp}_{id}` 格式
- **已有会话**：如果 session_id 已经是正确格式，直接使用

### 代码示例

```python
from mcp_servers.paper_search.modules.shared.session_folder_manager import get_session_folder

# 创建搜索会话
session_folder = get_session_folder(
    session_id="my_session_id",  # 可选，不提供则自动生成
    topic="machine learning",
    session_type="search",
    created_by="user"
)

# 创建上传会话
session_folder = get_session_folder(
    session_id="my_upload_session",
    topic="uploaded papers",
    session_type="upload",
    created_by="api"
)
```

---

## 3. 最佳实践

### CSV 清理

1. **定期清理**：建议在批量导入数据后运行清理
2. **先预览后清理**：首次使用时设置 `dry_run=True`
3. **保留备份**：重要数据清理时保持 `backup=True`

### 会话管理

1. **使用统一格式**：所有新会话都使用 `session_{timestamp}_{id}` 格式
2. **记录元数据**：在 `session_metadata.json` 中记录会话来源和用途
3. **避免手动命名**：让系统自动生成 session_id，确保唯一性

---

## 4. 故障排除

### CSV 清理失败

**问题**：清理时报错 "Permission denied"
**解决**：确保 CSV 文件未被其他程序打开

**问题**：备份文件已存在
**解决**：删除旧的 `.backup` 文件或使用 `backup=False`

### 会话命名冲突

**问题**：session_id 已存在
**解决**：系统会自动使用已有文件夹，不会创建重复

**问题**：文件夹名称与 session_id 不一致
**解决**：检查 `session_metadata.json` 中的映射关系

---

## 5. 更新日志

### 2025-11-16
- ✅ 实现 CSV 数据清理功能
- ✅ 统一会话命名为 `session_{timestamp}_{id}` 格式
- ✅ 在元数据中记录 `session_type` 和 `created_by`
- ✅ 添加 `clean_csv_data` MCP 工具

