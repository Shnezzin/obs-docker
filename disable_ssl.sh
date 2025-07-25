#!/bin/bash
# Disable SSL and use HTTP only

echo "🔧 Disabling SSL for HTTP Access"
echo "================================"

cd web/

echo ""
echo "1. Stopping web manager..."
./start-web-manager.sh stop

echo ""
echo "2. Checking current docker-compose configuration..."
if grep -q "8443" docker-compose.web.yml; then
    echo "SSL ports found in docker-compose.web.yml"
fi

echo ""
echo "3. Starting web manager with --no-ssl flag..."
# We need to modify the start script to pass --no-ssl to the Flask app

echo ""
echo "4. Creating HTTP-only configuration..."
# Create a temporary docker-compose file for HTTP only
cat > docker-compose.web.http.yml << 'EOF'
version: '3.8'

services:
  obs-web-manager:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: obs-web-manager
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ../scripts:/scripts:ro
      - obs-config:/opt/obs-config
      - obs-instances:/opt/obs-instances
      - obs-backups:/opt/obs-backups
    environment:
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
      - DOCKER_HOST=unix:///var/run/docker.sock
    networks:
      - obs-network
    restart: unless-stopped
    command: ["python", "app.py", "--no-ssl", "--host", "0.0.0.0", "--port", "8080"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/system/stats"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  obs-config:
  obs-instances:
  obs-backups:

networks:
  obs-network:
    driver: bridge
EOF

echo ""
echo "5. Starting with HTTP-only configuration..."
docker-compose -f docker-compose.web.http.yml up -d

echo ""
echo "6. Waiting for startup..."
sleep 10

echo ""
echo "7. Testing HTTP connection..."
curl -I http://localhost:8080/

echo ""
echo "8. Testing static files..."
curl -I http://localhost:8080/static/js/api.js
curl -I http://localhost:8080/static/js/csrf.js

echo ""
echo "🎉 HTTP-only setup complete!"
echo ""
echo "📝 Access Information:"
echo "   - Web interface: http://localhost:8080"
echo "   - No SSL certificate warnings"
echo "   - All static files should work"

echo ""
echo "🔄 To switch back to HTTPS:"
echo "   ./start-web-manager.sh restart"