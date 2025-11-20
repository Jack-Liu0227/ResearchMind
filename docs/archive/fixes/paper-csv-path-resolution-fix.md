# 文献 CSV 路径解析修复

## 问题描述

前端加载文献列表时报错：

```
加载失败: No papers found in CSV file: papers/session_1763569867416_d2sid7p5
CSV file not found: papers/session_1763569867416_d2sid7p5/all_papers.csv
```

## 根本原因

1. **前端传入的路径格式不一致：**
   - 可能是绝对路径：`D:/XJTU/.../session_data/papers/session_xxx/all_papers.csv`
   - 可能是相对路径：`papers/session_xxx/all_papers.csv`
   - 可能是部分路径：`session_data/papers/session_xxx/all_papers.csv`

2. **后端 `read_papers_from_csv` 函数只检查路径是否存在：**
   ```python
   # ❌ 原始逻辑
   if not os.path.exists(csv_file_path):
       logger.error(f"CSV file not found: {csv_file_path}")
       return []
   ```
   
   如果传入的是相对路径，但当前工作目录不正确，就会找不到文件。

## 解决方案

修改 `read_papers_from_csv` 函数，支持多种路径格式的智能解析：

```python
# ✅ 新逻辑
csv_path = Path(csv_file_path)

if csv_path.is_absolute() and csv_path.exists():
    # 1. 绝对路径且存在
    final_path = csv_path
elif csv_path.exists():
    # 2. 相对路径且存在（相对于当前工作目录）
    final_path = csv_path
else:
    # 3. 尝试相对于 session_data 目录
    from ..shared.session_folder_manager import SESSION_DATA_DIR
    
    # 移除可能的前缀
    path_str = str(csv_file_path).replace('\\', '/')
    if path_str.startswith('./'):
        path_str = path_str[2:]
    
    # 尝试多个可能的路径
    possible_paths = [
        SESSION_DATA_DIR / path_str,  # session_data/{path}
        SESSION_DATA_DIR / 'papers' / path_str,  # session_data/papers/{path}
    ]
    
    # 如果路径包含 session_data，提取相对部分
    if 'session_data' in path_str:
        parts = path_str.split('session_data/')
        if len(parts) > 1:
            relative_part = parts[-1]
            possible_paths.append(SESSION_DATA_DIR / relative_part)
    
    # 尝试所有可能的路径
    final_path = None
    for p in possible_paths:
        if p.exists():
            final_path = p
            break
    
    if final_path is None:
        logger.error(f"CSV file not found. Tried paths: {possible_paths}")
        return []
```

## 支持的路径格式

修复后，`read_papers_from_csv` 函数支持以下所有路径格式：

1. **绝对路径：**
   - `D:/XJTU/.../session_data/papers/session_xxx/all_papers.csv` ✅

2. **相对于当前工作目录：**
   - `session_data/papers/session_xxx/all_papers.csv` ✅

3. **相对于 session_data 目录：**
   - `papers/session_xxx/all_papers.csv` ✅

4. **包含 session_data 的部分路径：**
   - `session_data/papers/session_xxx/all_papers.csv` ✅

## 修改的文件

- `mcp_servers/paper_search/modules/paper_manager/export_tools.py` (Line 26-91)
  - 修改 `read_papers_from_csv` 函数
  - 添加智能路径解析逻辑
  - 添加详细的日志输出

## 调试日志

修复后，函数会输出详细的日志：

```python
logger.info(f"Found CSV file at: {final_path}")
logger.info(f"Successfully read CSV file: {final_path} ({len(df)} rows)")
```

如果找不到文件，会输出所有尝试的路径：

```python
logger.error(f"CSV file not found. Tried paths: {[str(p) for p in possible_paths]}")
logger.error(f"Original path: {csv_file_path}")
```

## 测试步骤

1. **重启后端服务**（必须）
2. **搜索文献：**
   - 执行 `search_papers` 工具
   - 验证 CSV 文件保存成功
3. **切换到"文献"标签页：**
   - 验证文献列表正确加载
   - 检查浏览器控制台是否有错误
4. **检查后端日志：**
   - 查看 `Found CSV file at:` 日志
   - 验证路径解析正确

## 影响范围

- ✅ 前端加载文献列表（`list_papers_from_csv` 工具）
- ✅ 所有使用 `read_papers_from_csv` 的功能
- ✅ 支持多种路径格式，提高兼容性
- ✅ 详细的日志输出，便于调试

## 注意事项

1. **必须重启后端服务**才能生效
2. 如果仍然找不到文件，检查后端日志中的 `Tried paths` 列表
3. 确保 CSV 文件确实存在于 `session_data/papers/session_xxx/` 目录中
4. 前端传入的路径应该是 `search_papers` 工具返回的 `csv_file_path`

