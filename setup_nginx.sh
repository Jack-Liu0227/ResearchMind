#!/bin/bash

# ResearchMind Nginx 反向代理自动配置脚本
# 用法：bash setup_nginx.sh

set -e

echo "=========================================="
echo "ResearchMind Nginx 反向代理配置"
echo "=========================================="

# 检查 Nginx 是否安装
if ! command -v nginx &> /dev/null; then
    echo "📦 Nginx 未安装，正在安装..."
    apt-get update
    apt-get install -y nginx
else
    echo "✅ Nginx 已安装"
fi

# 清理旧配置
echo "🧹 清理旧配置..."
rm -f /etc/nginx/sites-enabled/researchmind
rm -f /etc/nginx/sites-available/researchmind
rm -f /etc/nginx/sites-enabled/default

# 创建 Nginx 配置文件
echo "📝 创建 Nginx 配置文件..."

cat > /etc/nginx/sites-available/researchmind << 'EOF'
# 定义上游服务器
upstream frontend {
    server 127.0.0.1:50010;
}

upstream backend_api {
    server 127.0.0.1:50002;
}

upstream websocket {
    server 127.0.0.1:50003;
}

# HTTP 服务器配置
server {
    listen 50001 default_server;
    listen [::]:50001 default_server;
    
    server_name _;
    
    client_max_body_size 100M;
    
    access_log /var/log/nginx/researchmind_access.log;
    error_log /var/log/nginx/researchmind_error.log;

    # 前端静态文件和根路径
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 后端 API 路由
    # 重要：使用 proxy_pass http://backend_api/api/ 而不是 http://backend_api/
    # 这样 /api/download/... 会正确转发到 http://backend_api/api/download/...
    location /api/ {
        proxy_pass http://backend_api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # WebSocket 路由
    location /ws/ {
        proxy_pass http://websocket/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # 健康检查端点
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

echo "✅ Nginx 配置文件已创建"

# 创建新配置的符号链接
echo "🔗 创建配置符号链接..."
ln -sf /etc/nginx/sites-available/researchmind /etc/nginx/sites-enabled/researchmind

# 测试 Nginx 配置
echo "🧪 测试 Nginx 配置..."
if nginx -t; then
    echo "✅ Nginx 配置测试通过"
else
    echo "❌ Nginx 配置测试失败"
    exit 1
fi

# 启动或重新加载 Nginx
echo "🚀 启动/重新加载 Nginx..."

# 检查是否使用 systemd
if command -v systemctl &> /dev/null && systemctl is-active --quiet systemd-journald 2>/dev/null; then
    if systemctl is-active --quiet nginx; then
        systemctl reload nginx
        echo "✅ Nginx 已重新加载"
    else
        systemctl start nginx
        echo "✅ Nginx 已启动"
    fi

    # 验证 Nginx 状态
    echo "📊 验证 Nginx 状态..."
    systemctl status nginx --no-pager
else
    # 使用 service 命令（适用于非 systemd 系统）
    if service nginx status &> /dev/null; then
        service nginx reload
        echo "✅ Nginx 已重新加载"
    else
        service nginx start
        echo "✅ Nginx 已启动"
    fi
fi

# 检查端口监听
echo ""
echo "📡 检查端口监听..."
netstat -tlnp | grep 50001 || echo "⚠️  端口 50001 未监听"

echo ""
echo "=========================================="
echo "✅ Nginx 配置完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  前端：http://localhost:50001"
echo "  API：http://localhost:50001/api"
echo "  WebSocket：ws://localhost:50001/ws"
echo ""
echo "日志位置："
echo "  访问日志：/var/log/nginx/researchmind_access.log"
echo "  错误日志：/var/log/nginx/researchmind_error.log"
echo ""
echo "常用命令："
echo "  查看状态：sudo systemctl status nginx"
echo "  重新加载：sudo systemctl reload nginx"
echo "  重启：sudo systemctl restart nginx"
echo "  停止：sudo systemctl stop nginx"
echo ""

