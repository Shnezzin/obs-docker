#!/bin/bash
# Fix static files in Docker container

echo "🔧 Fixing Static Files in Docker Container"
echo "=========================================="

cd web/

echo ""
echo "1. Stopping current web manager..."
./start-web-manager.sh stop

echo ""
echo "2. Backing up current Dockerfile..."
cp Dockerfile.web Dockerfile.web.backup

echo ""
echo "3. Adding static files to Dockerfile..."
# Add the static files copy line after templates
sed -i '/COPY templates\/ templates\//a COPY static/ static/' Dockerfile.web

echo ""
echo "4. Verifying Dockerfile changes..."
echo "Lines around templates copy:"
grep -n -A 3 -B 1 "COPY templates" Dockerfile.web

echo ""
echo "5. Rebuilding web manager image..."
docker-compose -f docker-compose.web.yml build --no-cache

echo ""
echo "6. Starting web manager..."
./start-web-manager.sh start

echo ""
echo "7. Waiting for startup..."
sleep 10

echo ""
echo "8. Testing static files..."
echo "Testing HTTPS (with self-signed cert):"
curl -k -I https://localhost:8080/static/js/api.js
echo ""
curl -k -I https://localhost:8080/static/js/csrf.js

echo ""
echo "9. Testing main page:"
curl -k -I https://localhost:8080/

echo ""
echo "🎉 Fix complete!"
echo ""
echo "📝 Important Notes:"
echo "   - The web interface is running on HTTPS (SSL enabled)"
echo "   - Access it at: https://localhost:8080"
echo "   - You'll need to accept the self-signed certificate warning"
echo "   - If you prefer HTTP, we can disable SSL"

echo ""
echo "🌐 To access the web interface:"
echo "   1. Open your browser"
echo "   2. Go to: https://localhost:8080"
echo "   3. Accept the certificate warning"
echo "   4. The interface should now work properly"