# Redis Docker Deployment Script
# Using Docker Compose for better management

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Redis Docker Deployment (Compose)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Get project root
$projectRoot = Split-Path -Parent $PSScriptRoot

# Check Docker
Write-Host "Step 1/6: Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker not found" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check Docker Compose
Write-Host ""
Write-Host "Step 2/6: Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker compose version
    Write-Host "✓ Docker Compose available: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Compose not found" -ForegroundColor Red
    exit 1
}

# Check Docker service
Write-Host ""
Write-Host "Step 3/6: Checking Docker service..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "✓ Docker service running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker service not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and wait for it to be ready" -ForegroundColor Yellow
    exit 1
}

# Stop existing containers
Write-Host ""
Write-Host "Step 4/6: Stopping existing Redis containers..." -ForegroundColor Yellow
Push-Location $projectRoot
try {
    docker compose -f docker-compose.redis.yml down 2>&1 | Out-Null
    Write-Host "✓ Cleaned up existing containers" -ForegroundColor Green
} catch {
    Write-Host "✓ No cleanup needed" -ForegroundColor Green
}

# Start Redis with Docker Compose
Write-Host ""
Write-Host "Step 5/6: Starting Redis with Docker Compose..." -ForegroundColor Yellow
try {
    docker compose -f docker-compose.redis.yml up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Redis container started" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to start Redis" -ForegroundColor Red
        Pop-Location
        exit 1
    }
} catch {
    Write-Host "✗ Failed to start Redis: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# Wait for Redis to be ready
Write-Host ""
Write-Host "Waiting for Redis to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Test connection
Write-Host ""
Write-Host "Step 6/6: Testing Redis connection..." -ForegroundColor Yellow
$maxRetries = 5
$retryCount = 0
$connected = $false

while ($retryCount -lt $maxRetries -and -not $connected) {
    try {
        $pingResult = docker exec researchmind-redis redis-cli ping
        if ($pingResult -eq "PONG") {
            Write-Host "✓ Redis is ready and responding" -ForegroundColor Green
            $connected = $true
        }
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "Retry $retryCount/$maxRetries..." -ForegroundColor Gray
            Start-Sleep -Seconds 2
        }
    }
}

if (-not $connected) {
    Write-Host "✗ Redis connection failed after $maxRetries retries" -ForegroundColor Red
    exit 1
}

# Install Python Redis client
Write-Host ""
Write-Host "Installing Python Redis client..." -ForegroundColor Yellow
try {
    pip install redis -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Python Redis client installed" -ForegroundColor Green
    } else {
        Write-Host "⚠ Please install manually: pip install redis" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Please install manually: pip install redis" -ForegroundColor Yellow
}

# Show deployment summary
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✓ Redis Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Connection Info:" -ForegroundColor White
Write-Host "  Host:     localhost" -ForegroundColor Gray
Write-Host "  Port:     6379" -ForegroundColor Gray
Write-Host "  Database: 0" -ForegroundColor Gray
Write-Host ""
Write-Host "Container Info:" -ForegroundColor White
Write-Host "  Name:         researchmind-redis" -ForegroundColor Gray
Write-Host "  Status:       Running" -ForegroundColor Gray
Write-Host "  Restart:      Automatic" -ForegroundColor Gray
Write-Host "  Data Volume:  redis-data" -ForegroundColor Gray
Write-Host ""
Write-Host "Management Commands:" -ForegroundColor White
Write-Host "  View logs:    docker compose -f docker-compose.redis.yml logs" -ForegroundColor Cyan
Write-Host "  Stop:         docker compose -f docker-compose.redis.yml stop" -ForegroundColor Cyan
Write-Host "  Start:        docker compose -f docker-compose.redis.yml start" -ForegroundColor Cyan
Write-Host "  Restart:      docker compose -f docker-compose.redis.yml restart" -ForegroundColor Cyan
Write-Host "  Remove:       docker compose -f docker-compose.redis.yml down" -ForegroundColor Cyan
Write-Host ""
Write-Host "Connect to Redis CLI:" -ForegroundColor White
Write-Host "  docker exec -it researchmind-redis redis-cli" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment Variables (add to .env):" -ForegroundColor White
Write-Host "  REDIS_HOST=localhost" -ForegroundColor Gray
Write-Host "  REDIS_PORT=6379" -ForegroundColor Gray
Write-Host "  REDIS_DB=0" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Add environment variables to your .env file" -ForegroundColor Yellow
Write-Host "  2. Restart your application to enable Redis persistence" -ForegroundColor Yellow
Write-Host "  3. Monitor logs: docker compose -f docker-compose.redis.yml logs -f" -ForegroundColor Yellow
Write-Host ""
