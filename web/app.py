#!/usr/bin/env python3
"""
OBS Docker Container Web Management Interface
Provides a web-based dashboard for managing OBS containers
"""

import os
import json
import subprocess
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO, emit
import docker
import psutil

app = Flask(__name__)
app.secret_key = 'obs-docker-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
SCRIPTS_DIR = '/scripts'
CONFIG_DIR = '/opt/obs-config'
INSTANCES_DIR = '/opt/obs-instances'

# Docker client with error handling
try:
    # Try to connect to Docker daemon
    print("🔄 Attempting to connect to Docker daemon...")
    docker_client = docker.from_env()
    # Test the connection
    docker_client.ping()
    print("✅ Docker client connected successfully")
    print(f"📊 Docker version: {docker_client.version()['Version']}")
except Exception as e:
    print(f"⚠️ Docker client connection failed: {e}")
    print("📝 This is normal if running locally without Docker socket access")
    print("🔧 Running in standalone mode - system monitoring only")
    docker_client = None

class OBSManager:
    def __init__(self):
        self.containers = {}
        self.system_stats = {}
        self.update_stats()
    
    def update_stats(self):
        """Update system and container statistics"""
        try:
            # System stats
            self.system_stats = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory()._asdict(),
                'disk': psutil.disk_usage('/')._asdict(),
                'network': psutil.net_io_counters()._asdict(),
                'timestamp': datetime.now().isoformat()
            }
            
            # Container stats (only if Docker client is available)
            if docker_client:
                containers = docker_client.containers.list(all=True)
                self.containers = {}
                
                for container in containers:
                    if 'obs' in container.name.lower():
                        stats = {
                            'name': container.name,
                            'status': container.status,
                            'image': container.image.tags[0] if container.image.tags else 'unknown',
                            'created': container.attrs['Created'],
                            'ports': container.ports,
                            'labels': container.labels
                        }
                        
                        # Get container stats if running
                        if container.status == 'running':
                            try:
                                container_stats = container.stats(stream=False)
                                stats['cpu_percent'] = self.calculate_cpu_percent(container_stats)
                                stats['memory_usage'] = container_stats['memory_stats'].get('usage', 0)
                                stats['memory_limit'] = container_stats['memory_stats'].get('limit', 0)
                            except:
                                pass
                        
                        self.containers[container.name] = stats
            else:
                # Standalone mode - no container stats
                self.containers = {}
                    
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    def calculate_cpu_percent(self, stats):
        """Calculate CPU percentage from container stats"""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            if system_delta > 0:
                return (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
        except:
            pass
        return 0

obs_manager = OBSManager()

# Background task to update stats
def update_stats_background():
    while True:
        obs_manager.update_stats()
        socketio.emit('stats_update', {
            'system': obs_manager.system_stats,
            'containers': obs_manager.containers
        })
        time.sleep(5)

# Start background thread
stats_thread = threading.Thread(target=update_stats_background, daemon=True)
stats_thread.start()

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html', 
                         containers=obs_manager.containers,
                         system_stats=obs_manager.system_stats)

@app.route('/containers')
def containers():
    """Container management page"""
    return render_template('containers.html', containers=obs_manager.containers)

@app.route('/api/containers')
def api_containers():
    """API endpoint for container information"""
    return jsonify(obs_manager.containers)

@app.route('/api/container/<container_name>/start', methods=['POST'])
def start_container(container_name):
    """Start a container"""
    if not docker_client:
        return jsonify({'status': 'error', 'message': 'Docker client not available'}), 503
    try:
        container = docker_client.containers.get(container_name)
        container.start()
        return jsonify({'status': 'success', 'message': f'Container {container_name} started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/container/<container_name>/stop', methods=['POST'])
def stop_container(container_name):
    """Stop a container"""
    if not docker_client:
        return jsonify({'status': 'error', 'message': 'Docker client not available'}), 503
    try:
        container = docker_client.containers.get(container_name)
        container.stop()
        return jsonify({'status': 'success', 'message': f'Container {container_name} stopped'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/container/<container_name>/restart', methods=['POST'])
def restart_container(container_name):
    """Restart a container"""
    if not docker_client:
        return jsonify({'status': 'error', 'message': 'Docker client not available'}), 503
    try:
        container = docker_client.containers.get(container_name)
        container.restart()
        return jsonify({'status': 'success', 'message': f'Container {container_name} restarted'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/container/<container_name>/logs')
def container_logs(container_name):
    """Get container logs"""
    if not docker_client:
        return jsonify({'status': 'error', 'message': 'Docker client not available'}), 503
    try:
        container = docker_client.containers.get(container_name)
        logs = container.logs(tail=100).decode('utf-8')
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/instances')
def instances():
    """Instance management page"""
    return render_template('instances.html')

@app.route('/api/instances')
def api_instances():
    """API endpoint for instance information"""
    try:
        script_path = f'{SCRIPTS_DIR}/instance-manager.sh'
        if os.path.exists(script_path):
            result = subprocess.run([script_path, 'list'], 
                                  capture_output=True, text=True, timeout=10)
            # Parse the output to JSON format
            instances = {}
            return jsonify(instances)
        else:
            # Return demo data when script is not available
            demo_instances = {
                'obs-instance-1': {
                    'name': 'obs-instance-1',
                    'status': 'running',
                    'template': 'streaming',
                    'created': '2024-01-01T00:00:00Z',
                    'ports': {'3389': '3389', '4455': '4455'}
                },
                'obs-instance-2': {
                    'name': 'obs-instance-2', 
                    'status': 'stopped',
                    'template': 'recording',
                    'created': '2024-01-02T00:00:00Z',
                    'ports': {'3390': '3389', '4456': '4455'}
                }
            }
            return jsonify(demo_instances)
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Script timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/create', methods=['POST'])
def create_instance():
    """Create a new instance"""
    try:
        data = request.json
        name = data.get('name')
        template = data.get('template', 'streaming')
        user = data.get('user', 'developer')
        password = data.get('password', '')
        
        result = subprocess.run([
            f'{SCRIPTS_DIR}/instance-manager.sh', 'create', 
            name, template, user, password
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Instance {name} created'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/plugins')
def plugins():
    """Plugin management page"""
    return render_template('plugins.html')

@app.route('/api/plugins')
def api_plugins():
    """API endpoint for plugin information"""
    try:
        script_path = f'{SCRIPTS_DIR}/plugin-manager.sh'
        if os.path.exists(script_path):
            result = subprocess.run([script_path, 'list'], 
                                  capture_output=True, text=True, timeout=10)
            # Parse plugin list
            plugins = {}
            return jsonify(plugins)
        else:
            # Return demo plugin data when script is not available
            demo_plugins = {
                'obs-websocket': {
                    'name': 'obs-websocket',
                    'version': '5.4.2',
                    'status': 'installed',
                    'description': 'WebSocket API for OBS Studio',
                    'category': 'streaming'
                },
                'obs-browser': {
                    'name': 'obs-browser',
                    'version': '2.21.0',
                    'status': 'available',
                    'description': 'Browser source plugin for OBS',
                    'category': 'sources'
                },
                'obs-streamfx': {
                    'name': 'obs-streamfx',
                    'version': '0.12.0',
                    'status': 'available',
                    'description': 'Advanced effects and filters',
                    'category': 'effects'
                }
            }
            return jsonify(demo_plugins)
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Script timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/plugins/install', methods=['POST'])
def install_plugin():
    """Install a plugin"""
    try:
        data = request.json
        plugin_name = data.get('plugin_name')
        
        result = subprocess.run([f'{SCRIPTS_DIR}/plugin-manager.sh', 'install', plugin_name], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Plugin {plugin_name} installed'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/monitoring')
def monitoring():
    """Monitoring and analytics page"""
    return render_template('monitoring.html')

@app.route('/api/system/stats')
def system_stats():
    """Get system statistics"""
    return jsonify(obs_manager.system_stats)

@app.route('/backups')
def backups():
    """Backup management page"""
    return render_template('backups.html')

@app.route('/api/backups')
def api_backups():
    """API endpoint for backup information"""
    try:
        script_path = f'{SCRIPTS_DIR}/backup-recovery.sh'
        if os.path.exists(script_path):
            result = subprocess.run([script_path, 'list'], 
                                  capture_output=True, text=True, timeout=10)
            # Parse backup list
            backups = []
            return jsonify(backups)
        else:
            # Return demo backup data when script is not available
            demo_backups = [
                {
                    'id': 'backup-001',
                    'name': 'Full System Backup',
                    'type': 'full',
                    'size': '2.1 GB',
                    'created': '2024-01-15T10:30:00Z',
                    'status': 'completed',
                    'location': '/opt/obs-backups/backup-001.tar.gz'
                },
                {
                    'id': 'backup-002',
                    'name': 'Configuration Backup',
                    'type': 'config',
                    'size': '45 MB',
                    'created': '2024-01-14T08:15:00Z',
                    'status': 'completed',
                    'location': '/opt/obs-backups/backup-002.tar.gz'
                },
                {
                    'id': 'backup-003',
                    'name': 'Scenes Backup',
                    'type': 'scenes',
                    'size': '12 MB',
                    'created': '2024-01-13T16:45:00Z',
                    'status': 'completed',
                    'location': '/opt/obs-backups/backup-003.tar.gz'
                }
            ]
            return jsonify(demo_backups)
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Script timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/create', methods=['POST'])
def create_backup():
    """Create a backup"""
    try:
        data = request.json
        backup_type = data.get('type', 'full')
        
        result = subprocess.run([f'{SCRIPTS_DIR}/backup-recovery.sh', 'create', backup_type], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Backup created successfully'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/api/performance/profiles')
def performance_profiles():
    """Get performance profiles"""
    try:
        script_path = f'{SCRIPTS_DIR}/performance-profiles.sh'
        if os.path.exists(script_path):
            result = subprocess.run([script_path, 'list'], 
                                  capture_output=True, text=True, timeout=10)
            profiles = []
            return jsonify(profiles)
        else:
            # Return demo performance profiles when script is not available
            demo_profiles = [
                {
                    'name': 'streaming',
                    'description': 'Optimized for live streaming',
                    'cpu_usage': 'medium',
                    'memory_usage': 'high',
                    'quality': 'high',
                    'settings': {
                        'encoder': 'x264',
                        'bitrate': '6000',
                        'fps': '60',
                        'resolution': '1920x1080'
                    }
                },
                {
                    'name': 'recording',
                    'description': 'Optimized for local recording',
                    'cpu_usage': 'high',
                    'memory_usage': 'medium',
                    'quality': 'ultra',
                    'settings': {
                        'encoder': 'nvenc',
                        'bitrate': '50000',
                        'fps': '60',
                        'resolution': '1920x1080'
                    }
                },
                {
                    'name': 'low-power',
                    'description': 'Low resource usage',
                    'cpu_usage': 'low',
                    'memory_usage': 'low',
                    'quality': 'medium',
                    'settings': {
                        'encoder': 'quicksync',
                        'bitrate': '2500',
                        'fps': '30',
                        'resolution': '1280x720'
                    }
                }
            ]
            return jsonify(demo_profiles)
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Script timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/performance/apply', methods=['POST'])
def apply_performance_profile():
    """Apply performance profile"""
    try:
        data = request.json
        profile = data.get('profile')
        
        result = subprocess.run([f'{SCRIPTS_DIR}/performance-profiles.sh', 'apply', profile], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Profile {profile} applied'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/security/audit', methods=['POST'])
def security_audit():
    """Run security audit"""
    try:
        result = subprocess.run([f'{SCRIPTS_DIR}/security-manager.sh', 'audit'], 
                              capture_output=True, text=True)
        
        return jsonify({
            'status': 'success' if result.returncode == 0 else 'warning',
            'output': result.stdout,
            'errors': result.stderr
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    emit('connected', {'status': 'Connected to OBS Manager'})

@socketio.on('request_stats')
def handle_stats_request():
    """Handle stats request via WebSocket"""
    emit('stats_update', {
        'system': obs_manager.system_stats,
        'containers': obs_manager.containers
    })

if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs('/opt/obs-config', exist_ok=True)
    os.makedirs('/opt/obs-instances', exist_ok=True)
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)
