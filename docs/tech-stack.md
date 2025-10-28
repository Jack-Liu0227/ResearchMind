# ResearchMind 技术栈文档

## 📋 项目概述

**ResearchMind** 是一个创新的多智能体协作平台，专为材料科学研究人员设计。系统通过 Google ADK (Agent Development Kit) 和 MCP (Model Context Protocol) 技术，实现了从文献调研、数据库检索到仿真计算的全流程自动化研究支持。

### 核心特性

- 🤖 **多智能体协作**: 总智能体协调三个专业子智能体
- 📚 **文献调研**: 以文献研究为底座，提供高效准确的文献分析
- 🗄️ **数据库查询**: 集成多个材料科学数据库（Materials Project, AFLOW, QMPY等）
- 🧪 **仿真计算**: 支持材料性质预测和仿真计算
- 🔄 **全流程自动化**: 从调研到实验设计的完整工作流

---

## 🏗️ 系统架构

### 分层架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    前端层 (UI Layer)                     │
│              React + TypeScript + Vite                  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  服务层 (Service Layer)                  │
│         FastAPI + WebSocket + HTTP Server               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  智能体层 (Agent Layer)                  │
│    总智能体 (Coordinator) + 3个专业子智能体              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   MCP层 (MCP Servers)                    │
│     Paper Search MCP | Database MCP | Simulation MCP    │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 技术栈详解

### 1. 前端技术栈

#### 核心框架
- **React 18.2.0** - UI框架
- **TypeScript 5.2.2** - 类型安全的JavaScript超集
- **Vite 5.4.20** - 现代化构建工具

#### UI组件库
- **Tailwind CSS 3.3.5** - 实用优先的CSS框架
- **@headlessui/react 1.7.17** - 无样式可访问组件
- **Framer Motion 10.16.5** - 动画库
- **Lucide React 0.294.0** - 图标库

#### 3D可视化
- **Three.js 0.165.0** - 3D图形库
- **@react-three/fiber 8.18.0** - React的Three.js渲染器
- **@react-three/drei 9.122.0** - Three.js辅助工具

#### 状态管理与数据获取
- **Zustand 4.4.7** - 轻量级状态管理
- **@tanstack/react-query 5.8.4** - 服务端状态管理
- **Axios 1.6.2** - HTTP客户端

#### 路由与导航
- **React Router DOM 6.20.1** - 客户端路由

#### Markdown与代码高亮
- **React Markdown 9.0.1** - Markdown渲染
- **React Syntax Highlighter 15.5.0** - 代码语法高亮
- **Remark GFM 4.0.0** - GitHub风格Markdown

#### 通知系统
- **React Hot Toast 2.4.1** - 通知提示组件

---

### 2. 后端技术栈

#### Web框架
- **FastAPI 0.104.0+** - 现代高性能Web框架
- **Uvicorn 0.24.0+** - ASGI服务器
- **WebSockets 12.0+** - WebSocket支持

#### AI/LLM集成
- **Google ADK 1.15.0+** - Google Agent Development Kit
- **Google Generative AI 0.3.0+** - Google AI API
- **OpenAI 1.3.0+** - OpenAI API（兼容DeepSeek）
- **Anthropic 0.7.0+** - Claude API（可选）
- **LiteLLM 1.0.0+** - 统一LLM接口

#### MCP (Model Context Protocol)
- **MCP 1.0.0+** - Model Context Protocol核心
- **FastMCP 0.1.0+** - 快速MCP服务器开发

#### HTTP客户端
- **HTTPX 0.25.0+** - 异步HTTP客户端（支持SOCKS代理）
- **Requests 2.32.4+** - 同步HTTP客户端
- **AIOHTTP 3.9.0+** - 异步HTTP框架

---

### 3. 数据处理与科学计算

#### 数据分析
- **Pandas 2.1.0+** - 数据分析库
- **NumPy 1.25.0+** - 数值计算库
- **Matplotlib 3.7.0+** - 数据可视化
- **Seaborn 0.12.0+** - 统计数据可视化

#### 化学与材料科学
- **RDKit 2023.9.1+** - 化学信息学工具包
- **ASE 3.22.0+** - 原子模拟环境
- **Pymatgen 2023.10.0+** - 材料分析库
- **MatterSim 1.2.0+** - 材料模拟工具

#### 机器学习与深度学习
- **Scikit-learn 1.3.0+** - 机器学习库
- **PyTorch 2.6.0+cu124** - 深度学习框架（CUDA 12.4）
- **TorchVision 0.21.0+cu124** - 计算机视觉库
- **TorchAudio 2.6.0+cu124** - 音频处理库

---

### 4. 数据库与存储

#### 数据库
- **SQLAlchemy 2.0.0+** - ORM框架
- **Alembic 1.12.0+** - 数据库迁移工具
- **Redis 5.0.0+** - 内存数据库

#### 向量数据库
- **ChromaDB 1.1.0+** - 向量数据库（用于文献检索）

---

### 5. 材料科学数据库API

#### 材料数据库
- **mp-api 0.45.9** - Materials Project API
- **aflow 0.0.11** - AFLOW数据库API
- **qmpy-rester 0.2.0** - QMPY数据库API

#### 文献检索
- **ArXiv 1.4.0+** - ArXiv论文API
- **Scholarly 1.7.11+** - Google Scholar API
- **Tavily Python 0.7.12+** - Tavily搜索API
- **Langchain Tavily 0.2.11** - Langchain集成的Tavily

---

### 6. 工具库

#### 配置管理
- **Python-dotenv 1.0.0+** - 环境变量管理
- **Pydantic 2.4.0+** - 数据验证
- **Pydantic Settings 2.0.0+** - 配置管理
- **OmegaConf 2.3.0+** - 配置文件管理（CrystaLLM需要）

#### 文件处理
- **Python-multipart 0.0.6+** - 多部分表单数据
- **PyPDF2 3.0.0+** - PDF处理
- **pypdf 3.0.0+** - PDF处理（新版）
- **openpyxl 3.1.0+** - Excel处理
- **BeautifulSoup4 4.14.2+** - HTML解析

#### 日志与监控
- **Structlog 23.1.0+** - 结构化日志
- **Rich 13.6.0+** - 终端美化输出

#### 网络爬虫
- **Feedparser 6.0.0+** - RSS/Atom解析

---

### 7. 开发工具（可选）

#### 代码质量
- **Black 23.9.0+** - 代码格式化
- **isort 5.12.0+** - import排序
- **Flake8 6.1.0+** - 代码检查
- **Mypy 1.6.0+** - 类型检查
- **Pre-commit 3.4.0+** - Git钩子

#### 测试
- **Pytest 7.4.0+** - 测试框架
- **Pytest-asyncio 0.21.0+** - 异步测试
- **Pytest-cov 4.1.0+** - 测试覆盖率
- **Pytest-mock 3.11.0+** - Mock工具

#### 文档
- **MkDocs 1.5.0+** - 文档生成
- **MkDocs Material 9.4.0+** - Material主题
- **MkDocstrings 0.23.0+** - API文档生成

---

## 🔧 部署技术栈

### 包管理
- **uv** - Python包管理器（快速、现代化）
- **npm** - Node.js包管理器

### Web服务器
- **Nginx** - 反向代理服务器
  - 统一入口端口: 50001
  - 支持WebSocket升级
  - 静态文件服务
  - 负载均衡

### 进程管理
- **nohup** - 后台进程运行
- **systemd** - Linux系统服务管理（可选）
- **screen/tmux** - 终端复用器（可选）

---

## 🌐 网络架构

### 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 50001 | 统一入口（对外） |
| Backend HTTP | 50002 | 后端API（内部） |
| WebSocket | 50003 | WebSocket服务（内部） |
| Paper Search MCP | 50004 | 论文搜索MCP（内部） |
| Simulation MCP | 50005 | 仿真计算MCP（内部） |
| Database MCP | 50006 | 数据库MCP（内部） |
| Frontend Vite | 50010 | Vite开发服务器（内部） |

### 通信协议
- **HTTP/HTTPS** - RESTful API
- **WebSocket** - 实时双向通信
- **MCP** - Model Context Protocol（智能体间通信）

---

## 📦 依赖管理

### Python依赖
```bash
# 使用uv管理
uv sync                    # 安装依赖
uv add <package>          # 添加依赖
uv sync --upgrade         # 更新依赖
```

### Node.js依赖
```bash
# 使用npm管理
cd ui && npm install      # 安装依赖
npm install <package>     # 添加依赖
npm update                # 更新依赖
```

---

## 🔐 安全特性

### API密钥管理
- 环境变量存储（.env文件）
- 不提交到版本控制
- 支持多环境配置（.env, .env.remote）

### 网络安全
- MCP服务仅监听127.0.0.1（内部访问）
- Nginx作为唯一对外入口
- 支持防火墙配置（ufw/firewalld）

---

## 📊 性能优化

### 前端优化
- Vite HMR（热模块替换）
- 代码分割与懒加载
- 资源压缩与缓存

### 后端优化
- 异步I/O（FastAPI + HTTPX）
- WebSocket长连接
- Redis缓存

### 数据库优化
- SQLAlchemy ORM
- 连接池管理
- 向量数据库索引（ChromaDB）

---

## 🔄 版本要求

### 最低版本
- **Python**: 3.10+
- **Node.js**: 18+
- **Nginx**: 1.18+（推荐1.20+）

### 推荐版本
- **Python**: 3.11 或 3.12
- **Node.js**: 20 LTS
- **Nginx**: 最新稳定版

---

## 📚 相关文档

- [architecture.md](./architecture.md) - 系统架构详解
- [implementation-plan.md](./implementation-plan.md) - 实现计划
- [progress.md](./progress.md) - 开发进度追踪

