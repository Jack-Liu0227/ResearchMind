#!/bin/bash

# ============================================
# ResearchMind 一键启动脚本 v2.0
# ============================================
# 功能：启动所有服务（后端、MCP服务器、前端）
# 特性：
#   - 支持分布式部署（不同主机运行不同服务）
#   - 灵活的 HOST 和 PORT 配置
#   - UI 强制为 0.0.0.0:50001（跨主机访问）
#   - 完整的日志管理和错误处理
#
# 用法：
#   bash start.sh                    # 使用 .env 配置启动
#
# 推荐：使用 quick_deploy.sh 快速部署
#   bash quick_deploy.sh             # 本地部署
#   bash quick_deploy.sh 192.168.1.100  # 局域网部署
#   bash quick_deploy.sh api.example.com # 云服务器部署

set -e

# ============================================
# 颜色输出定义
# ============================================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================
# 日志函数
# ============================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_config() {
    echo -e "${CYAN}[CONFIG]${NC} $1"
}

# ============================================
# 清理函数
# ============================================
cleanup() {
    log_warning "\n正在停止所有服务..."

    # 停止所有后台进程
    if [ -f .service_pids ]; then
        while read pid; do
            if kill -0 $pid 2>/dev/null; then
                log_info "停止进程 PID: $pid"
                kill $pid 2>/dev/null || true
            fi
        done < .service_pids
        rm -f .service_pids
    fi

    log_success "所有服务已停止"
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# ============================================
# 加载配置函数
# ============================================
load_config() {
    if [ ! -f .env ]; then
        log_error ".env 文件不存在"
        exit 1
    fi

    # 从 .env 文件加载配置（安全处理注释、空行和 BOM）
    set -a
    # 移除 BOM 并加载配置
    source <(grep -v '^#' .env | grep -v '^$' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    set +a

    log_success ".env 配置已加载"
}

# ============================================
# 打印启动横幅
# ============================================
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║          ResearchMind 一键启动脚本 v2.0                  ║"
echo "║                                                           ║"
echo "║     支持分布式部署 | 灵活配置 | 跨主机访问               ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================
# 环境检查
# ============================================
log_info "检查环境..."

# 检查 Python/uv
if ! command -v uv &> /dev/null; then
    log_error "uv 未安装，请先安装 uv: https://docs.astral.sh/uv/"
    exit 1
fi
log_success "✓ uv 已安装"

# 检查 Node.js/npm
if ! command -v npm &> /dev/null; then
    log_error "npm 未安装，请先安装 Node.js"
    exit 1
fi
log_success "✓ npm 已安装"

# ============================================
# 清理旧进程和端口
# ============================================
log_info "清理旧进程..."
pkill -9 -f "uv run python" 2>/dev/null || true
pkill -9 -f "npm run dev" 2>/dev/null || true
pkill -9 -f "node" 2>/dev/null || true

# Windows 特定的端口清理
if command -v netstat &> /dev/null; then
    # 尝试释放占用的端口
    for port in 50001 50002 50003 50004 50005 50006; do
        pids=$(netstat -ano 2>/dev/null | grep ":$port " | awk '{print $NF}' | sort -u)
        for pid in $pids; do
            if [ ! -z "$pid" ] && [ "$pid" != "PID" ]; then
                taskkill /PID $pid /F 2>/dev/null || true
            fi
        done
    done
fi

sleep 8
log_success "✓ 旧进程已清理"

# ============================================
# 配置文件检查
# ============================================
if [ ! -f .env ]; then
    log_warning ".env 文件不存在，从 .env.example 复制..."
    if [ -f .env.example ]; then
        cp .env.example .env
        log_warning "请编辑 .env 文件配置 API keys"
    else
        log_error ".env.example 文件也不存在"
        exit 1
    fi
fi

# 清理 UTF-8 BOM（如果存在）
if file .env 2>/dev/null | grep -q "UTF-8 (with BOM)"; then
    log_warning "清理 .env 中的 UTF-8 BOM..."
    python3 -c "
import sys
with open('.env', 'rb') as f:
    content = f.read()
if content.startswith(b'\xef\xbb\xbf'):
    content = content[3:]
with open('.env', 'wb') as f:
    f.write(content)
" 2>/dev/null || sed -i '1s/^\xEF\xBB\xBF//' .env
fi

# 加载配置
load_config

# ============================================
# 创建必要的目录
# ============================================
mkdir -p logs
mkdir -p session_data/images
mkdir -p session_data/metadata
mkdir -p session_data/structures
log_success "✓ 创建必要的目录"

# 清空 PID 文件
> .service_pids

# ============================================
# 显示配置信息
# ============================================
echo ""
log_config "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_config "📋 服务配置信息"
log_config "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_config "前端 UI:        ${VITE_FRONTEND_HOST}:${VITE_FRONTEND_PORT}"
log_config "HTTP API:      ${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"
log_config "WebSocket:     ${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT}"
log_config "论文搜索 MCP:   ${PAPER_SEARCH_MCP_HOST}:${PAPER_SEARCH_MCP_PORT}"
log_config "模拟服务 MCP:   ${SIMULATION_MCP_HOST}:${SIMULATION_MCP_PORT}"
log_config "数据库服务 MCP: ${DATABASE_MCP_HOST}:${DATABASE_MCP_PORT}"
log_config "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================
# 启动 MCP 服务器
# ============================================
log_info "启动 MCP 服务器..."

# 数据库服务
log_info "启动数据库服务 (${DATABASE_MCP_HOST}:${DATABASE_MCP_PORT})..."
cd mcp_servers
uv run python database_call/server.py 2>&1 | tee ../logs/database.log &
DB_PID=$!
echo $DB_PID >> ../.service_pids
cd ..
sleep 3
log_success "✓ 数据库服务已启动 (PID: $DB_PID)"

# 论文搜索服务
log_info "启动论文搜索服务 (${PAPER_SEARCH_MCP_HOST}:${PAPER_SEARCH_MCP_PORT})..."
cd mcp_servers
uv run python paper_search/server.py 2>&1 | tee ../logs/paper_search.log &
PAPER_PID=$!
echo $PAPER_PID >> ../.service_pids
cd ..
sleep 3
log_success "✓ 论文搜索服务已启动 (PID: $PAPER_PID)"

# 模拟服务
log_info "启动模拟服务 (${SIMULATION_MCP_HOST}:${SIMULATION_MCP_PORT})..."
cd mcp_servers
uv run python simulation/server.py 2>&1 | tee ../logs/simulation.log &
SIM_PID=$!
echo $SIM_PID >> ../.service_pids
cd ..
sleep 3
log_success "✓ 模拟服务已启动 (PID: $SIM_PID)"

# ============================================
# 启动后端服务
# ============================================
log_info "\n启动后端服务..."
log_info "WebSocket 服务 (${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT})"
log_info "HTTP API 服务 (${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT})"

sleep 2
uv run python main.py 2>&1 | tee logs/backend.log &
BACKEND_PID=$!
echo $BACKEND_PID >> .service_pids
sleep 4
log_success "✓ 后端服务已启动 (PID: $BACKEND_PID)"

# ============================================
# 启动前端服务
# ============================================
log_info "\n启动前端服务..."

# 检查前端依赖
if [ ! -d "ui/node_modules" ]; then
    log_info "安装前端依赖..."
    cd ui
    npm install
    cd ..
fi

# 构建前端生产版本
log_info "构建前端生产版本..."
cd ui
npm run dev 2>&1 | tee ../logs/frontend_build.log
cd ..
log_success "✓ 前端构建完成"

# 启动前端预览服务器 (生产模式，端口 50001)
log_info "启动前端预览服务器 (0.0.0.0:50001)..."
cd ui
npm run preview 2>&1 | tee ../logs/frontend.log &
FRONTEND_PID=$!
echo $FRONTEND_PID >> ../.service_pids
cd ..
sleep 3
log_success "✓ 前端服务已启动 (PID: $FRONTEND_PID)"

# ============================================
# Nginx 反向代理已禁用
# ============================================
# 注意: 已移除 Nginx 反向代理
# 所有服务现在直接访问，无需反向代理
#
# 服务地址:
#   - 前端 UI: http://127.0.0.1:50001
#   - 后端 API: http://127.0.0.1:50006
#   - WebSocket: ws://127.0.0.1:50003/ws
#   - Paper Search MCP: http://127.0.0.1:50004/sse
#   - Simulation MCP: http://127.0.0.1:50005/sse
#   - Database MCP: http://127.0.0.1:50002/sse

# ============================================
# 服务状态总结
# ============================================
echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    所有服务已启动                         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${BLUE}📡 访问地址 (直接访问，无反向代理):${NC}"
echo -e "   ${YELLOW}前端 UI:${NC}        http://127.0.0.1:${VITE_FRONTEND_PORT}"
echo -e "   ${YELLOW}后端 API:${NC}       http://${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"
echo -e "   ${YELLOW}API 文档:${NC}       http://${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}/docs"
echo ""
echo -e "${BLUE}🔌 实时通信:${NC}"
echo -e "   ${YELLOW}WebSocket:${NC}      ws://127.0.0.1:${RESEARCHMIND_WS_PORT}/ws"
echo ""
echo -e "${BLUE}🔧 MCP 服务:${NC}"
echo -e "   ${YELLOW}论文搜索:${NC}       http://127.0.0.1:${PAPER_SEARCH_MCP_PORT}/sse"
echo -e "   ${YELLOW}模拟服务:${NC}       http://127.0.0.1:${SIMULATION_MCP_PORT}/sse"
echo -e "   ${YELLOW}数据库服务:${NC}     http://127.0.0.1:${DATABASE_MCP_PORT}/sse"
echo ""
echo -e "${BLUE}📝 日志文件:${NC}"
echo -e "   logs/backend.log"
echo -e "   logs/database.log"
echo -e "   logs/paper_search.log"
echo -e "   logs/simulation.log"
echo -e "   logs/frontend.log"
echo ""
echo -e "${BLUE}💡 远程部署提示:${NC}"
echo -e "   如需在不同主机运行服务，请修改 .env 文件中的配置："
echo -e "   - 前端监听: VITE_FRONTEND_HOST=0.0.0.0 (允许外部访问)"
echo -e "   - 后端监听: RESEARCHMIND_HTTP_HOST=0.0.0.0 (允许外部访问)"
echo -e "   - 客户端连接: VITE_API_URL, VITE_WS_URL, *_MCP_URL (改为目标主机 IP 或域名)"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}\n"

# ============================================
# 保持脚本运行
# ============================================
while true; do
    sleep 1
done