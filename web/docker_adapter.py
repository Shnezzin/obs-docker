#!/usr/bin/env python3
"""
Docker Client Adapter
Provides unified interface for both Python Docker library and subprocess client
"""

import subprocess
import docker
from docker_subprocess_client import DockerSubprocessClient
import json
import time

class DockerAdapter:
    """Unified Docker client adapter"""
    
    def __init__(self):
        self.client = None
        self.client_type = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the best available Docker client"""
        # Try Python Docker library first
        try:
            client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            client.ping()
            self.client = client
            self.client_type = 'python'
            print("✅ Using Python Docker client")
            return
        except Exception as e:
            print(f"❌ Python Docker client failed: {e}")
        
        # Fallback to subprocess client
        try:
            client = DockerSubprocessClient()
            if client.available:
                client.ping()
                self.client = client
                self.client_type = 'subprocess'
                print("✅ Using subprocess Docker client")
                return
        except Exception as e:
            print(f"❌ Subprocess Docker client failed: {e}")
        
        print("❌ No Docker client available")
        self.client = None
        self.client_type = None
    
    def is_available(self):
        """Check if Docker client is available"""
        return self.client is not None
    
    def ping(self):
        """Test Docker daemon connectivity"""
        if not self.client:
            raise Exception("No Docker client available")
        return self.client.ping()
    
    def version(self):
        """Get Docker version"""
        if not self.client:
            return {"Version": "Unknown"}
        return self.client.version()
    
    def create_container(self, image, name, ports=None, environment=None, volumes=None, network=None, labels=None):
        """Create a container with unified interface"""
        if not self.client:
            raise Exception("No Docker client available")
        
        if self.client_type == 'python':
            # Use Python Docker library
            return self.client.containers.run(
                image=image,
                name=name,
                detach=True,
                ports=ports,
                environment=environment,
                volumes=volumes,
                network=network,
                restart_policy={'Name': 'unless-stopped'},
                labels=labels
            )
        elif self.client_type == 'subprocess':
            # Use subprocess client
            return self.client.create_container(
                image=image,
                name=name,
                ports=ports,
                environment=environment,
                volumes=volumes,
                network=network,
                labels=labels
            )
        else:
            raise Exception("Unknown client type")
    
    def get_container(self, name):
        """Get container by name"""
        if not self.client:
            raise Exception("No Docker client available")
        
        if self.client_type == 'python':
            return self.client.containers.get(name)
        else:
            wrapper = SubprocessContainerWrapper(self.client, name)
            if not wrapper.exists:
                return None
            return wrapper
    
    def list_containers(self, all=False):
        """List containers with unified interface"""
        if not self.client:
            raise Exception("No Docker client available")
        if self.client_type == 'python':
            return self.client.containers.list(all=all)
        else:
            # For subprocess client, return a list of container wrappers
            def _extract_name(names):
                if isinstance(names, list):
                    return names[0].lstrip('/')
                elif isinstance(names, str):
                    return names.lstrip('/')
                return ''
            container_data = self.client.list_containers(all=all)
            return [SubprocessContainerWrapper(self.client, _extract_name(c['Names'])) 
                    for c in container_data if c.get('Names')]
    
    # Add containers property for backward compatibility
    @property
    def containers(self):
        """Containers property for backward compatibility"""
        if not self.client:
            raise Exception("No Docker client available")
            
        class ContainersNamespace:
            def __init__(self, adapter):
                self.adapter = adapter
                
            def list(self, **kwargs):
                return self.adapter.list_containers(all=kwargs.get('all', False))
                
            def get(self, container_id):
                return self.adapter.get_container(container_id)
                
        return ContainersNamespace(self)
    
    @property
    def volumes(self):
        if not self.client:
            raise Exception("No Docker client available")
        if self.client_type == 'python':
            return self.client.volumes
        else:
            # Dummy-Objekt für Subprocess-Client
            class VolumesNamespace:
                def __init__(self, client):
                    self.client = client
                def get(self, name):
                    class Volume:
                        def remove(self_inner):
                            # Versuche das Volume zu entfernen
                            import subprocess
                            subprocess.run(['docker', 'volume', 'rm', name], capture_output=True)
                    return Volume()
            return VolumesNamespace(self.client)

class SubprocessContainerWrapper:
    """Wrapper to make subprocess container behave like Python Docker library container"""
    def __init__(self, client, name):
        self.client = client
        self._name = name
        self._info = None

    @property
    def id(self):
        """Get container ID"""
        info = self._get_info()
        return info.get('Id', self._name)[:12]
    
    @property
    def status(self):
        """Get container status"""
        info = self._get_info()
        state = info.get('State', {})
        if state.get('Running'):
            return 'running'
        elif state.get('Paused'):
            return 'paused'
        else:
            return 'exited'
    
    @property
    def attrs(self):
        """Get container attributes"""
        return self._get_info()
    
    @property
    def labels(self):
        """Get container labels"""
        info = self._get_info()
        return info.get('Config', {}).get('Labels', {})
    
    @property
    def name(self):
        info = self._get_info()
        n = info.get('Names', '')
        if isinstance(n, list):
            return n[0]
        elif isinstance(n, str) and n:
            return n
        elif 'Name' in info:
            return info['Name']
        return self._name
    
    @property
    def ports(self):
        info = self._get_info()
        # docker inspect liefert Ports unter NetworkSettings.Ports
        ports = info.get('NetworkSettings', {}).get('Ports', {})
        return ports
    
    @property
    def exists(self):
        info = self._get_info()
        return bool(info) and 'Id' in info
    
    def _get_info(self):
        """Get container info (cached)"""
        if not self._info:
            try:
                self._info = self.client.get_container_info(self._name)
            except Exception:
                self._info = {}
        return self._info
    
    def start(self):
        """Start container"""
        return self.client.start_container(self._name)
    
    def stop(self):
        """Stop container"""
        return self.client.stop_container(self._name)
    
    def restart(self):
        """Restart container"""
        return self.client.restart_container(self._name)
    
    def remove(self, v=False):
        """Remove container"""
        return self.client.remove_container(self._name, volumes=v)
    
    def reload(self):
        """Reload container info"""
        self._info = None
        return self._get_info()
    
    def logs(self, tail=None, since=None, timestamps=False, follow=False):
        """Get container logs"""
        cmd = ['docker', 'logs']
        if tail:
            cmd.extend(['--tail', str(tail)])
        if since:
            cmd.extend(['--since', since])
        if timestamps:
            cmd.append('--timestamps')
        if follow:
            cmd.append('--follow')
        cmd.append(self._name)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.encode('utf-8')
            else:
                return f"Error getting logs: {result.stderr}".encode('utf-8')
        except Exception as e:
            return f"Error getting logs: {str(e)}".encode('utf-8')
    
    def stats(self, stream=False):
        """Get container statistics"""
        cmd = ['docker', 'stats', '--no-stream', '--format', 'json', self._name]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                # Parse the JSON output from docker stats
                stats_data = json.loads(result.stdout.strip())
                
                # Convert to the format expected by the Python Docker SDK
                # docker stats returns: {"CPUPerc":"0.00%","MemUsage":"1.5MiB / 1.944GiB",...}
                # We need to convert this to the format that calculate_cpu_percent expects
                
                # Parse CPU percentage
                cpu_perc = stats_data.get('CPUPerc', '0%').replace('%', '')
                try:
                    cpu_percent = float(cpu_perc)
                except:
                    cpu_percent = 0.0
                
                # Parse memory usage
                mem_usage_str = stats_data.get('MemUsage', '0B / 0B')
                mem_parts = mem_usage_str.split(' / ')
                if len(mem_parts) == 2:
                    try:
                        # Convert memory strings to bytes
                        mem_usage = self._parse_memory_string(mem_parts[0])
                        mem_limit = self._parse_memory_string(mem_parts[1])
                    except:
                        mem_usage = 0
                        mem_limit = 0
                else:
                    mem_usage = 0
                    mem_limit = 0
                
                # Create a mock stats structure that matches Python Docker SDK format
                # This is a simplified version - for full CPU calculation we'd need more data
                mock_stats = {
                    'cpu_stats': {
                        'cpu_usage': {
                            'total_usage': int(cpu_percent * 1000000),  # Mock value
                            'percpu_usage': [int(cpu_percent * 1000000)]  # Mock value
                        },
                        'system_cpu_usage': int(time.time() * 1000000000)  # Mock value
                    },
                    'precpu_stats': {
                        'cpu_usage': {
                            'total_usage': 0,  # Mock value
                        },
                        'system_cpu_usage': 0  # Mock value
                    },
                    'memory_stats': {
                        'usage': mem_usage,
                        'limit': mem_limit
                    }
                }
                
                return mock_stats
            else:
                # Return empty stats if container not running or error
                return {
                    'cpu_stats': {'cpu_usage': {'total_usage': 0, 'percpu_usage': [0]}, 'system_cpu_usage': 0},
                    'precpu_stats': {'cpu_usage': {'total_usage': 0}, 'system_cpu_usage': 0},
                    'memory_stats': {'usage': 0, 'limit': 0}
                }
        except Exception as e:
            # Return empty stats on error
            return {
                'cpu_stats': {'cpu_usage': {'total_usage': 0, 'percpu_usage': [0]}, 'system_cpu_usage': 0},
                'precpu_stats': {'cpu_usage': {'total_usage': 0}, 'system_cpu_usage': 0},
                'memory_stats': {'usage': 0, 'limit': 0}
            }
    
    def _parse_memory_string(self, mem_str):
        """Parse memory string like '1.5MiB' to bytes"""
        import re
        mem_str = mem_str.strip()
        
        # Handle different units
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'KiB': 1024,
            'MiB': 1024**2,
            'GiB': 1024**3
        }
        
        # Extract number and unit
        match = re.match(r'([\d.]+)\s*([A-Za-z]+)', mem_str)
        if match:
            number = float(match.group(1))
            unit = match.group(2)
            if unit in units:
                return int(number * units[unit])
        
        return 0

# Global adapter instance
docker_adapter = DockerAdapter()

def get_docker_client():
    """Get the unified Docker client"""
    return docker_adapter if docker_adapter.is_available() else None
