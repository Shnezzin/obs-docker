#!/usr/bin/env python3
"""
Docker Subprocess Client
Provides a Docker client implementation using subprocess calls to the docker CLI
"""

import subprocess
import json

class DockerSubprocessClient:
    """A Docker client that uses the `docker` command-line tool"""
    
    def __init__(self):
        self.available = self._check_docker_cli()
    
    def _check_docker_cli(self):
        """Check if the `docker` CLI is available"""
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def ping(self):
        """Test Docker daemon connectivity"""
        try:
            subprocess.run(['docker', 'info'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def version(self):
        """Get Docker version"""
        try:
            result = subprocess.run(['docker', 'version', '--format', 'json'], capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return {"Version": "Unknown"}
    
    def create_container(self, image, name, ports=None, environment=None, volumes=None, network=None, labels=None):
        """Create a container"""
        cmd = ['docker', 'create', '--name', name]
        
        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(['-p', f'{host_port}:{container_port}'])
        
        if environment:
            for key, value in environment.items():
                cmd.extend(['-e', f'{key}={value}'])
        
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(['-v', f'{host_path}:{container_path}'])
        
        if network:
            cmd.extend(['--network', network])
        
        if labels:
            for key, value in labels.items():
                cmd.extend(['--label', f'{key}={value}'])
        
        cmd.append(image)
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return self.get_container_info(name)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create container: {e.stderr.decode()}")
    
    def get_container_info(self, name):
        """Get information about a container"""
        try:
            result = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, check=True)
            return json.loads(result.stdout)[0]
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return None
    
    def list_containers(self, all=False):
        """List containers"""
        cmd = ['docker', 'ps', '--format', 'json']
        if all:
            cmd.append('-a')
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # The output of docker ps --format json is a list of json objects, one per line
            return [json.loads(line) for line in result.stdout.strip().split('\n')]
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return []
    
    def start_container(self, name):
        """Start a container"""
        try:
            subprocess.run(['docker', 'start', name], capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to start container: {e.stderr.decode()}")
    
    def stop_container(self, name):
        """Stop a container"""
        try:
            subprocess.run(['docker', 'stop', name], capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to stop container: {e.stderr.decode()}")
    
    def restart_container(self, name):
        """Restart a container"""
        try:
            subprocess.run(['docker', 'restart', name], capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to restart container: {e.stderr.decode()}")
    
    def remove_container(self, name, volumes=False):
        """Remove a container"""
        cmd = ['docker', 'rm', name]
        if volumes:
            cmd.append('-v')
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to remove container: {e.stderr.decode()}")
