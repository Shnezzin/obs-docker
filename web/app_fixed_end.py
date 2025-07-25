        # Check XRDP-SESMAN logs
        sesman_log_result = container.exec_run('tail -20 /var/log/xrdp-sesman.log', user='root', debug_logs=debug_logs)
        log_debug(f"XRDP-SESMAN logs: exit_code={sesman_log_result.exit_code}, output={sesman_log_result.output.decode()}")

        return jsonify({
            'status': 'success',
            'message': 'RDP debug information collected',
            'debug': debug_logs
        })
    except Exception as e:
        log_debug(f"Exception in debug_rdp_connection: {e}")
        return jsonify({'status': 'error', 'message': str(e), 'debug': debug_logs}), 500

@app.route('/api/container/<container_name>/fix-desktop', methods=['POST'])
def fix_desktop_configuration(container_name):
    """Fix desktop configuration for existing container"""
    debug_logs = []

    def log_debug(message):
        debug_logs.append(message)
        print(f"[DEBUG] {message}")

    try:
        log_debug(f"Fixing desktop configuration for container: {container_name}")

        if not docker_client:
            return jsonify({'status': 'error', 'message': 'Docker client not available', 'debug': debug_logs}), 503

        # Find container by name or instance name
        container = find_container_by_name_or_instance(container_name, debug_logs)
        if container is None:
            return jsonify({'status': 'error', 'message': f'Container "{container_name}" not found', 'debug': debug_logs}), 404

        log_debug("Container found, fixing desktop configuration...")

        actual_container_name = container.name if hasattr(container, 'name') else container.get('Names', [''])[0]
        log_debug(f"Actual container name: {actual_container_name}")

        log_debug(f"Calling ensure_user_exists with: {actual_container_name}, developer, obs123")
        if ensure_user_exists(actual_container_name, 'developer', 'obs123', debug_logs):
            log_debug("User creation successful")
            return jsonify({
                'status': 'success',
                'message': f'Desktop configuration fixed successfully for container {container_name}',
                'debug': debug_logs
            })
        else:
            log_debug("User creation failed")
            return jsonify({'status': 'error', 'message': f'Failed to fix desktop configuration for container {container_name}', 'debug': debug_logs}), 500

    except Exception as e:
        log_debug(f"Exception in fix_desktop_configuration: {e}")
        return jsonify({'status': 'error', 'message': str(e), 'debug': debug_logs}), 500

@app.route('/api/container/<container_name>/create-user', methods=['POST'])
def create_user_in_container(container_name):
    """Create user in existing container"""
    debug_logs = []

    def log_debug(message):
        debug_logs.append(message)
        print(f"[DEBUG] {message}")

    try:
        log_debug(f"create_user_in_container called with container_name: {container_name}")
        data = request.json or {}
        user = data.get('user', 'developer')
        password = data.get('password', 'obs123')

        log_debug(f"User: {user}, Password: {password}")

        if not docker_client:
            log_debug("docker_client not available")
            return jsonify({'status': 'error', 'message': 'Docker client not available', 'debug': debug_logs}), 503

        log_debug(f"docker_client available, searching for container: {container_name}")

        # Find container by name or instance name
        container = find_container_by_name_or_instance(container_name, debug_logs)
        if container is None:
            log_debug(f"Container {container_name} not found")
            return jsonify({'status': 'error', 'message': f'Container "{container_name}" not found', 'debug': debug_logs}), 404

        log_debug(f"Container found: {container}")

        actual_container_name = container.name if hasattr(container, 'name') else container.get('Names', [''])[0]
        log_debug(f"Actual container name: {actual_container_name}")

        log_debug(f"Calling ensure_user_exists with: {actual_container_name}, {user}, {password}")
        if ensure_user_exists(actual_container_name, user, password, debug_logs):
            log_debug("User creation successful")
            return jsonify({
                'status': 'success',
                'message': f'User {user} created successfully in container {container_name}',
                'debug': debug_logs
            })
        else:
            log_debug("User creation failed")
            return jsonify({'status': 'error', 'message': f'Failed to create user {user} in container {container_name}', 'debug': debug_logs}), 500

    except Exception as e:
        log_debug(f"Exception in create_user_in_container: {e}")
        return jsonify({'status': 'error', 'message': str(e), 'debug': debug_logs}), 500

# Add missing images route
@app.route('/images')
def images():
    """Docker images management page"""
    return render_template('images.html')

@app.route('/api/images')
def api_images():
    """API endpoint for Docker images information"""
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
            # Handle both Python client and subprocess client
            if hasattr(image, 'tags') and hasattr(image, 'id'):
                tags = image.tags or ['<none>:<none>']
                image_id = image.id[:12]
                size = getattr(image, 'attrs', {}).get('Size', 0) if hasattr(image, 'attrs') else 0
                created = getattr(image, 'attrs', {}).get('Created', '') if hasattr(image, 'attrs') else ''
            else:
                # Subprocess client format
                tags = image.get('RepoTags', ['<none>:<none>']) or ['<none>:<none>']
                image_id = image.get('Id', '')[:12]
                size = image.get('Size', 0)
                created = image.get('Created', '')
            
            image_info = {
                'id': image_id,
                'tags': tags,
                'size': size,
                'created': created
            }
            image_list.append(image_info)
        
        return jsonify({
            'status': 'success',
            'images': image_list
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'images': []
        }), 500

if __name__ == '__main__':
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='OBS Docker Web Manager')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL/HTTPS')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    args = parser.parse_args()

    # Ensure required directories exist
    os.makedirs('/opt/obs-config', exist_ok=True)
    os.makedirs('/opt/obs-instances', exist_ok=True)
    os.makedirs('/opt/obs-backups', exist_ok=True)

    # Configure SSL based on command line argument
    ssl_context = None
    if not args.no_ssl and not debug_mode:
        # For production you should provide proper certificate files
        ssl_context = 'adhoc'  # This will use a self-signed certificate

    # Run the application
    socketio.run(app,
                host=args.host,
                port=args.port,
                debug=debug_mode,
                ssl_context=ssl_context)