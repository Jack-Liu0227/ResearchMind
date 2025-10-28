# ResearchMind 实现计划

## 📋 项目目标

ResearchMind 是一个创新的多智能体协作平台，专为材料科学研究人员设计。系统通过 Google ADK (Agent Development Kit) 和 MCP (Model Context Protocol) 技术，实现了从文献调研、数据库检索到仿真计算的全流程自动化研究支持。

### 核心目标
1. **文献调研自动化** - 提供高效、准确的文献检索与分析
2. **数据库集成** - 整合多个材料科学数据库
3. **仿真计算支持** - 提供材料性质预测和仿真计算
4. **智能体协作** - 实现多智能体协同工作
5. **用户友好界面** - 提供直观的Web界面

---

## 🏗️ 系统架构设计

### 分层架构

```
┌─────────────────────────────────────────┐
│         前端层 (UI Layer)                │
│    React + TypeScript + Vite            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│       服务层 (Service Layer)             │
│   FastAPI + WebSocket + HTTP            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│       智能体层 (Agent Layer)             │
│  总智能体 + 3个专业子智能体               │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│        MCP层 (MCP Servers)              │
│  Paper Search | Database | Simulation   │
└─────────────────────────────────────────┘
```

---

## 📅 开发阶段

### 阶段1: 基础架构搭建 ✅

#### 1.1 项目初始化
- [x] 创建项目目录结构
- [x] 配置Python环境 (pyproject.toml)
- [x] 配置Node.js环境 (package.json)
- [x] 设置版本控制 (Git)

#### 1.2 开发环境配置
- [x] 配置uv包管理器
- [x] 配置npm包管理器
- [x] 创建环境变量模板 (.env)
- [x] 配置开发工具 (Black, isort, ESLint)

#### 1.3 基础服务搭建
- [x] 实现HTTP服务器 (FastAPI)
- [x] 实现WebSocket服务器
- [x] 配置Nginx反向代理
- [x] 实现健康检查端点

---

### 阶段2: MCP服务层开发 ✅

#### 2.1 Paper Search MCP
- [x] 实现MCP服务器框架
- [x] 集成ArXiv API
- [x] 集成Google Scholar API
- [x] 集成Tavily搜索API
- [x] 实现ChromaDB向量数据库
- [x] 实现向量检索功能
- [x] 实现论文缓存机制

#### 2.2 Database MCP
- [x] 实现MCP服务器框架
- [x] 集成Materials Project API
- [x] 集成AFLOW API
- [x] 集成QMPY API
- [x] 实现数据聚合功能
- [x] 实现数据缓存机制

#### 2.3 Simulation MCP
- [x] 实现MCP服务器框架
- [x] 集成CrystaLLM模型
- [x] 集成MatterSim模型
- [x] 实现Kappa热导率计算库
- [x] 实现声子谱计算
- [x] 实现结构优化功能

---

### 阶段3: 智能体层开发 ✅

#### 3.1 总智能体 (Coordinator Agent)
- [x] 实现Google ADK集成
- [x] 配置Gemini模型
- [x] 实现任务分解逻辑
- [x] 实现子智能体调用
- [x] 实现结果整合
- [x] 设计提示词模板

#### 3.2 Deep Research Agent (文献研究智能体)
- [x] 实现智能体框架
- [x] 连接Paper Search MCP
- [x] 实现文献检索逻辑
- [x] 实现文献分析功能
- [x] 实现摘要生成
- [x] 设计专业提示词

#### 3.3 Database Agent (数据库查询智能体)
- [x] 实现智能体框架
- [x] 连接Database MCP
- [x] 实现数据库查询逻辑
- [x] 实现数据分析功能
- [x] 实现结果可视化
- [x] 设计专业提示词

#### 3.4 Simulation Agent (仿真计算智能体)
- [x] 实现智能体框架
- [x] 连接Simulation MCP
- [x] 实现仿真任务调度
- [x] 实现结果处理
- [x] 实现结构可视化
- [x] 设计专业提示词

---

### 阶段4: 服务层开发 ✅

#### 4.1 核心服务
- [x] Agent Coordinator - 智能体协调器
- [x] Message Handler - 消息处理器
- [x] Session Manager - 会话管理器
- [x] Data Processor - 数据处理器

#### 4.2 辅助服务
- [x] Structure Converter - 结构转换器
- [x] Image Handler - 图片处理器
- [x] LLM Wrapper - LLM包装器
- [x] Static File Service - 静态文件服务

#### 4.3 配置与工具
- [x] Config - 配置管理
- [x] JSON Repair Patch - JSON修复
- [x] 日志系统 (Structlog)
- [x] 错误处理机制

---

### 阶段5: 前端开发 ✅

#### 5.1 基础框架
- [x] React项目初始化
- [x] TypeScript配置
- [x] Vite构建配置
- [x] Tailwind CSS配置
- [x] 路由配置 (React Router)

#### 5.2 核心组件
- [x] 聊天界面组件
- [x] 消息显示组件
- [x] Markdown渲染组件
- [x] 代码高亮组件
- [x] 3D结构可视化组件

#### 5.3 状态管理
- [x] Zustand状态管理
- [x] React Query数据获取
- [x] WebSocket连接管理
- [x] 会话状态管理

#### 5.4 UI/UX优化
- [x] 响应式设计
- [x] 动画效果 (Framer Motion)
- [x] 通知系统 (React Hot Toast)
- [x] 加载状态处理
- [x] 错误提示优化

---

### 阶段6: 部署与运维 ✅

#### 6.1 Windows部署
- [x] Windows启动脚本 (start.sh)
- [x] Windows Nginx配置
- [x] 环境变量配置
- [x] 依赖安装脚本

#### 6.2 Linux部署
- [x] Linux启动脚本 (start_linux.sh)
- [x] Linux停止脚本 (stop_linux.sh)
- [x] Nginx自动配置脚本 (setup_nginx.sh)
- [x] 环境变量模板 (.env.remote.example)
- [x] 防火墙配置
- [x] 进程管理

#### 6.3 运维工具
- [x] 日志管理
- [x] 健康检查
- [x] 进程监控
- [x] 自动重启机制

---

## 🔧 技术实现细节

### 1. Google ADK集成

```python
# 总智能体使用Google ADK
from google.adk import Agent

coordinator_agent = Agent(
    model="gemini-2.0-flash-exp",
    tools=[
        deep_research_agent,
        database_agent,
        simulation_agent
    ],
    system_instruction=COORDINATOR_PROMPT
)
```

### 2. MCP协议实现

```python
# MCP服务器实现
from fastmcp import FastMCP

mcp = FastMCP("paper_search")

@mcp.tool()
async def search_arxiv(query: str, max_results: int = 10):
    """搜索ArXiv论文"""
    # 实现逻辑
    pass
```

### 3. WebSocket通信

```python
# WebSocket服务器
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = await session_manager.create_session()
    
    async for message in websocket.iter_text():
        response = await agent_coordinator.process(message, session_id)
        await websocket.send_json(response)
```

### 4. 前端WebSocket连接

```typescript
// WebSocket客户端
const ws = new WebSocket('ws://localhost:50001/ws');

ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    updateChat(response);
};

ws.send(JSON.stringify({ message: userInput }));
```

---

## 📊 数据流设计

### 用户请求处理流程

```
1. 用户输入 → 前端UI
2. 前端UI → WebSocket → 后端服务器
3. 后端服务器 → Message Handler
4. Message Handler → Agent Coordinator
5. Agent Coordinator → 总智能体
6. 总智能体 → 任务分解 → 调用子智能体
7. 子智能体 → MCP服务器 → 外部API
8. 外部API → 返回数据 → MCP服务器
9. MCP服务器 → 子智能体 → 总智能体
10. 总智能体 → 结果整合 → Agent Coordinator
11. Agent Coordinator → Message Handler
12. Message Handler → WebSocket → 前端UI
13. 前端UI → 显示结果 → 用户
```

---

## 🎯 功能实现清单

### 核心功能

- [x] **文献检索**
  - [x] ArXiv搜索
  - [x] Google Scholar搜索
  - [x] Tavily网络搜索
  - [x] 向量语义检索

- [x] **数据库查询**
  - [x] Materials Project查询
  - [x] AFLOW查询
  - [x] QMPY查询
  - [x] 数据聚合分析

- [x] **仿真计算**
  - [x] CrystaLLM结构生成
  - [x] MatterSim性质预测
  - [x] 热导率计算
  - [x] 声子谱计算

- [x] **智能体协作**
  - [x] 任务自动分解
  - [x] 多智能体协同
  - [x] 结果智能整合

- [x] **用户界面**
  - [x] 聊天式交互
  - [x] Markdown渲染
  - [x] 3D结构可视化
  - [x] 实时响应

### 辅助功能

- [x] **会话管理**
  - [x] 会话创建
  - [x] 会话恢复
  - [x] 历史记录

- [x] **文件管理**
  - [x] 图片保存
  - [x] 结构文件保存
  - [x] 元数据保存

- [x] **格式转换**
  - [x] CIF ↔ POSCAR
  - [x] JSON ↔ ASE Atoms
  - [x] 结构可视化数据

---

## 🚀 部署方案

### Windows部署

```bash
# 1. 配置环境
cp .env.example .env
nano .env  # 填写API Keys

# 2. 启动服务
bash start.sh
```

### Linux部署

```bash
# 1. 配置环境
cp .env.remote.example .env.remote
nano .env.remote  # 填写API Keys

# 2. 配置Nginx
sudo bash setup_nginx.sh

# 3. 启动服务
bash start_linux.sh
```

---

## 📈 性能优化

### 已实现优化

- [x] **异步I/O** - FastAPI + HTTPX异步处理
- [x] **WebSocket长连接** - 减少连接开销
- [x] **向量数据库** - ChromaDB快速检索
- [x] **结果缓存** - 减少重复计算
- [x] **代码分割** - Vite动态导入
- [x] **资源压缩** - Vite生产构建优化

### 待优化项

- [ ] **Redis缓存** - 分布式缓存
- [ ] **负载均衡** - Nginx多实例
- [ ] **CDN加速** - 静态资源CDN
- [ ] **数据库连接池** - SQLAlchemy优化

---

## 🔐 安全措施

### 已实现

- [x] **API密钥管理** - 环境变量存储
- [x] **网络隔离** - MCP服务内部访问
- [x] **反向代理** - Nginx统一入口
- [x] **防火墙配置** - 仅开放必要端口

### 待实现

- [ ] **HTTPS支持** - SSL/TLS加密
- [ ] **用户认证** - JWT Token
- [ ] **访问控制** - RBAC权限管理
- [ ] **审计日志** - 操作记录

---

## 📚 文档计划

### 已完成文档

- [x] README.md - 项目说明
- [x] INTRO.md - 项目介绍
- [x] tech-stack.md - 技术栈文档
- [x] architecture.md - 系统架构文档
- [x] implementation-plan.md - 本文件
- [x] 各模块ARCHITECTURE.md - 模块架构文档
- [x] 各模块README.md - 模块说明文档

### 待完成文档

- [ ] API文档 - 详细API说明
- [ ] 用户手册 - 使用指南
- [ ] 开发者指南 - 贡献指南
- [ ] 部署手册 - 详细部署说明

---

## 🎯 下一步计划

### 短期目标 (1-2周)

1. **功能增强**
   - [ ] 添加更多数据库支持
   - [ ] 优化文献检索算法
   - [ ] 增强仿真计算能力

2. **性能优化**
   - [ ] 实现Redis缓存
   - [ ] 优化数据库查询
   - [ ] 前端性能优化

3. **用户体验**
   - [ ] 添加用户认证
   - [ ] 优化UI/UX
   - [ ] 添加更多可视化

### 中期目标 (1-3个月)

1. **功能扩展**
   - [ ] 支持批量处理
   - [ ] 添加实验设计建议
   - [ ] 集成更多AI模型

2. **系统优化**
   - [ ] 实现分布式部署
   - [ ] 添加监控告警
   - [ ] 优化资源使用

3. **文档完善**
   - [ ] 完整API文档
   - [ ] 用户使用手册
   - [ ] 开发者指南

### 长期目标 (3-6个月)

1. **平台化**
   - [ ] 多租户支持
   - [ ] 插件系统
   - [ ] 开放API

2. **智能化**
   - [ ] 自动实验设计
   - [ ] 智能推荐系统
   - [ ] 知识图谱构建

3. **社区建设**
   - [ ] 开源发布
   - [ ] 社区贡献
   - [ ] 生态建设

---

## 📝 总结

ResearchMind项目已完成核心功能开发，实现了从文献调研、数据库查询到仿真计算的全流程自动化支持。系统采用分层架构设计，通过Google ADK和MCP技术实现多智能体协作，为材料科学研究人员提供了强大的研究工具。

下一步将重点关注性能优化、功能扩展和用户体验提升，逐步实现平台化和智能化目标。

