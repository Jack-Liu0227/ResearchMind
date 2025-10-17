#!/bin/bash

# ResearchMind 一键启动脚本
# 启动所有服务：后端、MCP服务器、前端

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 清理函数
cleanup() {
    log_warning "\n正在停止所有服务..."
    
    # 停止所有后台进程
    if [ -f .service_pids ]; then
        while read pid; do
            if kill -0 $pid 2>/dev/null; then
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

# 打印横幅
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║              ResearchMind 一键启动脚本                    ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查环境
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

# 检查 .env 文件
if [ ! -f .env ]; then
    log_warning ".env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
    log_warning "请编辑 .env 文件配置 API keys"
fi

# # 创建必要的目录
# mkdir -p logs
# mkdir -p session_data/images
# mkdir -p session_data/metadata
# mkdir -p session_data/structures
# log_success "✓ 创建必要的目录"

# 清空 PID 文件
> .service_pids

# ============================================
# 启动 MCP 服务器
# ============================================
log_info "\n启动 MCP 服务器..."

# 数据库服务
log_info "启动数据库服务 (端口 50006)..."
cd mcp_servers
uv run python database_call/server.py > ../logs/database.log 2>&1 &
DB_PID=$!
echo $DB_PID >> ../.service_pids
cd ..
sleep 2
log_success "✓ 数据库服务已启动 (PID: $DB_PID)"

# 论文搜索服务
log_info "启动论文搜索服务 (端口 50004)..."
cd mcp_servers
uv run python paper_search/server.py > ../logs/paper_search.log 2>&1 &
PAPER_PID=$!
echo $PAPER_PID >> ../.service_pids
cd ..
sleep 2
log_success "✓ 论文搜索服务已启动 (PID: $PAPER_PID)"

# 模拟服务
log_info "启动模拟服务 (端口 50005)..."
cd mcp_servers
uv run python simulation/server.py > ../logs/simulation.log 2>&1 &
SIM_PID=$!
echo $SIM_PID >> ../.service_pids
cd ..
sleep 2
log_success "✓ 模拟服务已启动 (PID: $SIM_PID)"

# ============================================
# 启动后端服务
# ============================================
log_info "\n启动后端服务..."
log_info "WebSocket 服务 (端口 50003)"
log_info "HTTP API 服务 (端口 50002)"

uv run python main.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID >> .service_pids
sleep 3
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

# 启动前端开发服务器 (0.0.0.0:50001)
log_info "启动前端开发服务器 (0.0.0.0:50001)..."
cd ui
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID >> ../.service_pids
cd ..
sleep 3
log_success "✓ 前端服务已启动 (PID: $FRONTEND_PID)"

# ============================================
# 服务状态总结
# ============================================
echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    所有服务已启动                         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${BLUE}📡 服务地址 (可暴露端口 50001-50005):${NC}"
echo -e "   ${YELLOW}前端 UI:${NC}        http://0.0.0.0:50001"
echo -e "   ${YELLOW}后端 API:${NC}       http://0.0.0.0:50002"
echo -e "   ${YELLOW}WebSocket:${NC}      ws://0.0.0.0:50003"
echo -e "   ${YELLOW}API 文档:${NC}       http://0.0.0.0:50002/docs"
echo ""
echo -e "${BLUE}🔧 MCP 服务:${NC}"
echo -e "   ${YELLOW}论文搜索:${NC}       http://0.0.0.0:50004 (可暴露)"
echo -e "   ${YELLOW}模拟服务:${NC}       http://0.0.0.0:50005 (可暴露)"
echo -e "   ${YELLOW}数据库服务:${NC}     http://0.0.0.0:50006 (内部)"
echo ""
echo -e "${BLUE}📝 日志文件:${NC}"
echo -e "   logs/backend.log"
echo -e "   logs/database.log"
echo -e "   logs/paper_search.log"
echo -e "   logs/simulation.log"
echo -e "   logs/frontend.log"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}\n"

# 保持脚本运行
while true; do
    sleep 1
done
