#!/bin/bash

# =============================================================================
# ResearchMind unified launcher for Linux
# =============================================================================
# Starts every component (backend, MCP servers, frontend) using the variables
# defined in .env or .env.remote. It also handles log redirection, process 
# tracking, and graceful shutdown on Ctrl+C.
#
# Usage:
#   bash start_linux.sh
#
# NOTE: Nginx should be configured separately using setup_nginx.sh
# =============================================================================

set -euo pipefail

# ----------------------------- Colour definitions ----------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ----------------------------- Logging utilities -----------------------------
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

# ----------------------------- Cleanup handling ------------------------------
# Store tail PIDs for cleanup
TAIL_PIDS=()

cleanup() {
    log_warning "Stopping all managed processes..."

    # Kill tail processes first
    for tail_pid in "${TAIL_PIDS[@]}"; do
        if [ -n "$tail_pid" ] && kill -0 "$tail_pid" 2>/dev/null; then
            kill "$tail_pid" 2>/dev/null || true
        fi
    done

    # Kill all service processes
    if [ -f .service_pids ]; then
        while read -r pid; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                log_info "Stopping PID $pid"
                kill "$pid" 2>/dev/null || true
                sleep 0.5
                # Force kill if still running
                if kill -0 "$pid" 2>/dev/null; then
                    log_warning "Force killing PID $pid"
                    kill -9 "$pid" 2>/dev/null || true
                fi
            fi
        done < .service_pids
        rm -f .service_pids
    fi

    # Additional cleanup for any remaining processes
    pkill -f "uv run python main.py" 2>/dev/null || true
    pkill -f "uv run python.*server.py" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "node.*vite" 2>/dev/null || true

    log_success "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# ------------------------------- Load .env file ------------------------------
load_config() {
    # 使用 .env 配置文件
    if [ -f .env ]; then
        ENV_FILE=".env"
        log_info "Using config: .env"
    else
        log_error ".env file is missing."
        exit 1
    fi

    # shellcheck disable=SC2046,SC1090
    set -a
    source <(
        sed '1s/^\xEF\xBB\xBF//' "$ENV_FILE" \
        | sed 's/\r$//' \
        | grep -v '^\s*#' \
        | grep -v '^\s*$'
    )
    set +a

    log_success "Configuration loaded from $ENV_FILE"
}

# ------------------------------ Pre-flight checks ---------------------------
print_banner() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "   ResearchMind Linux Launcher v2.0"
    echo "   Production-ready | Distributed | Remote access"
    echo "============================================================"
    echo -e "${NC}"
}

check_dependencies() {
    log_info "Checking runtime dependencies..."

    if ! command -v uv >/dev/null 2>&1; then
        log_error "uv is not installed. Install it from https://docs.astral.sh/uv/"
        exit 1
    fi
    log_success "uv available: $(uv --version)"

    if ! command -v npm >/dev/null 2>&1; then
        log_error "npm is not installed. Install Node.js first."
        exit 1
    fi
    log_success "npm available: $(npm --version)"

    if ! command -v python3 >/dev/null 2>&1; then
        log_error "python3 is not installed."
        exit 1
    fi
    log_success "python3 available: $(python3 --version)"
}

prepare_workspace() {
    mkdir -p logs
    : > .service_pids
}

kill_stale_processes() {
    log_info "Cleaning up stale processes and occupied ports..."

    # 首先尝试优雅地停止已知的进程
    pkill -f "uv run python main.py" 2>/dev/null || true
    pkill -f "uv run python.*server.py" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "node.*vite" 2>/dev/null || true

    sleep 1

    # 收集所有需要清理的端口（从环境变量中读取）
    local ports_to_clean=(
        "${VITE_FRONTEND_PORT:-5173}"
        "${RESEARCHMIND_HTTP_PORT:-8000}"
        "${RESEARCHMIND_WS_PORT:-8000}"
        "${PAPER_SEARCH_MCP_PORT:-50002}"
        "${SIMULATION_MCP_PORT:-50003}"
        "${DATABASE_MCP_PORT:-50010}"
    )

    # 去重端口列表
    local unique_ports=($(printf '%s\n' "${ports_to_clean[@]}" | sort -u))

    # 清理占用端口的进程
    for port in "${unique_ports[@]}"; do
        local killed=false

        # 优先使用 lsof
        if command -v lsof >/dev/null 2>&1; then
            local pids=$(lsof -ti:$port 2>/dev/null || true)
            if [ -n "$pids" ]; then
                for pid in $pids; do
                    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                        log_warning "Port $port is occupied by PID $pid, terminating..."
                        kill -15 "$pid" 2>/dev/null || true
                        sleep 0.5
                        # 如果进程仍在运行，强制终止
                        if kill -0 "$pid" 2>/dev/null; then
                            log_warning "Force killing PID $pid on port $port"
                            kill -9 "$pid" 2>/dev/null || true
                        fi
                        killed=true
                    fi
                done
            fi
        # 备用方案：使用 fuser
        elif command -v fuser >/dev/null 2>&1; then
            local pids=$(fuser $port/tcp 2>/dev/null || true)
            if [ -n "$pids" ]; then
                for pid in $pids; do
                    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                        log_warning "Port $port is occupied by PID $pid, terminating..."
                        kill -15 "$pid" 2>/dev/null || true
                        sleep 0.5
                        if kill -0 "$pid" 2>/dev/null; then
                            log_warning "Force killing PID $pid on port $port"
                            kill -9 "$pid" 2>/dev/null || true
                        fi
                        killed=true
                    fi
                done
            fi
        fi

        if [ "$killed" = true ]; then
            log_success "Port $port released"
        fi
    done

    # 最后再次强制清理任何残留的相关进程
    pkill -9 -f "uv run python" 2>/dev/null || true
    pkill -9 -f "npm run dev" 2>/dev/null || true
    pkill -9 -f "node.*vite" 2>/dev/null || true

    sleep 1
    log_success "All stale processes and ports cleaned"
}

# ---------------------------- Service start helpers -------------------------
register_pid() {
    echo "$1" >> .service_pids
}

start_mcp_service() {
    local service_name=$1
    local script_path=$2
    local log_name=$3
    local host=$4
    local port=$5

    log_info "Starting ${service_name} (${host}:${port})..."
    pushd mcp_servers >/dev/null
    nohup uv run python "$script_path" > "../logs/${log_name}" 2>&1 &
    local pid=$!
    popd >/dev/null
    register_pid "$pid"
    sleep 3

    if kill -0 "$pid" 2>/dev/null; then
        log_success "${service_name} started (PID ${pid})"
    else
        log_error "${service_name} failed to start"
        exit 1
    fi
}

start_backend() {
    log_info "Starting backend services..."
    log_info "WebSocket endpoint: ${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT}"
    log_info "HTTP endpoint:      ${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"

    nohup uv run python main.py > logs/backend.log 2>&1 &
    local pid=$!
    register_pid "$pid"
    sleep 4

    if kill -0 "$pid" 2>/dev/null; then
        log_success "Backend started (PID ${pid})"
    else
        log_error "Backend failed to start. Check logs/backend.log"
        exit 1
    fi
}

start_frontend() {
    log_info "Starting frontend..."

    if [ ! -d "ui/node_modules" ]; then
        log_info "Installing frontend dependencies..."
        pushd ui >/dev/null
        npm install
        popd >/dev/null
    fi

    log_info "Launching Vite dev server (${VITE_FRONTEND_HOST}:${VITE_FRONTEND_PORT})..."
    pushd ui >/dev/null
    nohup npm run dev -- --host "${VITE_FRONTEND_HOST}" --port "${VITE_FRONTEND_PORT}" > ../logs/frontend.log 2>&1 &
    local pid=$!
    popd >/dev/null
    register_pid "$pid"
    sleep 3
    
    if kill -0 "$pid" 2>/dev/null; then
        log_success "Frontend started (PID ${pid})"
    else
        log_error "Frontend failed to start. Check logs/frontend.log"
        exit 1
    fi
}

print_summary() {
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}   All services are up and running${NC}"
    echo -e "${GREEN}============================================================${NC}\n"

    echo -e "${BLUE}Direct access endpoints:${NC}"
    echo -e "  ${YELLOW}Frontend UI:${NC}   http://${VITE_FRONTEND_HOST}:${VITE_FRONTEND_PORT}"
    echo -e "  ${YELLOW}Backend API:${NC}   http://${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"
    echo -e "  ${YELLOW}API Docs:${NC}      http://${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}/docs"
    echo -e "  ${YELLOW}WebSocket:${NC}     ws://${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT}/ws"
    echo ""

    echo -e "${BLUE}MCP services:${NC}"
    echo -e "  ${YELLOW}Paper Search:${NC}  http://${PAPER_SEARCH_MCP_HOST}:${PAPER_SEARCH_MCP_PORT}/sse"
    echo -e "  ${YELLOW}Simulation:${NC}    http://${SIMULATION_MCP_HOST}:${SIMULATION_MCP_PORT}/sse"
    echo -e "  ${YELLOW}Database:${NC}      http://${DATABASE_MCP_HOST}:${DATABASE_MCP_PORT}/sse"
    echo ""

    if command -v nginx >/dev/null 2>&1 && systemctl is-active --quiet nginx 2>/dev/null; then
        echo -e "${BLUE}Nginx reverse proxy (if configured):${NC}"
        echo -e "  ${YELLOW}Unified access:${NC} http://<server-ip>:50001"
        echo ""
    fi

    echo -e "${BLUE}Logs:${NC}"
    echo "  logs/backend.log"
    echo "  logs/database.log"
    echo "  logs/paper_search.log"
    echo "  logs/simulation.log"
    echo "  logs/frontend.log"
    echo ""
}

prompt_log_view() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}   开始实时查看日志${NC}"
    echo -e "${CYAN}============================================================${NC}\n"

    log_info "正在同时查看后端和前端日志..."
    echo -e "${CYAN}提示: ${GREEN}绿色${NC}=后端日志, ${BLUE}蓝色${NC}=前端日志${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止所有服务并退出${NC}\n"
    sleep 2

    # 使用 tail -f 同时监控两个文件，并用 sed 添加颜色标记
    # 保存 tail 进程的 PID 以便在 cleanup 时终止
    tail -f logs/backend.log | sed "s/^/$(echo -e '\033[0;32m')[后端] /" &
    TAIL_PIDS+=($!)
    tail -f logs/frontend.log | sed "s/^/$(echo -e '\033[0;34m')[前端] /" &
    TAIL_PIDS+=($!)
}

# -----------------------------------------------------------------------------
# Main flow
# -----------------------------------------------------------------------------
print_banner
check_dependencies
load_config
prepare_workspace
kill_stale_processes

log_info "Loaded configuration:"
log_config "Frontend:           ${VITE_FRONTEND_HOST}:${VITE_FRONTEND_PORT}"
log_config "Backend HTTP:       ${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"
log_config "Backend WebSocket:  ${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT}"
log_config "Paper Search MCP:   ${PAPER_SEARCH_MCP_HOST}:${PAPER_SEARCH_MCP_PORT}"
log_config "Simulation MCP:     ${SIMULATION_MCP_HOST}:${SIMULATION_MCP_PORT}"
log_config "Database MCP:       ${DATABASE_MCP_HOST}:${DATABASE_MCP_PORT}"
echo ""

log_info "Starting MCP services..."
start_mcp_service "Database MCP" "database_call/server.py" "database.log" "${DATABASE_MCP_HOST}" "${DATABASE_MCP_PORT}"
start_mcp_service "Paper Search MCP" "paper_search/server.py" "paper_search.log" "${PAPER_SEARCH_MCP_HOST}" "${PAPER_SEARCH_MCP_PORT}"
start_mcp_service "Simulation MCP" "simulation/server.py" "simulation.log" "${SIMULATION_MCP_HOST}" "${SIMULATION_MCP_PORT}"

start_backend
start_frontend
print_summary
prompt_log_view

# Wait for any process to exit (including tail processes)
# This allows Ctrl+C to trigger the cleanup trap
wait

