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
        result = subprocess.run([f'{SCRIPTS_DIR}/instance-manager.sh', 'list'], 
                              capture_output=True, text=True)
        # Parse the output to JSON format
        instances = {}
        return jsonify(instances)
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
        result = subprocess.run([f'{SCRIPTS_DIR}/plugin-manager.sh', 'list'], 
                              capture_output=True, text=True)
        # Parse plugin list
        plugins = {}
        return jsonify(plugins)
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
        result = subprocess.run([f'{SCRIPTS_DIR}/backup-recovery.sh', 'list'], 
                              capture_output=True, text=True)
        # Parse backup list
        backups = []
        return jsonify(backups)
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
        result = subprocess.run([f'{SCRIPTS_DIR}/performance-profiles.sh', 'list'], 
                              capture_output=True, text=True)
        profiles = []
        return jsonify(profiles)
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
