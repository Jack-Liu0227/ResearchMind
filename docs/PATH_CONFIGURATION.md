# 路径配置指南

## 概述

ResearchMind 使用统一的路径管理系统，支持通过环境变量配置所有数据存储路径。

## 环境变量

### 主要路径配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `SESSION_DATA_ROOT` | `data/session_data` | 会话数据根目录（所有会话相关数据的存储位置） |
| `PAPERS_ROOT` | `{SESSION_DATA_ROOT}/papers` | 论文存储目录 |
| `PHONON_ROOT` | `{SESSION_DATA_ROOT}/simulation` | 声子/仿真数据目录 |

### 配置方式

#### 方式 1：在 `.env` 文件中配置（推荐）

```bash
# 使用绝对路径（Windows）
SESSION_DATA_ROOT=D:\XJTU\Research\PHD\Agent\ST\data\session_data

# 使用绝对路径（Linux/Mac）
SESSION_DATA_ROOT=/mnt/data/session_data

# 使用相对路径（相对于项目根目录）
SESSION_DATA_ROOT=../data/session_data
```

#### 方式 2：在启动脚本中配置

```bash
# Linux/Mac
export SESSION_DATA_ROOT="/mnt/data/session_data"
bash start_linux.sh

# Windows PowerShell
$env:SESSION_DATA_ROOT="D:\data\session_data"
python main.py
```

#### 方式 3：Docker 容器中配置

```bash
docker run -d \
  -e SESSION_DATA_ROOT=/mnt/data/session_data \
  -v /host/path/to/data:/mnt/data/session_data \
  -p 8000:8000 \
  researchmind:latest
```

## 目录结构

配置 `SESSION_DATA_ROOT` 后，系统会自动创建以下目录结构：

```
{SESSION_DATA_ROOT}/
├── papers/                    # 论文存储（PAPERS_ROOT）
│   ├── {session_id}/
│   │   ├── research_report.md
│   │   ├── papers.csv
│   │   └── *.pdf
│   └── paper_sessions.json
├── simulation/                # 仿真数据（PHONON_ROOT）
│   └── {session_id}/
│       ├── phonon_dispersion.png
│       ├── phonon_dos.png
│       └── thermal_conductivity/
│           └── results.csv
├── structures/                # 晶体结构
│   └── {session_id}/
│       └── *.cif
└── metadata/                  # 元数据
    └── {session_id}/
        └── metadata.json

{SESSION_DATA_ROOT}/../
└── researchmind.db           # 数据库文件（在 SESSION_DATA_ROOT 的父目录）
```

## 验证配置

### 运行验证脚本

```bash
python scripts/verify_paths.py
```

### 预期输出

```
🎉 所有路径配置验证通过！

预期数据存储位置：
  - 会话数据: D:\XJTU\Research\PHD\Agent\ST\data\session_data
  - 论文文件: D:\XJTU\Research\PHD\Agent\ST\data\session_data\papers
  - 仿真结果: D:\XJTU\Research\PHD\Agent\ST\data\session_data\simulation
  - 数据库:   D:\XJTU\Research\PHD\Agent\ST\data\researchmind.db
```

## 常见场景

### 场景 1：本地开发（使用项目内部路径）

```bash
# .env 文件
# SESSION_DATA_ROOT=data/session_data  # 注释掉或不设置，使用默认值
```

数据存储在：`ResearchMind/data/session_data/`

### 场景 2：多项目共享数据

```bash
# .env 文件
SESSION_DATA_ROOT=D:\SharedData\researchmind\session_data
```

数据存储在：`D:\SharedData\researchmind\session_data/`

### 场景 3：Docker 部署

```bash
# docker-compose.yml
services:
  researchmind:
    image: researchmind:latest
    environment:
      - SESSION_DATA_ROOT=/mnt/data/session_data
    volumes:
      - /host/data:/mnt/data/session_data
```

数据存储在宿主机：`/host/data/`

## API 访问路径

无论 `SESSION_DATA_ROOT` 配置在哪里，前端访问文件的 URL 保持不变：

| 文件类型 | API 路径 | 示例 |
|---------|---------|------|
| 论文报告 | `/api/download/papers/{session_id}/{filename}` | `/api/download/papers/abc123/research_report.md` |
| 论文 CSV | `/api/download/papers/{session_id}/{filename}` | `/api/download/papers/abc123/papers.csv` |
| 声子图片 | `/api/images/phonon/{session_id}/{subpath}/{filename}` | `/api/images/phonon/abc123/phonon_dispersion.png` |
| 热导率数据 | `/api/files/thermal_conductivity/{session_id}/{filename}` | `/api/files/thermal_conductivity/abc123/results.csv` |

## 故障排查

### 问题 1：路径不生效

**症状：** 修改 `.env` 中的 `SESSION_DATA_ROOT` 后，数据仍然保存在旧路径。

**解决方案：**
1. 重启所有服务：`bash stop_linux.sh && bash start_linux.sh`
2. 确认环境变量已加载：`echo $SESSION_DATA_ROOT`
3. 运行验证脚本：`python scripts/verify_paths.py`

### 问题 2：权限错误

**症状：** `Permission denied: /path/to/session_data`

**解决方案：**
```bash
# Linux/Mac
chmod -R 755 /path/to/session_data
chown -R $USER:$USER /path/to/session_data

# Windows
# 右键目录 → 属性 → 安全 → 编辑权限
```

### 问题 3：数据库路径不一致

**症状：** 数据库文件在项目内部，但会话数据在外部。

**说明：** 这是正常的。数据库文件始终保存在 `SESSION_DATA_ROOT` 的父目录中。

**示例：**
- `SESSION_DATA_ROOT=D:\data\session_data`
- 数据库路径：`D:\data\researchmind.db`

## 参考

- 阶段 A 验证文档：`docs/STAGE_A_VERIFICATION.md`
- 实施总结：`docs/STAGE_AB_SUMMARY.md`
- 路径管理模块：`utils/paths.py`

