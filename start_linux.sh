#!/bin/bash

# =============================================================================
# ResearchMind 统一启动器 (Linux)
# =============================================================================
# 启动所有组件（后端、MCP 服务器、前端），使用 .env 或 .env.remote 中定义的变量。
# 处理日志重定向、进程跟踪、优雅关闭，并支持自动重启和健康检查。
#
# 使用方法:
#   bash start_linux.sh
#
# Docker 挂载方式（可选）:
#   如果在 Docker 容器中运行，可以通过环境变量和卷挂载来持久化数据：
#
#   docker run -d \
#     -e SESSION_DATA_ROOT=/mnt/data/session_data \
#     -v /host/path/to/data:/mnt/data/session_data \
#     -p 8000:8000 \
#     researchmind:latest
#
#   这样可以将宿主机的 /host/path/to/data 目录挂载到容器内的 /mnt/data/session_data
#   所有会话数据、论文、仿真结果都会保存在宿主机目录中
#
# 注意: Nginx 需要使用 setup_nginx.sh 单独配置
# =============================================================================

set -euo pipefail

# ----------------------------- 颜色定义 ----------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ----------------------------- 全局配置 -----------------------------
# 重启配置
MAX_RESTART_ATTEMPTS=3          # 最大重启尝试次数
RESTART_DELAY_BASE=5            # 基础重启延迟（秒）
HEALTH_CHECK_TIMEOUT=60         # 健康检查超时（秒）- 增加到 60 秒以支持较慢的服务启动
HEALTH_CHECK_INTERVAL=2         # 健康检查间隔（秒）
PORT_WAIT_TIMEOUT=60            # 端口释放等待超时（秒）- 同步增加到 60 秒
PORT_CHECK_INTERVAL=1           # 端口检查间隔（秒）

# 日志文件
STARTUP_LOG="logs/startup.log"
RESTART_LOG="logs/restart.log"

# ----------------------------- 日志工具 -----------------------------
# 确保日志目录存在
ensure_log_dir() {
    if [ ! -d "logs" ]; then
        mkdir -p logs
    fi
}

log_info() {
    ensure_log_dir
    local msg="[信息] $1"
    echo -e "${BLUE}${msg}${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${msg}" >> "$STARTUP_LOG"
}

log_success() {
    ensure_log_dir
    local msg="[成功] $1"
    echo -e "${GREEN}${msg}${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${msg}" >> "$STARTUP_LOG"
}

log_warning() {
    ensure_log_dir
    local msg="[警告] $1"
    echo -e "${YELLOW}${msg}${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${msg}" >> "$STARTUP_LOG"
}

log_error() {
    ensure_log_dir
    local msg="[错误] $1"
    echo -e "${RED}${msg}${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${msg}" >> "$STARTUP_LOG"
}

log_config() {
    ensure_log_dir
    local msg="[配置] $1"
    echo -e "${CYAN}${msg}${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${msg}" >> "$STARTUP_LOG"
}

log_restart() {
    ensure_log_dir
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${msg}" >> "$RESTART_LOG"
}

# ----------------------------- 清理处理 ------------------------------
# 存储 tail 进程 PID 用于清理
TAIL_PIDS=()
# 存储服务重启计数
declare -A SERVICE_RESTART_COUNT

cleanup() {
    log_warning "正在停止所有托管进程..."

    # 首先终止 tail 进程
    for tail_pid in "${TAIL_PIDS[@]}"; do
        if [ -n "$tail_pid" ] && kill -0 "$tail_pid" 2>/dev/null; then
            kill "$tail_pid" 2>/dev/null || true
        fi
    done

    # 终止所有服务进程
    if [ -f .service_pids ]; then
        while read -r pid; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                log_info "正在停止 PID $pid"
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
    fi

    # 额外清理任何残留进程
    pkill -f "uv run python main.py" 2>/dev/null || true
    pkill -f "uv run python.*server.py" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "node.*vite" 2>/dev/null || true

    log_success "所有服务已停止。"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# ------------------------------- 加载 .env 文件 ------------------------------
load_config() {
    # 使用 .env 配置文件
    if [ -f .env ]; then
        ENV_FILE=".env"
        log_info "使用配置文件: .env"
    else
        log_error ".env 文件缺失。"
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

    # 🔧 路径管理环境变量说明（支持 Docker 挂载）
    # 注意：不在这里设置默认值，避免覆盖 .env 文件中的配置
    # 默认值由 Python 代码（utils/paths.py）处理
    #
    # Docker 部署时可以通过环境变量覆盖：
    # 例如：docker run -e SESSION_DATA_ROOT=/mnt/data/session_data ...
    #
    # 如果 .env 文件中未配置，Python 会使用默认值：data/session_data

    log_success "已从 $ENV_FILE 加载配置"
    log_config "SESSION_DATA_ROOT: ${SESSION_DATA_ROOT:-(未设置，将使用 Python 默认值)}"
}

# ------------------------------ 启动前检查 ---------------------------
print_banner() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "   ResearchMind Linux 启动器 v2.1"
    echo "   生产就绪 | 分布式 | 远程访问 | 自动重启"
    echo "============================================================"
    echo -e "${NC}"
}

check_dependencies() {
    log_info "检查运行时依赖..."

    if ! command -v uv >/dev/null 2>&1; then
        log_error "uv 未安装。请从 https://docs.astral.sh/uv/ 安装"
        exit 1
    fi
    log_success "uv 可用: $(uv --version)"

    if ! command -v npm >/dev/null 2>&1; then
        log_error "npm 未安装。请先安装 Node.js"
        exit 1
    fi
    log_success "npm 可用: $(npm --version)"

    if ! command -v python3 >/dev/null 2>&1; then
        log_error "python3 未安装。"
        exit 1
    fi
    log_success "python3 可用: $(python3 --version)"
}

prepare_workspace() {
    mkdir -p logs
    : > .service_pids
    : > "$STARTUP_LOG"
    : > "$RESTART_LOG"

    # 🔧 数据目录由 Python 代码创建（utils/paths.py 会正确处理相对路径）
    # 不在 shell 脚本中创建，避免 Windows 环境下相对路径解析错误
    # 各个服务启动时会自动调用 ensure_dirs() 创建必要的目录

    log_info "工作空间已准备就绪"
    log_info "数据目录配置: ${SESSION_DATA_ROOT:-data/session_data}"
    log_info "（数据目录将由 Python 服务自动创建）"
}

# ----------------------------- 端口管理工具 -----------------------------
# 检查端口是否被占用
is_port_in_use() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti:$port >/dev/null 2>&1
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":$port "
    elif command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":$port "
    else
        return 1
    fi
}

# 等待端口释放
wait_for_port_release() {
    local port=$1
    local timeout=$PORT_WAIT_TIMEOUT
    local elapsed=0

    log_info "等待端口 $port 释放..."

    while is_port_in_use "$port"; do
        if [ $elapsed -ge $timeout ]; then
            log_error "等待端口 $port 释放超时（${timeout}秒）"
            return 1
        fi
        sleep $PORT_CHECK_INTERVAL
        elapsed=$((elapsed + PORT_CHECK_INTERVAL))
    done

    log_success "端口 $port 已释放"
    return 0
}

# 强制释放端口
force_release_port() {
    local port=$1
    local killed=false

    log_info "正在强制释放端口 $port..."

    # 优先使用 lsof
    if command -v lsof >/dev/null 2>&1; then
        local pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            for pid in $pids; do
                if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                    local cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                    log_warning "端口 $port 被 PID $pid ($cmd) 占用，正在终止..."
                    kill -15 "$pid" 2>/dev/null || true
                    sleep 0.5
                    # 如果进程仍在运行，强制终止
                    if kill -0 "$pid" 2>/dev/null; then
                        log_warning "强制终止 PID $pid (端口 $port)"
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
                    log_warning "端口 $port 被 PID $pid 占用，正在终止..."
                    kill -15 "$pid" 2>/dev/null || true
                    sleep 0.5
                    if kill -0 "$pid" 2>/dev/null; then
                        log_warning "强制终止 PID $pid (端口 $port)"
                        kill -9 "$pid" 2>/dev/null || true
                    fi
                    killed=true
                fi
            done
        fi
    fi

    if [ "$killed" = true ]; then
        # 等待端口真正释放
        sleep 1
        if ! wait_for_port_release "$port"; then
            return 1
        fi
        log_success "端口 $port 已成功释放"
    fi
    return 0
}

kill_stale_processes() {
    log_info "清理陈旧进程和占用端口..."

    # 首先尝试优雅地停止已知的进程
    log_info "优雅停止已知进程..."
    pkill -15 -f "uv run python main.py" 2>/dev/null || true
    pkill -15 -f "uv run python.*server.py" 2>/dev/null || true
    pkill -15 -f "npm run dev" 2>/dev/null || true
    pkill -15 -f "node.*vite" 2>/dev/null || true

    sleep 2

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
        if is_port_in_use "$port"; then
            log_warning "端口 $port 仍被占用"
            if ! force_release_port "$port"; then
                log_error "无法释放端口 $port，启动可能失败"
            fi
        else
            log_info "端口 $port 可用"
        fi
    done

    # 最后再次强制清理任何残留的相关进程
    log_info "最终清理残留进程..."
    pkill -9 -f "uv run python" 2>/dev/null || true
    pkill -9 -f "npm run dev" 2>/dev/null || true
    pkill -9 -f "node.*vite" 2>/dev/null || true

    sleep 1
    log_success "所有陈旧进程和端口已清理"
}

# ---------------------------- 健康检查工具 -------------------------
# HTTP 健康检查
check_http_health() {
    local host=$1
    local port=$2
    local endpoint=${3:-"/"}

    if command -v curl >/dev/null 2>&1; then
        curl -sf "http://${host}:${port}${endpoint}" >/dev/null 2>&1
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O /dev/null "http://${host}:${port}${endpoint}" 2>&1
    else
        # 备用方案：检查端口是否监听
        is_port_in_use "$port"
    fi
}

# 等待服务健康
wait_for_service_health() {
    local service_name=$1
    local host=$2
    local port=$3
    local endpoint=${4:-"/"}
    local timeout=$HEALTH_CHECK_TIMEOUT
    local elapsed=0

    log_info "等待 ${service_name} 健康检查..."

    while ! check_http_health "$host" "$port" "$endpoint"; do
        if [ $elapsed -ge $timeout ]; then
            log_error "${service_name} 健康检查超时（${timeout}秒）"
            return 1
        fi
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
    done

    log_success "${service_name} 健康检查通过"
    return 0
}

# ---------------------------- 服务启动助手 -------------------------
register_pid() {
    echo "$1" >> .service_pids
}

# 启动 MCP 服务（带重启支持）
# 参数 6（可选）：is_restart - 如果是重启则不强制释放端口
start_mcp_service() {
    local service_name=$1
    local script_path=$2
    local log_name=$3
    local host=$4
    local port=$5
    local is_restart=${6:-false}

    # 初始化重启计数（仅首次启动）
    if [ "$is_restart" != "true" ]; then
        SERVICE_RESTART_COUNT["$service_name"]=0
    fi

    log_info "正在启动 ${service_name} (${host}:${port})..."

    # 仅在首次启动时检查并释放端口，重启时跳过（因为进程已崩溃，端口应该已释放）
    if [ "$is_restart" != "true" ]; then
        if is_port_in_use "$port"; then
            log_warning "端口 $port 已被占用，尝试释放..."
            if ! force_release_port "$port"; then
                log_error "无法释放端口 $port，${service_name} 启动失败"
                exit 1
            fi
        fi
    else
        # 重启时，等待端口释放
        log_info "等待端口 $port 释放..."
        local wait_count=0
        while is_port_in_use "$port" && [ $wait_count -lt 10 ]; do
            sleep 1
            wait_count=$((wait_count + 1))
        done
        if is_port_in_use "$port"; then
            log_warning "端口 $port 仍被占用，但继续尝试启动..."
        fi
    fi

    pushd mcp_servers >/dev/null

    # 在 Git Bash/Windows 环境下，使用 --no-project 避免虚拟环境路径问题
    # 或者清除 VIRTUAL_ENV 变量让 uv 自动检测
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -n "${MSYSTEM-}" ]]; then
        log_info "检测到 Windows/Git Bash 环境，使用兼容模式启动..."
        unset VIRTUAL_ENV
        nohup uv run --no-project python "$script_path" > "../logs/${log_name}" 2>&1 &
    else
        nohup uv run python "$script_path" > "../logs/${log_name}" 2>&1 &
    fi

    local pid=$!
    popd >/dev/null
    register_pid "$pid"

    # 保存最后启动的服务 PID 到全局变量
    LAST_SERVICE_PID=$pid

    # 等待进程启动
    sleep 3

    # 检查进程是否存活
    if ! kill -0 "$pid" 2>/dev/null; then
        log_error "${service_name} 启动失败（进程已退出）"
        log_error "查看日志: logs/${log_name}"
        tail -n 20 "logs/${log_name}" | while read line; do
            log_error "  $line"
        done
        exit 1
    fi

    # MCP 服务：使用端口监听状态作为健康检查，避免 SSE /sse 接口导致 curl 失败
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -n "${MSYSTEM-}" ]]; then
        log_warning "Windows 环境下跳过 HTTP 健康检查，仅验证进程和端口..."
        sleep 5
        if is_port_in_use "$port"; then
            log_success "${service_name} 端口 $port 已监听"
        else
            log_warning "${service_name} 端口 $port 未监听，但进程仍在运行"
        fi
    else
        log_info "检查 ${service_name} 端口 ${port} 是否监听..."
        local elapsed=0
        while ! is_port_in_use "$port"; do
            if [ $elapsed -ge $HEALTH_CHECK_TIMEOUT ]; then
                log_error "${service_name} 端口 $port 在 ${HEALTH_CHECK_TIMEOUT} 秒内未开始监听"
                log_error "查看日志: logs/${log_name}"
                tail -n 20 "logs/${log_name}" | while read line; do
                    log_error "  $line"
                done
                exit 1
            fi
            sleep $HEALTH_CHECK_INTERVAL
            elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
        done
        log_success "${service_name} 端口 $port 已监听"
    fi

    log_success "${service_name} 已启动 (PID ${pid})"
}

# 启动后端服务（带重启支持）
start_backend() {
    local service_name="Backend"

    # 初始化重启计数
    SERVICE_RESTART_COUNT["$service_name"]=0

    log_info "正在启动后端服务..."
    log_info "WebSocket 端点: ${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT}"
    log_info "HTTP 端点:      ${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"

    # 检查端口是否可用
    local http_port="${RESEARCHMIND_HTTP_PORT}"
    if is_port_in_use "$http_port"; then
        log_warning "端口 $http_port 已被占用，尝试释放..."
        if ! force_release_port "$http_port"; then
            log_error "无法释放端口 $http_port，后端启动失败"
            exit 1
        fi
    fi

    # 在 Git Bash/Windows 环境下使用兼容模式
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -n "${MSYSTEM-}" ]]; then
        log_info "检测到 Windows/Git Bash 环境，使用兼容模式启动..."
        unset VIRTUAL_ENV
        nohup uv run --no-project python main.py > logs/backend.log 2>&1 &
    else
        nohup uv run python main.py > logs/backend.log 2>&1 &
    fi

    local pid=$!
    register_pid "$pid"

    # 保存最后启动的服务 PID 到全局变量
    LAST_SERVICE_PID=$pid

    # 等待进程启动
    sleep 4

    # 检查进程是否存活
    if ! kill -0 "$pid" 2>/dev/null; then
        log_error "后端启动失败（进程已退出）"
        log_error "查看日志: logs/backend.log"
        tail -n 20 "logs/backend.log" | while read line; do
            log_error "  $line"
        done
        exit 1
    fi

    # 健康检查（Windows 环境下跳过）
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -n "${MSYSTEM-}" ]]; then
        log_warning "Windows 环境下跳过 HTTP 健康检查"
        sleep 3
    else
        if ! wait_for_service_health "$service_name" "${RESEARCHMIND_HTTP_HOST}" "$http_port" "/docs"; then
            log_warning "后端健康检查失败，但进程仍在运行，继续..."
        fi
    fi

    log_success "后端已启动 (PID ${pid})"
}

# 启动前端服务（带重启支持）
start_frontend() {
    local service_name="Frontend"

    # 初始化重启计数
    SERVICE_RESTART_COUNT["$service_name"]=0

    log_info "正在启动前端..."

    if [ ! -d "ui/node_modules" ]; then
        log_info "安装前端依赖..."
        pushd ui >/dev/null
        npm install
        popd >/dev/null
    fi

    # 检查端口是否可用
    local frontend_port="${VITE_FRONTEND_PORT}"
    if is_port_in_use "$frontend_port"; then
        log_warning "端口 $frontend_port 已被占用，尝试释放..."
        if ! force_release_port "$frontend_port"; then
            log_error "无法释放端口 $frontend_port，前端启动失败"
            exit 1
        fi
    fi

    log_info "启动 Vite 开发服务器 (${VITE_FRONTEND_HOST}:${VITE_FRONTEND_PORT})..."
    pushd ui >/dev/null
    nohup npm run dev -- --host "${VITE_FRONTEND_HOST}" --port "${VITE_FRONTEND_PORT}" > ../logs/frontend.log 2>&1 &
    local pid=$!
    popd >/dev/null
    register_pid "$pid"

    # 保存最后启动的服务 PID 到全局变量
    LAST_SERVICE_PID=$pid

    # 等待进程启动
    sleep 5

    # 检查进程是否存活
    if ! kill -0 "$pid" 2>/dev/null; then
        log_error "前端启动失败（进程已退出）"
        log_error "查看日志: logs/frontend.log"
        tail -n 20 "logs/frontend.log" | while read line; do
            log_error "  $line"
        done
        exit 1
    fi

    # 健康检查（Windows 环境下跳过）
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -n "${MSYSTEM-}" ]]; then
        log_warning "Windows 环境下跳过 HTTP 健康检查"
        sleep 3
    else
        if ! wait_for_service_health "$service_name" "${VITE_FRONTEND_HOST}" "$frontend_port" "/"; then
            log_warning "前端健康检查失败，但进程仍在运行，继续..."
        fi
    fi

    log_success "前端已启动 (PID ${pid})"
}

# ---------------------------- 服务监控与自动重启 -------------------------
# 监控服务并在崩溃时重启
monitor_service() {
    local service_name=$1
    local initial_pid=$2
    local restart_cmd=$3
    local current_pid=$initial_pid

    while true; do
        sleep 10

        # 检查进程是否仍在运行
        if ! kill -0 "$current_pid" 2>/dev/null; then
            local restart_count=${SERVICE_RESTART_COUNT["$service_name"]:-0}

            if [ $restart_count -ge $MAX_RESTART_ATTEMPTS ]; then
                log_error "${service_name} 已达到最大重启次数 ($MAX_RESTART_ATTEMPTS)，停止重启"
                log_restart "${service_name} 达到最大重启次数，已停止"
                return 1
            fi

            restart_count=$((restart_count + 1))
            SERVICE_RESTART_COUNT["$service_name"]=$restart_count

            local delay=$((RESTART_DELAY_BASE * restart_count))
            log_warning "${service_name} (PID $current_pid) 已崩溃，将在 ${delay} 秒后重启（尝试 ${restart_count}/${MAX_RESTART_ATTEMPTS}）"
            log_restart "${service_name} 崩溃，PID: $current_pid，重启尝试: ${restart_count}/${MAX_RESTART_ATTEMPTS}"

            sleep $delay

            log_info "正在重启 ${service_name}..."

            # 执行重启命令并获取新的 PID
            eval "$restart_cmd"

            if [ $? -eq 0 ]; then
                # 获取最新启动的进程 PID（从全局变量）
                current_pid=$LAST_SERVICE_PID
                log_success "${service_name} 重启成功 (新 PID: $current_pid)"
                log_restart "${service_name} 重启成功，新 PID: $current_pid"
                # 重置重启计数
                SERVICE_RESTART_COUNT["$service_name"]=0
            else
                log_error "${service_name} 重启失败"
                log_restart "${service_name} 重启失败"
            fi
        fi
    done
}

print_summary() {
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}   所有服务已启动并运行${NC}"
    echo -e "${GREEN}============================================================${NC}\n"

    echo -e "${BLUE}直接访问端点:${NC}"
    echo -e "  ${YELLOW}前端 UI:${NC}      http://${VITE_FRONTEND_HOST}:${VITE_FRONTEND_PORT}"
    echo -e "  ${YELLOW}后端 API:${NC}     http://${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"
    echo -e "  ${YELLOW}API 文档:${NC}     http://${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}/docs"
    echo -e "  ${YELLOW}WebSocket:${NC}    ws://${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT}/ws"
    echo ""

    echo -e "${BLUE}MCP 服务:${NC}"
    echo -e "  ${YELLOW}论文搜索:${NC}     http://${PAPER_SEARCH_MCP_HOST}:${PAPER_SEARCH_MCP_PORT}/sse"
    echo -e "  ${YELLOW}仿真:${NC}         http://${SIMULATION_MCP_HOST}:${SIMULATION_MCP_PORT}/sse"
    echo -e "  ${YELLOW}数据库:${NC}       http://${DATABASE_MCP_HOST}:${DATABASE_MCP_PORT}/sse"
    echo ""

    if command -v nginx >/dev/null 2>&1 && systemctl is-active --quiet nginx 2>/dev/null; then
        echo -e "${BLUE}Nginx 反向代理（如已配置）:${NC}"
        echo -e "  ${YELLOW}统一访问:${NC}     http://<服务器IP>:50001"
        echo ""
    fi

    echo -e "${BLUE}日志文件:${NC}"
    echo "  logs/backend.log      - 后端日志"
    echo "  logs/database.log     - 数据库 MCP 日志"
    echo "  logs/paper_search.log - 论文搜索 MCP 日志"
    echo "  logs/simulation.log   - 仿真 MCP 日志"
    echo "  logs/frontend.log     - 前端日志"
    echo "  logs/startup.log      - 启动日志"
    echo "  logs/restart.log      - 重启日志"
    echo ""

    echo -e "${CYAN}自动重启已启用:${NC}"
    echo "  最大重启次数: ${MAX_RESTART_ATTEMPTS}"
    echo "  基础重启延迟: ${RESTART_DELAY_BASE} 秒（指数退避）"
    echo ""
}

prompt_log_view() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}   开始实时查看日志${NC}"
    echo -e "${CYAN}============================================================${NC}\n"

    log_info "正在同时查看后端和前端日志..."
    echo -e "${CYAN}提示: ${GREEN}绿色${NC}=后端日志, ${BLUE}蓝色${NC}=前端日志${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止所有服务并退出${NC}"
    echo -e "${CYAN}服务监控已启用，崩溃时将自动重启${NC}\n"
    sleep 2

    # 使用 tail -f 同时监控两个文件，并用 sed 添加颜色标记
    # 保存 tail 进程的 PID 以便在 cleanup 时终止
    tail -f logs/backend.log | sed "s/^/$(echo -e '\033[0;32m')[后端] /" &  
    TAIL_PIDS+=($!)
    tail -f logs/frontend.log | sed "s/^/$(echo -e '\033[0;34m')[前端] /" &  
    TAIL_PIDS+=($!)
}

# -----------------------------------------------------------------------------
# 主流程
# -----------------------------------------------------------------------------
print_banner
check_dependencies
load_config
prepare_workspace
kill_stale_processes

log_info "已加载配置:"
log_config "前端:              ${VITE_FRONTEND_HOST}:${VITE_FRONTEND_PORT}"
log_config "后端 HTTP:         ${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"
log_config "后端 WebSocket:    ${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT}"
log_config "论文搜索 MCP:      ${PAPER_SEARCH_MCP_HOST}:${PAPER_SEARCH_MCP_PORT}"
log_config "仿真 MCP:          ${SIMULATION_MCP_HOST}:${SIMULATION_MCP_PORT}"
log_config "数据库 MCP:        ${DATABASE_MCP_HOST}:${DATABASE_MCP_PORT}"
echo ""

log_info "正在启动 MCP 服务..."
start_mcp_service "Database MCP" "database_call/server.py" "database.log" "${DATABASE_MCP_HOST}" "${DATABASE_MCP_PORT}"
database_pid=$LAST_SERVICE_PID

start_mcp_service "Paper Search MCP" "paper_search/server.py" "paper_search.log" "${PAPER_SEARCH_MCP_HOST}" "${PAPER_SEARCH_MCP_PORT}"
paper_search_pid=$LAST_SERVICE_PID

start_mcp_service "Simulation MCP" "simulation/server.py" "simulation.log" "${SIMULATION_MCP_HOST}" "${SIMULATION_MCP_PORT}"
simulation_pid=$LAST_SERVICE_PID

start_backend
backend_pid=$LAST_SERVICE_PID

start_frontend
frontend_pid=$LAST_SERVICE_PID

print_summary

log_success "所有服务启动完成！"
log_info "启动日志已保存到: $STARTUP_LOG"
log_info "重启日志将保存到: $RESTART_LOG"
echo ""

# 启动后台监控进程
log_info "正在启动服务监控..."
monitor_service "Database MCP" "$database_pid" "start_mcp_service 'Database MCP' 'database_call/server.py' 'database.log' '${DATABASE_MCP_HOST}' '${DATABASE_MCP_PORT}' 'true'" &
monitor_service "Paper Search MCP" "$paper_search_pid" "start_mcp_service 'Paper Search MCP' 'paper_search/server.py' 'paper_search.log' '${PAPER_SEARCH_MCP_HOST}' '${PAPER_SEARCH_MCP_PORT}' 'true'" &
monitor_service "Simulation MCP" "$simulation_pid" "start_mcp_service 'Simulation MCP' 'simulation/server.py' 'simulation.log' '${SIMULATION_MCP_HOST}' '${SIMULATION_MCP_PORT}' 'true'" &
monitor_service "Backend" "$backend_pid" "start_backend" &
monitor_service "Frontend" "$frontend_pid" "start_frontend" &
log_success "服务监控已启动（自动重启已启用）"
echo ""

prompt_log_view

# 等待任何进程退出（包括 tail 进程）
# 这允许 Ctrl+C 触发清理陷阱
wait
