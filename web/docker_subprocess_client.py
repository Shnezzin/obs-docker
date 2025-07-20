#!/usr/bin/env python3
"""
Subprocess-based Docker Client
Alternative implementation using Docker CLI instead of Python library
"""

import subprocess
import json
import time
from datetime import datetime

class DockerSubprocessClient:
    """Docker client using subprocess calls to docker CLI"""
    
    def __init__(self):
        self.available = self._check_docker_available()
    
    def _check_docker_available(self):
        """Check if Docker CLI is available"""
        try:
            result = subprocess.run(['docker', 'version', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def ping(self):
        """Test Docker daemon connectivity"""
        if not self.available:
            raise Exception("Docker CLI not available")
        
        result = subprocess.run(['docker', 'version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise Exception(f"Docker ping failed: {result.stderr}")
        return True
    
    def version(self):
        """Get Docker version information"""
        # Try JSON format first
        result = subprocess.run(['docker', 'version', '--format', 'json'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
        
        # Fallback to plain text parsing
        result = subprocess.run(['docker', 'version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Parse version from plain text output
            lines = result.stdout.split('\n')
            version_info = {"Client": {}, "Server": {}}
            current_section = None
            
            for line in lines:
                line = line.strip()
                if 'Client:' in line:
                    current_section = 'Client'
                elif 'Server:' in line:
                    current_section = 'Server'
                elif 'Version:' in line and current_section:
                    version = line.split('Version:')[1].strip()
                    version_info[current_section]['Version'] = version
            
            return version_info
        else:
            return {"Client": {"Version": "Unknown"}, "Server": {"Version": "Unknown"}}
    
    def list_containers(self, all=False):
        """List containers"""
        # Try JSON format first
        cmd = ['docker', 'ps', '--format', 'json']
        if all:
            cmd.append('-a')
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            if containers:  # If we got valid JSON, return it
                return containers
        
        # Fallback to table format parsing
        cmd = ['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.ID}}']
        if all:
            cmd.append('-a')
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []
        
        containers = []
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:  # Skip header line
            for line in lines[1:]:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        containers.append({
                            'Names': parts[0].strip(),
                            'Status': parts[1].strip(),
                            'Image': parts[2].strip(),
                            'ID': parts[3].strip()
                        })
        return containers
    
    def create_container(self, image, name, ports=None, environment=None, volumes=None, network=None, labels=None):
        """Create a new container"""
        cmd = ['docker', 'run', '-d', '--name', name]
        
        # Add ports
        if ports:
            for container_port, host_port in ports.items():
                if host_port:
                    cmd.extend(['-p', f'{host_port}:{container_port}'])
                else:
                    cmd.extend(['-p', container_port])
        
        # Add environment variables
        if environment:
            for key, value in environment.items():
                cmd.extend(['-e', f'{key}={value}'])
        
        # Add volumes
        if volumes:
            for volume_name, mount_info in volumes.items():
                if isinstance(mount_info, dict):
                    bind_path = mount_info.get('bind')
                    mode = mount_info.get('mode', 'rw')
                    cmd.extend(['-v', f'{volume_name}:{bind_path}:{mode}'])
                else:
                    cmd.extend(['-v', f'{volume_name}:{mount_info}'])
        
        # Add network
        if network:
            cmd.extend(['--network', network])
        
        # Add labels
        if labels:
            for key, value in labels.items():
                cmd.extend(['--label', f'{key}={value}'])
        
        # Add restart policy
        cmd.extend(['--restart', 'unless-stopped'])
        
        # Add image
        cmd.append(image)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            container_id = result.stdout.strip()
            return {
                'id': container_id,
                'name': name,
                'status': 'running',
                'created': datetime.now().isoformat()
            }
        else:
            raise Exception(f"Container creation failed: {result.stderr}")
    
    def start_container(self, name):
        """Start a container"""
        result = subprocess.run(['docker', 'start', name], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"Container start failed: {result.stderr}")
        return True
    
    def stop_container(self, name):
        """Stop a container"""
        result = subprocess.run(['docker', 'stop', name], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"Container stop failed: {result.stderr}")
        return True
    
    def restart_container(self, name):
        """Restart a container"""
        result = subprocess.run(['docker', 'restart', name], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"Container restart failed: {result.stderr}")
        return True
    
    def remove_container(self, name, force=False, volumes=False):
        """Remove a container"""
        cmd = ['docker', 'rm']
        if force:
            cmd.append('-f')
        if volumes:
            cmd.append('-v')
        cmd.append(name)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"Container removal failed: {result.stderr}")
        return True
    
    def get_container_info(self, name):
        """Get detailed container information"""
        result = subprocess.run(['docker', 'inspect', name], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)[0]
            except (json.JSONDecodeError, IndexError):
                return {}
        return {}
    
    def container_exists(self, name):
        """Check if container exists"""
        result = subprocess.run(['docker', 'inspect', name], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0

def test_subprocess_client():
    """Test the subprocess-based Docker client"""
    print("🐳 Testing Subprocess Docker Client")
    print("=" * 40)
    
    client = DockerSubprocessClient()
    
    if not client.available:
        print("❌ Docker CLI not available")
        return False
    
    try:
        # Test ping
        client.ping()
        print("✅ Docker ping successful")
        
        # Test version
        version = client.version()
        print(f"✅ Docker version: {version.get('Client', {}).get('Version', 'Unknown')}")
        
        # Test container listing
        containers = client.list_containers(all=True)
        print(f"✅ Container listing successful - found {len(containers)} containers")
        
        return True
        
    except Exception as e:
        print(f"❌ Subprocess client failed: {e}")
        return False

if __name__ == "__main__":
    success = test_subprocess_client()
    if success:
        print("\n🎉 Subprocess Docker client is working!")
    else:
        print("\n💥 Subprocess Docker client failed")
