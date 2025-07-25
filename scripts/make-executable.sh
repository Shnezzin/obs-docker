#!/bin/bash
# Make all scripts executable

set -euo pipefail

echo "Making all scripts executable..."

# Find all shell scripts and make them executable
find /scripts -name "*.sh" -type f -exec chmod +x {} \;
find /app -name "*.sh" -type f -exec chmod +x {} \;

# Make Python scripts executable
find /app -name "*.py" -type f -exec chmod +x {} \;

# Make entrypoint scripts executable
chmod +x /app/docker-entrypoint.sh 2>/dev/null || true
chmod +x /app/docker-entrypoint-vnc.sh 2>/dev/null || true

echo "All scripts are now executable"