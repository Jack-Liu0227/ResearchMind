#!/bin/bash
# Redis WSL2 部署脚本

echo "========================================="
echo "Redis WSL2 自动部署脚本"
echo "========================================="

# 更新系统包
echo "步骤 1/5: 更新系统包..."
sudo apt update && sudo apt upgrade -y

# 安装 Redis
echo "步骤 2/5: 安装 Redis Server..."
sudo apt install redis-server -y

# 备份原配置文件
echo "步骤 3/5: 配置 Redis..."
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

# 配置 Redis 持久化
sudo tee /etc/redis/redis.conf > /dev/null <<EOF
# Redis 配置文件 - ADK 历史记录持久化

# 网络配置
bind 127.0.0.1
port 6379
protected-mode yes

# 内存配置
maxmemory 2gb
maxmemory-policy allkeys-lru

# RDB 持久化配置（快照）
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# AOF 持久化配置（追加文件）
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes
aof-use-rdb-preamble yes

# 日志配置
loglevel notice
logfile /var/log/redis/redis-server.log

# 安全配置
# requirepass your_strong_password_here

# 客户端配置
timeout 300
tcp-keepalive 300
maxclients 10000

# 慢查询日志
slowlog-log-slower-than 10000
slowlog-max-len 128
EOF

# 创建必要的目录
echo "步骤 4/5: 创建数据目录..."
sudo mkdir -p /var/lib/redis
sudo mkdir -p /var/log/redis
sudo chown redis:redis /var/lib/redis
sudo chown redis:redis /var/log/redis

# 启动 Redis
echo "步骤 5/5: 启动 Redis 服务..."
sudo service redis-server start

# 检查状态
echo ""
echo "========================================="
echo "Redis 部署完成！"
echo "========================================="
echo ""
redis-cli ping
echo ""
redis-cli INFO server | grep redis_version
echo ""
echo "配置文件位置: /etc/redis/redis.conf"
echo "数据目录: /var/lib/redis"
echo "日志文件: /var/log/redis/redis-server.log"
echo ""
echo "常用命令:"
echo "  启动: sudo service redis-server start"
echo "  停止: sudo service redis-server stop"
echo "  重启: sudo service redis-server restart"
echo "  状态: sudo service redis-server status"
echo "  连接: redis-cli"
echo ""
