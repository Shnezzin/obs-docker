# OBS Docker Startup Script for Windows
# This script helps start the OBS Docker environment on Windows

param(
    [switch]$Build,
    [switch]$NoBuild,
    [switch]$Logs,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Help
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    } else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Info($message) {
    Write-ColorOutput Green "[INFO] $message"
}

function Write-Warning($message) {
    Write-ColorOutput Yellow "[WARNING] $message"
}

function Write-Error($message) {
    Write-ColorOutput Red "[ERROR] $message"
}

function Write-Success($message) {
    Write-ColorOutput Green "[SUCCESS] $message"
}

# Help function
function Show-Help {
    Write-Host "OBS Docker Management Script" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\start-obs-docker.ps1 [OPTIONS]" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -Build      Build the Docker image before starting" -ForegroundColor White
    Write-Host "  -NoBuild    Start without building (use existing image)" -ForegroundColor White
    Write-Host "  -Logs       Show container logs" -ForegroundColor White
    Write-Host "  -Stop       Stop the OBS Docker containers" -ForegroundColor White
    Write-Host "  -Status     Show status of containers" -ForegroundColor White
    Write-Host "  -Help       Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\start-obs-docker.ps1 -Build    # Build and start" -ForegroundColor Gray
    Write-Host "  .\start-obs-docker.ps1 -NoBuild  # Start existing" -ForegroundColor Gray
    Write-Host "  .\start-obs-docker.ps1 -Status   # Check status" -ForegroundColor Gray
    Write-Host "  .\start-obs-docker.ps1 -Stop     # Stop containers" -ForegroundColor Gray
}

# Check if Docker is installed and running
function Test-Docker {
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Write-Info "Docker is installed: $dockerVersion"
        } else {
            throw "Docker not found"
        }
        
        # Test if Docker daemon is running
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker daemon is running"
            return $true
        } else {
            Write-Error "Docker daemon is not running. Please start Docker Desktop."
            return $false
        }
    } catch {
        Write-Error "Docker is not installed or not in PATH. Please install Docker Desktop."
        return $false
    }
}

# Check if docker-compose is available
function Test-DockerCompose {
    try {
        $composeVersion = docker-compose --version 2>$null
        if ($composeVersion) {
            Write-Info "Docker Compose is available: $composeVersion"
            return $true
        } else {
            # Try docker compose (newer syntax)
            docker compose version 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Info "Docker Compose (v2) is available"
                return $true
            } else {
                Write-Error "Docker Compose is not available"
                return $false
            }
        }
    } catch {
        Write-Error "Docker Compose is not available"
        return $false
    }
}

# Main execution
if ($Help) {
    Show-Help
    exit 0
}

Write-Host "OBS Docker Management" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
if (-not (Test-Docker)) {
    exit 1
}

if (-not (Test-DockerCompose)) {
    exit 1
}

# Handle different operations
if ($Status) {
    Write-Info "Checking container status..."
    docker-compose ps
    exit 0
}

if ($Stop) {
    Write-Info "Stopping OBS Docker containers..."
    docker-compose down
    Write-Success "Containers stopped"
    exit 0
}

if ($Logs) {
    Write-Info "Showing container logs..."
    docker-compose logs -f
    exit 0
}

if ($Build) {
    Write-Info "Building OBS Docker image..."
    docker-compose build
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Build failed"
        exit 1
    }
    Write-Success "Build completed"
}

if ($NoBuild -or $Build) {
    Write-Info "Starting OBS Docker containers..."
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Containers started successfully"
        Write-Host ""
        Write-Info "Access points:"
        Write-Host "  Web Interface: http://localhost:8080" -ForegroundColor Cyan
        Write-Host "  HTTPS Interface: https://localhost:8443" -ForegroundColor Cyan
        Write-Host "  RDP Connection: localhost:3389" -ForegroundColor Cyan
        Write-Host ""
        Write-Info "Use 'docker-compose logs -f' to view logs"
        Write-Info "Use '.\start-obs-docker.ps1 -Stop' to stop containers"
    } else {
        Write-Error "Failed to start containers"
        exit 1
    }
} else {
    Write-Warning "No action specified. Use -Help for usage information."
    Show-Help
}