#!/usr/bin/env python3
"""
Docker Socket Debug Script
Diagnoses Docker socket access issues in the web manager container
"""

import os
import stat
import grp
import pwd
import docker
import subprocess

def check_docker_socket():
    """Check Docker socket permissions and accessibility"""
    print("🔍 Docker Socket Diagnostic Report")
    print("=" * 50)
    
    # Check if socket exists
    socket_path = "/var/run/docker.sock"
    print(f"📁 Socket path: {socket_path}")
    print(f"📋 Socket exists: {os.path.exists(socket_path)}")
    
    if os.path.exists(socket_path):
        # Get socket stats
        socket_stat = os.stat(socket_path)
        print(f"📊 Socket permissions: {oct(socket_stat.st_mode)}")
        print(f"👤 Socket owner UID: {socket_stat.st_uid}")
        print(f"👥 Socket group GID: {socket_stat.st_gid}")
        
        # Get socket owner/group names
        try:
            owner_name = pwd.getpwuid(socket_stat.st_uid).pw_name
            print(f"👤 Socket owner name: {owner_name}")
        except KeyError:
            print(f"👤 Socket owner name: Unknown (UID {socket_stat.st_uid})")
        
        try:
            group_name = grp.getgrgid(socket_stat.st_gid).gr_name
            print(f"👥 Socket group name: {group_name}")
        except KeyError:
            print(f"👥 Socket group name: Unknown (GID {socket_stat.st_gid})")
    
    print("\n🔍 Current User Information")
    print("-" * 30)
    current_uid = os.getuid()
    current_gid = os.getgid()
    current_user = pwd.getpwuid(current_uid).pw_name
    print(f"👤 Current user: {current_user} (UID: {current_uid})")
    print(f"👥 Current primary group: {current_gid}")
    
    # Get all groups for current user
    try:
        groups = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
        print(f"👥 User groups: {', '.join(groups)}")
    except Exception as e:
        print(f"👥 Error getting groups: {e}")
    
    print("\n🔍 Docker Group Information")
    print("-" * 30)
    try:
        docker_group = grp.getgrnam('docker')
        print(f"👥 Docker group GID: {docker_group.gr_gid}")
        print(f"👥 Docker group members: {', '.join(docker_group.gr_mem)}")
        
        # Check if current user is in docker group
        if current_user in docker_group.gr_mem or docker_group.gr_gid in os.getgroups():
            print("✅ Current user is in docker group")
        else:
            print("❌ Current user is NOT in docker group")
    except KeyError:
        print("❌ Docker group does not exist")
    
    print("\n🔍 Docker Client Test")
    print("-" * 30)
    try:
        client = docker.from_env()
        print("✅ Docker client created successfully")
        
        # Test ping
        client.ping()
        print("✅ Docker daemon ping successful")
        
        # Get version
        version = client.version()
        print(f"📊 Docker version: {version.get('Version', 'Unknown')}")
        
        # Test listing containers
        containers = client.containers.list(all=True)
        print(f"📦 Found {len(containers)} containers")
        
    except docker.errors.DockerException as e:
        print(f"❌ Docker client error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n🔍 System Commands Test")
    print("-" * 30)
    try:
        # Test docker command
        result = subprocess.run(['docker', 'version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Docker CLI command works")
        else:
            print(f"❌ Docker CLI error: {result.stderr}")
    except Exception as e:
        print(f"❌ Docker CLI test failed: {e}")
    
    print("\n🔧 Recommendations")
    print("-" * 30)
    if not os.path.exists(socket_path):
        print("❌ Docker socket not found - ensure Docker is running and socket is mounted")
    else:
        socket_stat = os.stat(socket_path)
        if current_user not in grp.getgrnam('docker').gr_mem:
            print("❌ Add user to docker group: usermod -aG docker webuser")
        if not (socket_stat.st_mode & stat.S_IRGRP):
            print("❌ Docker socket not readable by group - check permissions")
        if not (socket_stat.st_mode & stat.S_IWGRP):
            print("❌ Docker socket not writable by group - check permissions")

if __name__ == "__main__":
    check_docker_socket()
