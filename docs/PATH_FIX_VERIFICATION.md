# 路径修复验证报告

## 问题现象（修复前）

1. **项目内部创建了错误目录**：
   - 路径：`ResearchMind\data\session_data`
   - 原因：Shell 脚本覆盖了 `.env` 配置并创建了错误目录

2. **文件保存到错误位置**：
   - 实际保存：`ResearchMind\data\session_data\papers\session_xxx\all_papers.csv`
   - 预期保存：`..\data\session_data\papers\session_xxx\all_papers.csv`

3. **HTTP 服务返回 404 错误**：
   ```
   GET /api/download/papers/session_xxx/all_papers.csv HTTP/1.0" 404 Not Found
   GET /api/images/phonon/session_xxx/phonon_results/sample_xxx/SiC_phonon_band.png HTTP/1.0" 404 Not Found
   ```

## 根本原因

### 原因 1：Shell 脚本覆盖环境变量

`start_linux.sh` 第 168 行：
```bash
export SESSION_DATA_ROOT="${SESSION_DATA_ROOT:-data/session_data}"
```

**问题**：这行代码会在 `SESSION_DATA_ROOT` 未设置或为空时使用默认值 `data/session_data`，覆盖了 `.env` 文件中的 `..\data\session_data` 配置。

### 原因 2：Shell 脚本创建错误目录

`start_linux.sh` 第 212 行：
```bash
mkdir -p "${SESSION_DATA_ROOT}"
```

**问题**：即使环境变量正确，shell 的 `mkdir` 在 Windows/Git Bash 环境下也无法正确解析相对路径 `..\data\session_data`。

## 修复方案

### 修复 1：移除环境变量默认值设置

**文件**：`start_linux.sh`  
**位置**：第 165-175 行

**修改**：
- 移除 `export SESSION_DATA_ROOT="${SESSION_DATA_ROOT:-data/session_data}"`
- 移除 `export PAPERS_ROOT=...` 和 `export PHONON_ROOT=...`
- 默认值处理交给 Python 代码（`utils/paths.py`）

### 修复 2：移除 Shell 脚本中的目录创建

**文件**：`start_linux.sh`  
**位置**：第 208-221 行

**修改**：
- 移除 `mkdir -p "${SESSION_DATA_ROOT}"` 等命令
- 目录创建交给 Python 代码（各服务启动时自动创建）

## 验证步骤

### 步骤 1：清理项目内部目录

```powershell
# 删除项目内部的错误目录
Remove-Item -Path "data\session_data" -Recurse -Force
```

### 步骤 2：验证路径配置

```bash
python scripts/verify_paths.py
```

**预期输出**：
```
✅ 所有路径配置验证通过！

预期数据存储位置：
  - 会话数据: D:\XJTU\Research\PHD\Agent\ST\data\session_data
  - 论文文件: D:\XJTU\Research\PHD\Agent\ST\data\session_data\papers
  - 仿真结果: D:\XJTU\Research\PHD\Agent\ST\data\session_data\simulation
  - 数据库:   D:\XJTU\Research\PHD\Agent\ST\data\researchmind.db
```

### 步骤 3：测试路径修复

```bash
python scripts/test_path_fix.py
```

**预期输出**：
```
🎉 路径修复测试通过！

✅ 确认：
  1. 项目内部不会创建 data/session_data 目录
  2. 所有数据都保存到外部路径
  3. 外部路径: D:\XJTU\Research\PHD\Agent\ST\data
```

### 步骤 4：启动服务验证

```bash
# 启动所有服务
bash start_linux.sh

# 等待服务启动完成后，检查项目内部
Test-Path "data\session_data"  # 应该返回 False

# 检查外部路径
Test-Path "..\data\session_data"  # 应该返回 True
```

### 步骤 5：功能测试

1. **论文搜索测试**：
   - 搜索论文并保存 CSV
   - 检查文件是否保存到 `..\data\session_data\papers\session_xxx\`
   - 访问 `/api/download/papers/session_xxx/all_papers.csv` 应该返回 200

2. **仿真测试**：
   - 运行声子谱计算
   - 检查图片是否保存到 `..\data\session_data\simulation\session_xxx\phonon_results\`
   - 访问 `/api/images/phonon/session_xxx/phonon_results/xxx/file.png` 应该返回 200

## 验证结果

### ✅ 路径解析正确

```python
# Python 路径解析测试
from pathlib import Path
from utils.paths import session_data_root

# 输入：SESSION_DATA_ROOT=..\data\session_data
# 输出：D:\XJTU\Research\PHD\Agent\ST\data\session_data
```

### ✅ 项目内部干净

```powershell
PS> Test-Path "data\session_data"
False
```

### ✅ 外部目录正确

```powershell
PS> Test-Path "..\data\session_data"
True

PS> Get-ChildItem "..\data\session_data"
papers/
simulation/
```

### ✅ HTTP 静态文件服务正确

**挂载点配置**：
- `/api/download` → `D:\XJTU\Research\PHD\Agent\ST\data\session_data`
- `/api/images/phonon` → `D:\XJTU\Research\PHD\Agent\ST\data\session_data\simulation`

**URL 映射**：
- `/api/download/papers/session_xxx/file.csv` → `session_data/papers/session_xxx/file.csv` ✅
- `/api/images/phonon/session_xxx/phonon_results/xxx/file.png` → `session_data/simulation/session_xxx/phonon_results/xxx/file.png` ✅

## 总结

### 修复前
- ❌ 项目内部存在 `data\session_data` 目录
- ❌ 文件保存到项目内部
- ❌ HTTP 服务找不到文件（404 错误）
- ❌ `.env` 配置被 shell 脚本覆盖

### 修复后
- ✅ 项目内部不再创建 `data\session_data` 目录
- ✅ 所有文件保存到外部路径 `D:\XJTU\Research\PHD\Agent\ST\data\session_data`
- ✅ HTTP 服务正确访问文件
- ✅ `.env` 配置正确生效
- ✅ Python 代码统一管理路径

### 关键改进
1. **移除 shell 脚本的环境变量默认值设置**，避免覆盖 `.env` 配置
2. **移除 shell 脚本的目录创建逻辑**，交给 Python 代码处理
3. **统一使用 `utils/paths.py` 模块**，确保路径解析一致
4. **HTTP 静态文件服务挂载点正确**，文件访问无问题

