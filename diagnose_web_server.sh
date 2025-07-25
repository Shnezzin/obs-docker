#!/bin/bash
# Diagnostic script for web server issues

echo "🔍 OBS Docker Web Server Diagnostics"
echo "====================================="

echo ""
echo "1. Checking if web manager is running..."
cd web/
./start-web-manager.sh status

echo ""
echo "2. Checking Docker containers..."
docker ps | grep -E "(web-manager|obs-docker)"

echo ""
echo "3. Checking port 8080..."
netstat -an | grep :8080 || ss -tuln | grep :8080

echo ""
echo "4. Checking if Flask app is running locally..."
ps aux | grep -E "(python.*app\.py|flask)" | grep -v grep

echo ""
echo "5. Testing local connection..."
curl -I http://localhost:8080/ 2>/dev/null || echo "❌ Cannot connect to localhost:8080"

echo ""
echo "6. Testing IP connection..."
curl -I http://192.168.84.12:8080/ 2>/dev/null || echo "❌ Cannot connect to 192.168.84.12:8080"

echo ""
echo "7. Checking web manager logs..."
./start-web-manager.sh logs | tail -20

echo ""
echo "8. Checking if static files exist..."
ls -la static/js/

echo ""
echo "9. Checking Flask static route..."
python3 -c "
import sys
sys.path.append('.')
try:
    from app import app
    print('✅ Flask app imports successfully')
    with app.test_client() as client:
        response = client.get('/static/js/api.js')
        print(f'Static file test: {response.status_code}')
except Exception as e:
    print(f'❌ Flask app error: {e}')
"

echo ""
echo "🔧 Suggested fixes:"
echo "1. Start web manager: ./start-web-manager.sh start"
echo "2. If that fails, try local mode: ./start-web-manager.sh local"
echo "3. Check logs: ./start-web-manager.sh logs"
echo "4. Restart: ./start-web-manager.sh restart"