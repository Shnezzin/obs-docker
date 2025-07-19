# OBS Docker Web Management Interface

A comprehensive web-based management interface for the OBS Docker project, providing real-time monitoring, container management, and advanced configuration capabilities.

## Features

### 🎛️ Dashboard
- Real-time system metrics (CPU, Memory, Disk, Network)
- Container status overview
- Performance charts and analytics
- Quick action buttons

### 📦 Container Management
- Start, stop, restart containers
- View container logs in real-time
- Resource usage monitoring
- RDP connection management
- Bulk operations support

### 🏗️ Instance Management
- Create new OBS instances with templates
- Multi-instance orchestration
- Scaling and load balancing
- Template-based deployment

### 🧩 Plugin Management
- Install and manage OBS plugins
- Popular plugin recommendations
- Plugin configuration interface
- Update and removal tools

### 📊 Monitoring & Analytics
- System performance tracking
- Container resource metrics
- Alert management
- Log aggregation
- Integration with Prometheus/Grafana

### 💾 Backup & Recovery
- Automated backup scheduling
- Multiple backup types (full, incremental, differential)
- Cloud storage integration
- Restore and migration tools
- Backup validation

### ⚙️ Settings & Configuration
- General system settings
- Performance profile management
- Security configuration
- Cloud integration setup
- Import/export settings

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- OBS Docker project setup
- Python 3.11+ (for development)

### Using Docker (Recommended)

1. **Start the web manager:**
   ```bash
   cd web/
   chmod +x start-web-manager.sh
   ./start-web-manager.sh start
   ```

2. **Access the interface:**
   Open your browser and navigate to `http://localhost:8080`

3. **Stop the web manager:**
   ```bash
   ./start-web-manager.sh stop
   ```

### Development Setup

1. **Install dependencies:**
   ```bash
   cd web/
   pip install -r requirements.txt
   ```

2. **Run the development server:**
   ```bash
   python app.py
   ```

3. **Access the interface:**
   Open your browser and navigate to `http://localhost:8080`

## Architecture

### Backend (Flask + SocketIO)
- **Flask**: Web framework for REST API endpoints
- **SocketIO**: Real-time communication for live updates
- **Docker SDK**: Container management and monitoring
- **psutil**: System resource monitoring

### Frontend (Bootstrap + Chart.js)
- **Bootstrap 5**: Responsive UI framework
- **Chart.js**: Interactive charts and graphs
- **Socket.IO Client**: Real-time data updates
- **Font Awesome**: Icons and visual elements

### Key Components

```
web/
├── app.py                 # Main Flask application
├── templates/             # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── dashboard.html    # Main dashboard
│   ├── containers.html   # Container management
│   ├── instances.html    # Instance management
│   ├── plugins.html      # Plugin management
│   ├── monitoring.html   # Monitoring & analytics
│   ├── backups.html      # Backup & recovery
│   └── settings.html     # Settings & configuration
├── requirements.txt      # Python dependencies
├── Dockerfile.web       # Docker image definition
├── docker-compose.web.yml # Docker Compose configuration
└── start-web-manager.sh # Startup script
```

## API Endpoints

### System Information
- `GET /api/system/stats` - Get system statistics
- `GET /api/system/info` - Get system information

### Container Management
- `GET /api/containers` - List all containers
- `POST /api/container/{name}/start` - Start container
- `POST /api/container/{name}/stop` - Stop container
- `POST /api/container/{name}/restart` - Restart container
- `GET /api/container/{name}/logs` - Get container logs

### Instance Management
- `GET /api/instances` - List all instances
- `POST /api/instances/create` - Create new instance
- `POST /api/instances/{name}/start` - Start instance
- `POST /api/instances/{name}/stop` - Stop instance
- `DELETE /api/instances/{name}/remove` - Remove instance

### Plugin Management
- `GET /api/plugins` - List installed plugins
- `POST /api/plugins/install` - Install plugin
- `POST /api/plugins/{name}/update` - Update plugin
- `DELETE /api/plugins/{name}/remove` - Remove plugin

### Backup Management
- `GET /api/backups` - List available backups
- `POST /api/backups/create` - Create backup
- `POST /api/backups/restore` - Restore from backup
- `DELETE /api/backups/{name}` - Delete backup

### Performance Management
- `GET /api/performance/profiles` - List performance profiles
- `POST /api/performance/apply` - Apply performance profile

### Security
- `POST /api/security/audit` - Run security audit

## Configuration

### Environment Variables
- `FLASK_ENV`: Flask environment (development/production)
- `FLASK_DEBUG`: Enable debug mode (true/false)
- `SCRIPTS_DIR`: Path to OBS scripts directory
- `CONFIG_DIR`: Path to configuration directory
- `INSTANCES_DIR`: Path to instances directory
- `BACKUPS_DIR`: Path to backups directory

### Docker Volumes
- `obs-config`: Configuration data
- `obs-instances`: Instance data
- `obs-backups`: Backup data
- `/var/run/docker.sock`: Docker socket (read-only)

## Security Considerations

### Access Control
- The web interface runs on localhost by default
- For remote access, configure proper authentication
- Use HTTPS in production environments

### Docker Socket Access
- The container requires read-only access to Docker socket
- This allows container management but limits security risks
- Consider using Docker API with authentication for production

### Data Protection
- Sensitive configuration is stored in Docker volumes
- Backup encryption is available for sensitive data
- Regular security audits are recommended

## Monitoring Integration

### Prometheus Metrics
The web interface exposes metrics compatible with Prometheus:
- System resource usage
- Container statistics
- Application performance metrics

### Grafana Dashboards
Pre-configured dashboards are available for:
- System overview
- Container performance
- Application metrics
- Alert management

### Log Aggregation
Integration with logging systems:
- Structured JSON logging
- Log forwarding to external systems
- Real-time log streaming

## Troubleshooting

### Common Issues

1. **Web interface not accessible:**
   - Check if the container is running: `docker ps`
   - Verify port mapping: `docker port obs-web-manager`
   - Check firewall settings

2. **Container management not working:**
   - Ensure Docker socket is mounted correctly
   - Check container permissions
   - Verify Docker daemon is running

3. **Real-time updates not working:**
   - Check WebSocket connection in browser console
   - Verify SocketIO is properly configured
   - Check for proxy/firewall blocking WebSocket

### Logs and Debugging

1. **View application logs:**
   ```bash
   ./start-web-manager.sh logs
   ```

2. **Check container status:**
   ```bash
   ./start-web-manager.sh status
   ```

3. **Debug mode:**
   Set `FLASK_DEBUG=true` in environment variables

## Development

### Adding New Features

1. **Backend (Flask):**
   - Add new routes in `app.py`
   - Implement API endpoints
   - Add WebSocket events if needed

2. **Frontend (Templates):**
   - Create new templates in `templates/`
   - Add navigation links in `base.html`
   - Implement JavaScript functionality

3. **Testing:**
   - Test API endpoints
   - Verify WebSocket functionality
   - Check responsive design

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the OBS Docker project and follows the same licensing terms.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue in the project repository
4. Consult the main OBS Docker documentation
