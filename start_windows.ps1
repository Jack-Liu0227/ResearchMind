<#
.SYNOPSIS
    ResearchMind Windows Startup Script
    Replicates the functionality of start_linux.sh for Windows environments.

.DESCRIPTION
    Starts the Backend, MCP Servers, and Frontend.
    Handles process cleanup, log redirection, and port waiting.
    
.NOTES
    Requires PowerShell 5.1 or later.
    Run via start_windows.bat is recommended.
#>

$ErrorActionPreference = "Stop"
$Script:ProjectRoot = $PSScriptRoot
$Script:LogDir = Join-Path $ProjectRoot "..\data\logs"
if (-not (Test-Path $Script:LogDir)) { New-Item -ItemType Directory -Force -Path $Script:LogDir | Out-Null }

$StartupLog = Join-Path $Script:LogDir "startup.log"
$RestartLog = Join-Path $Script:LogDir "restart.log"

# Clear startup log
"" | Out-File -FilePath $StartupLog -Encoding utf8

function Log-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [INFO] $Message" | Out-File -FilePath $StartupLog -Append -Encoding utf8
}

function Log-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [SUCCESS] $Message" | Out-File -FilePath $StartupLog -Append -Encoding utf8
}

function Log-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [WARNING] $Message" | Out-File -FilePath $StartupLog -Append -Encoding utf8
}

function Log-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [ERROR] $Message" | Out-File -FilePath $StartupLog -Append -Encoding utf8
}

function Load-Env {
    $EnvFile = Join-Path $Script:ProjectRoot ".env"
    if (Test-Path $EnvFile) {
        Log-Info "Loading .env file..."
        Get-Content $EnvFile | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#")) {
                $parts = $line.Split('=', 2)
                if ($parts.Count -eq 2) {
                    $name = $parts[0].Trim()
                    $value = $parts[1].Trim()
                    # Remove quotes if present
                    $value = $value -replace '^"|"$', '' -replace "^'|'$", ''
                    [Environment]::SetEnvironmentVariable($name, $value, "Process")
                }
            }
        }
    } else {
        Log-Warning ".env file not found."
    }
}

function Stop-PortProcess {
    param([int]$Port)
    if (!$Port) { return }
    
    try {
        $tcpConnections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($tcpConnections) {
            foreach ($conn in $tcpConnections) {
                $pidToKill = $conn.OwningProcess
                if ($pidToKill -gt 0) {
                    try {
                        $proc = Get-Process -Id $pidToKill -ErrorAction SilentlyContinue
                        if ($proc) {
                            Log-Warning "Port $Port is in use by PID $pidToKill ($($proc.ProcessName)). Killing..."
                            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
                        }
                    } catch {
                        # Ignore process access errors
                    }
                }
            }
        }
    } catch {
        # Ignore network errors
    }
}

function Check-Dependencies {
    Log-Info "Checking dependencies..."
    
    if (Get-Command "uv" -ErrorAction SilentlyContinue) {
        Log-Success "uv found: $(uv --version 2>&1)"
    } else {
        Log-Error "uv not found. Please install it from https://docs.astral.sh/uv/"
        exit 1
    }

    if (Get-Command "npm" -ErrorAction SilentlyContinue) {
        Log-Success "npm found: $(npm --version 2>&1)"
    } else {
        Log-Error "npm not found. Please install Node.js."
        exit 1
    }

    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        Log-Success "python found: $(python --version 2>&1)"
    } else {
        Log-Error "python not found."
        exit 1
    }
}

function Start-ServiceBackground {
    param(
        [string]$Name,
        [string]$Command,
        [string]$Arguments,
        [string]$LogFile,
        [string]$WorkingDirectory
    )
    
    Log-Info "Starting $Name..."
    $LogPath = Join-Path $Script:LogDir $LogFile
    
    $ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
    $ProcessInfo.FileName = "cmd.exe"
    # Use cmd /c to run the command and redirect output
    # We use >> for append or > for overwrite. Using > compatible pattern.
    $ProcessInfo.Arguments = "/c $Command $Arguments > ""$LogPath"" 2>&1"
    $ProcessInfo.WorkingDirectory = $WorkingDirectory
    $ProcessInfo.CreateNoWindow = $true
    $ProcessInfo.UseShellExecute = $false
    
    try {
        $Process = [System.Diagnostics.Process]::Start($ProcessInfo)
        Log-Success "$Name started (PID $($Process.Id))"
        return $Process
    } catch {
        Log-Error "Failed to start ${Name}: $_"
        return $null
    }
}

function Wait-ForPort {
    param(
        [string]$Name,
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutSeconds = 120
    )
    
    Log-Info "Waiting for $Name on port $Port..."
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $connectAsync = $tcp.ConnectAsync($HostName, $Port)
            if ($connectAsync.Wait(1000)) {
                $tcp.Close()
                Log-Success "$Name is listening on port $Port"
                return $true
            }
        } catch {
            # Connection failed
        }
        Start-Sleep -Seconds 1
    }
    
    Log-Error "Timeout waiting for $Name on port $Port"
    return $false
}

# --- Main Execution ---

Write-Host "============================================================" -ForegroundColor Green
Write-Host "   ResearchMind Windows Launcher" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

Check-Dependencies
Load-Env

# Set defaults if not in env
$Env:RESEARCHMIND_HTTP_HOST = If ($Env:RESEARCHMIND_HTTP_HOST) { $Env:RESEARCHMIND_HTTP_HOST } Else { "0.0.0.0" }
$Env:RESEARCHMIND_HTTP_PORT = If ($Env:RESEARCHMIND_HTTP_PORT) { $Env:RESEARCHMIND_HTTP_PORT } Else { "8000" }
$Env:RESEARCHMIND_WS_HOST = If ($Env:RESEARCHMIND_WS_HOST) { $Env:RESEARCHMIND_WS_HOST } Else { "0.0.0.0" }
$Env:RESEARCHMIND_WS_PORT = If ($Env:RESEARCHMIND_WS_PORT) { $Env:RESEARCHMIND_WS_PORT } Else { "8000" }

$Env:PAPER_SEARCH_MCP_HOST = If ($Env:PAPER_SEARCH_MCP_HOST) { $Env:PAPER_SEARCH_MCP_HOST } Else { "0.0.0.0" }
$Env:PAPER_SEARCH_MCP_PORT = If ($Env:PAPER_SEARCH_MCP_PORT) { $Env:PAPER_SEARCH_MCP_PORT } Else { "50004" }

$Env:SIMULATION_MCP_HOST = If ($Env:SIMULATION_MCP_HOST) { $Env:SIMULATION_MCP_HOST } Else { "0.0.0.0" }
$Env:SIMULATION_MCP_PORT = If ($Env:SIMULATION_MCP_PORT) { $Env:SIMULATION_MCP_PORT } Else { "50005" }

$Env:DATABASE_MCP_HOST = If ($Env:DATABASE_MCP_HOST) { $Env:DATABASE_MCP_HOST } Else { "0.0.0.0" }
$Env:DATABASE_MCP_PORT = If ($Env:DATABASE_MCP_PORT) { $Env:DATABASE_MCP_PORT } Else { "50006" }

$Env:VITE_FRONTEND_HOST = If ($Env:VITE_FRONTEND_HOST) { $Env:VITE_FRONTEND_HOST } Else { "0.0.0.0" }
$Env:VITE_FRONTEND_PORT = If ($Env:VITE_FRONTEND_PORT) { $Env:VITE_FRONTEND_PORT } Else { "5173" }

# Clean up
Log-Info "Cleaning up old processes..."
Stop-PortProcess $Env:RESEARCHMIND_HTTP_PORT
Stop-PortProcess $Env:PAPER_SEARCH_MCP_PORT
Stop-PortProcess $Env:SIMULATION_MCP_PORT
Stop-PortProcess $Env:DATABASE_MCP_PORT
Stop-PortProcess $Env:VITE_FRONTEND_PORT


# Start Services
$Pids = @()

# Database MCP
$Proc = Start-ServiceBackground -Name "Database MCP" `
    -Command "uv" -Arguments "run python mcp_servers/database_call/server.py" `
    -LogFile "database.log" -WorkingDirectory $Script:ProjectRoot
if ($Proc) { $Pids += $Proc.Id }

# Paper Search MCP
$Proc = Start-ServiceBackground -Name "Paper Search MCP" `
    -Command "uv" -Arguments "run python mcp_servers/paper_search/server.py" `
    -LogFile "paper_search.log" -WorkingDirectory $Script:ProjectRoot
if ($Proc) { $Pids += $Proc.Id }

# Simulation MCP
$Proc = Start-ServiceBackground -Name "Simulation MCP" `
    -Command "uv" -Arguments "run python mcp_servers/simulation/server.py" `
    -LogFile "simulation.log" -WorkingDirectory $Script:ProjectRoot
if ($Proc) { $Pids += $Proc.Id }

# Backend
$Proc = Start-ServiceBackground -Name "Backend" `
    -Command "uv" -Arguments "run python main.py" `
    -LogFile "backend.log" -WorkingDirectory $Script:ProjectRoot
if ($Proc) { $Pids += $Proc.Id }

# Frontend
Log-Info "Installing Frontend dependencies if needed..."
if (-not (Test-Path "$Script:ProjectRoot\ui\node_modules")) {
    Push-Location "$Script:ProjectRoot\ui"
    npm install
    Pop-Location
}

$Proc = Start-ServiceBackground -Name "Frontend" `
    -Command "npm" -Arguments "run dev -- --host $($Env:VITE_FRONTEND_HOST) --port $($Env:VITE_FRONTEND_PORT)" `
    -LogFile "frontend.log" -WorkingDirectory "$Script:ProjectRoot\ui"
if ($Proc) { $Pids += $Proc.Id }

# Wait for ports (localhost for check)
Wait-ForPort "Database MCP" "127.0.0.1" $Env:DATABASE_MCP_PORT
Wait-ForPort "Paper Search MCP" "127.0.0.1" $Env:PAPER_SEARCH_MCP_PORT
Wait-ForPort "Simulation MCP" "127.0.0.1" $Env:SIMULATION_MCP_PORT
Wait-ForPort "Backend" "127.0.0.1" $Env:RESEARCHMIND_HTTP_PORT
# Frontend check might be slower
Wait-ForPort "Frontend" "127.0.0.1" $Env:VITE_FRONTEND_PORT

Write-Host "`nAll services started!" -ForegroundColor Green
Write-Host "Frontend: http://$($Env:VITE_FRONTEND_HOST):$($Env:VITE_FRONTEND_PORT)" -ForegroundColor Cyan
Write-Host "Backend:  http://$($Env:RESEARCHMIND_HTTP_HOST):$($Env:RESEARCHMIND_HTTP_PORT)" -ForegroundColor Cyan

Log-Info "Tailing logs (Backend & Frontend)... Press Ctrl+C to stop."

# Simple log tailing
try {
    Get-Content -Path "$Script:LogDir\backend.log", "$Script:LogDir\frontend.log" -Wait -Tail 10
} finally {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    foreach ($p in $Pids) {
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
}
