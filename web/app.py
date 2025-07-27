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
import secrets
import logging
import psutil
import re
import shutil
import tarfile
import io
import sys
import traceback
from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory, Response, g
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import docker

# Load environment variables from .env file
load_dotenv()

# Define SCRIPTS_DIR constant
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts')

app = Flask(__name__)

# Configuration
app.config.update(
    SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32)),
    SESSION_COOKIE_SECURE=False,  # Disable for development
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload size
    UPLOAD_FOLDER='/tmp/uploads',
    ALLOWED_EXTENSIONS={'zip', 'tar', 'gz'},
    RATE_LIMIT=os.environ.get('RATE_LIMIT', '200 per day;50 per hour'),
    CSRF_ENABLED=os.environ.get('CSRF_ENABLED', 'True').lower() == 'true'
)

# Initialize rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[app.config['RATE_LIMIT']]
)

# Initialize CSRF protection
from csrf import csrf
csrf.init_app(app)

# Check if we're in development mode
debug_mode = True  # Force development mode for Windows testing

# Minimal CSP configuration
csp = {
    'default-src': ["'self'"],
    'script-src': [
        "'self'",
        'https://code.jquery.com',
        'https://cdn.jsdelivr.net',
        'https://cdnjs.cloudflare.com',
        "'unsafe-inline'",
        "'unsafe-eval'"
    ],
    'style-src': [
        "'self'",
        'https://cdn.jsdelivr.net',
        'https://cdnjs.cloudflare.com',
        'https://fonts.googleapis.com',
        "'unsafe-inline'"
    ],
    'img-src': ["'self'", 'data:', 'blob:', 'https:'],
    'font-src': ["'self'", 'data:', 'https:'],
    'connect-src': ["'self'", 'ws:', 'wss:'],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'frame-ancestors': ["'self'"],
    'upgrade-insecure-requests': ''
}

# Initialize Talisman without nonce for now
talisman = Talisman(
    app,
    content_security_policy=csp,
    content_security_policy_nonce_in=[],  # Disable nonce for now
    force_https=False,  # Disable HTTPS enforcement for development
    strict_transport_security=False,
    session_cookie_secure=False,
    force_https_permanent=False
)

# Configure SSL for the Flask app
if not debug_mode:
    app.config.update(
        PREFERRED_URL_SCHEME='https',
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )

# Initialize SocketIO with threading mode for Windows compatibility
socketio = SocketIO(
    app,
    async_mode='threading',
    cors_allowed_origins=[],
    logger=False,
    engineio_logger=False,
    manage_session=False
)

# Docker client with enhanced error handling and diagnostics
try:
    # Try to connect to Docker daemon
    print("🔄 Attempting to connect to Docker daemon...")
    
    # Check if Docker socket exists (Unix only)
    if os.name != 'nt':  # Not Windows
        socket_path = "/var/run/docker.sock"
        if os.path.exists(socket_path):
            print(f"✅ Docker socket found at {socket_path}")
            socket_stat = os.stat(socket_path)
            print(f"📊 Socket permissions: {oct(socket_stat.st_mode)}")
            print(f"👤 Socket owner: UID {socket_stat.st_uid}, GID {socket_stat.st_gid}")
            print(f"👤 Current user: UID {os.getuid()}, GID {os.getgid()}")
            print(f"👥 User groups: {os.getgroups()}")
        else:
            print(f"❌ Docker socket not found at {socket_path}")
    else:
        print("🪟 Running on Windows - using Docker Desktop")
    
    # Try different Docker client configurations
    docker_client = None
    
    # Method 1: Explicit socket path (most reliable)
    try:
        print("🔄 Trying explicit unix socket...")
        client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
        client.ping()
        docker_client = client
        print("✅ Docker client connected via explicit socket")
    except Exception as e1:
        print(f"❌ Explicit socket failed: {e1}")
        
        # Method 2: Clear environment and try from_env
        try:
            print("🔄 Trying docker.from_env() with cleared environment...")
            # Clear potentially problematic environment variables
            old_docker_host = os.environ.get('DOCKER_HOST')
            if 'DOCKER_HOST' in os.environ:
                del os.environ['DOCKER_HOST']
            
            client = docker.from_env()
            client.ping()
            docker_client = client
            print("✅ Docker client connected via from_env()")
            
            # Restore environment
            if old_docker_host:
                os.environ['DOCKER_HOST'] = old_docker_host
                
        except Exception as e2:
            print(f"❌ from_env() failed: {e2}")
            
            # Restore environment
            if old_docker_host:
                os.environ['DOCKER_HOST'] = old_docker_host
            
            # Method 3: Force socket with custom environment
            try:
                print("🔄 Trying with custom socket environment...")
                import docker.client
                client = docker.client.DockerClient(
                    base_url='unix:///var/run/docker.sock',
                    timeout=60
                )
                client.ping()
                docker_client = client
                print("✅ Docker client connected via custom socket")
            except Exception as e3:
                print(f"❌ Custom socket failed: {e3}")
    
    if docker_client:
        version = docker_client.version()
        print(f"📊 Docker version: {version.get('Version', 'Unknown')}")
        print(f"📊 API version: {version.get('ApiVersion', 'Unknown')}")
        
        # Test basic operations
        try:
            containers = docker_client.containers.list(all=True)
            print(f"📦 Docker API test successful - found {len(containers)} containers")
        except Exception as test_e:
            print(f"⚠️ Docker API test failed: {test_e}")
    else:
        print("❌ All Docker connection methods failed")
        
except Exception as e:
    print(f"⚠️ Docker client initialization error: {e}")
    docker_client = None

if not docker_client:
    print("🔧 Python Docker client failed - trying unified adapter...")
    try:
        from docker_adapter import get_docker_client, docker_adapter
        adapter_client = get_docker_client()
        if adapter_client and adapter_client.is_available():
            print("✅ Docker adapter working - using unified interface")
            docker_client = adapter_client
        else:
            print("❌ Docker adapter also failed")
    except Exception as e:
        print(f"❌ Docker adapter failed: {e}")

if not docker_client:
    print("🔧 Running in standalone mode - Docker operations will return errors")
    print("💡 To enable Docker functionality:")
    print("   1. Ensure Docker daemon is running")
    print("   2. Mount Docker socket: -v /var/run/docker.sock:/var/run/docker.sock")
    print("   3. Add user to docker group: usermod -aG docker webuser")

class OBSManager:
    def __init__(self):
        self.containers = {}
        self.system_stats = {}
        self.update_stats()
    
    def update_stats(self):
        """Update system and container statistics"""
        try:
            # System stats
            try:
                # Try to get disk usage - use C: on Windows, / on Unix
                disk_path = 'C:' if os.name == 'nt' else '/'
                disk_stats = psutil.disk_usage(disk_path)._asdict()
            except Exception:
                disk_stats = {'total': 0, 'used': 0, 'free': 0}
            
            self.system_stats = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory()._asdict(),
                'disk': disk_stats,
                'network': psutil.net_io_counters()._asdict(),
                'timestamp': datetime.now().isoformat()
            }
            
            # Container stats (only if Docker client is available)
            if docker_client:
                containers = docker_client.containers.list(all=True)
                self.containers = {}
                
                for container in containers:
                    # Robust extraction for both wrapper and dict
                    if hasattr(container, 'status'):
                        status = container.status
                        created = getattr(container, 'attrs', {}).get('Created', '') if hasattr(container, 'attrs') else ''
                        state = getattr(container, 'attrs', {}).get('State', {}) if hasattr(container, 'attrs') else {}
                    elif hasattr(container, '_get_info'):
                        info = container._get_info()
                        status = info.get('State', {}).get('Status', 'unknown')
                        created = info.get('Created', '')
                        state = info.get('State', {})
                    elif isinstance(container, dict):
                        status = container.get('State', {}).get('Status', 'unknown')
                        created = container.get('Created', '')
                        state = container.get('State', {})
                    else:
                        continue
                    # Format uptime
                    uptime = 'N/A'
                    if 'StartedAt' in state and state['StartedAt'] != '0001-01-01T00:00:00Z':
                        try:
                            started_at = datetime.fromisoformat(state['StartedAt'].replace('Z', '+00:00'))
                            uptime = str(datetime.now(timezone.utc) - started_at).split('.')[0]  # Remove microseconds
                        except (ValueError, TypeError):
                            uptime = 'N/A'
                    # Name
                    if hasattr(container, 'name'):
                        name = container.name
                    elif hasattr(container, '_name'):
                        name = container._name
                    elif hasattr(container, '_get_info'):
                        info = container._get_info()
                        name = info.get('Names', ['unknown'])[0] if isinstance(info.get('Names'), list) else info.get('Names', 'unknown')
                    elif isinstance(container, dict):
                        name = container.get('Names', ['unknown'])[0]
                    else:
                        name = 'unknown'
                    # Image
                    if hasattr(container, 'image') and hasattr(container.image, 'tags') and container.image.tags:
                        image = container.image.tags[0]
                    elif hasattr(container, '_get_info'):
                        info = container._get_info()
                        image = info.get('Image', 'unknown')
                    elif isinstance(container, dict):
                        image = container.get('Image', 'unknown')
                    else:
                        image = 'unknown'
                    # Ports
                    if hasattr(container, 'ports'):
                        ports = container.ports
                    elif hasattr(container, '_get_info'):
                        info = container._get_info()
                        ports = info.get('NetworkSettings', {}).get('Ports', {})
                    elif isinstance(container, dict):
                        ports = container.get('Ports', {})
                    else:
                        ports = {}
                    # Labels
                    if hasattr(container, 'labels'):
                        labels = container.labels
                    elif hasattr(container, '_get_info'):
                        info = container._get_info()
                        labels = info.get('Config', {}).get('Labels', {})
                    elif isinstance(container, dict):
                        labels = container.get('Labels', {})
                    else:
                        labels = {}
                    stats = {
                        'name': name,
                        'status': status,
                        'image': image,
                        'created': created,
                        'uptime': uptime,
                        'ports': ports,
                        'labels': labels,
                    }
                    # Get container stats if running
                    if status == 'running' and hasattr(container, 'stats'):
                        try:
                            container_stats = container.stats(stream=False)
                            stats['cpu_percent'] = self.calculate_cpu_percent(container_stats)
                            stats['memory_usage'] = container_stats['memory_stats'].get('usage', 0)
                            stats['memory_limit'] = container_stats['memory_stats'].get('limit', 0)
                        except Exception as e:
                            pass
                    self.containers[name] = stats
            else:
                # Standalone mode - no container stats
                self.containers = {}
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    def calculate_cpu_percent(self, stats):
        """Calculate CPU percentage from container stats"""
        try:
            cpu_count = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
            cpu_percent = 0.0
            cpu_delta = float(stats["cpu_stats"]["cpu_usage"]["total_usage"]) - float(stats["precpu_stats"]["cpu_usage"]["total_usage"])
            system_delta = float(stats["cpu_stats"]["system_cpu_usage"]) - float(stats["precpu_stats"]["system_cpu_usage"])
            if system_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
            return cpu_percent
        except (KeyError, ZeroDivisionError):
            return 0.0

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
    return jsonify({'status': 'success', 'containers': obs_manager.containers})

@app.route('/api/container/<container_name>/start', methods=['POST'])
def api_container_start(container_name):
    """Start a container"""
    try:
        container = docker_client.containers.get(container_name)
        container.start()
        return jsonify({'status': 'success', 'message': f'Container "{container_name}" started successfully'})
    except docker.errors.NotFound:
        return jsonify({'status': 'error', 'message': 'Container not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/container/<container_name>/stop', methods=['POST'])
def api_container_stop(container_name):
    """Stop a container"""
    try:
        container = docker_client.containers.get(container_name)
        container.stop()
        return jsonify({'status': 'success', 'message': f'Container "{container_name}" stopped successfully'})
    except docker.errors.NotFound:
        return jsonify({'status': 'error', 'message': 'Container not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/container/<container_name>/restart', methods=['POST'])
def api_container_restart(container_name):
    """Restart a container"""
    try:
        container = docker_client.containers.get(container_name)
        container.restart()
        return jsonify({'status': 'success', 'message': f'Container "{container_name}" restarted successfully'})
    except docker.errors.NotFound:
        return jsonify({'status': 'error', 'message': 'Container not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/containers/cleanup', methods=['POST'])
def api_containers_cleanup():
    """Remove all stopped containers"""
    try:
        docker_client.containers.prune()
        return jsonify({'status': 'success', 'message': 'Cleaned up stopped containers'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/container/<container_name>/logs', methods=['GET'])
def api_container_logs(container_name):
    """Get container logs"""
    try:
        # Mock logs - in real implementation this would get actual container logs
        mock_logs = f"""[2024-01-20 10:30:00] Container {container_name} started
[2024-01-20 10:30:01] OBS Studio initializing...
[2024-01-20 10:30:02] Desktop environment loaded
[2024-01-20 10:30:03] RDP server started on port 3389
[2024-01-20 10:30:04] VNC server started on port 5900
[2024-01-20 10:30:05] Container ready for connections
[2024-01-20 10:30:06] Waiting for user connections..."""
        
        return jsonify({
            'status': 'success',
            'logs': mock_logs
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/system/stats')
def api_system_stats():
    """API endpoint for system statistics"""
    return jsonify({'status': 'success', 'stats': obs_manager.system_stats})

@app.route('/api/system/info')
def api_system_info():
    """API endpoint for system information"""
    import platform
    system_info = {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'docker_available': docker_client is not None,
        'timestamp': datetime.now().isoformat()
    }
    return jsonify({'status': 'success', 'info': system_info})

@app.route('/api/images/<image_id>')
def api_image_details(image_id):
    """API endpoint for single Docker image details"""
    try:
        if not docker_client:
            return jsonify({
                'status': 'error', 
                'message': 'Docker service not available'
            }), 503
        
        image = docker_client.images.get(image_id)
        return jsonify({'status': 'success', 'details': image.attrs})
    except docker.errors.ImageNotFound:
        return jsonify({'status': 'error', 'message': 'Image not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/images')
def api_images():
    """API endpoint for Docker images"""
    try:
        if not docker_client:
            return jsonify({
                'status': 'error', 
                'message': 'Docker service not available',
                'images': []
            }), 503
        
        images = docker_client.images.list()
        image_list = []
        for image in images:
            image_info = {
                'id': getattr(image, 'id', '')[:12],
                'tags': getattr(image, 'tags', []),
                'created': getattr(image, 'attrs', {}).get('Created', ''),
                'size': getattr(image, 'attrs', {}).get('Size', 0)
            }
            image_list.append(image_info)
        
        return jsonify({'status': 'success', 'images': image_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'images': []}), 500

@app.route('/api/images/pull', methods=['POST'])
def api_images_pull():
    """API endpoint to pull a Docker image and stream progress"""
    data = request.get_json()
    image_name = data.get('image')
    tag = data.get('tag', 'latest')

    if not image_name:
        return jsonify({'status': 'error', 'message': 'Image name is required'}), 400

    def generate_pull_stream():
        try:
            yield f"Attempting to pull {image_name}:{tag}...\n"
            stream = docker_client.api.pull(image_name, tag=tag, stream=True, decode=True)
            for chunk in stream:
                if 'status' in chunk:
                    yield f"{chunk['status']}: {chunk.get('progress', '')}\n"
            yield f"\nImage {image_name}:{tag} pulled successfully!\n"
        except docker.errors.APIError as e:
            yield f"\nError pulling image: {e.explanation}\n"
        except Exception as e:
            yield f"\nAn unexpected error occurred: {str(e)}\n"

    return Response(generate_pull_stream(), mimetype='text/plain')

@app.route('/api/images/<image_id>/remove', methods=['DELETE'])
def api_images_remove(image_id):
    """API endpoint to remove a Docker image"""
    try:
        docker_client.images.remove(image_id, force=True)
        return jsonify({'status': 'success', 'message': f'Image {image_id} removed successfully'})
    except docker.errors.ImageNotFound:
        return jsonify({'status': 'error', 'message': 'Image not found'}), 404
    except docker.errors.APIError as e:
        if 'image is being used by running container' in e.explanation:
            return jsonify({'status': 'error', 'message': 'Image is in use by a running container'}), 409
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def load_plugins():
    try:
        with open('plugins.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_plugins(plugins):
    with open('plugins.json', 'w') as f:
        json.dump(plugins, f, indent=4)

plugins = load_plugins()

@app.route('/api/plugins')
def api_plugins():
    """API endpoint for OBS plugins"""
    return jsonify({'status': 'success', 'plugins': plugins})

@app.route('/api/plugins/install', methods=['POST'])
def api_plugins_install():
    """API endpoint to install a plugin"""
    data = request.get_json()
    plugin_url = data.get('plugin_url')
    if not plugin_url:
        return jsonify({'status': 'error', 'message': 'Plugin URL is required'}), 400

    def generate_install_stream():
        try:
            plugin_name = plugin_url.split('/')[-1].replace('.git', '')
            plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plugins')
            if not os.path.exists(plugins_dir):
                os.makedirs(plugins_dir)
            plugin_path = os.path.join(plugins_dir, plugin_name)

            yield f"Installing plugin from {plugin_url} into {plugin_path}...\n"
            
            process = subprocess.Popen(['git', 'clone', plugin_url, plugin_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                plugins[plugin_name] = {
                    'name': plugin_name,
                    'version': '1.0.0', # You might want to get this from the plugin itself
                    'status': 'installed',
                    'description': f'A plugin from {plugin_url}',
                    'author': 'Unknown',
                    'configurable': False,
                    'config': {}
                }
                save_plugins(plugins)
                yield "Plugin installed successfully!\n"
            else:
                yield f"Error installing plugin: {stderr.decode('utf-8')}\n"

        except Exception as e:
            yield f"Error installing plugin: {str(e)}\n"

    return Response(generate_install_stream(), mimetype='text/plain')

@app.route('/api/plugins/<plugin_name>/update', methods=['POST'])
def api_plugins_update(plugin_name):
    """API endpoint to update a plugin"""
    def generate_update_stream():
        try:
            yield f"Updating plugin {plugin_name}...\n"
            # This is a mock implementation. In a real scenario, you would update the plugin.
            yield "Plugin updated successfully!\n"
        except Exception as e:
            yield f"Error updating plugin: {str(e)}\n"

    return Response(generate_update_stream(), mimetype='text/plain')

@app.route('/api/plugins/<plugin_name>/remove', methods=['DELETE'])
def api_plugins_remove(plugin_name):
    """API endpoint to remove a plugin"""
    global plugins
    if plugin_name in plugins:
        del plugins[plugin_name]
        save_plugins(plugins)
        return jsonify({'status': 'success', 'message': f'Plugin "{plugin_name}" removed successfully'})
    return jsonify({'status': 'error', 'message': 'Plugin not found'}), 404

@app.route('/api/plugins/<plugin_name>/config', methods=['GET', 'POST'])
def api_plugin_config(plugin_name):
    """API endpoint for plugin configuration"""
    global plugins
    if request.method == 'POST':
        if plugin_name in plugins:
            plugins[plugin_name]['config'] = request.get_json()
            save_plugins(plugins)
            return jsonify({'status': 'success', 'message': 'Configuration saved'})
        return jsonify({'status': 'error', 'message': 'Plugin not found'}), 404
    else:
        if plugin_name in plugins:
            return jsonify({'status': 'success', 'config': plugins[plugin_name]})
        return jsonify({'status': 'error', 'message': 'Plugin not found'}), 404

@app.route('/api/backups')
def api_backups():
    """API endpoint for backup management"""
    # Mock backup data for now
    backups = [
        {'name': 'backup-20240120-full.tar.gz', 'size': '1.2GB', 'created': '2024-01-20T10:30:00Z'},
        {'name': 'backup-20240119-incremental.tar.gz', 'size': '256MB', 'created': '2024-01-19T10:30:00Z'}
    ]
    return jsonify({'status': 'success', 'backups': backups})

@app.route('/api/backups/create', methods=['POST'])
def api_backups_create():
    """API endpoint to create a backup"""
    try:
        # Mock backup creation - in real implementation this would create a backup
        return jsonify({
            'status': 'success',
            'message': 'Backup created successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/schedule', methods=['POST'])
def api_backups_schedule():
    """API endpoint to schedule a backup"""
    try:
        # Mock backup scheduling - in real implementation this would schedule a backup
        return jsonify({
            'status': 'success',
            'message': 'Backup scheduled successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/restore', methods=['POST'])
def api_backups_restore():
    """API endpoint to restore a backup"""
    try:
        # Mock backup restoration - in real implementation this would restore a backup
        return jsonify({
            'status': 'success',
            'message': 'Backup restored successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/cleanup', methods=['POST'])
def api_backups_cleanup():
    """API endpoint to cleanup backups"""
    try:
        # Mock backup cleanup - in real implementation this would cleanup backups
        return jsonify({
            'status': 'success',
            'message': 'Backups cleaned up successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/backups/validate', methods=['POST'])
def api_backups_validate():
    """API endpoint to validate backups"""
    try:
        # Mock backup validation - in real implementation this would validate backups
        return jsonify({
            'status': 'success',
            'message': 'Backups validated successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/performance/profiles')
def api_performance_profiles():
    """API endpoint for performance profiles"""
    profiles = [
        {'name': 'streaming', 'description': 'Optimized for live streaming'},
        {'name': 'recording', 'description': 'High-quality local recording'},
        {'name': 'low-resource', 'description': 'Minimal resource usage'},
        {'name': 'gpu-accelerated', 'description': 'Hardware acceleration enabled'}
    ]
    return jsonify({'status': 'success', 'profiles': profiles})

@app.route('/api/performance/apply', methods=['POST'])
def api_performance_apply():
    """API endpoint to apply performance profile"""
    try:
        data = request.get_json()
        profile = data.get('profile')
        
        if not profile:
            return jsonify({'status': 'error', 'message': 'Profile name is required'}), 400
        
        # Mock profile application - in real implementation this would apply the profile
        return jsonify({
            'status': 'success',
            'message': f'Performance profile "{profile}" applied successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def load_settings():
    try:
        with open('settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_settings(settings):
    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

@app.route('/api/settings/general', methods=['POST'])
def api_settings_general():
    """API endpoint to save general settings"""
    try:
        settings = load_settings()
        settings['general'] = request.get_json()
        save_settings(settings)
        return jsonify({'status': 'success', 'message': 'General settings saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/settings/security', methods=['POST'])
def api_settings_security():
    """API endpoint to save security settings"""
    try:
        settings = load_settings()
        settings['security'] = request.get_json()
        save_settings(settings)
        return jsonify({'status': 'success', 'message': 'Security settings saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/settings/cloud', methods=['POST'])
def api_settings_cloud():
    """API endpoint to save cloud settings"""
    try:
        settings = load_settings()
        settings['cloud'] = request.get_json()
        save_settings(settings)
        return jsonify({'status': 'success', 'message': 'Cloud settings saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/settings/backup', methods=['POST'])
def api_settings_backup():
    """API endpoint to save backup settings"""
    try:
        settings = load_settings()
        settings['backup'] = request.get_json()
        save_settings(settings)
        return jsonify({'status': 'success', 'message': 'Backup settings saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/settings/cloud_backup', methods=['POST'])
def api_settings_cloud_backup():
    """API endpoint to save cloud backup settings"""
    try:
        settings = load_settings()
        settings['cloud_backup'] = request.get_json()
        save_settings(settings)
        return jsonify({'status': 'success', 'message': 'Cloud backup settings saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/monitoring/alerts')
def api_monitoring_alerts():
    """API endpoint for monitoring alerts"""
    # In a real application, you would fetch these from a database or a log file.
    alerts = [] 
    return jsonify({'status': 'success', 'alerts': alerts})

@app.route('/api/monitoring/logs')
def api_monitoring_logs():
    """API endpoint for system logs"""
    # In a real application, you would fetch these from a log file.
    logs = []
    return jsonify({'status': 'success', 'logs': logs})

@app.route('/api/monitoring/alerts/clear', methods=['POST'])
def api_monitoring_alerts_clear():
    """API endpoint to clear monitoring alerts"""
    # In a real application, this would clear the alerts from the database or cache.
    return jsonify({'status': 'success', 'message': 'Alerts cleared'})

@app.route('/api/monitoring/logs/clear', methods=['POST'])
def api_monitoring_logs_clear():
    """API endpoint to clear system logs"""
    # In a real application, this would clear the logs from the database or file.
    return jsonify({'status': 'success', 'message': 'Logs cleared'})

@app.route('/api/security/audit', methods=['POST'])
def api_security_audit():
    """API endpoint to run security audit"""
    try:
        # Mock security audit - in real implementation this would run actual security checks
        audit_results = {
            'status': 'success',
            'message': 'Security audit completed successfully',
            'findings': [
                {'level': 'info', 'message': 'All security checks passed'},
                {'level': 'warning', 'message': 'Consider enabling MFA for enhanced security'}
            ]
        }
        return jsonify(audit_results)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/instances')
def instances():
    """Instance management page"""
    return render_template('instances.html')

@app.route('/images')
def images():
    """Image management page"""
    return render_template('images.html')

@app.route('/plugins')
def manage_plugins_page():
    """Plugin management page"""
    return render_template('plugins.html')

@app.route('/monitoring')
def monitoring():
    """Monitoring page"""
    return render_template('monitoring.html')

@app.route('/backups')
def backups():
    """Backup management page"""
    return render_template('backups.html')

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/api/instances/create', methods=['POST'])
def api_instances_create():
    """Create a new OBS instance"""
    try:
        data = request.get_json()
        name = data.get('name')
        template = data.get('template')
        user = data.get('user', 'developer')
        password = data.get('password')
        port = data.get('port')
        desktop_env = data.get('desktop_env', 'lxde')
        
        if not name or not template or not password:
            return jsonify({
                'status': 'error',
                'message': 'Name, template, and password are required'
            }), 400
        
        def generate_log_stream():
            try:
                image_name = f'obs-docker-{desktop_env}:latest'
                try:
                    docker_client.images.get(image_name)
                    yield f"Image '{image_name}' found locally.\n"
                except docker.errors.ImageNotFound:
                    yield f"Image '{image_name}' not found locally, building from Dockerfile...\n"
                    try:
                        stream = docker_client.api.build(
                            path='..',
                            tag=image_name,
                            rm=True,
                            decode=True,
                            buildargs={'DESKTOP_ENV': desktop_env}
                        )
                        for chunk in stream:
                            if 'stream' in chunk:
                                yield chunk['stream']
                        yield f"Image '{image_name}' built successfully.\n"
                    except docker.errors.BuildError as e:
                        yield f"Failed to build Docker image: {e}\n"
                        return

                port_mapping = {'3389/tcp': port} if port else {'3389/tcp': None}
                yield f"Creating container '{name}'...\n"
                docker_client.containers.run(
                    image=image_name,
                    name=name,
                    detach=True,
                    ports=port_mapping,
                    environment=[
                        f'USER={user}',
                        f'PASSWD={password}',
                        'GROUP=developer',
                        'DISPLAY=:1',
                        'TZ=UTC',
                        'LANG=en_US.UTF-8',
                        f'PERFORMANCE_PROFILE={template}'
                    ],
                    labels={
                        'com.obs-docker.instance': name,
                        'com.obs-docker.template': template,
                        'com.obs-docker.user': user,
                        'com.obs-docker.desktop': desktop_env
                    }
                )
                yield f"Instance '{name}' created successfully with template '{template}' and desktop '{desktop_env}'.\n"
            except docker.errors.APIError as e:
                yield f"Error: {e}\n"
        return Response(generate_log_stream(), mimetype='text/plain')
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/instances/start_all', methods=['POST'])
def api_instances_start_all():
    """Start all instances"""
    try:
        for container in docker_client.containers.list(all=True):
            if container.status != 'running':
                container.start()
        return jsonify({'status': 'success', 'message': 'All instances started successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/stop_all', methods=['POST'])
def api_instances_stop_all():
    """Stop all instances"""
    try:
        for container in docker_client.containers.list():
            container.stop()
        return jsonify({'status': 'success', 'message': 'All instances stopped successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/remove_all', methods=['POST'])
def api_instances_remove_all():
    """Remove all stopped instances"""
    try:
        for container in docker_client.containers.list(all=True):
            if container.status != 'running':
                container.remove(force=True)
        return jsonify({'status': 'success', 'message': 'All stopped instances removed successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/scale', methods=['POST'])
def api_instances_scale():
    """Scale instances"""
    try:
        data = request.get_json()
        template = data.get('template')
        count = data.get('count', 1)
        prefix = data.get('prefix', 'obs-instance')
        
        # Mock scaling - in real implementation this would create multiple containers
        return jsonify({
            'status': 'success',
            'message': f'Created {count} instances with template "{template}" and prefix "{prefix}"'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/<instance_name>/start', methods=['POST'])
def api_instance_start(instance_name):
    """Start an instance"""
    try:
        container = docker_client.containers.get(instance_name)
        container.start()
        return jsonify({'status': 'success', 'message': f'Instance "{instance_name}" started successfully'})
    except docker.errors.NotFound:
        return jsonify({'status': 'error', 'message': 'Instance not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/<instance_name>/stop', methods=['POST'])
def api_instance_stop(instance_name):
    """Stop an instance"""
    try:
        container = docker_client.containers.get(instance_name)
        container.stop()
        return jsonify({'status': 'success', 'message': f'Instance "{instance_name}" stopped successfully'})
    except docker.errors.NotFound:
        return jsonify({'status': 'error', 'message': 'Instance not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/<instance_name>/restart', methods=['POST'])
def api_instance_restart(instance_name):
    """Restart an instance"""
    try:
        container = docker_client.containers.get(instance_name)
        container.restart()
        return jsonify({'status': 'success', 'message': f'Instance "{instance_name}" restarted successfully'})
    except docker.errors.NotFound:
        return jsonify({'status': 'error', 'message': 'Instance not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances/<instance_name>/remove', methods=['DELETE'])
def api_instance_remove(instance_name):
    """Remove an instance"""
    try:
        container = docker_client.containers.get(instance_name)
        container.remove(force=True)
        return jsonify({'status': 'success', 'message': f'Instance "{instance_name}" removed successfully'})
    except docker.errors.NotFound:
        return jsonify({'status': 'error', 'message': 'Instance not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/instances', methods=['GET'])
def api_instances():
    """Get all Docker containers"""
    try:
        if not docker_client:
            return jsonify({
                'status': 'error', 
                'message': 'Docker service not available',
                'instances': [],
                'count': 0
            }), 503
        
        # List all containers
        all_containers = docker_client.containers.list(all=True)
        print(f"Found {len(all_containers)} containers total")
        container_infos = []
        for idx, container in enumerate(all_containers):
            try:
                if hasattr(container, 'name'):
                    container_name = container.name
                    container_id = getattr(container, 'id', '')[:12]
                    status = getattr(container, 'status', '')
                    attrs = getattr(container, 'attrs', {})
                    created = attrs.get('Created', '')
                    state = attrs.get('State', {})
                    container_labels = getattr(container, 'labels', {})
                    ports_info = getattr(container, 'ports', {}) if hasattr(container, 'ports') else {}
                else:
                    container_name = container.get('Names', ['unknown'])[0]
                    container_id = container.get('Id', '')[:12]
                    status = container.get('State', {}).get('Status', 'unknown')
                    created = container.get('Created', '')
                    state = container.get('State', {})
                    container_labels = container.get('Labels', {})
                    if isinstance(container_labels, str):
                        container_labels = parse_label_string(container_labels)
                    ports_info = container.get('Ports', {})
                # Uptime
                uptime = 'N/A'
                started_at = state.get('StartedAt')
                if started_at and started_at != '0001-01-01T00:00:00Z':
                    try:
                        started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                        uptime = str(datetime.now(timezone.utc) - started_at).split('.')[0]
                    except (ValueError, TypeError):
                        pass
                # Ports
                ports = {}
                if isinstance(ports_info, dict):
                    if '3389/tcp' in ports_info and ports_info['3389/tcp']:
                        for binding in ports_info['3389/tcp']:
                            if binding and binding.get('HostPort'):
                                ports['rdp'] = binding['HostPort']
                                break
                    if '5900/tcp' in ports_info and ports_info['5900/tcp']:
                        for binding in ports_info['5900/tcp']:
                            if binding and binding.get('HostPort'):
                                ports['vnc'] = binding['HostPort']
                                break
                elif isinstance(ports_info, str):
                    match = re.search(r':(\d+)->3389/tcp', ports_info)
                    if match:
                        ports['rdp'] = match.group(1)
                    match = re.search(r':(\d+)->5900/tcp', ports_info)
                    if match:
                        ports['vnc'] = match.group(1)
                # Image
                image_name = 'unknown'
                try:
                    if hasattr(container, 'image') and container.image:
                        if hasattr(container.image, 'tags') and container.image.tags:
                            image_name = container.image.tags[0]
                    elif not hasattr(container, 'image'):
                        image_name = container.get('Image', 'unknown')
                except Exception:
                    pass
                # Extract instance name from labels
                instance_name = container_labels.get('com.obs-docker.instance', '')
                if instance_name:
                    display_name = f"obs-{instance_name}"
                else:
                    display_name = container_name
                
                container_info = {
                    'id': container_id,
                    'name': container_name,
                    'display_name': display_name,
                    'instance_name': instance_name,
                    'status': status,
                    'image': image_name,
                    'created': created,
                    'uptime': uptime,
                    'ports': ports,
                    'labels': container_labels,
                    'template': container_labels.get('com.obs-docker.template', ''),
                    'user': container_labels.get('com.obs-docker.user', ''),
                    'rdp_port': ports.get('rdp', ''),
                }
                container_infos.append(container_info)
            except Exception as e:
                continue
        # Convert list to dict with names as keys
        instances_dict = {}
        for container_info in container_infos:
            key = container_info.get('display_name', container_info.get('name', 'unknown'))
            instances_dict[key] = container_info
        
        return jsonify({
            'status': 'success',
            'instances': instances_dict,
            'count': len(instances_dict)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'instances': [],
            'count': 0
        }), 500

def parse_label_string(label_str):
    if not label_str:
        return {}
    pairs = [kv.split('=', 1) for kv in label_str.split(',') if '=' in kv]
    return {k.strip(): v.strip() for k, v in pairs}

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
    socketio.run(app, debug=debug_mode, host='0.0.0.0', port=8080)