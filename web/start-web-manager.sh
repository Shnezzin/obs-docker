#!/bin/bash

# OBS Docker Web Manager Startup Script
# This script starts the web-based management interface

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$WEB_DIR")"
COMPOSE_FILE="$WEB_DIR/docker-compose.web.yml"
LOG_FILE="$WEB_DIR/web-manager.log"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Setup local Python environment
setup_local() {
    log "Setting up local Python environment..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        error "Python is not installed or not in PATH"
        exit 1
    fi
    
    # Run local setup script
    if [ -f "setup-local.py" ]; then
        python3 setup-local.py 2>/dev/null || python setup-local.py
    else
        error "setup-local.py not found"
        exit 1
    fi
    
    success "Local environment setup completed"
}

# Build the web manager image
build_image() {
    log "Building OBS Web Manager image..."
    
    cd "$WEB_DIR"
    
    if docker-compose -f "$COMPOSE_FILE" build; then
        success "Web manager image built successfully"
    else
        error "Failed to build web manager image"
        exit 1
    fi
}

# Start the web manager
start_manager() {
    log "Starting OBS Web Manager..."
    
    cd "$WEB_DIR"
    
    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/data/web-config"
    mkdir -p "$PROJECT_ROOT/data/web-instances"
    mkdir -p "$PROJECT_ROOT/data/web-backups"
    
    if docker-compose -f "$COMPOSE_FILE" up -d; then
        success "OBS Web Manager started successfully"
        log "Web interface available at: http://localhost:8080"
        log "Logs: docker-compose -f $COMPOSE_FILE logs -f"
    else
        error "Failed to start web manager"
        exit 1
    fi
}

# Stop the web manager
stop_manager() {
    log "Stopping OBS Web Manager..."
    
    cd "$WEB_DIR"
    
    if docker-compose -f "$COMPOSE_FILE" down; then
        success "OBS Web Manager stopped successfully"
    else
        error "Failed to stop web manager"
        exit 1
    fi
}

# Show status
show_status() {
    log "Checking OBS Web Manager status..."
    
    cd "$WEB_DIR"
    docker-compose -f "$COMPOSE_FILE" ps
    
    # Check if service is responding
    if curl -s -f http://localhost:8080/api/system/stats > /dev/null 2>&1; then
        success "Web manager is running and responding"
    else
        warning "Web manager may not be fully ready yet"
    fi
}

# Show logs
show_logs() {
    log "Showing OBS Web Manager logs..."
    
    cd "$WEB_DIR"
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Restart the web manager
restart_manager() {
    log "Restarting OBS Web Manager..."
    stop_manager
    sleep 2
    start_manager
}

# Update the web manager
update_manager() {
    log "Updating OBS Web Manager..."
    stop_manager
    build_image
    start_manager
}

# Show help
show_help() {
    echo "OBS Docker Web Manager Control Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start the web manager (Docker)"
    echo "  stop      Stop the web manager"
    echo "  restart   Restart the web manager"
    echo "  status    Show status"
    echo "  logs      Show logs (follow mode)"
    echo "  build     Build the web manager image"
    echo "  update    Update and restart the web manager"
    echo "  setup     Setup local Python environment"
    echo "  local     Run web manager locally (without Docker)"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start    # Start with Docker"
    echo "  $0 setup    # Setup local Python environment"
    echo "  $0 local    # Run locally without Docker"
    echo "  $0 logs     # Follow the logs"
    echo "  $0 status   # Check if running"
    echo ""
    echo "Troubleshooting:"
    echo "  If you get 'ModuleNotFoundError: No module named distutils':"
    echo "  1. Run: $0 setup"
    echo "  2. Then: $0 local"
    echo ""
}

# Run locally without Docker
run_local() {
    log "Starting OBS Web Manager locally..."
    
    # Check if dependencies are installed
    if ! python3 -c "import flask" 2>/dev/null && ! python -c "import flask" 2>/dev/null; then
        warning "Flask not found. Running setup first..."
        setup_local
    fi
    
    # Start the application
    log "Starting Flask application..."
    log "Web interface will be available at: http://localhost:8080"
    
    if command -v python3 &> /dev/null; then
        python3 app.py
    else
        python app.py
    fi
}

# Main script logic
main() {
    case "${1:-help}" in
        start)
            check_prerequisites
            build_image
            start_manager
            ;;
        stop)
            stop_manager
            ;;
        restart)
            restart_manager
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        build)
            check_prerequisites
            build_image
            ;;
        update)
            check_prerequisites
            update_manager
            ;;
        setup)
            setup_local
            ;;
        local)
            run_local
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
