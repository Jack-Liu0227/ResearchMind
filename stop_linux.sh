#!/bin/bash

# =============================================================================
# ResearchMind service stopper for Linux
# =============================================================================
# Stops all ResearchMind services gracefully
#
# Usage:
#   bash stop_linux.sh
# =============================================================================

set -euo pipefail

# ----------------------------- Colour definitions ----------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

# -----------------------------------------------------------------------------
# Main cleanup
# -----------------------------------------------------------------------------
log_info "Stopping ResearchMind services..."

# Stop processes tracked in .service_pids
if [ -f .service_pids ]; then
    while read -r pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping PID $pid"
            kill "$pid" 2>/dev/null || true
            sleep 1
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_warning "Force killing PID $pid"
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
    done < .service_pids
    rm -f .service_pids
    log_success "Tracked processes stopped"
else
    log_warning "No .service_pids file found"
fi

# Kill any remaining ResearchMind processes
log_info "Cleaning up any remaining processes..."
pkill -f "uv run python main.py" 2>/dev/null || true
pkill -f "uv run python.*server.py" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true

sleep 2

log_success "All ResearchMind services stopped"
log_info "Nginx is not managed by this script. Use 'sudo systemctl stop nginx' if needed."

