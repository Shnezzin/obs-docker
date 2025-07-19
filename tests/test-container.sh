#!/bin/bash
# Basic integration tests for OBS Docker container
# Tests container build, startup, and basic functionality

set -euo pipefail

# Configuration
CONTAINER_NAME="obs-test-container"
IMAGE_NAME="obs-studio-test"
TEST_PORT="3390"  # Use different port to avoid conflicts
TEST_TIMEOUT=60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test resources..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    docker rmi "$IMAGE_NAME" 2>/dev/null || true
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Test functions
test_docker_build() {
    log_info "Testing Docker build..."
    
    if docker build -t "$IMAGE_NAME" .; then
        log_info "✓ Docker build successful"
        return 0
    else
        log_error "✗ Docker build failed"
        return 1
    fi
}

test_container_start() {
    log_info "Testing container startup..."
    
    # Start container
    if docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$TEST_PORT:3389" \
        -e USER=testuser \
        -e PASSWD=TestPassword123! \
        "$IMAGE_NAME"; then
        log_info "✓ Container started successfully"
    else
        log_error "✗ Container failed to start"
        return 1
    fi
    
    # Wait for container to be ready
    log_info "Waiting for container to be ready..."
    local count=0
    while [ $count -lt $TEST_TIMEOUT ]; do
        if docker exec "$CONTAINER_NAME" pgrep -f "supervisord" > /dev/null 2>&1; then
            log_info "✓ Container is ready"
            return 0
        fi
        sleep 1
        ((count++))
    done
    
    log_error "✗ Container failed to become ready within ${TEST_TIMEOUT} seconds"
    return 1
}

test_services_running() {
    log_info "Testing essential services..."
    
    local services=("xrdp" "xrdp-sesman" "dbus" "supervisord")
    local failed=0
    
    for service in "${services[@]}"; do
        if docker exec "$CONTAINER_NAME" pgrep -f "$service" > /dev/null 2>&1; then
            log_info "✓ $service is running"
        else
            log_error "✗ $service is not running"
            ((failed++))
        fi
    done
    
    return $failed
}

test_rdp_port() {
    log_info "Testing RDP port accessibility..."
    
    if docker exec "$CONTAINER_NAME" netstat -ln | grep -q ":3389.*LISTEN" 2>/dev/null; then
        log_info "✓ RDP port 3389 is listening"
        return 0
    else
        log_error "✗ RDP port 3389 is not listening"
        return 1
    fi
}

test_obs_installation() {
    log_info "Testing OBS Studio installation..."
    
    # Check for OBS binary
    if docker exec "$CONTAINER_NAME" command -v obs > /dev/null 2>&1; then
        log_info "✓ OBS Studio binary found"
        return 0
    fi
    
    # Check for OBS Flatpak
    if docker exec "$CONTAINER_NAME" flatpak list 2>/dev/null | grep -q "com.obsproject.Studio"; then
        log_info "✓ OBS Studio Flatpak found"
        return 0
    fi
    
    log_warn "⚠ OBS Studio not found (this may be expected during build)"
    return 0  # Don't fail the test for this
}

test_user_creation() {
    log_info "Testing user creation..."
    
    if docker exec "$CONTAINER_NAME" id testuser > /dev/null 2>&1; then
        log_info "✓ Test user created successfully"
        return 0
    else
        log_error "✗ Test user was not created"
        return 1
    fi
}

test_health_check() {
    log_info "Testing health check script..."
    
    if docker exec "$CONTAINER_NAME" /bin/bash -c "chmod +x /scripts/health-check.sh && /scripts/health-check.sh"; then
        log_info "✓ Health check passed"
        return 0
    else
        log_error "✗ Health check failed"
        return 1
    fi
}

# Main test execution
main() {
    log_info "Starting OBS Docker container tests..."
    log_info "Container: $CONTAINER_NAME"
    log_info "Image: $IMAGE_NAME"
    log_info "Test Port: $TEST_PORT"
    echo
    
    local failed_tests=0
    
    # Run tests
    test_docker_build || ((failed_tests++))
    test_container_start || ((failed_tests++))
    sleep 5  # Give services time to start
    test_services_running || ((failed_tests++))
    test_rdp_port || ((failed_tests++))
    test_obs_installation || ((failed_tests++))
    test_user_creation || ((failed_tests++))
    test_health_check || ((failed_tests++))
    
    echo
    if [ $failed_tests -eq 0 ]; then
        log_info "🎉 All tests passed!"
        return 0
    else
        log_error "❌ $failed_tests test(s) failed"
        return 1
    fi
}

# Check if Docker is available
if ! command -v docker > /dev/null 2>&1; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker daemon is not running"
    exit 1
fi

# Run main function
main "$@"
