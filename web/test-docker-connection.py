#!/usr/bin/env python3
"""
Docker Connection Test Script
Tests Docker client connectivity for OBS Web Manager
"""

import docker
import sys
import os

def test_docker_connection():
    """Test Docker daemon connection"""
    print("🔍 Docker Connection Test")
    print("=" * 40)
    
    # Check environment
    print(f"🐍 Python version: {sys.version}")
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"🔧 Docker socket path: /var/run/docker.sock")
    print(f"📊 Socket exists: {os.path.exists('/var/run/docker.sock')}")
    
    if os.path.exists('/var/run/docker.sock'):
        import stat
        socket_stat = os.stat('/var/run/docker.sock')
        print(f"🔐 Socket permissions: {oct(socket_stat.st_mode)[-3:]}")
    
    print("\n🔄 Testing Docker client connection...")
    
    try:
        # Try to connect to Docker daemon
        client = docker.from_env()
        print("✅ Docker client created successfully")
        
        # Test ping
        client.ping()
        print("✅ Docker daemon ping successful")
        
        # Get version info
        version_info = client.version()
        print(f"📊 Docker version: {version_info['Version']}")
        print(f"🏗️ API version: {version_info['ApiVersion']}")
        print(f"🖥️ OS/Arch: {version_info['Os']}/{version_info['Arch']}")
        
        # List containers
        containers = client.containers.list(all=True)
        print(f"📦 Total containers: {len(containers)}")
        
        obs_containers = [c for c in containers if 'obs' in c.name.lower()]
        print(f"🎥 OBS containers: {len(obs_containers)}")
        
        if obs_containers:
            print("📋 OBS containers found:")
            for container in obs_containers:
                print(f"  - {container.name} ({container.status})")
        
        print("\n✅ Docker connection test PASSED!")
        return True
        
    except docker.errors.DockerException as e:
        print(f"❌ Docker connection failed: {e}")
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Ensure Docker daemon is running")
        print("2. Check Docker socket permissions")
        print("3. Verify Docker socket mount in docker-compose.yml")
        print("4. Try running with --privileged flag")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function"""
    success = test_docker_connection()
    
    if success:
        print("\n🚀 Ready to start OBS Web Manager!")
        print("Run: python app.py")
    else:
        print("\n⚠️ Docker connection issues detected")
        print("Web manager will run in standalone mode (system monitoring only)")
        print("Run: python app.py (will work but without container management)")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
