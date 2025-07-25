#!/usr/bin/env python3
"""
Simple test script to check web server status and fix static file issues
"""

import requests
import os
import sys
import subprocess
import time

def test_connection(url):
    """Test if we can connect to the web server"""
    try:
        response = requests.get(url, timeout=5)
        return True, response.status_code, response.headers.get('content-type', '')
    except Exception as e:
        return False, 0, str(e)

def check_static_files():
    """Check if static files exist"""
    static_dir = os.path.join('web', 'static', 'js')
    files = ['api.js', 'csrf.js']
    
    print("📁 Checking static files...")
    for file in files:
        file_path = os.path.join(static_dir, file)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✅ {file} exists ({size} bytes)")
        else:
            print(f"  ❌ {file} missing")
            return False
    return True

def start_web_server():
    """Try to start the web server"""
    print("🚀 Attempting to start web server...")
    
    os.chdir('web')
    
    # Try Docker method first
    try:
        result = subprocess.run(['./start-web-manager.sh', 'start'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Web server started with Docker")
            return True
        else:
            print(f"❌ Docker start failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Docker start error: {e}")
    
    # Try local method
    try:
        result = subprocess.run(['./start-web-manager.sh', 'local'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Web server started locally")
            return True
        else:
            print(f"❌ Local start failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Local start error: {e}")
    
    return False

def main():
    print("🔍 OBS Docker Web Server Test")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('web'):
        print("❌ Please run this script from the obs-docker root directory")
        sys.exit(1)
    
    # Check static files
    if not check_static_files():
        print("❌ Static files missing")
        sys.exit(1)
    
    # Test connections
    urls = [
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        'http://192.168.84.12:8080'
    ]
    
    print("\n🌐 Testing connections...")
    working_url = None
    
    for url in urls:
        connected, status, content_type = test_connection(url)
        if connected:
            print(f"  ✅ {url} - Status: {status}, Type: {content_type}")
            working_url = url
            break
        else:
            print(f"  ❌ {url} - Error: {content_type}")
    
    if not working_url:
        print("\n🚀 No working connection found. Attempting to start web server...")
        if start_web_server():
            print("⏳ Waiting for server to start...")
            time.sleep(5)
            
            # Test again
            for url in urls:
                connected, status, content_type = test_connection(url)
                if connected:
                    print(f"  ✅ {url} - Status: {status}, Type: {content_type}")
                    working_url = url
                    break
    
    if working_url:
        print(f"\n✅ Web server is accessible at: {working_url}")
        
        # Test static files
        print("\n📄 Testing static files...")
        static_files = ['/static/js/api.js', '/static/js/csrf.js']
        
        for file_path in static_files:
            url = working_url + file_path
            connected, status, content_type = test_connection(url)
            if connected and status == 200:
                print(f"  ✅ {file_path} - Status: {status}, Type: {content_type}")
            else:
                print(f"  ❌ {file_path} - Status: {status}, Error: {content_type}")
        
        print(f"\n🎉 Success! Open your browser to: {working_url}")
        
    else:
        print("\n❌ Could not establish connection to web server")
        print("\n🔧 Manual troubleshooting steps:")
        print("1. cd web/")
        print("2. ./start-web-manager.sh status")
        print("3. ./start-web-manager.sh logs")
        print("4. ./start-web-manager.sh restart")
        print("5. If all fails: ./start-web-manager.sh local")

if __name__ == '__main__':
    main()