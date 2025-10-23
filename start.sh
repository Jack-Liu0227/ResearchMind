#!/bin/bash

# =============================================================================
# ResearchMind unified launcher
# =============================================================================
# Starts every component (backend, MCP servers, frontend) using the variables
# defined in .env. It also handles log redirection, process tracking, and
# graceful shutdown on Ctrl+C.
#
# Usage:
#   bash start.sh
#
# NOTE: Nginx is not managed here. Configure and start it manually if needed.
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
cleanup() {
    log_warning "Stopping all managed processes..."

    if [ -f .service_pids ]; then
        while read -r pid; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                log_info "Killing PID $pid"
                kill "$pid" 2>/dev/null || true
            fi
        done < .service_pids
        rm -f .service_pids
    fi

    log_success "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# ------------------------------- Load .env file ------------------------------
load_config() {
    if [ ! -f .env ]; then
        log_error ".env file is missing."
        exit 1
    fi

    # shellcheck disable=SC2046,SC1090
    set -a
    source <(
        sed '1s/^\xEF\xBB\xBF//' .env \
        | sed 's/\r$//' \
        | grep -v '^\s*#' \
        | grep -v '^\s*$'
    )
    set +a

    log_success ".env configuration loaded."
}

# ------------------------------ Pre-flight checks ---------------------------
print_banner() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "   ResearchMind start script v2.0"
    echo "   Distributed-ready | Flexible config | Cross-host access"
    echo "============================================================"
    echo -e "${NC}"
}

check_dependencies() {
    log_info "Checking runtime dependencies..."

    if ! command -v uv >/dev/null 2>&1; then
        log_error "uv is not installed. Install it from https://docs.astral.sh/uv/"
        exit 1
    fi
    log_success "uv available."

    if ! command -v npm >/dev/null 2>&1; then
        log_error "npm is not installed. Install Node.js first."
        exit 1
    fi
    log_success "npm available."
}

prepare_workspace() {
    mkdir -p logs
    : > .service_pids
}

kill_stale_processes() {
    log_info "Cleaning up stale processes and occupied ports..."

    pkill -9 -f "uv run python" 2>/dev/null || true
    pkill -9 -f "npm run dev" 2>/dev/null || true
    pkill -9 -f "node .*vite" 2>/dev/null || true

    if command -v netstat >/dev/null 2>&1 && command -v awk >/dev/null 2>&1; then
        for port in 50001 50002 50003 50004 50005 50006; do
            pids=$(netstat -ano 2>/dev/null | awk -v p=":$port" '$0 ~ p {print $NF}' | sort -u)
            for pid in $pids; do
                # Skip non-numeric or PID 0 entries (system idle)
                if ! [[ "$pid" =~ ^[0-9]+$ ]] || [ "$pid" -eq 0 ]; then
                    continue
                fi
                if kill -0 "$pid" 2>/dev/null; then
                    log_info "Releasing port $port (PID $pid)"
                    kill "$pid" 2>/dev/null || true
                fi
            done
        done
    fi
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
    uv run python "$script_path" 2>&1 | tee "../logs/${log_name}" &
    local pid=$!
    popd >/dev/null
    register_pid "$pid"
    sleep 3
    log_success "${service_name} started (PID ${pid})."
}

start_backend() {
    log_info "Starting backend services..."
    log_info "WebSocket endpoint: ${RESEARCHMIND_WS_HOST}:${RESEARCHMIND_WS_PORT}"
    log_info "HTTP endpoint:      ${RESEARCHMIND_HTTP_HOST}:${RESEARCHMIND_HTTP_PORT}"

    uv run python main.py 2>&1 | tee logs/backend.log &
    local pid=$!
    register_pid "$pid"
    sleep 4
    log_success "Backend started (PID ${pid})."
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
    npm run dev -- --host "${VITE_FRONTEND_HOST}" --port "${VITE_FRONTEND_PORT}" 2>&1 | tee ../logs/frontend.log &
    local pid=$!
    popd >/dev/null
    register_pid "$pid"
    sleep 3
    log_success "Frontend started (PID ${pid})."
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

    echo -e "${BLUE}Logs:${NC}"
    echo "  logs/backend.log"
    echo "  logs/database.log"
    echo "  logs/paper_search.log"
    echo "  logs/simulation.log"
    echo "  logs/frontend.log"
    echo ""

    echo -e "${BLUE}Remote deployment hints:${NC}"
    echo "  - Set VITE_FRONTEND_HOST=0.0.0.0 to expose the UI"
    echo "  - Set RESEARCHMIND_HTTP_HOST=0.0.0.0 for remote API access"
    echo "  - Update VITE_API_URL, VITE_WS_URL and *_MCP_URL with the public host"
    echo ""

    echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"
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

while true; do
    sleep 1
done
