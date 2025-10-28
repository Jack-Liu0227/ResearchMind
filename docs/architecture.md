# ResearchMind 系统架构文档

## 📋 目录结构

```
ResearchMind/
├── agents/                          # 智能体层
│   ├── agent.py                     # 总智能体（协调者）
│   ├── callbacks.py                 # 回调处理
│   ├── prompt.py                    # 提示词模板
│   ├── database_agent/              # 数据库查询智能体
│   │   ├── agent.py                 # 智能体实现
│   │   ├── prompts.py               # 提示词
│   │   ├── ARCHITECTURE.md          # 架构文档
│   │   └── README.md                # 说明文档
│   ├── deep_research_agent/         # 文献研究智能体
│   │   ├── agent.py                 # 智能体实现
│   │   ├── prompts.py               # 提示词
│   │   ├── ARCHITECTURE.md          # 架构文档
│   │   └── README.md                # 说明文档
│   └── simulation_agent/            # 仿真计算智能体
│       ├── agent.py                 # 智能体实现
│       ├── handler.py               # 处理器
│       ├── prompts.py               # 提示词
│       ├── ARCHITECTURE.md          # 架构文档
│       └── README.md                # 说明文档
│
├── mcp_servers/                     # MCP服务层
│   ├── paper_search/                # 论文搜索MCP服务
│   │   ├── server.py                # MCP服务器
│   │   ├── prompts.py               # 提示词
│   │   ├── modules/                 # 功能模块
│   │   ├── papers/                  # 论文缓存
│   │   ├── ARCHITECTURE.md          # 架构文档
│   │   └── README.md                # 说明文档
│   ├── database_call/               # 数据库调用MCP服务
│   │   ├── server.py                # MCP服务器
│   │   ├── ARCHITECTURE.md          # 架构文档
│   │   └── README.md                # 说明文档
│   ├── simulation/                  # 仿真计算MCP服务
│   │   ├── server.py                # MCP服务器
│   │   ├── crystallm/               # CrystaLLM模型
│   │   ├── kappa_lib/               # 热导率计算库
│   │   ├── modules/                 # 功能模块
│   │   ├── models/                  # 模型文件
│   │   ├── data/                    # 数据文件
│   │   ├── phonon_results/          # 声子计算结果
│   │   ├── ARCHITECTURE.md          # 架构文档
│   │   └── README.md                # 说明文档
│   └── session_data/                # 会话数据存储
│       ├── images/                  # 图片文件
│       ├── metadata/                # 元数据
│       └── structures/              # 结构文件
│
├── services/                        # 服务层
│   ├── http_server.py               # HTTP API服务器
│   ├── websocket_server.py          # WebSocket服务器
│   ├── agent_coordinator.py         # 智能体协调器
│   ├── message_handler.py           # 消息处理器
│   ├── session_manager.py           # 会话管理器
│   ├── data_processor.py            # 数据处理器
│   ├── structure_converter.py       # 结构转换器
│   ├── image_handler.py             # 图片处理器
│   ├── llm_wrapper.py               # LLM包装器
│   ├── static_file_service.py       # 静态文件服务
│   ├── json_repair_patch.py         # JSON修复补丁
│   ├── config.py                    # 配置管理
│   ├── ARCHITECTURE.md              # 架构文档
│   └── README.md                    # 说明文档
│
├── ui/                              # 前端层
│   ├── src/                         # 源代码
│   ├── index.html                   # 入口HTML
│   ├── package.json                 # 依赖配置
│   ├── vite.config.ts               # Vite配置
│   ├── tailwind.config.js           # Tailwind配置
│   ├── postcss.config.js            # PostCSS配置
│   ├── QUICK_START.md               # 快速开始
│   └── README.md                    # 说明文档
│
├── session_data/                    # 会话数据
│   ├── images/                      # 图片存储
│   ├── metadata/                    # 元数据存储
│   ├── structures/                  # 结构文件存储
│   └── session_registry.json        # 会话注册表
│
├── logs/                            # 日志文件
│   ├── backend.log                  # 后端日志
│   ├── frontend.log                 # 前端日志
│   ├── database.log                 # 数据库MCP日志
│   ├── paper_search.log             # 论文搜索MCP日志
│   ├── simulation.log               # 仿真MCP日志
│   ├── access.log                   # Nginx访问日志
│   └── error.log                    # Nginx错误日志
│
├── docs/                            # 项目文档
│   ├── tech-stack.md                # 技术栈文档
│   ├── architecture.md              # 本文件
│   ├── implementation-plan.md       # 实现计划
│   └── progress.md                  # 进度追踪
│
├── main.py                          # 主入口文件
├── pyproject.toml                   # Python项目配置
├── uv.lock                          # uv锁文件
├── .env                             # 环境变量（本地）
├── .env.remote.example              # 环境变量模板（远程）
├── start.sh                         # Windows启动脚本
├── start_linux.sh                   # Linux启动脚本
├── stop_linux.sh                    # Linux停止脚本
├── setup_nginx.sh                   # Nginx配置脚本
├── nginx_windows.conf               # Windows Nginx配置
├── README.md                        # 项目说明
└── INTRO.md                         # 项目介绍
```

---

## 🏗️ 系统架构

### 分层架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户界面层                               │
│                    React + TypeScript + Vite                    │
│                  (端口: 50010, 通过Nginx:50001访问)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                         服务层                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  HTTP Server     │  │ WebSocket Server │  │ Static Files │  │
│  │  (FastAPI)       │  │  (WebSocket)     │  │   Service    │  │
│  │  端口: 50002     │  │  端口: 50003     │  │              │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│           ↓                      ↓                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Agent Coordinator (智能体协调器)               │  │
│  │         Message Handler | Session Manager                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓ Google ADK
┌─────────────────────────────────────────────────────────────────┐
│                         智能体层                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              总智能体 (Coordinator Agent)                 │  │
│  │                   Google ADK + Gemini                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│           ↓                  ↓                  ↓               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Deep Research│    │  Database   │    │ Simulation  │        │
│  │    Agent     │    │    Agent    │    │   Agent     │        │
│  │  文献研究助手 │    │ 数据库助手   │    │  仿真助手    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↓ MCP Protocol
┌─────────────────────────────────────────────────────────────────┐
│                         MCP服务层                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │Paper Search │    │  Database   │    │ Simulation  │        │
│  │ MCP Server  │    │ MCP Server  │    │ MCP Server  │        │
│  │ 端口: 50004  │    │ 端口: 50006  │    │ 端口: 50005  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         ↓                  ↓                  ↓                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ ArXiv API   │    │Materials    │    │ CrystaLLM   │        │
│  │ Tavily API  │    │ Project API │    │ MatterSim   │        │
│  │ Scholar API │    │ AFLOW API   │    │ Kappa Lib   │        │
│  │ ChromaDB    │    │ QMPY API    │    │ ASE/Pymatgen│        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 数据流

### 1. 用户请求流程

```
用户输入
  ↓
前端UI (React)
  ↓ HTTP/WebSocket
Nginx (50001)
  ↓ 反向代理
WebSocket Server (50003)
  ↓
Message Handler
  ↓
Agent Coordinator
  ↓
总智能体 (Coordinator Agent)
  ↓ 任务分解
专业子智能体 (Deep Research / Database / Simulation)
  ↓ MCP调用
MCP服务器 (Paper Search / Database / Simulation)
  ↓ 外部API
外部服务 (ArXiv, Materials Project, CrystaLLM等)
  ↓ 结果返回
MCP服务器
  ↓
专业子智能体
  ↓ 结果汇总
总智能体
  ↓
Message Handler
  ↓
WebSocket Server
  ↓
前端UI
  ↓
用户查看结果
```

### 2. 会话管理流程

```
新会话创建
  ↓
Session Manager 生成 session_id
  ↓
创建会话目录结构
  - session_data/images/{session_id}/
  - session_data/metadata/{session_id}/
  - session_data/structures/{session_id}/
  ↓
注册到 session_registry.json
  ↓
会话进行中
  - 保存对话历史
  - 保存生成的图片
  - 保存结构文件
  - 保存元数据
  ↓
会话结束
  - 保留会话数据
  - 可恢复历史会话
```

---

## 🧩 核心组件详解

### 1. 前端层 (ui/)

#### 主要职责
- 用户界面渲染
- 用户交互处理
- WebSocket通信
- 3D结构可视化
- Markdown渲染

#### 关键文件
- `src/` - React组件源代码
- `vite.config.ts` - Vite构建配置
- `tailwind.config.js` - 样式配置

---

### 2. 服务层 (services/)

#### http_server.py
- **职责**: 提供RESTful API
- **端口**: 50002
- **功能**:
  - 健康检查 `/health`
  - API文档 `/docs`
  - 静态文件服务

#### websocket_server.py
- **职责**: 实时双向通信
- **端口**: 50003
- **功能**:
  - 接收用户消息
  - 推送智能体响应
  - 流式输出支持

#### agent_coordinator.py
- **职责**: 协调智能体工作
- **功能**:
  - 初始化总智能体
  - 管理子智能体
  - 任务分发与结果汇总

#### message_handler.py
- **职责**: 消息处理与路由
- **功能**:
  - 解析用户消息
  - 调用智能体
  - 格式化响应

#### session_manager.py
- **职责**: 会话生命周期管理
- **功能**:
  - 创建/恢复会话
  - 保存对话历史
  - 管理会话数据

#### data_processor.py
- **职责**: 数据处理与转换
- **功能**:
  - 数据清洗
  - 格式转换
  - 结果聚合

#### structure_converter.py
- **职责**: 材料结构格式转换
- **功能**:
  - CIF ↔ POSCAR
  - JSON ↔ ASE Atoms
  - 结构可视化数据生成

#### image_handler.py
- **职责**: 图片处理与存储
- **功能**:
  - 图片生成
  - 图片保存
  - 图片URL管理

---

### 3. 智能体层 (agents/)

#### agent.py (总智能体)
- **职责**: 协调统筹所有子智能体
- **技术**: Google ADK + Gemini
- **功能**:
  - 理解用户意图
  - 任务分解
  - 调用子智能体
  - 结果整合

#### deep_research_agent/ (文献研究智能体)
- **职责**: 文献调研与分析
- **MCP**: Paper Search MCP (50004)
- **功能**:
  - ArXiv论文搜索
  - Google Scholar检索
  - Tavily网络搜索
  - 文献摘要生成
  - 向量数据库检索

#### database_agent/ (数据库查询智能体)
- **职责**: 材料数据库查询
- **MCP**: Database MCP (50006)
- **功能**:
  - Materials Project查询
  - AFLOW数据库查询
  - QMPY数据库查询
  - 数据聚合与分析

#### simulation_agent/ (仿真计算智能体)
- **职责**: 材料性质预测与仿真
- **MCP**: Simulation MCP (50005)
- **功能**:
  - CrystaLLM结构生成
  - MatterSim性质预测
  - 热导率计算
  - 声子谱计算

---

### 4. MCP服务层 (mcp_servers/)

#### paper_search/ (论文搜索MCP)
- **端口**: 50004
- **协议**: MCP (Model Context Protocol)
- **工具**:
  - `search_arxiv` - ArXiv搜索
  - `search_scholar` - Google Scholar搜索
  - `search_tavily` - Tavily网络搜索
  - `vector_search` - 向量数据库检索
- **存储**: ChromaDB向量数据库

#### database_call/ (数据库MCP)
- **端口**: 50006
- **协议**: MCP
- **工具**:
  - `query_materials_project` - MP查询
  - `query_aflow` - AFLOW查询
  - `query_qmpy` - QMPY查询
  - `aggregate_data` - 数据聚合

#### simulation/ (仿真MCP)
- **端口**: 50005
- **协议**: MCP
- **工具**:
  - `generate_structure` - CrystaLLM结构生成
  - `predict_properties` - MatterSim性质预测
  - `calculate_thermal` - 热导率计算
  - `phonon_calculation` - 声子计算
- **模型**:
  - CrystaLLM - 晶体结构生成
  - MatterSim - 材料性质预测
  - Kappa Lib - 热导率计算库

---

## 🌐 网络架构

### Nginx反向代理配置

```nginx
# 统一入口: 50001
server {
    listen 50001;
    
    # 前端
    location / {
        proxy_pass http://127.0.0.1:50010;
    }
    
    # 后端API
    location /api/ {
        proxy_pass http://127.0.0.1:50002/api/;
    }
    
    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:50003/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:50002/health;
    }
}
```

---

## 📊 数据存储

### 文件系统存储

```
session_data/
├── images/              # 图片文件
│   └── {session_id}/
│       └── *.png
├── metadata/            # 元数据
│   └── {session_id}/
│       └── *.json
├── structures/          # 结构文件
│   └── {session_id}/
│       ├── *.cif
│       └── *.vasp
└── session_registry.json  # 会话注册表
```

### 向量数据库 (ChromaDB)
- **用途**: 文献向量检索
- **位置**: `mcp_servers/paper_search/`
- **功能**: 语义搜索、相似文献推荐

---

## 🔐 安全设计

### 网络隔离
- **对外**: 仅Nginx端口50001
- **内部**: MCP服务仅监听127.0.0.1

### API密钥管理
- 环境变量存储
- 不提交到版本控制
- 支持多环境配置

---

## 📚 相关文档

- [tech-stack.md](./tech-stack.md) - 技术栈详解
- [implementation-plan.md](./implementation-plan.md) - 实现计划
- [progress.md](./progress.md) - 开发进度

