# Redis WSL2 部署完成指南

## 当前状态

✓ WSL2 已安装并启用
✓ Ubuntu 发行版已下载并安装
⏳ Ubuntu 正在等待初始化配置

## 下一步操作

### 1. 完成 Ubuntu 初始化

Ubuntu 安装程序正在等待您创建用户账户。请按照以下步骤操作：

1. **在弹出的终端窗口中**，输入您想要的 Unix 用户名（建议使用小写字母）
   ```
   例如: research
   ```

2. **设置密码**（输入时不会显示，这是正常的）
   ```
   输入密码并确认
   ```

3. **等待初始化完成**
   ```
   系统会自动完成配置
   ```

### 2. 自动部署 Redis

初始化完成后，运行以下命令：

```powershell
# 方法 1: 使用自动部署脚本（推荐）
cd d:\XJTU\Research\PHD\Agent\ST\ResearchMind
.\scripts\deploy_redis_windows.ps1
```

或者手动部署：

```powershell
# 方法 2: 手动执行部署脚本
wsl -d Ubuntu bash -c "cd /mnt/d/XJTU/Research/PHD/Agent/ST/ResearchMind/scripts && chmod +x setup_redis_wsl.sh && ./setup_redis_wsl.sh"
```

### 3. 验证部署

```powershell
# 测试 Redis 连接
wsl -d Ubuntu redis-cli ping
# 应该返回: PONG

# 运行 Python 测试
python mcp_servers\database_call\redis_history_manager.py
```

## 快速命令参考

### 启动 Redis
```powershell
wsl -d Ubuntu sudo service redis-server start
```

### 停止 Redis
```powershell
wsl -d Ubuntu sudo service redis-server stop
```

### 检查状态
```powershell
wsl -d Ubuntu sudo service redis-server status
```

### 连接 Redis CLI
```powershell
wsl -d Ubuntu redis-cli
```

## 文件位置

### 部署脚本
- Windows PowerShell: `scripts\deploy_redis_windows.ps1`
- Linux Bash: `scripts\setup_redis_wsl.sh`

### Python 管理器
- `mcp_servers\database_call\redis_history_manager.py`

### 文档
- 完整部署指南: `docs\redis_deployment_guide.md`

## 配置信息

### Redis 连接参数
- **主机**: localhost
- **端口**: 6379
- **数据库**: 0
- **密码**: 无（默认）

### 持久化配置
- **RDB 快照**: 启用（每 15 分钟/5 分钟/1 分钟）
- **AOF 日志**: 启用（每秒同步）
- **混合模式**: 启用

### 数据存储位置（WSL 内）
- 配置文件: `/etc/redis/redis.conf`
- 数据目录: `/var/lib/redis/`
- 日志文件: `/var/log/redis/redis-server.log`

## Python 使用示例

```python
from mcp_servers.database_call.redis_history_manager import RedisHistoryManager

# 初始化
manager = RedisHistoryManager(host="localhost", port=6379)

# 添加对话历史
session_id = "research_session_001"
manager.add_message(session_id, "user", "分析材料热导率")
manager.add_message(session_id, "assistant", "开始分析...")

# 获取历史
history = manager.get_history(session_id, limit=10)

# 保存状态
state = {"project": "ResearchMind", "task": "material_analysis"}
manager.save_session_state(session_id, state)
```

## 故障排查

### 如果 Ubuntu 初始化卡住

```powershell
# 终止当前进程
Ctrl + C

# 重新启动 Ubuntu
wsl -d Ubuntu
```

### 如果 Redis 无法启动

```powershell
# 检查日志
wsl -d Ubuntu sudo cat /var/log/redis/redis-server.log

# 测试配置文件
wsl -d Ubuntu redis-server /etc/redis/redis.conf --test-memory 1
```

### 如果 Python 无法连接

```powershell
# 检查 Redis 是否运行
wsl -d Ubuntu redis-cli ping

# 检查端口
wsl -d Ubuntu sudo netstat -tlnp | grep 6379

# 重启 Redis
wsl -d Ubuntu sudo service redis-server restart
```

## 性能优化建议

1. **内存限制**: 默认设置为 2GB，可根据需要调整
2. **过期策略**: 使用 `allkeys-lru` 自动清理旧数据
3. **持久化**: 混合模式平衡性能和数据安全
4. **连接池**: Python 客户端自动管理连接池

## 安全建议

1. **仅本地访问**: 默认绑定到 127.0.0.1
2. **设置密码**: 生产环境建议启用密码认证
3. **禁用危险命令**: 可重命名 FLUSHALL 等命令
4. **定期备份**: 使用 RDB 快照进行数据备份

## 下一步学习

- 阅读完整文档: `docs\redis_deployment_guide.md`
- 查看 Redis 官方文档: https://redis.io/documentation
- 学习 Redis 数据结构: https://redis.io/topics/data-types
- 了解持久化机制: https://redis.io/topics/persistence

---

**部署时间**: 2026-01-03
**系统**: Windows + WSL2 + Ubuntu
**Redis 版本**: 最新稳定版
**Python 客户端**: redis-py
