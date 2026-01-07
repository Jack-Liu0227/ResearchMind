# Redis WSL2 部署脚本 - Windows PowerShell
# 用于在 Windows 系统上通过 WSL2 部署 Redis

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Redis WSL2 自动部署脚本 (Windows)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 WSL 状态
Write-Host "步骤 1/6: 检查 WSL 状态..." -ForegroundColor Yellow
$wslStatus = wsl --status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ WSL 未安装或未启用" -ForegroundColor Red
    Write-Host "请运行: wsl --install" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ WSL 已安装" -ForegroundColor Green

# 检查 Ubuntu 是否安装
Write-Host ""
Write-Host "步骤 2/6: 检查 Ubuntu 发行版..." -ForegroundColor Yellow
$wslList = wsl --list --quiet
if ($wslList -notcontains "Ubuntu") {
    Write-Host "Ubuntu 未安装，正在安装..." -ForegroundColor Yellow
    wsl --install -d Ubuntu
    Write-Host "✓ Ubuntu 安装完成" -ForegroundColor Green
    Write-Host "请重启系统后重新运行此脚本" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "✓ Ubuntu 已安装" -ForegroundColor Green
}

# 复制部署脚本到 WSL
Write-Host ""
Write-Host "步骤 3/6: 准备部署脚本..." -ForegroundColor Yellow
$scriptPath = "$PSScriptRoot\setup_redis_wsl.sh"
if (Test-Path $scriptPath) {
    # 转换为 WSL 路径
    $wslScriptPath = wsl wslpath -a $scriptPath
    Write-Host "✓ 脚本路径: $wslScriptPath" -ForegroundColor Green
} else {
    Write-Host "✗ 找不到部署脚本: $scriptPath" -ForegroundColor Red
    exit 1
}

# 在 WSL 中执行部署
Write-Host ""
Write-Host "步骤 4/6: 在 WSL Ubuntu 中部署 Redis..." -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray

# 赋予执行权限并运行
wsl -d Ubuntu bash -c "chmod +x '$wslScriptPath' && '$wslScriptPath'"

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Redis 部署失败" -ForegroundColor Red
    exit 1
}

# 测试 Redis 连接
Write-Host ""
Write-Host "步骤 5/6: 测试 Redis 连接..." -ForegroundColor Yellow
$pingResult = wsl -d Ubuntu redis-cli ping 2>&1
if ($pingResult -eq "PONG") {
    Write-Host "✓ Redis 运行正常" -ForegroundColor Green
} else {
    Write-Host "✗ Redis 连接失败" -ForegroundColor Red
    Write-Host "尝试启动 Redis..." -ForegroundColor Yellow
    wsl -d Ubuntu sudo service redis-server start
    Start-Sleep -Seconds 2
    $pingResult = wsl -d Ubuntu redis-cli ping 2>&1
    if ($pingResult -eq "PONG") {
        Write-Host "✓ Redis 启动成功" -ForegroundColor Green
    } else {
        Write-Host "✗ Redis 启动失败，请检查日志" -ForegroundColor Red
    }
}

# 安装 Python Redis 客户端
Write-Host ""
Write-Host "步骤 6/6: 安装 Python Redis 客户端..." -ForegroundColor Yellow
pip install redis -q
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python Redis 客户端安装成功" -ForegroundColor Green
} else {
    Write-Host "⚠ Python Redis 客户端安装失败，请手动安装: pip install redis" -ForegroundColor Yellow
}

# 显示完成信息
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Redis 部署完成！" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "连接信息:" -ForegroundColor White
Write-Host "  主机: localhost" -ForegroundColor Gray
Write-Host "  端口: 6379" -ForegroundColor Gray
Write-Host "  数据库: 0" -ForegroundColor Gray
Write-Host ""
Write-Host "常用命令:" -ForegroundColor White
Write-Host "  启动 Redis:" -ForegroundColor Gray
Write-Host "    wsl -d Ubuntu sudo service redis-server start" -ForegroundColor Cyan
Write-Host "  停止 Redis:" -ForegroundColor Gray
Write-Host "    wsl -d Ubuntu sudo service redis-server stop" -ForegroundColor Cyan
Write-Host "  检查状态:" -ForegroundColor Gray
Write-Host "    wsl -d Ubuntu sudo service redis-server status" -ForegroundColor Cyan
Write-Host "  连接 Redis CLI:" -ForegroundColor Gray
Write-Host "    wsl -d Ubuntu redis-cli" -ForegroundColor Cyan
Write-Host "  查看日志:" -ForegroundColor Gray
Write-Host "    wsl -d Ubuntu sudo tail -f /var/log/redis/redis-server.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "Python 使用示例:" -ForegroundColor White
Write-Host "  python mcp_servers\database_call\redis_history_manager.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "配置文件位置 (WSL):" -ForegroundColor White
Write-Host "  /etc/redis/redis.conf" -ForegroundColor Gray
Write-Host ""
Write-Host "数据目录 (WSL):" -ForegroundColor White
Write-Host "  /var/lib/redis" -ForegroundColor Gray
Write-Host ""

# 创建快捷启动脚本
$startScript = @"
# Redis 快捷启动脚本
wsl -d Ubuntu sudo service redis-server start
`$pingResult = wsl -d Ubuntu redis-cli ping 2>&1
if (`$pingResult -eq "PONG") {
    Write-Host "✓ Redis 已启动" -ForegroundColor Green
} else {
    Write-Host "✗ Redis 启动失败" -ForegroundColor Red
}
"@

$startScriptPath = "$PSScriptRoot\start_redis.ps1"
$startScript | Out-File -FilePath $startScriptPath -Encoding UTF8
Write-Host "已创建快捷启动脚本: $startScriptPath" -ForegroundColor Green
Write-Host ""
