# ResearchMind 数据存储结构

## 概述

ResearchMind 的所有运行时数据统一存储在 `SESSION_DATA_ROOT` 配置的目录中。

## 配置方式

在 `.env` 文件中设置：
```
SESSION_DATA_ROOT=../data/session_data
```

支持相对路径（相对于项目根目录）和绝对路径。

## 目录结构

```
{SESSION_DATA_ROOT}/                          # 默认: D:\XJTU\Research\PHD\Agent\ST\data\session_data
├── cache/
│   ├── analysis/                             # 论文分析结果缓存（JSON 格式）
│   └── search/                               # 搜索上下文缓存（JSON 格式）
├── reports/                                  # 生成的研究报告（Markdown 格式）
├── exports/                                  # 导出的数据文件（CSV、JSON）
├── visualizations/                           # 图表和可视化结果（PNG、SVG）
├── structures/                               # 晶体结构文件（CIF 格式）
├── logs/                                     # 应用日志文件
├── temp/                                     # 临时文件
├── metadata/                                 # 元数据文件（JSON 格式）
├── images/                                   # 图像文件（PNG、JPG）
├── papers/                                   # 论文会话数据（前端依赖，不可修改）
├── simulation/                               # 模拟数据（前端依赖，不可修改）
└── paper_sessions.json                       # 会话元数据（前端依赖，不可修改）

{SESSION_DATA_ROOT}/../database/              # 默认: D:\XJTU\Research\PHD\Agent\ST\data\database
└── researchmind.db                           # SQLite 数据库文件
```

## 数据类型说明

| 目录 | 用途 | 文件类型 | 清理策略 |
|------|------|---------|---------|
| `cache/analysis/` | 论文分析结果缓存 | `.json` | 根据 TTL 自动清理 |
| `cache/search/` | 搜索上下文缓存 | `.json` | 24 小时过期 |
| `reports/` | 用户生成的研究报告 | `.md` | 永久保留 |
| `exports/` | 用户导出的数据 | `.csv`, `.json` | 用户手动清理 |
| `visualizations/` | 图表和图像 | `.png`, `.svg`, `.jpg` | 与报告关联保留 |
| `structures/` | 晶体结构文件 | `.cif` | 与会话关联保留 |
| `logs/` | 应用运行日志 | `.log` | 定期轮转（建议保留 30 天） |
| `temp/` | 临时文件 | 各种 | 应用退出时清理 |
| `metadata/` | 元数据 | `.json` | 永久保留 |
| `images/` | 图像文件 | `.png`, `.jpg` | 与会话关联保留 |
| `papers/` | 论文会话数据 | 各种 | **永久保留（前端依赖）** |
| `simulation/` | 模拟数据 | 各种 | **永久保留（前端依赖）** |
| `paper_sessions.json` | 会话元数据 | `.json` | **永久保留（前端依赖）** |
| `../database/` | 数据库文件 | `.db`, `.sqlite` | 手动备份 |

## 配置参数

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SESSION_DATA_ROOT` | `../data/session_data` | 会话数据根目录 |
| `PAPERS_ROOT` | `{SESSION_DATA_ROOT}/papers` | 论文存储目录 |
| `PHONON_ROOT` | `{SESSION_DATA_ROOT}/simulation` | 声子/仿真数据目录 |

### 代码中的配置常量

在 `mcp_servers/paper_search/config.py` 中定义：

```python
SESSION_DATA_ROOT = session_data_root()  # 从环境变量读取
CACHE_DIR = SESSION_DATA_ROOT / 'cache' / 'analysis'
SEARCH_CACHE_DIR = SESSION_DATA_ROOT / 'cache' / 'search'
REPORTS_DIR = SESSION_DATA_ROOT / 'reports'
EXPORTS_DIR = SESSION_DATA_ROOT / 'exports'
DATABASE_DIR = SESSION_DATA_ROOT.parent / 'database'
VISUALIZATIONS_DIR = SESSION_DATA_ROOT / 'visualizations'
STRUCTURES_DIR = SESSION_DATA_ROOT / 'structures'
LOGS_DIR = SESSION_DATA_ROOT / 'logs'
TEMP_DIR = SESSION_DATA_ROOT / 'temp'
PAPERS_DIR = SESSION_DATA_ROOT / 'papers'
SIMULATION_DIR = SESSION_DATA_ROOT / 'simulation'
METADATA_DIR = SESSION_DATA_ROOT / 'metadata'
IMAGES_DIR = SESSION_DATA_ROOT / 'images'
```

## 迁移指南

### 从旧版本迁移

如果您已有旧版本的数据（如 `mcp_servers/paper_search/cache`），请按以下步骤迁移：

1. **备份现有数据**：
   ```bash
   # Windows PowerShell
   Copy-Item -Path "mcp_servers\paper_search\cache" -Destination "{SESSION_DATA_ROOT}\cache\analysis_backup" -Recurse
   
   # Linux/Mac
   cp -r mcp_servers/paper_search/cache {SESSION_DATA_ROOT}/cache/analysis_backup
   ```

2. **移动数据到新位置**：
   ```bash
   # Windows PowerShell
   Move-Item -Path "mcp_servers\paper_search\cache\*" -Destination "{SESSION_DATA_ROOT}\cache\analysis\"
   
   # Linux/Mac
   mv mcp_servers/paper_search/cache/* {SESSION_DATA_ROOT}/cache/analysis/
   ```

3. **验证迁移结果**：
   ```bash
   # 检查新目录中的文件数量
   Get-ChildItem -Path "{SESSION_DATA_ROOT}\cache\analysis" -Recurse | Measure-Object
   ```

4. **删除旧目录**（确认迁移成功后）：
   ```bash
   Remove-Item -Path "mcp_servers\paper_search\cache" -Recurse -Force
   ```

### 自动迁移（未来版本）

未来版本将提供自动迁移脚本：
```bash
python scripts/migrate_data_paths.py
```

## 故障排查

### 问题：目录未自动创建

**症状**：启动时报错 "No such file or directory"

**解决方案**：
1. 检查 `SESSION_DATA_ROOT` 路径是否有写权限
2. 查看日志文件中的错误信息
3. 手动创建目录：
   ```bash
   mkdir -p {SESSION_DATA_ROOT}/cache/analysis
   mkdir -p {SESSION_DATA_ROOT}/cache/search
   mkdir -p {SESSION_DATA_ROOT}/reports
   # ... 其他目录
   ```

### 问题：前端无法读取数据

**症状**：前端显示"无法加载论文数据"

**解决方案**：
1. 确认 `papers/`, `simulation/`, `paper_sessions.json` 未被移动
2. 检查前端配置中的路径设置
3. 验证 HTTP 静态文件服务的挂载点：
   ```python
   # services/static_file_service.py
   app.mount("/api/download", StaticFiles(directory=session_data_root()))
   ```

### 问题：缓存未生效

**症状**：重复分析相同论文，API 调用次数未减少

**解决方案**：
1. 验证 `CACHE_DIR` 配置是否正确：
   ```python
   from mcp_servers.paper_search.config import CACHE_DIR
   print(f"CACHE_DIR: {CACHE_DIR}")
   ```
2. 检查缓存文件是否成功写入：
   ```bash
   Get-ChildItem -Path "{SESSION_DATA_ROOT}\cache\analysis" -Recurse
   ```
3. 确认 `ENABLE_ANALYSIS_CACHE` 环境变量为 `true`

### 问题：数据库文件找不到

**症状**：启动时报错 "database file not found"

**解决方案**：
1. 检查 `DATABASE_DIR` 配置：
   ```python
   from mcp_servers.paper_search.config import DATABASE_DIR
   print(f"DATABASE_DIR: {DATABASE_DIR}")
   ```
2. 确认数据库文件存在：
   ```bash
   Test-Path "{SESSION_DATA_ROOT}\..\database\researchmind.db"
   ```
3. 如果不存在，数据库会在首次启动时自动创建

## 最佳实践

1. **定期备份**：
   - 每周备份 `SESSION_DATA_ROOT` 目录
   - 特别注意 `papers/`, `simulation/`, `paper_sessions.json`

2. **磁盘空间监控**：
   - 监控 `cache/` 目录大小，定期清理过期缓存
   - 监控 `logs/` 目录，配置日志轮转

3. **权限管理**：
   - 确保应用有 `SESSION_DATA_ROOT` 的读写权限
   - 避免使用需要管理员权限的路径

4. **路径配置**：
   - 优先使用相对路径（便于迁移）
   - 生产环境使用绝对路径（避免歧义）

## 参考文档

- [路径配置指南](PATH_CONFIGURATION.md)
- [环境变量配置](.env.example)
- [统一路径管理模块](../utils/paths.py)

