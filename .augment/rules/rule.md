---
type: "manual"
---

# Warp Rule Configuration for ResearchMind AI Research Assistant
# 配置文件: ResearchMind AI研究助手 Warp终端规则

# 项目基本信息
project_name: "ResearchMind_V2"
project_type: "AI Research Assistant"
language: "Python"
framework: ["FastAPI", "React", "Google ADK"]

# 环境管理规则
[environment]
# Python版本要求
python_version: "3.10+"
# 包管理器优先级
package_managers: ["uv", "pip"]
# 虚拟环境检测
venv_detection: true
venv_paths: [".venv", "venv", "env"]

# 自动激活虚拟环境
auto_activate_venv: true

# 工作目录规则
[directories]
# 项目根目录识别文件
root_indicators: ["pyproject.toml", "uv.lock", ".env.example"]

# 重要目录快捷访问
shortcuts:
  agents: "agents/"
  communication: "communication/"  
  mcp: "mcp_servers/"
  ui: "ui/"
  docs: "docs/"
  models: "models/"

# 自动补全规则
[completion]
# Python模块自动补全
python_modules: [
  "agents.literature_agent",
  "agents.database_agent", 
  "agents.simulation_agent",
  "communication.api_server",
  "mcp_servers"
]

# 常用命令自动补全
commands: [
  "uv run python",
  "uv sync",
  "uv add",
  "pytest",
  "black",
  "isort",
  "mypy",
  "flake8"
]

# 服务启动命令
[services]
# 后端API服务器
api_server:
  command: "uv run python communication/api_server.py"
  port: 8000
  health_check: "http://localhost:8000/api/health"
  description: "FastAPI主服务器"

# WebSocket服务器  
websocket_server:
  command: "uv run python communication/websocket_server.py"
  port: 8001
  description: "WebSocket通信服务器"

# 前端开发服务器
frontend:
  command: "npm run dev"
  working_dir: "ui/"
  port: 5173
  description: "React前端开发服务器"

# MCP服务器
mcp_paper_search:
  command: "uv run python mcp_servers/paper_search/server.py"
  description: "论文搜索MCP服务器"

mcp_materials:
  command: "uv run python mcp_servers/materials/server.py"
  description: "材料数据库MCP服务器"

mcp_simulation:
  command: "uv run python mcp_servers/simulation/server.py"
  description: "仿真计算MCP服务器"

# 开发工具规则
[development]
# 代码格式化
formatters:
  python: ["black", "isort"]
  typescript: ["prettier"]
  json: ["prettier"]

# 代码检查工具
linters:
  python: ["flake8", "mypy", "bandit"]
  typescript: ["eslint"]

# 测试工具
testing:
  python: ["pytest", "pytest-cov", "pytest-asyncio"]
  typescript: ["jest", "vitest"]

# Git工作流规则
[git]
# 分支命名规范
branch_patterns: [
  "feature/*",
  "bugfix/*", 
  "hotfix/*",
  "release/*"
]

# 提交信息规范
commit_types: [
  "feat", "fix", "docs", "style", 
  "refactor", "test", "chore", "perf"
]

# 预提交钩子
pre_commit: true
pre_commit_config: ".pre-commit-config.yaml"

# 环境变量规则
[environment_variables]
# 必需的环境变量
required: [
  "GOOGLE_API_KEY",
  "DEEPSEEK_API_KEY"
]

# 可选的环境变量
optional: [
  "ANTHROPIC_API_KEY",
  "OPENAI_API_KEY",
  "REDIS_URL",
  "DATABASE_URL"
]

# 环境文件
env_files: [".env", ".env.local", ".env.example"]

# 日志规则
[logging]
# 日志级别
levels: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# 日志文件路径
log_paths: [
  "logs/",
  "communication/logs/",
  "agents/logs/"
]

# 日志格式
format: "structured"
handler: "rich"

# 性能监控规则  
[monitoring]
# 健康检查端点
health_endpoints: [
  "http://localhost:8000/api/health",
  "http://localhost:8001/health"
]

# 性能指标
metrics: [
  "response_time",
  "memory_usage", 
  "cpu_usage",
  "active_connections"
]

# 安全规则
[security]
# 敏感文件检测
sensitive_files: [
  "*.key",
  "*.pem", 
  "*.p12",
  "credentials.json",
  "service-account.json"
]

# API密钥格式检测
api_key_patterns: [
  "sk-[a-zA-Z0-9]{40,}",  # OpenAI
  "AIza[a-zA-Z0-9]{35}",  # Google
  "sk-ant-[a-zA-Z0-9-]{40,}" # Anthropic
]

# 端口安全扫描
secure_ports: [8000, 8001, 5173]

# 文件监控规则
[file_watching]
# 自动重启触发文件
auto_reload: [
  "**/*.py",
  "pyproject.toml",
  ".env"
]

# 忽略的文件/目录
ignore_patterns: [
  "__pycache__/",
  "*.pyc",
  ".git/",
  "node_modules/",
  ".venv/",
  "*.log",
  "models/*.pth"
]

# 热重载配置
hot_reload: true
reload_delay: 1000  # 毫秒

# 快捷命令规则
[aliases]
# 常用命令别名
start_all: "uv run python communication/api_server.py & npm run dev --prefix ui"
test: "uv run pytest"
lint: "uv run black . && uv run isort . && uv run flake8"
type_check: "uv run mypy ."
install: "uv sync"
install_dev: "uv sync --extra dev"
format: "uv run black . && uv run isort ."
clean: "find . -type d -name __pycache__ -delete"
docs: "uv run mkdocs serve"

# 服务管理别名
start_api: "uv run python communication/api_server.py"
start_ws: "uv run python communication/websocket_server.py"  
start_ui: "npm run dev --prefix ui"
start_mcp: "uv run python mcp_servers/paper_search/server.py"

# Docker支持规则
[docker]
# Dockerfile检测
dockerfile_paths: ["Dockerfile", "docker/Dockerfile", "Dockerfile.*"]

# Docker Compose检测  
compose_files: ["docker-compose.yml", "docker-compose.yaml", "compose.yaml"]

# 容器命名规范
container_prefix: "researchmind"

# 端口映射
port_mappings: [
  "8000:8000",  # API服务器
  "8001:8001",  # WebSocket服务器
  "5173:5173"   # 前端开发服务器
]

# AI/ML特定规则
[ai_ml]
# 模型文件检测
model_extensions: [".pth", ".pkl", ".h5", ".onnx", ".tflite"]

# 数据文件检测
data_extensions: [".csv", ".json", ".parquet", ".npy", ".h5"]

# 大文件警告阈值 (MB)
large_file_threshold: 100

# GPU使用检测
gpu_monitoring: true
cuda_detection: true

# 实验跟踪
experiment_tracking: ["mlflow", "wandb", "tensorboard"]

# 通知规则
[notifications]
# 构建完成通知
build_success: true
build_failure: true

# 测试结果通知
test_completion: true
test_failure: true

# 服务状态通知
service_up: true
service_down: true

# 错误监控
error_threshold: 10  # 连续错误数量阈值

# 文档规则
[documentation]
# 文档格式
formats: ["markdown", "rst", "html"]

# 文档路径
paths: ["docs/", "README.md", "ARCHITECTURE.md"]

# API文档
api_docs: [
  "http://localhost:8000/docs",  # FastAPI自动文档
  "http://localhost:8000/redoc"  # ReDoc文档
]

# 版本控制规则
[versioning]
# 语义化版本
semantic_versioning: true
version_file: "pyproject.toml"

# 发布分支
release_branches: ["main", "master", "release/*"]

# 标签格式
tag_format: "v{version}"

# 更新日志
changelog: "CHANGELOG.md"