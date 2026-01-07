# Redis 历史记录持久化部署指南

## Windows WSL2 部署步骤

### 前置要求
- Windows 10/11 (版本 2004 或更高)
- 已启用 WSL2
- 管理员权限

### 自动部署

#### 方法 1: 使用 PowerShell 脚本（推荐）

```powershell
# 1. 进入项目目录
cd d:\XJTU\Research\PHD\Agent\ST\ResearchMind

# 2. 运行部署脚本
.\scripts\deploy_redis_windows.ps1
```

#### 方法 2: 手动部署

```powershell
# 1. 检查 WSL 状态
wsl --status

# 2. 安装 Ubuntu (如果未安装)
wsl --install -d Ubuntu

# 3. 进入 WSL Ubuntu
wsl -d Ubuntu

# 4. 在 WSL 中执行以下命令
sudo apt update
sudo apt install redis-server -y

# 5. 配置 Redis
sudo nano /etc/redis/redis.conf

# 6. 启动 Redis
sudo service redis-server start

# 7. 测试连接
redis-cli ping
```

### 配置说明

#### Redis 配置文件位置
- WSL: `/etc/redis/redis.conf`
- Windows 访问: `\\wsl$\Ubuntu\etc\redis\redis.conf`

#### 关键配置项

```conf
# 网络
bind 127.0.0.1
port 6379

# 内存
maxmemory 2gb
maxmemory-policy allkeys-lru

# RDB 持久化
save 900 1
save 300 10
save 60 10000
dbfilename dump.rdb
dir /var/lib/redis

# AOF 持久化
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
aof-use-rdb-preamble yes
```

### 常用操作

#### 启动/停止服务

```powershell
# 启动
wsl -d Ubuntu sudo service redis-server start

# 停止
wsl -d Ubuntu sudo service redis-server stop

# 重启
wsl -d Ubuntu sudo service redis-server restart

# 查看状态
wsl -d Ubuntu sudo service redis-server status
```

#### 连接 Redis CLI

```powershell
# 进入 Redis CLI
wsl -d Ubuntu redis-cli

# 在 CLI 中测试
127.0.0.1:6379> PING
PONG
127.0.0.1:6379> SET test "Hello Redis"
OK
127.0.0.1:6379> GET test
"Hello Redis"
```

#### 查看日志

```powershell
# 实时查看日志
wsl -d Ubuntu sudo tail -f /var/log/redis/redis-server.log

# 查看最后 100 行
wsl -d Ubuntu sudo tail -n 100 /var/log/redis/redis-server.log
```

### Python 集成

#### 安装依赖

```powershell
pip install redis
```

#### 基本使用

```python
from mcp_servers.database_call.redis_history_manager import RedisHistoryManager

# 初始化管理器
manager = RedisHistoryManager(host="localhost", port=6379)

# 添加消息
session_id = "user_session_001"
manager.add_message(session_id, "user", "你好")
manager.add_message(session_id, "assistant", "您好！有什么可以帮您？")

# 获取历史记录
history = manager.get_history(session_id)
for msg in history:
    print(f"{msg['role']}: {msg['content']}")

# 保存会话状态
state = {"user_id": "123", "context": "research"}
manager.save_session_state(session_id, state)

# 获取会话状态
loaded_state = manager.get_session_state(session_id)
print(loaded_state)
```

### 性能优化

#### 内存管理

```powershell
# 查看内存使用
wsl -d Ubuntu redis-cli INFO memory

# 设置最大内存
wsl -d Ubuntu redis-cli CONFIG SET maxmemory 2gb
wsl -d Ubuntu redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### 持久化策略

- **RDB**: 适合定期备份，恢复快
- **AOF**: 数据安全性高，可能影响性能
- **混合模式**: 推荐使用，兼顾性能和安全

### 监控与维护

#### 查看统计信息

```powershell
# 服务器信息
wsl -d Ubuntu redis-cli INFO server

# 内存信息
wsl -d Ubuntu redis-cli INFO memory

# 持久化信息
wsl -d Ubuntu redis-cli INFO persistence

# 统计信息
wsl -d Ubuntu redis-cli INFO stats
```

#### 备份数据

```powershell
# 手动触发 RDB 快照
wsl -d Ubuntu redis-cli BGSAVE

# 复制数据文件
wsl -d Ubuntu sudo cp /var/lib/redis/dump.rdb /backup/dump_$(date +%Y%m%d).rdb
```

#### 清理过期数据

```python
from mcp_servers.database_call.redis_history_manager import RedisHistoryManager

manager = RedisHistoryManager()
# 清理 7 天前的会话
cleaned = manager.cleanup_expired_sessions(days=7)
print(f"清理了 {cleaned} 个过期会话")
```

### 故障排查

#### Redis 无法启动

```powershell
# 检查配置文件语法
wsl -d Ubuntu redis-server /etc/redis/redis.conf --test-memory 1

# 查看错误日志
wsl -d Ubuntu sudo cat /var/log/redis/redis-server.log
```

#### 连接被拒绝

```powershell
# 检查服务状态
wsl -d Ubuntu sudo service redis-server status

# 检查端口占用
wsl -d Ubuntu sudo netstat -tlnp | grep 6379

# 检查防火墙
wsl -d Ubuntu sudo ufw status
```

#### 内存不足

```powershell
# 查看内存使用
wsl -d Ubuntu redis-cli INFO memory

# 清理所有数据（谨慎使用）
wsl -d Ubuntu redis-cli FLUSHALL

# 删除特定键
wsl -d Ubuntu redis-cli DEL key_name
```

### 安全建议

1. **设置密码**
```conf
# /etc/redis/redis.conf
requirepass your_strong_password_here
```

2. **限制访问**
```conf
bind 127.0.0.1  # 仅本地访问
protected-mode yes
```

3. **禁用危险命令**
```conf
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

### 自动启动配置

#### Windows 启动时自动启动 Redis

创建任务计划程序任务：

```powershell
# 创建启动脚本
$script = @"
wsl -d Ubuntu sudo service redis-server start
"@
$script | Out-File -FilePath "$env:USERPROFILE\start_redis.ps1"

# 创建计划任务
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File $env:USERPROFILE\start_redis.ps1"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "StartRedis" -Action $action -Trigger $trigger -RunLevel Highest
```

### 测试部署

运行测试脚本验证部署：

```powershell
# 运行 Python 测试
python mcp_servers\database_call\redis_history_manager.py
```

预期输出：
```
✓ Redis 连接成功: localhost:6379

1. 添加消息...
2. 获取历史记录...
  [1] user: 你好，请帮我分析一下材料性能
  [2] assistant: 好的，我可以帮您分析材料的各项性能指标
  [3] user: 关注热导率数据
3. 保存会话状态...
4. 获取会话状态...
  状态: {'user_id': 'user_123', 'context': 'material_analysis', 'preferences': {'language': 'zh-CN'}}
5. Redis 统计信息...
  版本: 7.x.x
  内存使用: 1.23M
  运行天数: 0
6. 列出所有会话...
  会话数量: 1
7. 清理测试数据...

✓ 测试完成！
```

## Linux 系统部署差异

### Ubuntu/Debian

```bash
# 安装
sudo apt update
sudo apt install redis-server

# 配置文件
/etc/redis/redis.conf

# 服务管理
sudo systemctl start redis-server
sudo systemctl enable redis-server
sudo systemctl status redis-server
```

### CentOS/RHEL

```bash
# 安装
sudo yum install redis

# 配置文件
/etc/redis.conf

# 服务管理
sudo systemctl start redis
sudo systemctl enable redis
sudo systemctl status redis
```

### 主要差异

| 项目 | Windows (WSL2) | Linux (原生) |
|------|----------------|--------------|
| 安装方式 | 通过 WSL Ubuntu | 系统包管理器 |
| 服务管理 | `service` 命令 | `systemctl` |
| 性能 | 轻微虚拟化开销 | 原生性能 |
| 配置路径 | `/etc/redis/` | `/etc/redis/` |
| 数据路径 | `/var/lib/redis/` | `/var/lib/redis/` |
| 自动启动 | 需手动配置 | `systemctl enable` |

## 参考资料

- [Redis 官方文档](https://redis.io/documentation)
- [Redis 持久化](https://redis.io/topics/persistence)
- [WSL 文档](https://docs.microsoft.com/en-us/windows/wsl/)
