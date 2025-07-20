#!/usr/bin/env python3
"""
Alternative Docker Client Implementation
Uses direct socket communication to bypass Python Docker library issues
"""

import os
import json
import socket
import requests
import urllib3
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool
import docker

class UnixSocketHTTPConnection(HTTPConnection):
    """HTTP connection over Unix socket"""
    def __init__(self, socket_path):
        super().__init__('localhost')
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)

class UnixSocketHTTPConnectionPool(HTTPConnectionPool):
    """HTTP connection pool for Unix socket"""
    def __init__(self, socket_path):
        super().__init__('localhost')
        self.socket_path = socket_path

    def _new_conn(self):
        return UnixSocketHTTPConnection(self.socket_path)

def create_docker_client_alternative():
    """Create Docker client using alternative methods"""
    print("🔧 Trying alternative Docker client methods...")
    
    # Method 1: Force specific Docker client version and configuration
    try:
        print("🔄 Method 1: Docker client with explicit configuration...")
        
        # Clear all Docker-related environment variables
        docker_env_vars = ['DOCKER_HOST', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH', 'DOCKER_API_VERSION']
        old_env = {}
        for var in docker_env_vars:
            if var in os.environ:
                old_env[var] = os.environ[var]
                del os.environ[var]
        
        # Create client with minimal configuration
        client = docker.DockerClient(
            base_url='unix:///var/run/docker.sock',
            version='auto',
            timeout=60
        )
        
        # Test the connection
        client.ping()
        print("✅ Alternative Docker client method 1 successful!")
        
        # Restore environment
        for var, value in old_env.items():
            os.environ[var] = value
            
        return client
        
    except Exception as e1:
        print(f"❌ Method 1 failed: {e1}")
        
        # Restore environment
        for var, value in old_env.items():
            os.environ[var] = value
    
    # Method 2: Use requests with Unix socket adapter
    try:
        print("🔄 Method 2: Direct HTTP over Unix socket...")
        
        import requests_unixsocket
        session = requests_unixsocket.Session()
        
        # Test Docker API directly
        response = session.get('http+unix://%2Fvar%2Frun%2Fdocker.sock/version')
        if response.status_code == 200:
            print("✅ Direct Unix socket HTTP works!")
            version_info = response.json()
            print(f"Docker version: {version_info.get('Version', 'Unknown')}")
            
            # Now try to create Docker client with this knowledge
            client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            return client
        else:
            print(f"❌ HTTP response error: {response.status_code}")
            
    except ImportError:
        print("❌ requests-unixsocket not available")
    except Exception as e2:
        print(f"❌ Method 2 failed: {e2}")
    
    # Method 3: Use low-level socket communication
    try:
        print("🔄 Method 3: Low-level socket test...")
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect('/var/run/docker.sock')
        
        # Send HTTP request manually
        request = b"GET /version HTTP/1.1\r\nHost: localhost\r\n\r\n"
        sock.send(request)
        
        response = sock.recv(4096).decode('utf-8')
        sock.close()
        
        if "HTTP/1.1 200 OK" in response:
            print("✅ Low-level socket communication works!")
            
            # Try Docker client one more time
            client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            return client
        else:
            print(f"❌ Unexpected response: {response[:200]}")
            
    except Exception as e3:
        print(f"❌ Method 3 failed: {e3}")
    
    print("❌ All alternative methods failed")
    return None

def test_docker_operations(client):
    """Test basic Docker operations"""
    if not client:
        return False
    
    try:
        # Test ping
        client.ping()
        print("✅ Docker ping successful")
        
        # Test version
        version = client.version()
        print(f"✅ Docker version: {version.get('Version', 'Unknown')}")
        
        # Test container listing
        containers = client.containers.list(all=True, limit=1)
        print(f"✅ Container listing successful - found {len(containers)} containers")
        
        return True
        
    except Exception as e:
        print(f"❌ Docker operations failed: {e}")
        return False

if __name__ == "__main__":
    print("🐳 Alternative Docker Client Test")
    print("=" * 40)
    
    client = create_docker_client_alternative()
    success = test_docker_operations(client)
    
    if success:
        print("\n🎉 Docker client is working with alternative method!")
    else:
        print("\n💥 All Docker client methods failed")
        print("\n🔧 Possible solutions:")
        print("1. Run container with privileged: true")
        print("2. Run container as root user: '0:0'")
        print("3. Install requests-unixsocket: pip install requests-unixsocket")
        print("4. Check Docker daemon is running on host")
