# OBS Docker - Professional Streaming & Recording Platform

A comprehensive, enterprise-ready Docker solution for OBS Studio with advanced web management, multi-architecture support, and professional-grade features. Perfect for content creators, streamers, broadcasters, and organizations requiring scalable OBS deployments with remote desktop access.

## 🚀 Key Features

### Core Platform
- 🎥 **OBS Studio 31.1.1** - Latest version with all features
- 🖥️ **Multiple Desktop Environments** - LXDE, XFCE, KDE, GNOME support
- 🔗 **RDP & VNC Access** - Secure remote desktop connectivity
- 🐧 **Ubuntu 24.04 LTS** - Latest stable and secure base
- 🏗️ **Multi-Architecture** - AMD64, ARM64, ARM/v7 support
- ⚡ **GPU Acceleration** - Optional NVIDIA, Intel, AMD support

### Advanced Web Management
- 🌐 **Comprehensive Web Interface** - Full-featured dashboard at `http://localhost:8080`
- 📊 **Real-time Monitoring** - Live system metrics, performance analytics, and alerts
- 🔧 **Plugin Management** - Automated installation, updates, and configuration
- 📦 **Multi-Instance Orchestration** - Create and manage multiple OBS containers
- 💾 **Automated Backup & Recovery** - Scheduled, encrypted backups with restoration
- ⚙️ **Performance Profiles** - Optimized configurations for streaming, recording, and more
- 🛡️ **Enhanced Security** - SSL/TLS, CSRF protection, rate limiting, and audit tools
- ☁️ **Cloud Integration** - AWS S3, Google Cloud Storage support

### Production-Ready Features
- 🔒 **Enterprise Security** - Multi-factor authentication, VPN support, security audits
- 📈 **Scalability** - Horizontal scaling, load balancing, resource management
- 🔍 **Comprehensive Monitoring** - Prometheus metrics, Grafana dashboards, alerting
- 🧪 **Testing Suite** - Automated functionality and connectivity testing
- 📚 **Complete Documentation** - Detailed guides, API documentation, troubleshooting

## 🚀 Quick Start

### Option 1: Web Management Interface (Recommended)

```bash
# Clone the repository
git clone https://github.com/Shnezzin/obs-docker.git
cd obs-docker

# Build the OBS Docker image
docker build -t obs-docker:latest .

# Start the web management interface
cd web/
chmod +x start-web-manager.sh
./start-web-manager.sh start

# Access the web dashboard
# Open http://localhost:8080 in your browser
```

### Option 2: Docker Compose (Simple Setup)

```bash
# Using Docker Compose
docker-compose up -d

# Connect via RDP to localhost:3389
# Username: developer
# Password: SecurePassword123!
```

### Option 3: Manual Docker Commands

```bash
# Build the image
docker build -t obs-docker:latest .

# Run with basic configuration
docker run -d \
  --name obs-studio \
  -p 3389:3389 \
  -p 5900:5900 \
  -v obs-config:/opt/obs-config \
  -e DEFAULT_USER=myuser \
  -e DEFAULT_PASSWD=MySecurePassword123! \
  -e DESKTOP_ENV=lxde \
  -e ENABLE_GPU=false \
  obs-docker:latest
```

## 🌐 Web Management Interface

The comprehensive web dashboard provides complete control over your OBS Docker environment with a modern, responsive interface.

### 📄 Available Pages

| Page | URL | Description |
|------|-----|-------------|
| **Dashboard** | `/` | System overview, metrics, container status |
| **Instances** | `/instances` | Create and manage OBS instances |
| **Containers** | `/containers` | Docker container management |
| **Images** | `/images` | Docker image management and registry |
| **Plugins** | `/plugins` | OBS plugin installation and management |
| **Monitoring** | `/monitoring` | Real-time system monitoring and alerts |
| **Backups** | `/backups` | Backup creation, scheduling, and restoration |
| **Settings** | `/settings` | System configuration and preferences |

### 🎛️ Key Features

- **Real-time Updates** - Live metrics and status updates via WebSocket
- **Responsive Design** - Works on desktop, tablet, and mobile devices
- **Dark/Light Theme** - Modern UI with professional styling
- **Interactive Charts** - Performance monitoring with Chart.js
- **Bulk Operations** - Manage multiple containers simultaneously
- **Advanced Search** - Filter and search across all resources
- **Export/Import** - Configuration backup and restoration
- **Security Features** - CSRF protection, rate limiting, audit logging

### 🚀 Quick Setup

**Method A: Docker (Recommended)**
```bash
cd web/
./start-web-manager.sh start
# Open http://localhost:8080
```

**Method B: Local Python**
```bash
cd web/
./start-web-manager.sh setup    # Install dependencies
./start-web-manager.sh local    # Run locally
# Open http://localhost:8080
```

**Available Commands:**
```bash
./start-web-manager.sh start     # Start with Docker
./start-web-manager.sh stop      # Stop web manager
./start-web-manager.sh restart   # Restart web manager
./start-web-manager.sh status    # Check status
./start-web-manager.sh logs      # View logs
./start-web-manager.sh setup     # Setup environment
./start-web-manager.sh local     # Run locally
./start-web-manager.sh help      # Show all commands
```

## 🖥️ Remote Desktop Access

### RDP Connectivity (Primary)
**Supported on all platforms with excellent performance**

**Windows:**
1. Open "Remote Desktop Connection"
2. Enter `localhost:<port>` (port shown in web interface)
3. Use container credentials

**macOS:**
1. Install Microsoft Remote Desktop from App Store
2. Add connection to `localhost:<port>`
3. Use container credentials

**Linux:**
```bash
# Using xfreerdp (recommended)
xfreerdp /v:localhost:<port> /u:<username>

# Using rdesktop
rdesktop localhost:<port>

# Using Remmina (GUI)
remmina
```

### VNC Connectivity (Alternative)
**Available as backup option**

```bash
# Default VNC ports: 5900, 5901
# Connect using any VNC client:
# - TigerVNC Viewer
# - RealVNC
# - Built-in Screen Sharing (macOS)
```

### 🔧 Connection Troubleshooting

**If RDP connection fails:**
1. Check container status in web interface
2. Verify assigned port number
3. Test port connectivity: `telnet localhost <port>`
4. Use "Debug RDP" button in web interface
5. Check container logs for errors

**Connection Details:**
- **Host:** `localhost` or `127.0.0.1`
- **Port:** Displayed in web interface (usually 3389 or auto-assigned)
- **Username:** Specified during container creation
- **Password:** Specified during container creation
- **Desktop:** LXDE (default), XFCE, KDE, or GNOME

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_USER` | `developer` | Username for RDP/VNC login |
| `DEFAULT_PASSWD` | `SecurePassword123!` | Password for remote access |
| `DESKTOP_ENV` | `lxde` | Desktop environment (lxde/xfce/kde/gnome) |
| `LOCALE` | `en_US.UTF-8` | System locale (language/region) |
| `TIMEZONE` | `UTC` | System timezone |
| `OBS_VERSION` | `31.1.1` | OBS Studio version to install |
| `UBUNTU_VERSION` | `24.04` | Ubuntu base image version |
| `ENABLE_GPU` | `false` | Enable GPU acceleration support |
| `FLASK_SECRET_KEY` | `auto-generated` | Web interface security key |
| `CSRF_ENABLED` | `true` | Enable CSRF protection |
| `RATE_LIMIT` | `200 per day;50 per hour` | API rate limiting |

### Port Configuration

| Port | Service | Description |
|------|---------|-------------|
| `3389` | RDP | Remote Desktop Protocol access |
| `5900` | VNC | VNC remote desktop access |
| `8080` | Web UI | Web management interface |
| `9090` | Prometheus | Metrics collection (optional) |
| `3000` | Grafana | Monitoring dashboards (optional) |

### Volume Mounts

| Volume | Purpose | Description |
|--------|---------|-------------|
| `/opt/obs-config` | Configuration | OBS and system settings |
| `/opt/obs-instances` | Instance Data | Multi-instance storage |
| `/opt/obs-backups` | Backups | Backup storage location |
| `/home` | User Data | User home directories |

## 🚀 Advanced Features

### 📦 Multi-Instance Management

Create and manage multiple OBS containers with different configurations:

```bash
# Via Web Interface (Recommended)
# 1. Go to http://localhost:8080/instances
# 2. Click "Create Instance"
# 3. Configure name, template, user, password
# 4. Click "Create Instance"

# Via Command Line
./scripts/instance-manager.sh create streaming-1 streaming developer password123
./scripts/instance-manager.sh create recording-1 recording developer password123
./scripts/instance-manager.sh list
```

**Available Templates:**
- **Streaming** - Optimized for live streaming (6000 kbps, 60fps)
- **Recording** - High-quality local recording (50000 kbps, 60fps)
- **Low Resource** - Minimal resource usage (2500 kbps, 30fps)
- **GPU Accelerated** - Hardware acceleration enabled

### 🔌 Plugin Management

Install and manage OBS plugins through the web interface:

```bash
# Popular plugins available:
# - OBS WebRTC (WebRTC streaming)
# - Noise Suppression (AI-powered audio filtering)
# - Source Record (Individual source recording)
# - Browser Source (Web content integration)
# - StreamFX (Advanced effects and filters)

# Via Web Interface
# Go to http://localhost:8080/plugins

# Via Command Line
./scripts/plugin-manager.sh install obs-webrtc
./scripts/plugin-manager.sh list
```

### 📊 Performance Optimization

Apply performance profiles based on your use case:

```bash
# Via Web Interface
# Go to http://localhost:8080/settings

# Via Command Line
./scripts/performance-profiles.sh apply streaming      # Live streaming
./scripts/performance-profiles.sh apply recording     # High-quality recording
./scripts/performance-profiles.sh apply gpu-accelerated  # GPU systems
./scripts/performance-profiles.sh apply low-resource     # Limited resources
```

### 💾 Backup & Recovery

Automated backup system with scheduling and cloud integration:

```bash
# Via Web Interface
# Go to http://localhost:8080/backups

# Via Command Line
./scripts/backup-recovery.sh create full
./scripts/backup-recovery.sh schedule daily full
./scripts/backup-recovery.sh restore backup-20240120-full.tar.gz
```

**Backup Types:**
- **Full** - Complete system backup
- **Incremental** - Changes since last backup
- **Differential** - Changes since last full backup

### ☁️ Cloud Integration

Connect to cloud storage for automatic uploads and backups:

```bash
# AWS S3 Integration
./scripts/cloud-integration.sh configure aws s3 my-obs-bucket

# Google Cloud Storage
./scripts/cloud-integration.sh configure gcp gs my-obs-bucket

# Enable auto-upload
./scripts/cloud-integration.sh enable-upload
```

### 🛡️ Security Features

Enterprise-grade security features:

```bash
# Enable SSL/TLS
./scripts/security-manager.sh enable-ssl

# Setup VPN (WireGuard)
./scripts/security-manager.sh setup-vpn

# Enable Multi-Factor Authentication
./scripts/security-manager.sh enable-mfa

# Run security audit
./scripts/security-manager.sh audit
```

**Security Features:**
- CSRF protection enabled by default
- Rate limiting on API endpoints
- Secure session management
- Input validation and sanitization
- Security audit tools
- SSL/TLS support
- VPN integration
- Multi-factor authentication

## 📊 Monitoring & Analytics

### Built-in Monitoring

Access real-time monitoring at `http://localhost:8080/monitoring`:

- **System Metrics** - CPU, Memory, Disk, Network usage
- **Container Metrics** - Per-container resource usage
- **Performance Charts** - Historical data visualization
- **Alerts** - Configurable threshold-based alerts
- **Logs** - Centralized log viewing and filtering

### External Monitoring Stack

```bash
# Start Prometheus + Grafana stack
cd monitoring/
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# AlertManager: http://localhost:9093
```

## 🧪 Testing & Validation

### Automated Testing Suite

Comprehensive testing tools to verify functionality:

```bash
# Test all web functionality
python test_web_functionality.py --url http://localhost:8080

# Test VNC/RDP connectivity
python test_vnc_rdp_connectivity.py --url http://localhost:8080

# Run container health checks
docker exec obs-container /scripts/health-check.sh
```

### Manual Testing Checklist

1. **Web Interface** - All pages load and function correctly
2. **Container Creation** - Instances can be created and started
3. **RDP Connectivity** - Remote desktop access works
4. **VNC Connectivity** - VNC access works (if enabled)
5. **Plugin Management** - Plugins can be installed and managed
6. **Backup/Restore** - Backup and restoration functions work
7. **Monitoring** - Real-time metrics display correctly
8. **Security** - Authentication and authorization work

## 🛠️ Troubleshooting

### Common Issues

**Web interface not accessible:**
```bash
# Check if web manager is running
./web/start-web-manager.sh status

# Check logs
./web/start-web-manager.sh logs

# Restart web interface
./web/start-web-manager.sh restart
```

**Docker service not available (503 error):**
```bash
# Check Docker daemon
docker info

# Check Docker socket permissions
ls -la /var/run/docker.sock

# Add user to docker group
sudo usermod -aG docker $USER
```

**RDP connection refused:**
```bash
# Check container status
docker ps | grep obs

# Test port connectivity
telnet localhost <port>

# Debug RDP services (via web interface)
# Go to Containers page �� Click "Debug RDP" button

# Check container logs
docker logs <container-name>
```

**Container creation fails:**
```bash
# Check Docker image
docker images | grep obs-docker

# Build image if missing
docker build -t obs-docker:latest .

# Check available resources
docker system df
```

### Debug Tools

**Web Interface Debug Features:**
- Container log viewer with auto-refresh
- RDP connection debugger
- Desktop configuration fixer
- System information display
- Health check runner

**Command Line Tools:**
```bash
# Health check
./scripts/health-check.sh

# System cleanup
./scripts/cleanup.sh

# Make scripts executable
./scripts/make-executable.sh
```

## 🏗️ Development & Building

### Building from Source

```bash
# Clone repository
git clone https://github.com/Shnezzin/obs-docker.git
cd obs-docker

# Build for current architecture
docker build -t obs-docker:latest .

# Build with custom configuration
docker build \
  --build-arg OBS_VERSION=31.1.1 \
  --build-arg DESKTOP_ENV=xfce \
  --build-arg ENABLE_GPU=true \
  -t obs-docker:custom .
```

### Multi-Architecture Builds

```bash
# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  --build-arg OBS_VERSION=31.1.1 \
  --build-arg UBUNTU_VERSION=24.04 \
  -t obs-docker:multi-arch .
```

### Development Environment

```bash
# Setup development environment
pip install -r web/requirements.txt

# Run tests
python test_web_functionality.py
python test_vnc_rdp_connectivity.py

# Start development server
cd web/
python app.py --no-ssl --port 8080
```

## 🔒 Security & Production

### Production Deployment

```bash
# Production-ready deployment
docker-compose -f docker-compose.prod.yml up -d

# Enable all security features
./scripts/security-manager.sh enable-all

# Run security audit
./scripts/security-manager.sh audit
```

### Security Best Practices

1. **Change Default Passwords** - Never use default credentials in production
2. **Enable SSL/TLS** - Use HTTPS for web interface
3. **Configure Firewall** - Restrict access to necessary ports only
4. **Regular Updates** - Keep base images and dependencies updated
5. **Monitor Logs** - Enable centralized logging and monitoring
6. **Backup Regularly** - Implement automated backup strategies
7. **Network Isolation** - Use Docker networks and VPNs
8. **Access Control** - Implement proper authentication and authorization

### Environment Configuration

Create a `.env` file for production:

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

**Key Production Settings:**
```env
FLASK_SECRET_KEY=your-secret-key-here
DEFAULT_PASSWD=YourSecurePassword123!
CSRF_ENABLED=true
RATE_LIMIT=100 per day;20 per hour
ENABLE_SSL=true
LOG_LEVEL=INFO
```

## 📋 Project Structure

```
obs-docker/
├── Dockerfile                    # Main container definition
├── docker-compose.yml            # Basic deployment
├── docker-entrypoint.sh          # Container startup script
├── .env.example                  # Environment configuration template
├── scripts/                      # Management scripts
│   ├── health-check.sh           # Health monitoring
│   ├── cleanup.sh                # System cleanup
│   ├── plugin-manager.sh         # Plugin management
│   ├── performance-profiles.sh   # Performance optimization
│   ├── security-manager.sh       # Security configuration
│   ├── backup-recovery.sh        # Backup and recovery
│   └── make-executable.sh        # Script permissions
├── web/                          # Web management interface
│   ├── app.py                    # Flask application
│   ├── templates/                # HTML templates
│   │   ├── base.html             # Base template
│   │   ├── dashboard.html        # Dashboard page
│   │   ├── instances.html        # Instance management
│   │   ├── containers.html       # Container management
│   │   ├── images.html           # Image management
│   │   ├── plugins.html          # Plugin management
│   │   ├── monitoring.html       # Monitoring dashboard
│   │   ├── backups.html          # Backup management
│   │   └── settings.html         # Settings page
│   ├── static/js/                # JavaScript files
│   │   ├── api.js                # API helper functions
│   │   └── csrf.js               # CSRF protection
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile.web            # Web interface container
│   └── start-web-manager.sh      # Web interface startup
├── monitoring/                   # Monitoring stack
│   ├── docker-compose.monitoring.yml
│   ├── prometheus/               # Metrics collection
│   └── grafana/                  # Dashboards
├── tests/                        # Test scripts
│   ├── test_web_functionality.py # Web interface tests
│   └── test_vnc_rdp_connectivity.py # Connectivity tests
├── FIXES_APPLIED.md              # Documentation of fixes
├── WEB_FUNCTIONALITY_CHECKLIST.md # Functionality checklist
└── .github/                      # CI/CD workflows
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes and test thoroughly
4. **Run** the test suite (`python test_web_functionality.py`)
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to the branch (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

### Testing

```bash
# Run all tests
python test_web_functionality.py
python test_vnc_rdp_connectivity.py

# Test specific features
./scripts/health-check.sh
docker exec obs-container /scripts/health-check.sh
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Community

### Getting Help

- **Documentation** - Check this README and the `/web/README.md`
- **Functionality Checklist** - See `WEB_FUNCTIONALITY_CHECKLIST.md`
- **Troubleshooting** - Review the troubleshooting section above
- **Test Results** - Run the provided test scripts
- **Issues** - Open an issue on GitHub with detailed information
- **Discussions** - Join community discussions for questions and ideas

### Reporting Issues

When reporting issues, please include:

1. **System Information** - OS, Docker version, architecture
2. **Test Results** - Output from `test_web_functionality.py`
3. **Container Logs** - `docker logs <container-name>`
4. **Web Interface Logs** - `./web/start-web-manager.sh logs`
5. **Steps to Reproduce** - Detailed reproduction steps
6. **Expected vs Actual Behavior** - What should happen vs what happens
7. **Configuration** - Environment variables, docker-compose.yml, etc.

### Feature Requests

We welcome feature requests! Please:

- Check existing issues and discussions first
- Provide detailed use case and requirements
- Consider contributing the feature yourself
- Include mockups or examples if applicable

---

## 🎉 Success Stories

**OBS Docker** transforms a simple OBS Studio container into a comprehensive, enterprise-ready streaming and recording platform. Whether you're a:

- **Content Creator** - Stream and record with professional quality
- **Broadcaster** - Scale to multiple channels and platforms
- **Organization** - Deploy OBS at scale with centralized management
- **Developer** - Build streaming applications with our API

**OBS Docker provides the tools, scalability, and reliability you need.**

### 🌟 Key Achievements

- ✅ **100% Web-Managed** - Complete control via web interface
- ✅ **Production-Ready** - Enterprise security and monitoring
- ✅ **Multi-Platform** - Works on AMD64, ARM64, ARM/v7
- ✅ **Fully Tested** - Comprehensive test suite included
- ✅ **Well Documented** - Complete guides and API documentation
- ✅ **Community Driven** - Open source with active development

### 🚀 Quick Success Path

1. **Clone & Build** - `git clone` → `docker build`
2. **Start Web Interface** - `./start-web-manager.sh start`
3. **Create Instance** - Use web interface at `http://localhost:8080`
4. **Connect via RDP** - Use any RDP client with assigned port
5. **Start Streaming** - OBS Studio ready to use!

---

**⭐ Star the project if you find it useful!**

**🤝 Contribute to make it even better!**

**📢 Share with the community!**

---

*Last Updated: January 2024 | Version: 2.0.0 | Status: Production Ready*