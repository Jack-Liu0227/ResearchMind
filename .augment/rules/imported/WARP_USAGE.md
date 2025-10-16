---
type: "manual"
---

# Warp Rule 使用说明

本文档描述了 ResearchMind 项目的 `warp.rule` 配置文件的使用方法。

## 📋 配置概述

`warp.rule` 文件为 ResearchMind AI 研究助手项目提供了完整的 Warp 终端配置，包括：

- 🐍 Python 环境管理
- 🚀 服务启动配置  
- 🔧 开发工具集成
- 📊 性能监控
- 🔒 安全规则
- 🤖 AI/ML 特定配置

## 🎯 主要功能

### 1. 环境管理
```yaml
[environment]
python_version: "3.10+"
package_managers: ["uv", "pip"]
auto_activate_venv: true
```

### 2. 快捷命令别名
```bash
# 安装依赖
warp alias install

# 启动所有服务
warp alias start_all

# 代码格式化
warp alias format

# 运行测试
warp alias test
```

### 3. 服务管理
```bash
# 启动 API 服务器
warp service start api_server

# 启动前端
warp service start frontend

# 启动 MCP 服务器
warp service start mcp_paper_search
```

## 🛠️ 常用命令

### 开发命令
```bash
# 代码格式化
warp run format

# 类型检查
warp run type_check

# 清理缓存
warp run clean

# 运行文档服务器
warp run docs
```

### 服务命令
```bash
# 启动API服务器
warp run start_api

# 启动WebSocket服务器
warp run start_ws

# 启动前端开发服务器
warp run start_ui

# 启动MCP服务器
warp run start_mcp
```

## 📁 目录快捷访问

```bash
# 快速导航到各个模块
cd agents/          # 智能体模块
cd communication/   # 通信模块
cd mcp_servers/     # MCP服务器
cd ui/              # 前端界面
cd docs/            # 文档
cd models/          # 模型文件
```

## 🔍 监控功能

### 健康检查
```bash
# 检查服务状态
curl http://localhost:8000/api/health
curl http://localhost:8001/health
```

### 性能监控
- 响应时间监控
- 内存使用监控
- CPU 使用监控
- 活跃连接数监控

## 🔒 安全特性

### 敏感文件检测
自动检测和保护：
- API 密钥文件 (`*.key`, `credentials.json`)
- 证书文件 (`*.pem`, `*.p12`)
- 配置文件中的敏感信息

### API 密钥格式检测
- OpenAI: `sk-[a-zA-Z0-9]{40,}`
- Google: `AIza[a-zA-Z0-9]{35}`
- Anthropic: `sk-ant-[a-zA-Z0-9-]{40,}`

## 🤖 AI/ML 特定配置

### 模型文件管理
- 自动检测模型文件 (`.pth`, `.pkl`, `.h5`, `.onnx`)
- 大文件警告 (>100MB)
- GPU 使用监控

### 实验跟踪
- MLflow 集成
- Weights & Biases 支持
- TensorBoard 支持

## 📊 文件监控

### 热重载配置
- 自动监控 Python 文件变化
- 配置文件变更检测
- 1秒延迟热重载

### 忽略模式
```yaml
ignore_patterns: [
  "__pycache__/",
  "*.pyc",
  ".git/",
  "node_modules/",
  ".venv/",
  "*.log",
  "models/*.pth"
]
```

## 🔄 Git 工作流

### 分支命名规范
- `feature/*` - 新功能分支
- `bugfix/*` - 错误修复分支
- `hotfix/*` - 热修复分支
- `release/*` - 发布分支

### 提交类型
- `feat` - 新功能
- `fix` - 错误修复
- `docs` - 文档更新
- `style` - 代码样式
- `refactor` - 重构
- `test` - 测试相关
- `chore` - 构建/工具相关

## 📚 文档集成

### API 文档访问
- FastAPI 自动文档: http://localhost:8000/docs
- ReDoc 文档: http://localhost:8000/redoc

### 本地文档服务器
```bash
warp run docs  # 启动 MkDocs 服务器
```

## 🚀 快速开始

1. **确保 Warp 终端安装了规则支持**
2. **将 `warp.rule` 文件放在项目根目录**
3. **重启 Warp 终端或重载配置**
4. **使用快捷命令开始开发**

```bash
# 安装依赖
warp alias install_dev

# 启动所有服务
warp alias start_all

# 在新标签页中监控日志
warp tail logs/
```

## 💡 提示和技巧

### 1. 环境变量检查
```bash
# 检查必需的环境变量
echo $GOOGLE_API_KEY
echo $DEEPSEEK_API_KEY
```

### 2. 服务健康检查
```bash
# 检查所有服务状态
warp health check
```

### 3. 批量操作
```bash
# 格式化并检查代码
warp run format && warp run lint && warp run type_check
```

### 4. 开发环境重置
```bash
# 清理并重新安装
warp run clean && warp alias install_dev
```

## ⚠️ 注意事项

1. **环境变量**: 确保在 `.env` 文件中正确配置所有必需的 API 密钥
2. **端口冲突**: 检查端口 8000, 8001, 5173 是否被其他进程占用
3. **Python 版本**: 确保使用 Python 3.10 或更高版本
4. **依赖管理**: 优先使用 `uv` 进行包管理，提高安装速度
5. **模型文件**: 大型模型文件不会自动同步到 Git，需要单独管理

## 🐛 故障排除

### 常见问题

1. **虚拟环境未激活**
   ```bash
   # 手动激活虚拟环境
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

2. **端口被占用**
   ```bash
   # 查找占用端口的进程
   netstat -ano | findstr :8000  # Windows
   lsof -i :8000                 # Linux/Mac
   ```

3. **依赖安装失败**
   ```bash
   # 清理并重新安装
   uv cache clean
   uv sync --reinstall
   ```

4. **API 密钥未设置**
   ```bash
   # 检查环境文件
   cat .env
   # 或
   type .env  # Windows
   ```

---

*此配置文件是为 ResearchMind AI 研究助手项目量身定制的，可以根据具体需求进行调整。*