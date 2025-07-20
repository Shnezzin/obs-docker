#!/usr/bin/env python3
"""
Docker Client Adapter
Provides unified interface for both Python Docker library and subprocess client
"""

import docker
from docker_subprocess_client import DockerSubprocessClient

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
        elif self.client_type == 'subprocess':
            if self.client.container_exists(name):
                return SubprocessContainerWrapper(self.client, name)
            else:
                raise docker.errors.NotFound(f"Container {name} not found")
    
    def list_containers(self, all=False):
        """List containers"""
        if not self.client:
            return []
        
        if self.client_type == 'python':
            return self.client.containers.list(all=all)
        elif self.client_type == 'subprocess':
            containers = self.client.list_containers(all=all)
            return [SubprocessContainerWrapper(self.client, c.get('Names', '')) for c in containers]
        else:
            return []

class SubprocessContainerWrapper:
    """Wrapper to make subprocess container behave like Python Docker library container"""
    
    def __init__(self, client, name):
        self.client = client
        self.name = name
        self._info = None
    
    @property
    def id(self):
        """Get container ID"""
        info = self._get_info()
        return info.get('Id', self.name)[:12]
    
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
    
    def _get_info(self):
        """Get container info (cached)"""
        if not self._info:
            try:
                self._info = self.client.get_container_info(self.name)
            except Exception:
                self._info = {}
        return self._info
    
    def start(self):
        """Start container"""
        return self.client.start_container(self.name)
    
    def stop(self):
        """Stop container"""
        return self.client.stop_container(self.name)
    
    def restart(self):
        """Restart container"""
        return self.client.restart_container(self.name)
    
    def remove(self, v=False):
        """Remove container"""
        return self.client.remove_container(self.name, volumes=v)
    
    def reload(self):
        """Reload container info"""
        self._info = None
        return self._get_info()

# Global adapter instance
docker_adapter = DockerAdapter()

def get_docker_client():
    """Get the unified Docker client"""
    return docker_adapter if docker_adapter.is_available() else None
