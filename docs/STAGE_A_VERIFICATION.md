# 阶段 A 验证步骤：路径管理统一

## 概述

本文档提供完整的验证流程，确保路径管理统一功能正常工作。

## 前置条件

1. 已完成阶段 A 的所有代码修改
2. 已安装所有依赖（`uv sync`）
3. 已配置 `.env` 文件

## 验证步骤

### 步骤 1：验证路径管理模块

```bash
# 进入项目根目录
cd /path/to/ResearchMind

# 测试路径管理模块
python3 << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "utils"))

from utils.paths import session_data_root, papers_root, phonon_root, ensure_dirs

# 打印路径
print(f"Session Data Root: {session_data_root()}")
print(f"Papers Root: {papers_root()}")
print(f"Phonon Root: {phonon_root()}")

# 测试目录创建
ensure_dirs(session_data_root(), papers_root(), phonon_root())
print("✅ 所有目录已创建")
EOF
```

**预期输出：**
```
Session Data Root: /path/to/ResearchMind/data/session_data
Papers Root: /path/to/ResearchMind/data/session_data/papers
Phonon Root: /path/to/ResearchMind/data/session_data/simulation
✅ 所有目录已创建
```

### 步骤 2：创建测试文件

```bash
# 创建测试会话目录
mkdir -p data/session_data/papers/session_test_12345

# 创建测试文件
echo "# Test Report" > data/session_data/papers/session_test_12345/test_report.md
echo "title,authors,abstract" > data/session_data/papers/session_test_12345/test_papers.csv
echo "Test Paper,John Doe,This is a test abstract" >> data/session_data/papers/session_test_12345/test_papers.csv

# 验证文件已创建
ls -lh data/session_data/papers/session_test_12345/
```

**预期输出：**
```
total 8.0K
-rw-r--r-- 1 user user  14 Dec  4 10:00 test_report.md
-rw-r--r-- 1 user user  75 Dec  4 10:00 test_papers.csv
```

### 步骤 3：启动服务并验证路径

```bash
# 启动服务（使用启动脚本）
bash start_linux.sh
```

**检查启动日志：**
```bash
# 查看后端日志，确认路径配置
tail -f logs/backend.log | grep -i "session_data\|directory"
```

**预期日志输出：**
```
📁 Session data directory: /path/to/ResearchMind/data/session_data
📁 Simulation directory: /path/to/ResearchMind/data/session_data/simulation
✅ Static files: /api/download -> /path/to/ResearchMind/data/session_data
✅ Static files: /api/images/phonon -> /path/to/ResearchMind/data/session_data/simulation
```

### 步骤 4：通过 API 访问测试文件

```bash
# 方法 1：使用 curl 访问测试文件
curl -v http://localhost:8000/api/download/papers/session_test_12345/test_report.md

# 方法 2：使用 wget
wget -O - http://localhost:8000/api/download/papers/session_test_12345/test_report.md

# 方法 3：使用浏览器
# 打开浏览器访问：http://localhost:8000/api/download/papers/session_test_12345/test_report.md
```

**预期返回：**
- HTTP 状态码：200 OK
- Content-Type: text/markdown 或 application/octet-stream
- 内容：`# Test Report`

### 步骤 5：验证 CSV 文件访问

```bash
# 访问 CSV 文件
curl http://localhost:8000/api/download/papers/session_test_12345/test_papers.csv
```

**预期返回：**
```
title,authors,abstract
Test Paper,John Doe,This is a test abstract
```

### 步骤 6：验证环境变量覆盖

```bash
# 停止服务
bash stop_linux.sh

# 使用自定义路径启动
export SESSION_DATA_ROOT="../custom_data/session_data"
bash start_linux.sh

# 验证新路径
ls -lh ../custom_data/session_data/
```

**预期结果：**
- 服务在新路径下创建目录
- 所有数据保存到 `../custom_data/session_data/`

### 步骤 7：验证 URL 转换工具

```python
# 测试 URL 转换
python3 << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "utils"))

from utils.urls import file_to_download_url, file_to_image_url

# 测试下载 URL
file_path = "/path/to/data/session_data/papers/session_123/report.md"
url = file_to_download_url(file_path, "session_123")
print(f"Download URL: {url}")
assert url == "/api/download/papers/session_123/report.md", "URL 转换失败"

# 测试图片 URL
image_path = "/path/to/data/phonon.png"
url = file_to_image_url(image_path, "session_123", "phonon_results")
print(f"Image URL: {url}")
assert url == "/api/images/phonon/session_123/phonon_results/phonon.png", "URL 转换失败"

print("✅ URL 转换工具验证通过")
EOF
```

## 常见问题排查

### 问题 1：404 文件未找到

**症状：**
```
HTTP 404: File not found: papers/session_xxx/file.csv
```

**排查步骤：**
1. 检查文件是否存在：
   ```bash
   ls -lh data/session_data/papers/session_xxx/file.csv
   ```

2. 检查路径配置：
   ```bash
   grep SESSION_DATA_ROOT .env
   echo $SESSION_DATA_ROOT
   ```

3. 检查静态文件挂载：
   ```bash
   curl http://localhost:8000/api/ | jq '.endpoints'
   ```

### 问题 2：权限错误

**症状：**
```
Permission denied: /path/to/data/session_data
```

**解决方案：**
```bash
# 修改目录权限
chmod -R 755 data/session_data
chown -R $USER:$USER data/session_data
```

### 问题 3：路径不一致

**症状：**
不同模块使用不同的路径

**解决方案：**
确保所有模块都导入 `utils.paths` 模块：
```python
from utils.paths import session_data_root
```

## 验收标准

- [ ] 所有路径通过 `utils.paths` 模块获取
- [ ] 环境变量 `SESSION_DATA_ROOT` 可以覆盖默认路径
- [ ] 测试文件可以通过 `/api/download/` 访问并返回 200 状态码
- [ ] 启动脚本自动创建必要的目录
- [ ] Docker 挂载说明已添加到启动脚本注释中
- [ ] URL 转换工具正常工作

## 下一步

完成阶段 A 验证后，继续进行阶段 B：Markdown 报告生成优化。

