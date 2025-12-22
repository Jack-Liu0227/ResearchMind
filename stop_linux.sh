#!/bin/bash

# =============================================================================
# ResearchMind 服务停止脚本 (Linux)
# =============================================================================
# 用于停止所有 ResearchMind 相关服务并释放端口
#
# 使用方法:
#   bash stop_linux.sh
# =============================================================================

set -euo pipefail

# ----------------------------- 颜色定义 ----------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# ----------------------------- 日志工具 -----------------------------
log_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

log_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# ----------------------------- Banner -----------------------------
echo -e "${YELLOW}"
echo "============================================================"
echo "   ResearchMind 服务停止器"
echo "============================================================"
echo -e "${NC}"

# ----------------------------- 停止服务 -----------------------------
log_info "正在停止所有 ResearchMind 服务..."

# 1. 使用 .service_pids 文件停止已知服务
if [ -f .service_pids ]; then
    log_info "从 .service_pids 停止服务..."
    while read -r pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log_info "停止 PID $pid"
            kill -15 "$pid" 2>/dev/null || true
            sleep 0.5
            # 如果仍在运行则强制终止
            if kill -0 "$pid" 2>/dev/null; then
                log_warning "强制终止 PID $pid"
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
    done < .service_pids
    rm -f .service_pids
    log_success "已清理 .service_pids"
fi

# 2. 按进程名称停止
log_info "按进程名称停止服务..."

# 优雅停止
pkill -15 -f "uv run python main.py" 2>/dev/null || true
pkill -15 -f "uv run python.*server.py" 2>/dev/null || true
pkill -15 -f "npm run dev" 2>/dev/null || true
pkill -15 -f "node.*vite" 2>/dev/null || true

log_info "等待进程优雅退出..."
sleep 3

# 强制停止残留进程
log_info "强制停止残留进程..."
pkill -9 -f "uv run python" 2>/dev/null || true
pkill -9 -f "npm run dev" 2>/dev/null || true
pkill -9 -f "node.*vite" 2>/dev/null || true

# 3. 释放端口（从 .env 读取配置）
log_info "释放占用的端口..."

# 加载 .env 配置
if [ -f .env ]; then
    set -a
    source <(
        sed '1s/^\xEF\xBB\xBF//' ".env" \
        | sed 's/\r$//' \
        | grep -v '^\s*#' \
        | grep -v '^\s*$'
    )
    set +a
fi

# 检查端口是否被占用
is_port_in_use() {
    local port=$1
    if command -v lsof > /dev/null 2>&1; then
        lsof -ti:$port > /dev/null 2>&1
    elif command -v netstat > /dev/null 2>&1; then
        netstat -tuln | grep -q ":$port "
    elif command -v ss > /dev/null 2>&1; then
        ss -tuln | grep -q ":$port "
    else
        return 1
    fi
}

# 强制释放端口
force_release_port() {
    local port=$1
    
    if command -v lsof > /dev/null 2>&1; then
        local pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            for pid in $pids; do
                if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                    log_warning "端口 $port 被 PID $pid 占用，正在终止..."
                    kill -9 "$pid" 2>/dev/null || true
                fi
            done
        fi
    elif command -v fuser > /dev/null 2>&1; then
        fuser -k $port/tcp 2>/dev/null || true
    fi
}

# 收集所有端口
ports_to_clean=(
    "${VITE_FRONTEND_PORT:-50010}"
    "${RESEARCHMIND_HTTP_PORT:-50002}"
    "${RESEARCHMIND_WS_PORT:-50003}"
    "${PAPER_SEARCH_MCP_PORT:-50004}"
    "${SIMULATION_MCP_PORT:-50005}"
    "${DATABASE_MCP_PORT:-50006}"
)

# 去重并清理
unique_ports=($(printf '%s\n' "${ports_to_clean[@]}" | sort -u))

for port in "${unique_ports[@]}"; do
    if is_port_in_use "$port"; then
        log_warning "端口 $port 被占用，正在释放..."
        force_release_port "$port"
        sleep 0.5
        if is_port_in_use "$port"; then
            log_error "无法释放端口 $port"
        else
            log_success "端口 $port 已释放"
        fi
    else
        log_success "端口 $port 已空闲"
    fi
done

# 4. 清理日志锁文件（如果有）
rm -f logs/*.lock 2>/dev/null || true

# 5. 最终验证
log_info ""
log_info "验证所有端口状态..."
all_clear=true
for port in "${unique_ports[@]}"; do
    if is_port_in_use "$port"; then
        log_error "端口 $port 仍被占用"
        all_clear=false
    fi
done

if [ "$all_clear" = true ]; then
    log_success ""
    log_success "============================================================"
    log_success "   所有服务已停止，端口已释放"
    log_success "============================================================"
    log_success ""
    log_info "现在可以安全地运行: bash start_linux.sh"
else
    log_warning ""
    log_warning "============================================================"
    log_warning "   部分端口仍被占用，请手动检查"
    log_warning "============================================================"
    log_warning ""
    log_info "使用以下命令查看端口占用情况:"
    log_info "  lsof -i:50002  # 查看端口 50002"
    log_info "  lsof -i:50006  # 查看端口 50006"
fi
