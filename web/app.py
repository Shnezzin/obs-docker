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
        
        # Check if script exists
        script_path = f'{SCRIPTS_DIR}/instance-manager.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Instance {name} created successfully (demo mode)',
                'instance': {
                    'name': name,
                    'template': template,
                    'user': user,
                    'status': 'running',
                    'created': datetime.now().isoformat()
                }
            })
        
        # Run the script (jq should be available from Dockerfile)
        result = subprocess.run([
            script_path, 'create', 
            name, template, user, password
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Instance {name} created successfully'})
        else:
            # If jq is still missing, provide helpful error message
            if 'jq: command not found' in result.stderr:
                return jsonify({
                    'status': 'error', 
                    'message': 'jq dependency missing. Please rebuild the Docker container to install required dependencies.',
                    'details': result.stderr
                }), 500
            else:
                return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Instance creation timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/<instance_name>/start', methods=['POST'])
def start_instance(instance_name):
    """Start an instance"""
    try:
        script_path = f'{SCRIPTS_DIR}/instance-manager.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Instance {instance_name} started successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'start', instance_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Instance {instance_name} started'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Instance start timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/<instance_name>/stop', methods=['POST'])
def stop_instance(instance_name):
    """Stop an instance"""
    try:
        script_path = f'{SCRIPTS_DIR}/instance-manager.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Instance {instance_name} stopped successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'stop', instance_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Instance {instance_name} stopped'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Instance stop timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/<instance_name>/restart', methods=['POST'])
def restart_instance(instance_name):
    """Restart an instance"""
    try:
        script_path = f'{SCRIPTS_DIR}/instance-manager.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Instance {instance_name} restarted successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'restart', instance_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Instance {instance_name} restarted'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Instance restart timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/<instance_name>/remove', methods=['DELETE'])
def remove_instance(instance_name):
    """Remove an instance"""
    try:
        script_path = f'{SCRIPTS_DIR}/instance-manager.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Instance {instance_name} removed successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'remove', instance_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Instance {instance_name} removed'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Instance removal timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/scale', methods=['POST'])
def scale_instances():
    """Scale instances up or down"""
    try:
        data = request.json
        action = data.get('action')  # 'up' or 'down'
        count = data.get('count', 1)
        
        script_path = f'{SCRIPTS_DIR}/instance-manager.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Instances scaled {action} by {count} (demo mode)'
            })
        
        result = subprocess.run([script_path, 'scale', action, str(count)], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Instances scaled {action} by {count}'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Instance scaling timeout'}), 500
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
        
        # Create plugins directory if it doesn't exist
        plugins_dir = '/opt/obs-plugins'
        try:
            os.makedirs(plugins_dir, exist_ok=True)
        except PermissionError:
            # Fallback to user directory if system directory is not writable
            plugins_dir = os.path.expanduser('~/obs-plugins')
            os.makedirs(plugins_dir, exist_ok=True)
        
        # Check if script exists
        script_path = f'{SCRIPTS_DIR}/plugin-manager.sh'
        if not os.path.exists(script_path):
            # Return success for demo purposes
            return jsonify({
                'status': 'success', 
                'message': f'Plugin {plugin_name} installed successfully (demo mode)',
                'location': plugins_dir
            })
        
        result = subprocess.run([script_path, 'install', plugin_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Plugin {plugin_name} installed'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Plugin installation timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/plugins/<plugin_name>/update', methods=['POST'])
def update_plugin(plugin_name):
    """Update a plugin"""
    try:
        script_path = f'{SCRIPTS_DIR}/plugin-manager.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Plugin {plugin_name} updated successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'update', plugin_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Plugin {plugin_name} updated'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Plugin update timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/plugins/<plugin_name>/remove', methods=['DELETE'])
def remove_plugin(plugin_name):
    """Remove a plugin"""
    try:
        script_path = f'{SCRIPTS_DIR}/plugin-manager.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Plugin {plugin_name} removed successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'remove', plugin_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Plugin {plugin_name} removed'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Plugin removal timeout'}), 500
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

@app.route('/api/system/info')
def system_info():
    """Get system information for settings page"""
    try:
        import platform
        import sys
        import shutil
        
        # Get memory info
        memory = psutil.virtual_memory()
        
        # Get disk info (try multiple paths for cross-platform compatibility)
        disk_total = 0
        disk_free = 0
        try:
            if os.path.exists('/'):
                disk_usage = psutil.disk_usage('/')
            else:
                disk_usage = psutil.disk_usage('C:\\' if platform.system() == 'Windows' else '.')
            disk_total = disk_usage.total
            disk_free = disk_usage.free
        except:
            disk_total = 0
            disk_free = 0
        
        # Get Docker version safely
        docker_version = 'Not available'
        if docker_client:
            try:
                docker_version = docker_client.version()['Version']
            except:
                docker_version = 'Connected but version unavailable'
        
        system_info = {
            'platform': {
                'system': platform.system() or 'Unknown',
                'release': platform.release() or 'Unknown',
                'version': platform.version() or 'Unknown',
                'machine': platform.machine() or 'Unknown',
                'processor': platform.processor() or 'Unknown',
                'architecture': platform.architecture()[0] if platform.architecture() else 'Unknown'
            },
            'python': {
                'version': sys.version.split()[0] if sys.version else 'Unknown',
                'full_version': sys.version or 'Unknown',
                'executable': sys.executable or 'Unknown'
            },
            'docker': {
                'available': docker_client is not None,
                'version': docker_version,
                'status': 'Connected' if docker_client else 'Not available'
            },
            'obs_manager': {
                'version': '2.0.0',
                'status': 'Running',
                'features': [
                    'Multi-architecture support',
                    'Web management interface',
                    'Plugin management',
                    'Backup and recovery',
                    'Performance profiles',
                    'Security management'
                ]
            },
            'resources': {
                'cpu_count': psutil.cpu_count() or 0,
                'cpu_percent': round(psutil.cpu_percent(interval=1), 1),
                'memory_total': memory.total,
                'memory_available': memory.available,
                'memory_used': memory.used,
                'memory_percent': round(memory.percent, 1),
                'disk_total': disk_total,
                'disk_free': disk_free,
                'disk_used': disk_total - disk_free if disk_total > 0 else 0,
                'disk_percent': round(((disk_total - disk_free) / disk_total * 100), 1) if disk_total > 0 else 0
            },
            'network': {
                'hostname': platform.node() or 'Unknown'
            }
        }
        
        return jsonify(system_info)
    except Exception as e:
        print(f"System info error: {e}")
        # Return fallback data even on error
        fallback_info = {
            'platform': {
                'system': 'Unknown',
                'release': 'Unknown',
                'version': 'Unknown',
                'machine': 'Unknown',
                'processor': 'Unknown'
            },
            'python': {
                'version': 'Unknown',
                'executable': 'Unknown'
            },
            'docker': {
                'available': False,
                'version': 'Not available'
            },
            'obs_manager': {
                'version': '2.0.0',
                'status': 'Running'
            },
            'resources': {
                'cpu_count': 0,
                'memory_total': 0,
                'disk_total': 0
            },
            'error': str(e)
        }
        return jsonify(fallback_info)

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
        
        script_path = f'{SCRIPTS_DIR}/backup-recovery.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'{backup_type.title()} backup created successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'create', backup_type], 
                              capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Backup created successfully'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Backup creation timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/schedule', methods=['POST'])
def schedule_backup():
    """Schedule a backup"""
    try:
        data = request.json
        schedule = data.get('schedule')
        backup_type = data.get('type', 'full')
        
        script_path = f'{SCRIPTS_DIR}/backup-recovery.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Backup scheduled for {schedule} (demo mode)'
            })
        
        result = subprocess.run([script_path, 'schedule', schedule, backup_type], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Backup scheduled for {schedule}'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Backup scheduling timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/restore', methods=['POST'])
def restore_backup():
    """Restore from backup"""
    try:
        data = request.json
        backup_id = data.get('backup_id')
        
        script_path = f'{SCRIPTS_DIR}/backup-recovery.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Backup {backup_id} restored successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'restore', backup_id], 
                              capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Backup {backup_id} restored successfully'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Backup restoration timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/<backup_name>/verify', methods=['POST'])
def verify_backup(backup_name):
    """Verify backup integrity"""
    try:
        script_path = f'{SCRIPTS_DIR}/backup-recovery.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Backup {backup_name} verified successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'verify', backup_name], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Backup {backup_name} verified successfully'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Backup verification timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/<backup_name>', methods=['DELETE'])
def delete_backup(backup_name):
    """Delete a backup"""
    try:
        script_path = f'{SCRIPTS_DIR}/backup-recovery.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': f'Backup {backup_name} deleted successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'delete', backup_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': f'Backup {backup_name} deleted successfully'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Backup deletion timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/cleanup', methods=['POST'])
def cleanup_backups():
    """Clean up old backups"""
    try:
        script_path = f'{SCRIPTS_DIR}/backup-recovery.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': 'Old backups cleaned up successfully (demo mode)'
            })
        
        result = subprocess.run([script_path, 'cleanup'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': 'Old backups cleaned up successfully'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Backup cleanup timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/validate', methods=['POST'])
def validate_backups():
    """Validate all backups"""
    try:
        script_path = f'{SCRIPTS_DIR}/backup-recovery.sh'
        if not os.path.exists(script_path):
            return jsonify({
                'status': 'success', 
                'message': 'All backups validated successfully (demo mode)',
                'valid_count': 3,
                'invalid_count': 0
            })
        
        result = subprocess.run([script_path, 'validate'], 
                              capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': 'All backups validated successfully'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Backup validation timeout'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/api/settings/save', methods=['POST'])
def save_settings():
    """Save general settings"""
    try:
        data = request.json
        settings_type = data.get('type', 'general')
        
        # Create settings directory if it doesn't exist
        settings_dir = '/opt/obs-config/settings'
        try:
            os.makedirs(settings_dir, exist_ok=True)
        except PermissionError:
            # Fallback to user directory
            settings_dir = os.path.expanduser('~/obs-config/settings')
            os.makedirs(settings_dir, exist_ok=True)
        
        # Save settings to JSON file
        settings_file = os.path.join(settings_dir, f'{settings_type}.json')
        with open(settings_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({
            'status': 'success', 
            'message': f'{settings_type.title()} settings saved successfully',
            'location': settings_file
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Additional settings endpoints for different setting types
@app.route('/api/settings/general', methods=['POST'])
def save_general_settings():
    """Save general settings"""
    return save_settings()

@app.route('/api/settings/security', methods=['POST'])
def save_security_settings():
    """Save security settings"""
    return save_settings()

@app.route('/api/settings/cloud', methods=['POST'])
def save_cloud_settings():
    """Save cloud settings"""
    return save_settings()

@app.route('/api/settings/backup', methods=['POST'])
def save_backup_settings():
    """Save backup settings"""
    return save_settings()

@app.route('/api/settings/load', methods=['GET'])
def load_settings():
    """Load settings"""
    try:
        settings_type = request.args.get('type', 'general')
        
        # Try to load from different possible locations
        possible_paths = [
            f'/opt/obs-config/settings/{settings_type}.json',
            os.path.expanduser(f'~/obs-config/settings/{settings_type}.json')
        ]
        
        for settings_file in possible_paths:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings_data = json.load(f)
                return jsonify(settings_data)
        
        # Return default settings if no file found
        default_settings = {
            'general': {
                'auto_start': False,
                'minimize_to_tray': True,
                'check_updates': True,
                'language': 'en'
            },
            'recording': {
                'format': 'mp4',
                'quality': 'high',
                'fps': 60
            },
            'streaming': {
                'service': 'twitch',
                'bitrate': 6000,
                'keyframe_interval': 2
            }
        }
        
        return jsonify(default_settings.get(settings_type, {}))
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

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
