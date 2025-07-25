#!/bin/bash
# Cleanup script for OBS Docker environment
# Removes unused containers, images, volumes, and networks

set -euo pipefail

# Configuration
DRY_RUN=${1:-false}
FORCE=${FORCE:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

log_info() {
    log "${BLUE}INFO:${NC} $*"
}

log_warn() {
    log "${YELLOW}WARN:${NC} $*"
}

log_error() {
    log "${RED}ERROR:${NC} $*"
}

log_success() {
    log "${GREEN}SUCCESS:${NC} $*"
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! docker info &> /dev/null; then
    log_error "Cannot connect to Docker daemon"
    exit 1
fi

log_info "Starting OBS Docker cleanup..."

if [ "$DRY_RUN" = "true" ]; then
    log_warn "DRY RUN MODE - No changes will be made"
    DOCKER_CMD="echo docker"
else
    DOCKER_CMD="docker"
fi

# Function to get user confirmation
confirm() {
    if [ "$FORCE" = "true" ]; then
        return 0
    fi
    
    read -p "$1 (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Clean up stopped containers
log_info "Checking for stopped containers..."
STOPPED_CONTAINERS=$(docker ps -a -q -f status=exited -f status=created)

if [ -n "$STOPPED_CONTAINERS" ]; then
    log_info "Found $(echo "$STOPPED_CONTAINERS" | wc -l) stopped containers"
    if confirm "Remove stopped containers?"; then
        $DOCKER_CMD container prune -f
        log_success "Removed stopped containers"
    fi
else
    log_info "No stopped containers found"
fi

# Clean up dangling images
log_info "Checking for dangling images..."
DANGLING_IMAGES=$(docker images -q -f dangling=true)

if [ -n "$DANGLING_IMAGES" ]; then
    log_info "Found $(echo "$DANGLING_IMAGES" | wc -l) dangling images"
    if confirm "Remove dangling images?"; then
        $DOCKER_CMD image prune -f
        log_success "Removed dangling images"
    fi
else
    log_info "No dangling images found"
fi

# Clean up unused images (not referenced by any container)
log_info "Checking for unused images..."
if confirm "Remove unused images? (This may remove images you want to keep)"; then
    $DOCKER_CMD image prune -a -f
    log_success "Removed unused images"
fi

# Clean up unused volumes
log_info "Checking for unused volumes..."
UNUSED_VOLUMES=$(docker volume ls -q -f dangling=true)

if [ -n "$UNUSED_VOLUMES" ]; then
    log_info "Found $(echo "$UNUSED_VOLUMES" | wc -l) unused volumes"
    if confirm "Remove unused volumes? (This will permanently delete data)"; then
        $DOCKER_CMD volume prune -f
        log_success "Removed unused volumes"
    fi
else
    log_info "No unused volumes found"
fi

# Clean up unused networks
log_info "Checking for unused networks..."
if confirm "Remove unused networks?"; then
    $DOCKER_CMD network prune -f
    log_success "Removed unused networks"
fi

# Clean up build cache
log_info "Checking build cache..."
if confirm "Remove build cache?"; then
    $DOCKER_CMD builder prune -f
    log_success "Removed build cache"
fi

# Clean up system (comprehensive cleanup)
log_info "System cleanup..."
if confirm "Perform comprehensive system cleanup?"; then
    $DOCKER_CMD system prune -a -f --volumes
    log_success "Performed system cleanup"
fi

# Show disk space saved
log_info "Cleanup completed!"

# Display current Docker disk usage
log_info "Current Docker disk usage:"
docker system df

# Clean up log files if they exist
LOG_DIRS=(
    "/var/log/obs-docker"
    "/opt/obs-config/logs"
    "/tmp/obs-*"
)

for log_dir in "${LOG_DIRS[@]}"; do
    if [ -d "$log_dir" ] || ls $log_dir 1> /dev/null 2>&1; then
        log_info "Cleaning up logs in $log_dir"
        if confirm "Remove old log files in $log_dir?"; then
            if [ "$DRY_RUN" = "true" ]; then
                echo "Would remove: $log_dir"
            else
                find $log_dir -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
                find $log_dir -name "*.log.*" -type f -mtime +7 -delete 2>/dev/null || true
                log_success "Cleaned up old log files in $log_dir"
            fi
        fi
    fi
done

# Clean up temporary files
TEMP_DIRS=(
    "/tmp/obs-*"
    "/tmp/docker-*"
    "/var/tmp/obs-*"
)

for temp_dir in "${TEMP_DIRS[@]}"; do
    if ls $temp_dir 1> /dev/null 2>&1; then
        log_info "Cleaning up temporary files: $temp_dir"
        if confirm "Remove temporary files matching $temp_dir?"; then
            if [ "$DRY_RUN" = "true" ]; then
                echo "Would remove: $temp_dir"
            else
                rm -rf $temp_dir 2>/dev/null || true
                log_success "Cleaned up temporary files: $temp_dir"
            fi
        fi
    fi
done

log_success "Cleanup process completed!"

# Show final statistics
log_info "Final Docker system information:"
docker system df
docker system info | grep -E "(Containers|Images|Local Volumes)"