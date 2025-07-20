#!/usr/bin/env python3
"""
Simple Docker Socket Test
Quick test to check if Docker socket is accessible
"""

import os
import docker

print("🔍 Simple Docker Socket Test")
print("=" * 30)

# Check socket exists
socket_path = "/var/run/docker.sock"
print(f"Socket exists: {os.path.exists(socket_path)}")

if os.path.exists(socket_path):
    stat = os.stat(socket_path)
    print(f"Socket permissions: {oct(stat.st_mode)}")
    print(f"Socket GID: {stat.st_gid}")
    print(f"Current UID: {os.getuid()}")
    print(f"Current GID: {os.getgid()}")
    print(f"User groups: {os.getgroups()}")

# Test Docker client with explicit socket path
try:
    # Method 1: Explicit socket (most reliable)
    client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
    client.ping()
    print("✅ Docker client works (explicit socket)!")
    version = client.version()
    print(f"Docker version: {version.get('Version', 'Unknown')}")
except Exception as e1:
    print(f"❌ Explicit socket failed: {e1}")
    try:
        # Method 2: from_env as fallback
        client = docker.from_env()
        client.ping()
        print("✅ Docker client works (from_env)!")
        version = client.version()
        print(f"Docker version: {version.get('Version', 'Unknown')}")
    except Exception as e2:
        print(f"❌ Docker client completely failed: {e2}")
