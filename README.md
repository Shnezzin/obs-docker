# OBS Docker - Professional Streaming & Recording Platform

A comprehensive, enterprise-ready Docker solution for OBS Studio with advanced management capabilities, multi-architecture support, and professional-grade features. Perfect for content creators, streamers, broadcasters, and organizations requiring scalable OBS deployments.

## 🚀 Key Features

### Core Platform
- 🎥 **OBS Studio 31.1.1** - Latest version with all features
- 🖥️ **Multiple Desktop Environments** - LXDE, XFCE, KDE, GNOME support
- 🔗 **RDP Access** - Secure remote desktop connectivity
- 🐧 **Ubuntu 24.04 LTS** - Latest stable and secure base
- 🏗️ **Multi-Architecture** - AMD64, ARM64, ARM/v7 support
- ⚡ **GPU Acceleration** - Optional NVIDIA, Intel, AMD support

### Advanced Management
- 🌐 **Web Management Interface** - Comprehensive dashboard at `http://localhost:8080`
- 📊 **Real-time Monitoring** - System metrics, performance analytics
- 🔧 **Plugin Management** - Automated installation and updates
- ☁️ **Cloud Integration** - AWS S3, Google Cloud Storage support
- 🛡️ **Enhanced Security** - SSL/TLS, VPN, MFA capabilities
- 📦 **Multi-Instance Orchestration** - Scale to multiple containers
- 💾 **Automated Backup & Recovery** - Scheduled, encrypted backups
- ⚙️ **Performance Profiles** - Optimized configurations for different use cases

## 🚀 Quick Start

### Option 1: Web Management Interface (Recommended)

```bash
# Clone the repository
git clone https://github.com/Shnezzin/obs-docker.git
cd obs-docker

# Start the web management interface
cd web/
chmod +x start-web-manager.sh
./start-web-manager.sh start

# Access the web dashboard
# Open http://localhost:8080 in your browser
```

### Option 2: Basic Container Setup

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
docker build -t obs-docker .

# Run with basic configuration
docker run -d \
  --name obs-studio \
  -p 3389:3389 \
  -v $(pwd)/home:/home:rw \
  -e USER=myuser \
  -e PASSWD=MySecurePassword123! \
  -e DESKTOP_ENV=lxde \
  -e ENABLE_GPU=false \
  obs-docker
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USER` | `developer` | Username for RDP login |
| `PASSWD` | `SecurePassword123!` | Password for RDP login (change in production!) |
| `GROUP` | Same as USER | Primary group name |
| `LOCALE` | `en_US.UTF-8` | System locale (language/region) |
| `TIMEZONE` | `UTC` | System timezone |
| `OBS_VERSION` | `31.1.1` | OBS Studio version to install |
| `UBUNTU_VERSION` | `24.04` | Ubuntu base image version |
| `DESKTOP_ENV` | `lxde` | Desktop environment (lxde/xfce/kde/gnome) |
| `ENABLE_GPU` | `false` | Enable GPU acceleration support |

### Ports

- `3389` - RDP port for remote desktop access
- `8080` - Web management interface
- `4455` - Additional port for OBS plugins
- `9090` - Prometheus metrics (monitoring stack)
- `3000` - Grafana dashboard (monitoring stack)

### Volumes

- `/home` - User home directories (persistence)
- `/opt/obs-config` - OBS and system configuration
- `/opt/obs-instances` - Multi-instance data
- `/opt/obs-backups` - Backup storage
- `/scripts` - Management scripts

## 🌐 Web Management Interface

The comprehensive web dashboard provides complete control over your OBS Docker environment:

### Features
- **Dashboard** - Real-time system metrics and container overview
- **Container Management** - Start, stop, restart containers with live monitoring
- **Instance Management** - Create and manage multiple OBS instances
- **Plugin Management** - Install and configure OBS plugins
- **Monitoring & Analytics** - Performance tracking and alerting
- **Backup & Recovery** - Automated backup scheduling and restoration
- **Settings** - System configuration and security management

### Access
```bash
# Start the web interface
cd web/
./start-web-manager.sh start

# Open in browser
http://localhost:8080
```

## 🖥️ Direct RDP Access

### Windows
1. Open "Remote Desktop Connection"
2. Enter `localhost:3389`
3. Use the configured username/password

### macOS
1. Install Microsoft Remote Desktop from App Store
2. Add connection to `localhost:3389`
3. Use the configured username/password

### Linux
```bash
# Using rdesktop
rdesktop localhost:3389

# Using xfreerdp
xfreerdp /v:localhost:3389 /u:developer
```

## 🚀 Advanced Features

### Multi-Instance Management
```bash
# Create multiple OBS instances
./scripts/instance-manager.sh create streaming-1 streaming developer password123
./scripts/instance-manager.sh create recording-1 recording developer password123

# Scale instances
./scripts/instance-manager.sh scale streaming 3

# List all instances
./scripts/instance-manager.sh list
```

### Plugin Management
```bash
# Install popular plugins
./scripts/plugin-manager.sh install obs-webrtc
./scripts/plugin-manager.sh install noise-suppression
./scripts/plugin-manager.sh install source-record

# List installed plugins
./scripts/plugin-manager.sh list
```

### Performance Optimization
```bash
# Apply performance profiles
./scripts/performance-profiles.sh apply streaming    # For live streaming
./scripts/performance-profiles.sh apply recording   # For high-quality recording
./scripts/performance-profiles.sh apply gpu-accelerated  # For GPU systems
./scripts/performance-profiles.sh apply low-resource     # For limited resources
```

### Cloud Integration
```bash
# Configure AWS S3 backup
./scripts/cloud-integration.sh configure aws s3 my-obs-bucket

# Configure Google Cloud Storage
./scripts/cloud-integration.sh configure gcp gs my-obs-bucket

# Enable auto-upload of recordings
./scripts/cloud-integration.sh enable-upload
```

### Security Management
```bash
# Enable SSL/TLS for RDP
./scripts/security-manager.sh enable-ssl

# Setup VPN (WireGuard)
./scripts/security-manager.sh setup-vpn

# Enable Multi-Factor Authentication
./scripts/security-manager.sh enable-mfa

# Run security audit
./scripts/security-manager.sh audit
```

### Backup & Recovery
```bash
# Create backups
./scripts/backup-recovery.sh create full
./scripts/backup-recovery.sh create incremental

# Schedule automated backups
./scripts/backup-recovery.sh schedule daily full

# Restore from backup
./scripts/backup-recovery.sh restore backup-20240120-full.tar.gz
```

### Desktop Environment Management
```bash
# Switch desktop environments
./scripts/desktop-manager.sh install xfce
./scripts/desktop-manager.sh switch xfce

# Available environments: lxde, xfce, kde, gnome
./scripts/desktop-manager.sh list
```

## 📊 Monitoring & Analytics

### Built-in Monitoring Stack
```bash
# Start monitoring services
cd monitoring/
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
# AlertManager: http://localhost:9093
```

### Real-time Metrics
- System resource usage (CPU, Memory, Disk, Network)
- Container performance metrics
- OBS-specific metrics and alerts
- Custom dashboards and visualizations

## 🛠️ Troubleshooting

### Web Interface Issues
```bash
# Check web manager status
./web/start-web-manager.sh status

# View web manager logs
./web/start-web-manager.sh logs

# Restart web interface
./web/start-web-manager.sh restart
```

### Container Issues
```bash
# View container logs
docker logs obs-studio

# Check container health
docker inspect obs-studio | grep Health

# Access container shell
docker exec -it obs-studio /bin/bash

# Run health check manually
docker exec -it obs-studio /scripts/health-check.sh
```

### Common Solutions

**Web interface not accessible:**
- Ensure port 8080 is not blocked
- Check if web container is running: `docker ps | grep web-manager`
- Verify Docker socket permissions

**RDP connection fails:**
- Check port 3389 availability
- Verify container is running and healthy
- Check firewall settings

**OBS won't start:**
- Ensure sufficient resources (minimum 2GB RAM)
- Check GPU acceleration settings if enabled
- Verify desktop environment installation

**Plugin installation fails:**
- Check internet connectivity
- Verify plugin compatibility
- Check available disk space

**Performance issues:**
- Apply appropriate performance profile
- Monitor resource usage via web interface
- Consider enabling GPU acceleration
- Scale to multiple instances if needed

## 🏗️ Development & Building

### Multi-Architecture Builds
```bash
# Build for all supported architectures
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  --build-arg OBS_VERSION=31.1.1 \
  --build-arg UBUNTU_VERSION=24.04 \
  --build-arg DESKTOP_ENV=lxde \
  --build-arg ENABLE_GPU=false \
  -t obs-docker:latest .

# Build with GPU support
docker build \
  --build-arg ENABLE_GPU=true \
  --build-arg DESKTOP_ENV=kde \
  -t obs-docker:gpu .

# Using Makefile (recommended)
make build          # Single architecture
make build-multi    # Multi-architecture
make build-gpu      # With GPU support
make test          # Run tests
```

### Custom Configuration
```bash
# Build with custom settings
docker build \
  --build-arg OBS_VERSION=31.1.1 \
  --build-arg UBUNTU_VERSION=24.04 \
  --build-arg LOCALE=de_DE.UTF-8 \
  --build-arg TIMEZONE=Europe/Berlin \
  --build-arg DESKTOP_ENV=xfce \
  -t obs-docker:custom .
```

### Development Environment
```bash
# Clone and setup development environment
git clone https://github.com/Shnezzin/obs-docker.git
cd obs-docker

# Install development dependencies
pip install -r web/requirements.txt

# Run tests
./tests/test-container.sh

# Start development web interface
cd web/
python app.py
```

## 🔒 Security & Production

### Security Best Practices
- **Change default passwords** - Never use default credentials in production
- **Enable SSL/TLS** - Use `./scripts/security-manager.sh enable-ssl`
- **Setup VPN access** - Use `./scripts/security-manager.sh setup-vpn`
- **Enable MFA** - Use `./scripts/security-manager.sh enable-mfa`
- **Regular audits** - Run `./scripts/security-manager.sh audit`
- **Network isolation** - Use Docker networks and firewall rules
- **Regular updates** - Keep base images and dependencies updated

### Production Deployment
```bash
# Production-ready deployment
docker-compose -f docker-compose.prod.yml up -d

# With monitoring stack
docker-compose -f docker-compose.yml -f monitoring/docker-compose.monitoring.yml up -d

# Enable all security features
./scripts/security-manager.sh enable-all
```

## 📋 Project Structure

```
obs-docker/
├── Dockerfile                 # Main container definition
├── docker-compose.yml         # Basic deployment
├── docker-entrypoint.sh       # Container startup script
├── scripts/                   # Management scripts
│   ├── plugin-manager.sh      # Plugin management
│   ├── cloud-integration.sh   # Cloud storage setup
│   ├── performance-profiles.sh # Performance optimization
│   ├── security-manager.sh    # Security configuration
│   ├── desktop-manager.sh     # Desktop environment management
│   ├── instance-manager.sh    # Multi-instance orchestration
│   ├── backup-recovery.sh     # Backup and recovery
│   └── health-check.sh        # Health monitoring
├── web/                       # Web management interface
│   ├── app.py                 # Flask application
│   ├── templates/             # HTML templates
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile.web         # Web interface container
│   └── start-web-manager.sh   # Web interface startup
├── monitoring/                # Monitoring stack
│   ├── docker-compose.monitoring.yml
│   ├── prometheus/            # Metrics collection
│   └── grafana/              # Dashboards
├── tests/                     # Test scripts
└── .github/                   # CI/CD workflows
```

## 🤝 Contributing

### Development Workflow
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes
4. **Test** thoroughly using provided test scripts
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to the branch (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

### Testing
```bash
# Run all tests
./tests/test-container.sh

# Test specific features
./scripts/health-check.sh
./tests/test-plugins.sh
./tests/test-security.sh
```

### Code Standards
- Follow existing code style and conventions
- Add comprehensive documentation for new features
- Include tests for new functionality
- Update README and documentation as needed

## 📄 License

This project is open source under the MIT License. See individual component licenses for specific terms.

## 🆘 Support & Community

### Getting Help
- **Documentation** - Check this README and `/web/README.md`
- **Troubleshooting** - Review the troubleshooting section above
- **Logs** - Check container and application logs
- **Issues** - Open an issue on GitHub with detailed information
- **Discussions** - Join community discussions for questions and ideas

### Reporting Issues
When reporting issues, please include:
- System information (OS, Docker version, architecture)
- Container logs (`docker logs container-name`)
- Steps to reproduce the issue
- Expected vs actual behavior
- Configuration details (environment variables, etc.)

### Feature Requests
We welcome feature requests! Please:
- Check existing issues and discussions first
- Provide detailed use case and requirements
- Consider contributing the feature yourself

---

**🎉 Thank you for using OBS Docker!** 

This project transforms a simple OBS Studio container into a comprehensive, enterprise-ready streaming and recording platform. Whether you're a content creator, broadcaster, or organization, OBS Docker provides the tools and scalability you need.

**Star ⭐ the project if you find it useful!**
