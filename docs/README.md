# ResearchMind 项目文档

本文件夹包含 ResearchMind 项目的完整文档，用于追踪项目进度、技术架构和实现计划。

---

## 📚 文档列表

### 1. [tech-stack.md](./tech-stack.md) - 技术栈文档

**用途**: 详细记录项目使用的所有技术和工具

**内容包括**:
- 前端技术栈 (React, TypeScript, Vite等)
- 后端技术栈 (FastAPI, Google ADK, MCP等)
- 数据处理与科学计算库
- 数据库与存储方案
- 材料科学数据库API
- 部署技术栈
- 网络架构与端口分配
- 依赖管理方案

**适合阅读对象**: 开发者、技术架构师、新成员

---

### 2. [architecture.md](./architecture.md) - 系统架构文档

**用途**: 记录系统的整体架构设计和各模块的职责

**内容包括**:
- 完整的目录结构
- 分层架构设计
- 数据流图
- 核心组件详解
  - 前端层 (ui/)
  - 服务层 (services/)
  - 智能体层 (agents/)
  - MCP服务层 (mcp_servers/)
- 网络架构与Nginx配置
- 数据存储方案
- 安全设计

**适合阅读对象**: 架构师、开发者、系统管理员

---

### 3. [implementation-plan.md](./implementation-plan.md) - 实现计划文档

**用途**: 记录项目的实现计划和开发路线图

**内容包括**:
- 项目目标与核心特性
- 系统架构设计
- 开发阶段划分
  - 阶段1: 基础架构搭建
  - 阶段2: MCP服务层开发
  - 阶段3: 智能体层开发
  - 阶段4: 服务层开发
  - 阶段5: 前端开发
  - 阶段6: 部署与运维
- 技术实现细节
- 数据流设计
- 功能实现清单
- 部署方案
- 性能优化计划
- 安全措施
- 下一步计划

**适合阅读对象**: 项目经理、开发者、产品经理

---

### 4. [progress.md](./progress.md) - 开发进度追踪文档

**用途**: 实时追踪项目的开发进度和完成情况

**内容包括**:
- 总体进度概览
- 已完成功能清单
  - 基础架构 (100%)
  - MCP服务层 (100%)
  - 智能体层 (100%)
  - 服务层 (100%)
  - 前端层 (100%)
  - 部署运维 (100%)
  - 文档 (90%)
- 进行中的工作
- 待完成功能
- 里程碑记录
- 已知问题
- 代码统计
- 下一步计划
- 更新日志

**适合阅读对象**: 所有项目成员、项目经理、利益相关者

---

## 🎯 文档使用指南

### 新成员入门

如果你是新加入的团队成员，建议按以下顺序阅读文档：

1. **README.md** (项目根目录) - 了解项目基本信息和快速启动
2. **tech-stack.md** - 了解项目使用的技术栈
3. **architecture.md** - 理解系统架构和各模块职责
4. **implementation-plan.md** - 了解项目的实现计划和开发路线
5. **progress.md** - 查看当前开发进度和待完成任务

### 开发者

- **开发新功能前**: 查看 `implementation-plan.md` 和 `progress.md`
- **了解技术细节**: 查看 `tech-stack.md`
- **理解模块职责**: 查看 `architecture.md`
- **更新进度**: 及时更新 `progress.md`

### 项目经理

- **追踪进度**: 定期查看 `progress.md`
- **规划任务**: 参考 `implementation-plan.md`
- **评估风险**: 查看 `progress.md` 中的已知问题

### 架构师

- **系统设计**: 参考 `architecture.md`
- **技术选型**: 参考 `tech-stack.md`
- **优化方向**: 查看 `implementation-plan.md` 中的优化计划

---

## 📝 文档更新规范

### 更新频率

- **progress.md**: 每周更新一次，记录本周完成的工作
- **implementation-plan.md**: 每月更新一次，调整下一步计划
- **architecture.md**: 架构变更时更新
- **tech-stack.md**: 技术栈变更时更新

### 更新流程

1. 修改相应文档
2. 在 `progress.md` 的更新日志中记录变更
3. 提交Git commit，注明文档更新内容

### 更新示例

```markdown
### 2025-10-28
- ✅ 完成Redis缓存集成
- ✅ 优化数据库连接池
- ✅ 更新tech-stack.md，添加Redis相关内容
- ✅ 更新architecture.md，添加缓存层架构图
```

---

## 🔗 相关文档链接

### 项目根目录文档
- [README.md](../README.md) - 项目说明和快速启动
- [INTRO.md](../INTRO.md) - 项目介绍

### 模块文档
- [agents/ARCHITECTURE.md](../agents/ARCHITECTURE.md) - 智能体层架构
- [agents/README.md](../agents/README.md) - 智能体层说明
- [services/ARCHITECTURE.md](../services/ARCHITECTURE.md) - 服务层架构
- [services/README.md](../services/README.md) - 服务层说明
- [mcp_servers/paper_search/ARCHITECTURE.md](../mcp_servers/paper_search/ARCHITECTURE.md) - 论文搜索MCP架构
- [mcp_servers/database_call/ARCHITECTURE.md](../mcp_servers/database_call/ARCHITECTURE.md) - 数据库MCP架构
- [mcp_servers/simulation/ARCHITECTURE.md](../mcp_servers/simulation/ARCHITECTURE.md) - 仿真MCP架构
- [ui/README.md](../ui/README.md) - 前端说明
- [ui/QUICK_START.md](../ui/QUICK_START.md) - 前端快速开始

---

## 📊 文档结构图

```
docs/
├── README.md                    # 本文件 - 文档索引
├── tech-stack.md                # 技术栈文档
├── architecture.md              # 系统架构文档
├── implementation-plan.md       # 实现计划文档
└── progress.md                  # 进度追踪文档
```

---

## 🎯 项目目标

ResearchMind 是一个创新的多智能体协作平台，专为材料科学研究人员设计。系统通过 Google ADK (Agent Development Kit) 和 MCP (Model Context Protocol) 技术，实现了从文献调研、数据库检索到仿真计算的全流程自动化研究支持。

### 核心特性

- 🤖 **多智能体协作**: 总智能体协调三个专业子智能体
- 📚 **文献调研**: 以文献研究为底座，提供高效准确的文献分析
- 🗄️ **数据库查询**: 集成多个材料科学数据库
- 🧪 **仿真计算**: 支持材料性质预测和仿真计算
- 🔄 **全流程自动化**: 从调研到实验设计的完整工作流

---

## 📞 联系方式

如有文档相关问题，请联系项目维护者。

---

**最后更新**: 2025-10-28

