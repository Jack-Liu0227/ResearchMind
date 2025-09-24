# 安装指南

本指南将帮助您在系统上安装和配置ResearchMind。

> 🇺🇸 **English Users**: [Click here for English version](../installation.md) | **英文用户**: [点击这里查看英文版本](../installation.md)

## 系统要求

### 最低要求
- **操作系统**: Windows 10+、macOS 10.15+ 或 Linux (Ubuntu 18.04+)
- **Python**: 3.9或更高版本
- **内存**: 最低4GB RAM，推荐8GB
- **存储**: 2GB可用空间
- **网络**: 互联网连接以访问API

### 推荐要求
- **Python**: 3.11或更高版本
- **内存**: 16GB RAM用于大规模仿真
- **存储**: 10GB可用空间用于数据缓存
- **GPU**: 支持CUDA的GPU用于加速计算（可选）

## 安装方法

### 方法1：快速安装（推荐）

```bash
# 一键克隆和安装
curl -fsSL https://raw.githubusercontent.com/your-org/researchmind/main/install.sh | bash
```

### 方法2：手动安装

#### 步骤1：克隆仓库

```bash
git clone https://github.com/your-org/researchmind.git
cd researchmind
```

#### 步骤2：创建虚拟环境

```bash
# 使用venv（推荐）
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

#### 步骤3：安装依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements-dev.txt
```

#### 步骤4：安装Google ADK

```bash
# 安装Google ADK
pip install google-adk

# 验证安装
adk --version
```

### 方法3：Docker安装

```bash
# 拉取并运行Docker容器
docker pull researchmind/researchmind:latest
docker run -p 8080:8080 -v $(pwd)/data:/app/data researchmind/researchmind:latest
```

## 配置

### 环境变量

在项目根目录创建`.env`文件：

```bash
# 复制模板
cp .env.example .env
```

编辑`.env`文件配置：

```bash
# 必需：Google API密钥用于Gemini模型
GOOGLE_API_KEY=your_google_api_key_here

# 可选：Materials Project API密钥
MATERIALS_PROJECT_API_KEY=your_mp_api_key_here

# 可选：MatterSim许可证
MATTERSIM_LICENSE=your_mattersim_license_here

# 可选：ArXiv API配置
ARXIV_API_RATE_LIMIT=3
ARXIV_MAX_RESULTS=100

# 可选：网络搜索配置
WEB_SEARCH_ENGINE=google
WEB_SEARCH_API_KEY=your_search_api_key

# 可选：数据库配置
DATABASE_URL=sqlite:///researchmind.db
CACHE_ENABLED=true
CACHE_TTL=3600

# 可选：日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/researchmind.log
```

### API密钥设置

#### Google API密钥（必需）
1. 访问 [Google AI Studio](https://aistudio.google.com/)
2. 创建新的API密钥
3. 添加到`.env`文件：`GOOGLE_API_KEY=your_key_here`

#### Materials Project API密钥（可选）
1. 在 [Materials Project](https://materialsproject.org/) 注册
2. 在您的个人资料中生成API密钥
3. 添加到`.env`文件：`MATERIALS_PROJECT_API_KEY=your_key_here`

#### MatterSim许可证（可选）
1. 联系 [DeepModeling](https://deepmodeling.org/) 获取许可证
2. 添加到`.env`文件：`MATTERSIM_LICENSE=your_license_here`

### 智能体配置

编辑 `config/agent_config.yaml`：

```yaml
# 智能体行为设置
agents:
  coordinator:
    model: "gemini-2.0-flash"
    temperature: 0.1
    max_tokens: 4096
    
  literature:
    model: "gemini-2.0-flash"
    temperature: 0.2
    max_results: 20
    
  database:
    model: "gemini-2.0-flash"
    cache_enabled: true
    timeout: 30
    
  simulation:
    model: "gemini-2.0-flash"
    precision: "high"
    parallel_jobs: 4
    
  experiment:
    model: "gemini-2.0-flash"
    safety_checks: true
    cost_estimation: true

# 工作流设置
workflows:
  hybrid:
    decision_threshold: 0.7
    fallback_mode: "sequential"
    
  parallel:
    max_concurrent: 4
    timeout: 300
    
  sequential:
    early_stopping: true
    checkpoint_enabled: true
```

### MCP服务器配置

编辑 `config/mcp_config.yaml`：

```yaml
# MCP服务器设置
mcp_servers:
  literature:
    command: "python"
    args: ["mcp_servers/literature/server.py"]
    env:
      ARXIV_API_KEY: "${ARXIV_API_KEY}"
    timeout: 30
    
  materials:
    command: "python"
    args: ["mcp_servers/materials/server.py"]
    env:
      MATERIALS_PROJECT_API_KEY: "${MATERIALS_PROJECT_API_KEY}"
    timeout: 60
    
  simulation:
    command: "python"
    args: ["mcp_servers/simulation/server.py"]
    env:
      MATTERSIM_LICENSE: "${MATTERSIM_LICENSE}"
    timeout: 300
    
  experiment:
    command: "python"
    args: ["mcp_servers/experiment/server.py"]
    timeout: 30
```

## 验证

### 运行系统测试

```bash
# 测试所有组件
python test_agents.py

# 预期输出：
# 🧪 测试智能体导入... ✅
# 🧪 测试智能体注册表... ✅
# 🧪 测试智能体管理器... ✅
# 🧪 测试MCP服务器... ✅
# 🧪 测试配置文件... ✅
# 🧪 测试工作流智能体... ✅
# 🧪 测试主程序集成... ✅
# 📊 测试结果: 7/7 通过
# 🎉 所有测试通过！ResearchMind已就绪！
```

### 运行演示

```bash
# 运行交互式演示
python main_mcp.py --demo

# 预期输出：
# 🚀 ResearchMind智能体系统演示
# 🔍 === 文献研究智能体演示 ===
# 📋 创建任务: task_000001
# ✅ 任务完成
# ...
```

### 测试单个组件

```bash
# 测试文献智能体
python main_mcp.py --agent literature_agent --research "测试查询"

# 测试web界面
python main_mcp.py --web --port 8080
# 在浏览器中打开 http://localhost:8080
```

## 故障排除

### 常见问题

#### 导入错误
```bash
# 错误：ModuleNotFoundError: No module named 'google.adk'
# 解决方案：安装Google ADK
pip install google-adk
```

#### API密钥问题
```bash
# 错误：Invalid API key
# 解决方案：检查.env文件和API密钥有效性
cat .env | grep GOOGLE_API_KEY
```

#### MCP服务器启动问题
```bash
# 错误：MCP server failed to start
# 解决方案：检查服务器日志
python mcp_servers/literature/server.py --debug
```

#### 权限问题（Linux/macOS）
```bash
# 错误：Permission denied
# 解决方案：使脚本可执行
chmod +x scripts/*.sh
```

### 获取帮助

如果遇到问题：

1. **检查日志**: `tail -f logs/researchmind.log`
2. **运行诊断**: `python test_agents.py --verbose`
3. **查看GitHub问题**: [问题页面](https://github.com/your-org/researchmind/issues)
4. **寻求帮助**: [讨论区](https://github.com/your-org/researchmind/discussions)

### 性能优化

#### 提高性能
```bash
# 启用缓存
export CACHE_ENABLED=true

# 增加并行作业数
export PARALLEL_JOBS=8

# 开发模式使用更快的模型
export DEVELOPMENT_MODE=true
```

#### 生产环境
```bash
# 使用生产配置
cp config/production.yaml config/agent_config.yaml

# 启用监控
export MONITORING_ENABLED=true
export LOG_LEVEL=WARNING
```

## 下一步

成功安装后：

1. **完成[快速教程](quickstart.md)** 创建您的第一个研究工作流
2. **探索[智能体配置](agent-config.md)** 自定义行为
3. **尝试[示例项目](samples/)** 查看ResearchMind的实际应用
4. **阅读[最佳实践](best-practices.md)** 获得最佳使用效果

---

**安装完成！** 🎉 您已准备好开始使用ResearchMind进行智能研究辅助。


