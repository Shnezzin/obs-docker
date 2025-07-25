#!/bin/bash
# Quick fix script for web interface issues

echo "🔧 OBS Docker Web Interface Quick Fix"
echo "====================================="

# Make sure we're in the right directory
if [ ! -d "web" ]; then
    echo "❌ Please run this script from the obs-docker root directory"
    exit 1
fi

cd web/

echo ""
echo "1. Making scripts executable..."
chmod +x start-web-manager.sh
chmod +x ../scripts/*.sh 2>/dev/null || true

echo ""
echo "2. Checking static files..."
if [ ! -f "static/js/api.js" ]; then
    echo "❌ api.js missing - this should not happen"
    exit 1
else
    echo "✅ api.js exists ($(wc -c < static/js/api.js) bytes)"
fi

if [ ! -f "static/js/csrf.js" ]; then
    echo "❌ csrf.js missing - this should not happen"
    exit 1
else
    echo "✅ csrf.js exists ($(wc -c < static/js/csrf.js) bytes)"
fi

echo ""
echo "3. Stopping any existing web manager..."
./start-web-manager.sh stop 2>/dev/null || true

echo ""
echo "4. Cleaning up any stale processes..."
pkill -f "python.*app.py" 2>/dev/null || true
docker stop obs-web-manager 2>/dev/null || true
docker rm obs-web-manager 2>/dev/null || true

echo ""
echo "5. Starting web manager (Docker method)..."
if ./start-web-manager.sh start; then
    echo "✅ Web manager started with Docker"
    
    echo ""
    echo "6. Waiting for startup..."
    sleep 5
    
    echo ""
    echo "7. Testing connection..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ | grep -q "200"; then
        echo "✅ Web interface is accessible at http://localhost:8080"
        
        echo ""
        echo "8. Testing static files..."
        api_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/js/api.js)
        csrf_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/js/csrf.js)
        
        if [ "$api_status" = "200" ]; then
            echo "✅ api.js is accessible"
        else
            echo "❌ api.js returns status $api_status"
        fi
        
        if [ "$csrf_status" = "200" ]; then
            echo "✅ csrf.js is accessible"
        else
            echo "❌ csrf.js returns status $csrf_status"
        fi
        
        echo ""
        echo "🎉 Web interface should now work properly!"
        echo "   Open http://localhost:8080 in your browser"
        
    else
        echo "❌ Web interface not responding"
        echo ""
        echo "Trying local method..."
        ./start-web-manager.sh stop
        if ./start-web-manager.sh local; then
            echo "✅ Started in local mode"
            echo "   Open http://localhost:8080 in your browser"
        else
            echo "❌ Local method also failed"
            echo ""
            echo "Manual troubleshooting:"
            echo "1. Check logs: ./start-web-manager.sh logs"
            echo "2. Check status: ./start-web-manager.sh status"
            echo "3. Try setup: ./start-web-manager.sh setup"
        fi
    fi
else
    echo "❌ Docker method failed, trying local method..."
    
    echo ""
    echo "5b. Setting up local environment..."
    ./start-web-manager.sh setup
    
    echo ""
    echo "5c. Starting in local mode..."
    if ./start-web-manager.sh local; then
        echo "✅ Web manager started in local mode"
        echo "   Open http://localhost:8080 in your browser"
    else
        echo "❌ Both Docker and local methods failed"
        echo ""
        echo "Please check:"
        echo "1. Docker is running: docker info"
        echo "2. Python is available: python3 --version"
        echo "3. Port 8080 is free: netstat -an | grep :8080"
        echo "4. Check logs: ./start-web-manager.sh logs"
    fi
fi

echo ""
echo "🔍 Current status:"
./start-web-manager.sh status