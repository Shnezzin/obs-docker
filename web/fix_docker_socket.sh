#!/bin/bash
# Docker Socket Permission Fix Script
# This script helps diagnose and fix Docker socket access issues

echo "🔧 Docker Socket Permission Fix Script"
echo "======================================"

# Get host Docker group GID
echo "🔍 Detecting host Docker group GID..."
if [ -S /var/run/docker.sock ]; then
    DOCKER_SOCKET_GID=$(stat -c %g /var/run/docker.sock)
    echo "✅ Docker socket found with GID: $DOCKER_SOCKET_GID"
else
    echo "❌ Docker socket not found at /var/run/docker.sock"
    exit 1
fi

# Export for docker-compose
export DOCKER_GID=$DOCKER_SOCKET_GID
echo "📝 Setting DOCKER_GID=$DOCKER_GID for docker-compose"

# Create .env file for docker-compose
echo "📝 Creating .env file..."
cat > .env << EOF
# Docker socket group ID (auto-detected)
DOCKER_GID=$DOCKER_GID

# Web manager configuration
FLASK_ENV=production
FLASK_DEBUG=false
EOF

echo "✅ Created .env file with DOCKER_GID=$DOCKER_GID"

# Rebuild and restart the web manager
echo "🔄 Rebuilding web manager with correct Docker group..."
docker-compose -f docker-compose.web.yml down
echo "📦 Building container with debug scripts..."
docker-compose -f docker-compose.web.yml build --no-cache --pull
echo "🚀 Starting web manager..."
docker-compose -f docker-compose.web.yml up -d

echo "⏳ Waiting for web manager to start..."
sleep 10

# Check if it's working
echo "🔍 Testing Docker socket access..."
docker exec obs-web-manager python3 debug_docker.py

echo "🌐 Web manager should now be accessible at http://localhost:8080"
echo "📋 Check the logs with: docker logs obs-web-manager"
