# ResearchMind UI 快速启动指南

## 🚀 快速开始

### 1. 环境准备

确保您的系统已安装：
- **Node.js** >= 16.0.0 ([下载地址](https://nodejs.org/))
- **npm** 或 **yarn** 或 **pnpm**

### 2. 安装依赖

在 `ui` 目录下运行：

```bash
# 使用 npm
npm install

# 或使用 yarn
yarn install

# 或使用 pnpm
pnpm install
```

### 3. 环境配置

复制环境变量文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，确保后端地址正确：

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

### 4. 启动开发服务器

```bash
# 使用 npm
npm run dev

# 或使用 yarn
yarn dev

# 或使用 pnpm
pnpm dev
```

### 5. 访问应用

打开浏览器访问：`http://localhost:5173`

## 🎯 主要功能

### 智能体选择
- 点击顶部的智能体选择器
- 选择合适的智能体（研究协调器、文献智能体、数据库智能体、仿真智能体）

### 开始对话
- 在底部输入框输入您的问题
- 按 Enter 发送，Shift + Enter 换行
- 支持 Markdown 格式的回复

### 对话管理
- 左侧边栏显示对话历史
- 点击"新对话"创建新的会话
- 支持重命名和删除对话

### 结构展示
- 右侧面板显示晶体结构
- 支持 3D 交互式查看
- 显示结构详细信息

## 🔧 Windows 用户

可以直接双击运行：
- `scripts/start.bat` - 启动开发服务器
- `scripts/build.bat` - 构建生产版本

## ⚠️ 常见问题

### 1. 端口被占用
如果 5173 端口被占用，Vite 会自动选择下一个可用端口。

### 2. 连接后端失败
- 确保后端服务正在运行（通常在 8000 端口）
- 检查 `.env` 文件中的 API 地址是否正确
- 查看浏览器控制台的错误信息

### 3. 依赖安装失败
- 尝试清除缓存：`npm cache clean --force`
- 删除 `node_modules` 文件夹后重新安装
- 使用国内镜像：`npm config set registry https://registry.npmmirror.com`

### 4. 构建失败
- 运行类型检查：`npm run type-check`
- 检查 TypeScript 错误并修复

## 📝 开发提示

### 热重载
开发模式下，修改代码会自动刷新页面。

### 调试
- 打开浏览器开发者工具
- 查看 Console 面板的日志信息
- 使用 Network 面板检查 API 请求

### 代码格式化
```bash
npm run lint
```

## 🏗️ 生产部署

### 构建
```bash
npm run build
```

### 预览
```bash
npm run preview
```

构建产物在 `dist` 目录中，可以部署到任何静态文件服务器。

## 📞 获取帮助

如果遇到问题：
1. 查看浏览器控制台错误
2. 检查后端服务状态
3. 参考完整的 README.md 文档
4. 提交 Issue 到项目仓库

---

**祝您使用愉快！** 🎉