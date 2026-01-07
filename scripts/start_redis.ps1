<#
Start Redis (Docker) for Windows

- Uses current repo directory for redis.conf and data (./redis-data)
- Auto-starts Docker Desktop if needed
- Ensures .env has REDIS_HOST/REDIS_PORT

Usage:
  powershell -ExecutionPolicy Bypass -File ./scripts/start_redis.ps1
#>

param(
  [string]$ContainerName = "researchmind-redis",
  [int]$Port = 6379
)

$ErrorActionPreference = 'Stop'

function Ensure-Docker {
  try {
    $ver = docker version --format '{{.Server.Version}}' 2>$null
    if (-not $ver) { throw 'Docker engine not running' }
    Write-Host "[OK] Docker engine: $ver"
  } catch {
    Write-Host "[INFO] Starting Docker Desktop..."
    $dockerApp = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerApp)) { throw "Docker Desktop not found at: $dockerApp" }
    Start-Process -FilePath $dockerApp | Out-Null
    Start-Sleep -Seconds 8
    $retry = 0
    while ($retry -lt 30) {
      try {
        $ver = docker version --format '{{.Server.Version}}' 2>$null
        if ($ver) { Write-Host "[OK] Docker engine: $ver"; return }
      } catch {}
      Start-Sleep -Seconds 2
      $retry++
    }
    throw "Docker engine did not start in time"
  }
}

function Ensure-Paths {
  $root = $PSScriptRoot
  $confPath = Join-Path $root "..\redis.conf" | Resolve-Path -ErrorAction SilentlyContinue
  if (-not $confPath) {
    $confPath = Join-Path $root "..\redis.conf"
    Write-Host "[WARN] redis.conf not found, creating minimal config at $confPath"
    @(
      "bind 127.0.0.1",
      "port $Port",
      "protected-mode yes",
      "appendonly yes",
      "dir /data"
    ) | Set-Content -NoNewline:$false -Path $confPath -Encoding utf8
  }
  $dataDir = Join-Path $root "..\redis-data"
  if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
  return @{ Conf = (Resolve-Path $confPath).Path; Data = (Resolve-Path $dataDir).Path }
}

function Run-Redis($conf, $data) {
  Write-Host "[INFO] Using redis.conf: $conf"
  Write-Host "[INFO] Using data dir   : $data"

  docker pull redis:7-alpine | Out-Null

  $existing = docker ps -a --format '{{.Names}}' | Select-String -SimpleMatch $ContainerName
  if ($existing) {
    Write-Host "[INFO] Removing existing container '$ContainerName'"
    docker rm -f $ContainerName | Out-Null
  }

  $runArgs = @(
    'run','-d','--name', $ContainerName,
    '-p', "$Port:$Port",
    '-v', "$conf:/usr/local/etc/redis/redis.conf",
    '-v', "$data:/data",
    'redis:7-alpine','redis-server','/usr/local/etc/redis/redis.conf'
  )
  Write-Host "[CMD] docker $($runArgs -join ' ')"
  docker @runArgs | Out-Null

  Start-Sleep -Seconds 2
  $pong = docker exec $ContainerName redis-cli -p $Port ping
  if ($pong -ne 'PONG') { throw "Redis did not respond to PING" }
  Write-Host "[OK] Redis is up (PONG) on 127.0.0.1:$Port"
}

function Ensure-EnvVars($port) {
  $envFile = Join-Path $PSScriptRoot "..\.env"
  $lines = @()
  if (Test-Path $envFile) { $lines = Get-Content $envFile }
  $hasHost = $false; $hasPort = $false
  for ($i=0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^REDIS_HOST=') { $lines[$i] = 'REDIS_HOST=127.0.0.1'; $hasHost = $true }
    if ($lines[$i] -match '^REDIS_PORT=') { $lines[$i] = "REDIS_PORT=$port"; $hasPort = $true }
  }
  if (-not $hasHost) { $lines += 'REDIS_HOST=127.0.0.1' }
  if (-not $hasPort) { $lines += "REDIS_PORT=$port" }
  Set-Content -Path $envFile -Value $lines -Encoding utf8
  Write-Host "[OK] Updated .env with REDIS_HOST/REDIS_PORT"
}

try {
  Ensure-Docker
  $paths = Ensure-Paths
  Run-Redis -conf $paths.Conf -data $paths.Data
  Ensure-EnvVars -port $Port
  Write-Host "\nDone. Next steps:" -ForegroundColor Green
  Write-Host "  - Backend will auto-detect Redis via .env"
  Write-Host "  - To view logs: docker logs -f $ContainerName"
  Write-Host "  - To stop      : docker stop $ContainerName"
  Write-Host "  - To restart   : docker restart $ContainerName"
} catch {
  Write-Error $_
  exit 1
}

