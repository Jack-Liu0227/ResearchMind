# ResearchMind Frontend

> 基于 React + TypeScript + Vite 的材料科学研究助手前端界面

## 📖 概述

ResearchMind Frontend 是一个现代化的单页应用（SPA），为材料科学研究人员提供直观、高效的交互界面。它通过WebSocket与后端实时通信，支持晶体结构3D可视化、文件查看、声子谱展示等功能。

## ✨ 核心功能

### 1. 智能对话界面
- 实时消息流
- Markdown渲染
- 代码高亮
- 打字机效果
- 消息历史记录

### 2. 晶体结构可视化
- **3D渲染** (Three.js)
  - 40+种元素颜色（CPK配色方案）
  - 原子球体和化学键
  - 鼠标交互（旋转、缩放、平移）
  - 自动相机定位
- **结构信息展示**
  - 化学式
  - 晶格参数 (a, b, c, α, β, γ)
  - 原子列表
  - 空间群信息

### 3. 文件查看器
- **CSV查看器**
  - 表格展示
  - 可滚动（最大高度400px）
  - 智能CSV解析
  - 下载功能
  - 行数统计
- **Markdown查看器**
  - GFM (GitHub Flavored Markdown) 支持
  - 目录导航（自动提取H1-H6标题）
  - 代码高亮
  - 可折叠/展开（默认展开）
  - 平滑滚动
  - 下载功能

### 4. 声子谱可视化
- 声子色散图
- 声子态密度图
- 图片缩放和下载

### 5. 拖拽布局
- **左侧边栏**
  - 可拖拽调整宽度（200px - 600px）
  - 对话历史
  - 快速切换
- **右侧面板**
  - 可拖拽调整宽度（200px - 600px）
  - 结构查看器
  - 声子谱查看器
  - 上下分割可调整
- **中央内容区**
  - 自动适应宽度
  - 居中显示

## 🏗️ 技术栈

### 核心框架
- **React 18** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具

### UI库
- **TailwindCSS** - 样式框架
- **Headless UI** - 无样式组件
- **Lucide React** - 图标库

### 3D渲染
- **Three.js** - 3D图形库
- **@react-three/fiber** - React Three.js集成
- **@react-three/drei** - Three.js辅助工具

### 数据处理
- **ReactMarkdown** - Markdown渲染
- **remark-gfm** - GitHub Flavored Markdown
- **react-syntax-highlighter** - 代码高亮

### 状态管理
- **Zustand** - 轻量级状态管理

### 网络通信
- **WebSocket API** - 实时通信
- **Fetch API** - HTTP请求

## 📁 项目结构

```
ui/
├── src/
│   ├── components/              # React组件
│   │   ├── ChatInterface.tsx    # 聊天界面
│   │   ├── MessageList.tsx      # 消息列表
│   │   ├── Layout.tsx           # 主布局
│   │   ├── Sidebar.tsx          # 左侧边栏
│   │   ├── RightPanel.tsx       # 右侧面板
│   │   ├── StructureViewerThreeJS.tsx  # 3D结构查看器
│   │   ├── StructureList.tsx    # 结构列表
│   │   ├── FileViewer/          # 文件查看器
│   │   │   ├── CsvViewer.tsx    # CSV查看器
│   │   │   ├── MarkdownViewer.tsx  # Markdown查看器
│   │   │   └── index.ts
│   │   ├── ErrorBoundary.tsx    # 错误边界
│   │   └── StorageValidator.tsx # 存储验证
│   ├── pages/                   # 页面
│   │   ├── ChatPage.tsx         # 聊天页面
│   │   └── Dashboard.tsx        # 仪表板
│   ├── services/                # 服务
│   │   └── websocket.ts         # WebSocket服务
│   ├── store/                   # 状态管理
│   │   └── index.ts             # Zustand store
│   ├── types/                   # TypeScript类型
│   │   └── index.ts
│   ├── App.tsx                  # 应用入口
│   ├── main.tsx                 # 主入口
│   └── index.css                # 全局样式
├── public/                      # 静态资源
├── index.html                   # HTML模板
├── package.json                 # 依赖配置
├── tsconfig.json                # TypeScript配置
├── vite.config.ts               # Vite配置
└── tailwind.config.js           # TailwindCSS配置
```

## 🚀 快速开始

### 安装依赖

```bash
cd ui
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问: http://localhost:5173

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 📚 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - UI架构详解
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - 系统整体架构
- [../services/README.md](../services/README.md) - Backend服务文档

## 📄 许可证

MIT License
