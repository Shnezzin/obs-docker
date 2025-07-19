#!/bin/bash
# Health check script for OBS Docker container
# This script verifies that all essential services are running properly

set -euo pipefail

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] HEALTH: $*" >&2
}

# Exit codes
EXIT_SUCCESS=0
EXIT_FAILURE=1

log "Starting health check..."

# Check if XRDP is running
if ! pgrep -f "xrdp" > /dev/null 2>&1; then
    log "ERROR: XRDP service is not running"
    exit $EXIT_FAILURE
fi
log "✓ XRDP service is running"

# Check if XRDP-SESMAN is running
if ! pgrep -f "xrdp-sesman" > /dev/null 2>&1; then
    log "ERROR: XRDP-SESMAN service is not running"
    exit $EXIT_FAILURE
fi
log "✓ XRDP-SESMAN service is running"

# Check if D-Bus is running
if ! pgrep -f "dbus" > /dev/null 2>&1; then
    log "ERROR: D-Bus service is not running"
    exit $EXIT_FAILURE
fi
log "✓ D-Bus service is running"

# Check if Supervisor is running
if ! pgrep -f "supervisord" > /dev/null 2>&1; then
    log "ERROR: Supervisor service is not running"
    exit $EXIT_FAILURE
fi
log "✓ Supervisor service is running"

# Check if RDP port is listening
if ! netstat -ln | grep -q ":3389.*LISTEN" 2>/dev/null; then
    log "ERROR: RDP port 3389 is not listening"
    exit $EXIT_FAILURE
fi
log "✓ RDP port 3389 is listening"

# Check if OBS Studio is available
if command -v obs > /dev/null 2>&1; then
    log "✓ OBS Studio binary is available"
elif flatpak list | grep -q "com.obsproject.Studio" 2>/dev/null; then
    log "✓ OBS Studio Flatpak is available"
else
    log "WARNING: OBS Studio not found via binary or Flatpak"
fi

# Check system resources
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
log "Memory usage: ${MEMORY_USAGE}%"

if (( $(echo "$MEMORY_USAGE > 90.0" | bc -l) )); then
    log "WARNING: High memory usage (${MEMORY_USAGE}%)"
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
log "Disk usage: ${DISK_USAGE}%"

if (( DISK_USAGE > 90 )); then
    log "WARNING: High disk usage (${DISK_USAGE}%)"
fi

log "Health check completed successfully"
exit $EXIT_SUCCESS
