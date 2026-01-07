# Redis 持久化存储 - 部署指南

## 概述

ResearchMind 现在支持使用 **Redis** 进行 Agent 会话和历史记录的持久化存储，提供以下优势：

- **高性能**: 内存存储，读写速度快
- **持久化**: AOF 和 RDB 双重持久化机制
- **自动过期**: TTL 机制自动清理过期数据
- **高可用**: 支持主从复制和集群模式
- **无缝降级**: Redis 不可用时自动降级到文件存储

## 快速开始

### 方式一: Docker Compose (推荐)

**前提条件**: 已安装 Docker Desktop

```powershell
# 1. 启动 Redis
docker compose -f docker-compose.redis.yml up -d

# 2. 验证 Redis 运行状态
docker exec researchmind-redis redis-cli ping
# 应该返回: PONG

# 3. 安装 Python Redis 客户端
pip install redis

# 4. 添加环境变量到 .env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 5. 重启应用
```

### 方式二: 一键部署脚本

```powershell
# 运行部署脚本(自动安装和配置)
.\scripts\deploy_redis_docker.ps1
```

## 架构设计

```
┌─────────────────────────────────────────┐
│        Agent Coordinator                │
│  (services/agent_coordinator.py)        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     Hybrid Session Manager               │
│  (services/hybrid_session_manager.py)    │
│                                          │
│  ┌──────────────┐    ┌────────────────┐ │
│  │ Redis Manager │◄──►│ Session Manager│ │
│  │  (Primary)   │    │   (Fallback)   │ │
│  └──────────────┘    └────────────────┘ │
└──────────────┬───────────────────────────┘
               │
               ▼
       ┌───────────────┐
       │  Redis Server  │
       │  (Port 6379)   │
       └───────────────┘
```

### 关键组件

1. **RedisSessionManager** (`services/redis_session_manager.py`)
   - Redis 连接管理和连接池
   - 会话和历史记录的 CRUD 操作
   - TTL 自动过期管理

2. **HybridSessionManager** (`services/hybrid_session_manager.py`)
   - 自动选择 Redis 或文件存储
   - 无缝降级和容错处理
   - 统一的 API 接口

3. **SessionManager** (`services/session_manager.py`)
   - 文件存储后备方案
   - 向后兼容性保证

## 数据结构

### Redis 键命名规范

```
session:{session_id}      -> 会话元数据 (JSON, TTL: 24h)
history:{session_id}      -> 会话历史 (JSON, TTL: 7d)
metadata:{session_id}     -> 额外元数据 (JSON, TTL: 24h)
sessions:index            -> 会话索引 (Sorted Set, 按创建时间排序)
```

### 会话数据示例

```json
{
  "session_id": "abc123",
  "client_id": "user_1",
  "agent_id": "research_coordinator",
  "title": "材料研究会话",
  "created_at": "2026-01-03T19:00:00",
  "updated_at": "2026-01-03T19:30:00",
  "message_count": 10
}
```

## 配置选项

### 环境变量 (.env)

```env
# Redis 连接
REDIS_HOST=localhost          # Redis 主机地址
REDIS_PORT=6379               # Redis 端口
REDIS_DB=0                    # Redis 数据库编号 (0-15)
REDIS_PASSWORD=               # Redis 密码 (可选)

# TTL 配置 (可选,默认值如下)
# REDIS_SESSION_EXPIRE=86400  # 会话过期时间 (24小时)
# REDIS_HISTORY_EXPIRE=604800 # 历史过期时间 (7天)
```

### Redis 配置 (redis.conf)

关键配置项:

```conf
# 持久化
save 900 1                    # 15分钟内至少1次修改
appendonly yes                # 启用 AOF
appendfsync everysec          # 每秒同步

# 内存管理
maxmemory 256mb               # 最大内存限制
maxmemory-policy allkeys-lru  # LRU 淘汰策略

# 性能
tcp-keepalive 300             # TCP 保活时间
```

## 管理操作

### Docker Compose 命令

```powershell
# 查看日志
docker compose -f docker-compose.redis.yml logs -f

# 停止 Redis
docker compose -f docker-compose.redis.yml stop

# 启动 Redis
docker compose -f docker-compose.redis.yml start

# 重启 Redis
docker compose -f docker-compose.redis.yml restart

# 删除 Redis (包括数据)
docker compose -f docker-compose.redis.yml down -v
```

### Redis CLI 命令

```bash
# 连接到 Redis
docker exec -it researchmind-redis redis-cli

# 查看所有会话
KEYS session:*

# 查看会话数量
ZCARD sessions:index

# 查看特定会话
GET session:abc123

# 查看会话历史
GET history:abc123

# 清空所有数据 (谨慎使用!)
FLUSHDB

# 查看内存使用
INFO memory

# 查看持久化状态
INFO persistence
```

## 监控和调试

### 检查 Redis 健康状态

```powershell
# Python 检查
python -c "from services.redis_session_manager import is_redis_available; print(is_redis_available())"

# 直接 ping
docker exec researchmind-redis redis-cli ping
```

### 查看日志

```powershell
# 应用日志 (查找 Redis 相关)
# 成功: "✅ Redis connected"
# 失败: "⚠️ Redis not available, using fallback storage"

# Redis 日志
docker compose -f docker-compose.redis.yml logs -f redis
```

### 故障排除

**问题: Redis 连接失败**

```powershell
# 1. 检查 Docker 运行状态
docker ps | findstr redis

# 2. 检查 Redis 服务
docker exec researchmind-redis redis-cli ping

# 3. 查看 Redis 日志
docker logs researchmind-redis

# 4. 重启 Redis
docker restart researchmind-redis
```

**问题: 数据未持久化**

```bash
# 检查 AOF 状态
docker exec -it researchmind-redis redis-cli INFO persistence

# 检查数据目录
docker volume inspect redis-data
```

## 性能优化

### 连接池配置

默认配置:
- 最大连接数: 50
- 连接超时: 5秒
- Socket keepalive: 启用

自定义连接池 (修改 redis_session_manager.py):

```python
redis_manager = RedisSessionManager(
    host="localhost",
    port=6379,
    max_connections=100,  # 增加连接池大小
    socket_connect_timeout=10  # 增加超时时间
)
```

### 内存优化

监控内存使用:

```bash
# 查看内存统计
docker exec researchmind-redis redis-cli INFO memory

# 查看最大内存设置
docker exec researchmind-redis redis-cli CONFIG GET maxmemory
```

调整最大内存 (编辑 redis.conf):

```conf
maxmemory 512mb  # 增加到 512MB
```

## 备份和恢复

### 手动备份

```bash
# RDB 快照
docker exec researchmind-redis redis-cli BGSAVE

# 复制 RDB 文件
docker cp researchmind-redis:/data/dump.rdb ./backup/
```

### 自动备份

添加到 cron (Linux/WSL):

```bash
# 每天凌晨 2 点备份
0 2 * * * docker exec researchmind-redis redis-cli BGSAVE && docker cp researchmind-redis:/data/dump.rdb ~/backup/redis-$(date +\%Y\%m\%d).rdb
```

### 恢复数据

```bash
# 1. 停止 Redis
docker compose -f docker-compose.redis.yml stop

# 2. 复制备份文件
docker cp ./backup/dump.rdb researchmind-redis:/data/

# 3. 启动 Redis
docker compose -f docker-compose.redis.yml start
```

## 迁移指南

### 从文件存储迁移到 Redis

数据会自动迁移:

1. 启动 Redis
2. 重启应用
3. 现有会话会在下次访问时加载到 Redis
4. 新会话直接存储在 Redis

### 从 Redis 迁移到文件存储

1. 导出 Redis 数据 (可选):
```bash
docker exec researchmind-redis redis-cli --rdb dump.rdb
```

2. 停止 Redis 或移除环境变量
3. 应用自动降级到文件存储

## 生产环境建议

### 安全配置

1. **设置密码**:
```conf
# redis.conf
requirepass your_strong_password
```

```env
# .env
REDIS_PASSWORD=your_strong_password
```

2. **绑定内网地址**:
```conf
# redis.conf
bind 127.0.0.1
```

3. **禁用危险命令**:
```conf
# redis.conf
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

### 高可用配置

使用 Redis Sentinel 或 Redis Cluster 实现高可用性。

### 监控告警

集成 Prometheus + Grafana 监控 Redis 指标:
- 内存使用率
- 连接数
- 命令执行延迟
- 持久化状态

## 常见问题 (FAQ)

**Q: Redis 挂了怎么办?**

A: HybridSessionManager 会自动降级到文件存储,不影响使用。

**Q: Redis 数据会丢失吗?**

A: 使用 AOF + RDB 双重持久化,数据安全有保障。

**Q: 如何删除旧会话?**

A: Redis 使用 TTL 自动清理,也可手动删除:
```bash
docker exec researchmind-redis redis-cli DEL session:xxx history:xxx
```

**Q: 支持多个应用共享 Redis 吗?**

A: 支持,使用不同的 REDIS_DB 编号隔离数据。

**Q: Windows 上可以用吗?**

A: 可以,通过 Docker Desktop 或 WSL2 运行 Redis。

## 相关文档

- [Redis 官方文档](https://redis.io/documentation)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Redis Python 客户端](https://redis-py.readthedocs.io/)

## 支持

遇到问题? 查看:
- 应用日志
- Redis 日志: `docker logs researchmind-redis`
- 健康检查: `docker exec researchmind-redis redis-cli ping`
