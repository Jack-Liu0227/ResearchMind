# ResearchMind Nginx和端口配置指南

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户浏览器                                 │
│                  http://127.0.0.1:50001                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nginx反向代理                              │
│                  监听端口: 50001                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 路由规则:                                             │   │
│  │ /api/*  → http://127.0.0.1:8000 (后端API)           │   │
│  │ /*      → http://127.0.0.1:8001 (前端UI)            │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│   后端API服务    │          │   前端UI服务     │
│  端口: 8000      │          │  端口: 8001      │
│  FastAPI        │          │  Vite Dev Server │
│  - CIF上传       │          │  - React应用     │
│  - 结构转换      │          │  - 用户界面      │
│  - 数据处理      │          │  - 交互逻辑      │
└──────────────────┘          └──────────────────┘
```

## 端口说明

### 外部端口（用户访问）

| 端口 | 服务 | 说明 |
|------|------|------|
| **50001** | Nginx反向代理 | 用户访问的唯一入口 |

### 内部端口（服务间通信）

| 端口 | 服务 | 说明 |
|------|------|------|
| **8000** | 后端API (FastAPI) | 处理CIF上传、结构转换等 |
| **8001** | 前端UI (Vite) | React应用，用户界面 |

## 为什么使用Nginx反向代理？

### 问题1：跨域请求（CORS）
- 前端运行在 http://127.0.0.1:8001
- 后端运行在 http://127.0.0.1:8000
- 浏览器会阻止跨域请求

### 问题2：大文件上传
- CIF文件可能很大
- Nginx默认缓冲会截断文件
- 需要禁用缓冲

### 问题3：端口统一
- 用户只需访问一个端口（50001）
- 所有请求自动路由到正确的服务
- 简化部署和配置

## Nginx配置详解

### 配置文件位置

| 操作系统 | 位置 |
|---------|------|
| Windows | `C:\nginx\conf\nginx.conf` 或 `nginx.conf` |
| Linux | `/etc/nginx/nginx.conf` |
| macOS | `/usr/local/etc/nginx/nginx.conf` |

### 关键配置

```nginx
# 监听端口50001
listen 50001;

# 后端API代理
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    
    # 禁用缓冲（重要：支持大文件上传）
    proxy_request_buffering off;
    proxy_buffering off;
    
    # 缓冲区设置
    proxy_buffer_size 128k;
    proxy_buffers 256 16k;
    proxy_busy_buffers_size 256k;
}

# 前端UI代理
location / {
    proxy_pass http://127.0.0.1:8001;
}
```

## 启动流程

### 步骤1：查找Nginx

```bash
find_nginx.bat
```

**输出示例**:
```
Found Nginx at: C:\ProgramData\chocolatey\lib\nginx\tools
SUCCESS: Nginx added to PATH
```

### 步骤2：重启命令行

关闭并重新打开命令行窗口，使PATH生效

### 步骤3：启动Nginx

```bash
start_nginx.bat
```

**输出示例**:
```
========================================
ResearchMind Nginx Startup
========================================

Checking if Nginx is installed...
SUCCESS: Nginx is installed

Checking nginx.conf...
SUCCESS: nginx.conf found

Verifying Nginx configuration...
SUCCESS: Nginx configuration is valid

Starting Nginx...
SUCCESS: Nginx started

========================================
Nginx is running on port 50001
========================================

Checking backend on port 8000...
WARNING: Backend is not running on port 8000
Start it with: python main.py

Checking frontend on port 8001...
WARNING: Frontend is not running on port 8001
Start it with: npm run dev
```

### 步骤4：启动后端（新命令行窗口）

```bash
python main.py
```

**输出示例**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 步骤5：启动前端（新命令行窗口）

```bash
npm run dev
```

**输出示例**:
```
VITE v5.0.0  ready in 123 ms

➜  Local:   http://127.0.0.1:8001
```

### 步骤6：访问应用

打开浏览器访问：
```
http://127.0.0.1:50001
```

## 验证配置

### 检查Nginx是否运行

```bash
# Windows
tasklist | findstr nginx

# Linux/macOS
ps aux | grep nginx
```

**预期输出**:
```
nginx.exe                    1234 Console                 0      5,120 K
nginx.exe                    5678 Console                 0      6,144 K
```

### 检查端口是否监听

```bash
# Windows
netstat -ano | findstr ":50001"

# Linux/macOS
sudo netstat -tlnp | grep 50001
```

**预期输出**:
```
TCP    127.0.0.1:50001        0.0.0.0:0              LISTENING       1234
```

### 测试API连接

```bash
# 测试后端API
curl http://127.0.0.1:50001/api/health

# 测试前端
curl http://127.0.0.1:50001/
```

### 测试CIF上传

```bash
# 上传CIF文件
curl -X POST -F "file=@test.cif" \
  http://127.0.0.1:50001/api/upload/structure

# 预期响应
{
  "id": "...",
  "formula": "...",
  "source": {
    "database": "Upload",
    "materialId": "...",
    "uploadedAt": "..."
  }
}
```

## 常见问题

### Q1: 访问 http://127.0.0.1:50001 显示"无法连接"

**原因**: Nginx未运行

**解决方案**:
```bash
# 检查Nginx是否运行
tasklist | findstr nginx

# 如果没有运行，启动Nginx
start_nginx.bat

# 检查nginx.conf是否存在
dir nginx.conf
```

### Q2: 上传CIF文件后显示"unknown"而不是"upload"

**原因**: 结构转换处理失败或标记错误

**解决方案**:
1. 检查后端日志
2. 验证CIF文件格式
3. 检查pymatgen是否安装

```bash
# 检查pymatgen
python -c "import pymatgen; print(pymatgen.__version__)"

# 如果未安装
pip install pymatgen
```

### Q3: 上传大文件时显示"413 Request Entity Too Large"

**原因**: Nginx缓冲区太小

**解决方案**: 修改nginx.conf中的缓冲区设置

```nginx
client_max_body_size 100M;
proxy_buffer_size 256k;
proxy_buffers 512 32k;
proxy_busy_buffers_size 512k;
```

### Q4: 前端显示"API连接失败"

**原因**: 前端使用了错误的API端口

**解决方案**: 检查环境变量

```bash
# 检查.env文件
cat .env

# 应该包含
VITE_API_URL=http://127.0.0.1:50001
VITE_WS_URL=ws://127.0.0.1:50001
```

### Q5: Nginx命令未找到

**原因**: Nginx不在PATH中

**解决方案**:
```bash
# 运行查找脚本
find_nginx.bat

# 重启命令行窗口
```

## 停止服务

### 停止Nginx

```bash
# Windows
nginx -s stop

# Linux/macOS
sudo nginx -s stop
```

### 停止后端

```bash
# 在后端命令行窗口按 Ctrl+C
```

### 停止前端

```bash
# 在前端命令行窗口按 Ctrl+C
```

## 重新加载配置

### 修改nginx.conf后

```bash
# 验证配置
nginx -t

# 重新加载
nginx -s reload
```

## 日志位置

### Nginx日志

| 操作系统 | 位置 |
|---------|------|
| Windows | `C:\nginx\logs\` |
| Linux | `/var/log/nginx/` |
| macOS | `/usr/local/var/log/nginx/` |

### 查看日志

```bash
# Windows
type C:\nginx\logs\access.log
type C:\nginx\logs\error.log

# Linux/macOS
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## 完整的启动脚本

### Windows

```bash
@echo off
REM 启动所有服务

echo Starting Nginx...
start_nginx.bat

echo.
echo Starting backend...
start cmd /k "python main.py"

echo.
echo Starting frontend...
start cmd /k "npm run dev"

echo.
echo All services started!
echo Access the app at: http://127.0.0.1:50001
```

### Linux/macOS

```bash
#!/bin/bash

echo "Starting Nginx..."
./setup_nginx.sh

echo ""
echo "Starting backend..."
python main.py &

echo ""
echo "Starting frontend..."
npm run dev &

echo ""
echo "All services started!"
echo "Access the app at: http://127.0.0.1:50001"
```

## 总结

| 组件 | 端口 | 说明 |
|------|------|------|
| 用户访问 | 50001 | Nginx反向代理 |
| 后端API | 8000 | FastAPI服务 |
| 前端UI | 8001 | Vite开发服务器 |

**关键点**:
- ✅ 用户只访问端口50001
- ✅ Nginx自动路由到正确的服务
- ✅ 禁用缓冲支持大文件上传
- ✅ 所有URL使用50001端口

