#!/usr/bin/env bash
# ResearchMind Nginx 反向代理自动配置（Linux 生产环境版）
# 用法：sudo bash setup_nginx.sh [--listen-port 50001]

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
bash setup_nginx.sh
# 日志函数
log() {
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

# 检查是否以 root 权限运行
if [[ $EUID -ne 0 ]]; then
   log_error "此脚本必须以 root 权限运行"
   log "请使用: sudo bash setup_nginx.sh"
   exit 1
fi

LISTEN_PORT="${2:-50001}"
if [[ "${1:-}" != "--listen-port" && -n "${1:-}" ]]; then LISTEN_PORT="50001"; fi

# 检查 .env 文件是否存在，如果存在远程部署配置文件则优先使用
if [[ -f .env.remote ]]; then
  log "使用远程部署配置文件 .env.remote"
  ENV_FILE=".env.remote"
elif [[ -f .env ]]; then
  log "使用本地配置文件 .env"
  ENV_FILE=".env"
else
  log_error "未找到 .env 或 .env.remote 配置文件"
  exit 1
fi

set -a
source <(sed '1s/^\xEF\xBB\xBF//' "$ENV_FILE" | sed 's/\r$//' | grep -v '^\s*#' | grep -v '^\s*$')
set +a

FRONTEND_PORT="${VITE_FRONTEND_PORT:-50010}"
HTTP_PORT="${RESEARCHMIND_HTTP_PORT:-50002}"
WS_PORT="${RESEARCHMIND_WS_PORT:-50003}"

# 检查 Nginx 是否安装
if ! command -v nginx &> /dev/null; then
  log_error "未找到 nginx，请先安装 nginx"
  log "Ubuntu/Debian: apt update && apt install nginx"
  log "CentOS/RHEL: yum install nginx"
  exit 1
fi

log_success "Nginx 已安装: $(nginx -v 2>&1)"

# 确定 Nginx 配置目录
if [[ -d "/etc/nginx/sites-available" ]]; then
  CONF_DIR="/etc/nginx/sites-available"
  CONF_PATH="${CONF_DIR}/researchmind"
  USE_SITES=true
else
  CONF_DIR="/etc/nginx/conf.d"
  CONF_PATH="${CONF_DIR}/researchmind.conf"
  USE_SITES=false
fi

mkdir -p "$CONF_DIR"

# 备份现有配置
if [[ -f "$CONF_PATH" ]]; then
  BACKUP_PATH="${CONF_PATH}.backup.$(date +%Y%m%d%H%M%S)"
  log "备份现有配置到 $BACKUP_PATH"
  cp "$CONF_PATH" "$BACKUP_PATH"
fi

# 若 nginx.conf 未包含 conf.d，则自动注入一次
if ! grep -Eq 'include\s+/etc/nginx/conf\.d/\*\.conf;' /etc/nginx/nginx.conf && [[ "$USE_SITES" == false ]]; then
  log "修改 nginx.conf 以包含 conf.d 配置..."
  cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak.$(date +%Y%m%d%H%M%S)
  awk '
    BEGIN{ins=0}
    {print}
    /http\s*\{/ && !ins {print "    include /etc/nginx/conf.d/*.conf;"; ins=1}
  ' /etc/nginx/nginx.conf > /etc/nginx/nginx.conf.tmp && mv /etc/nginx/nginx.conf.tmp /etc/nginx/nginx.conf
fi

cat > "$CONF_PATH" <<EOF

# ResearchMind reverse proxy (generated)

# WebSocket upgrade mapping for robust Connection header
map \$http_upgrade \$connection_upgrade {
    default close;
    "websocket" upgrade;
}

upstream researchmind_frontend { server 127.0.0.1:${FRONTEND_PORT}; }
upstream researchmind_backend  { server 127.0.0.1:${HTTP_PORT}; }
upstream researchmind_ws       { server 127.0.0.1:${WS_PORT}; }

server {
    listen 0.0.0.0:${LISTEN_PORT} default_server;
    listen [::]:${LISTEN_PORT} default_server;
    server_name _;

    client_max_body_size 100M;

    access_log /var/log/nginx/researchmind_access.log;
    error_log  /var/log/nginx/researchmind_error.log warn;

    # 全局设置：彻底解决 ERR_CONTENT_LENGTH_MISMATCH 问题
    # 完全禁用代理缓冲以避免内容长度不匹配
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_http_version 1.1;

    # 禁用临时文件存储（关键！）
    proxy_max_temp_file_size 0;

    # 禁用所有缓存
    proxy_cache off;
    proxy_store off;

    # 禁用压缩
    proxy_set_header Accept-Encoding "";

    # 设置较小的缓冲区（即使禁用了缓冲，这些设置也很重要）
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;

    # 前端（Vite/HMR），关闭缓冲避免 /var/lib/nginx/proxy 权限问题
    location / {
        proxy_pass http://researchmind_frontend;

        # HTTP/1.1 和 WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;

        # 基础代理头部
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_set_header X-Forwarded-Port \$server_port;

        # 禁用缓冲和缓存
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_cache off;
        proxy_store off;

        # 禁用压缩
        proxy_set_header Accept-Encoding "";

        # 增加超时
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 专门处理 Vite 依赖文件 - 解决 ERR_CONTENT_LENGTH_MISMATCH
    location ~* /node_modules/\.vite/deps/ {
        proxy_pass http://researchmind_frontend;

        # 基础代理头部
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # HTTP/1.1 支持
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        # 关键：完全禁用所有缓冲和缓存
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_cache off;
        proxy_store off;

        # 禁用压缩（让 Vite 直接发送原始内容）
        proxy_set_header Accept-Encoding "";

        # 使用分块传输编码
        chunked_transfer_encoding on;

        # 增加超时时间
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # 禁用重定向
        proxy_redirect off;

        # 增加缓冲区大小（虽然禁用了缓冲，但这些设置可以帮助处理大文件）
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # /api -> /api/
    location = /api { return 308 /api/; }

    # 后端 HTTP（保留 /api 前缀）
    location /api/ {
        proxy_pass http://researchmind_backend;  # 不带末尾 / ：保留 /api
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_set_header X-Forwarded-Port \$server_port;

        proxy_connect_timeout 60s;
        proxy_send_timeout    300s;
        proxy_read_timeout    300s;

        proxy_request_buffering off;
        proxy_buffering off;
    }

    location /ws/ {
        proxy_pass http://researchmind_ws/;  # ← 带结尾 / ：去掉 /ws 前缀再转发
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_set_header X-Forwarded-Port \$server_port;

        proxy_read_timeout 7d;
        proxy_send_timeout 7d;
        proxy_connect_timeout 7d;
    }
    # 可选：把 /ws 重定向到 /ws/，避免落到 /
    location = /ws { return 308 /ws/; }

    # 健康检查
    location = /health { proxy_pass http://researchmind_backend/api/health; }
}
EOF

# 如果使用 sites-available/sites-enabled 结构，创建软链接
if [[ "$USE_SITES" == true ]]; then
  if [[ -f "/etc/nginx/sites-enabled/researchmind" ]]; then
    rm "/etc/nginx/sites-enabled/researchmind"
  fi
  ln -s "$CONF_PATH" "/etc/nginx/sites-enabled/researchmind"
  
  # 删除默认站点配置（如果存在）
  if [[ -f "/etc/nginx/sites-enabled/default" ]]; then
    rm "/etc/nginx/sites-enabled/default"
  fi
fi

log "🧪 测试 Nginx 配置"
if nginx -t; then
  log_success "Nginx 配置测试通过"
else
  log_error "Nginx 配置测试失败"
  exit 1
fi

log "🚀 重新加载 Nginx"
SYSTEMD_ACTIVE=false
if command -v systemctl >/dev/null 2>&1 && [[ "$(cat /proc/1/comm 2>/dev/null || true)" == "systemd" ]]; then
  SYSTEMD_ACTIVE=true
fi

if [[ "$SYSTEMD_ACTIVE" == true ]]; then
  systemctl reload nginx || systemctl restart nginx
else
  if command -v service >/dev/null 2>&1; then
    service nginx reload >/dev/null 2>&1 || service nginx start >/dev/null 2>&1 || true
  fi
  if pgrep -x nginx >/dev/null 2>&1; then
    nginx -s reload || true
  else
    nginx -c /etc/nginx/nginx.conf || true
  fi
fi

log_success "✅ 已写入：$CONF_PATH"
log_success "前端:   http://<IP>:${LISTEN_PORT}/"
log_success "API:    http://<IP>:${LISTEN_PORT}/api"
log_success "WS:     ws://<IP>:${LISTEN_PORT}/ws"