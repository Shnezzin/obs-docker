# Docker Socket Configuration for OBS Web Manager

## Overview

The OBS Web Manager requires access to the Docker daemon to create, manage, and monitor real OBS container instances. This document explains how to configure Docker socket access securely.

## Prerequisites

- Docker installed and running on the host system
- Docker Compose (included with Docker Desktop)
- OBS Docker image built (`obs-docker:latest`)

## Quick Start

### 1. Build the OBS Docker Image

First, build the main OBS Docker image that will be used for instances:

```bash
# From the project root directory
docker build -t obs-docker:latest .
```

### 2. Start the Web Manager

```bash
# Navigate to the web directory
cd web

# Start the web manager with Docker socket access
docker-compose -f docker-compose.web.yml up -d
```

### 3. Verify Docker Access

Check the web manager logs to ensure Docker connection is working:

```bash
docker logs obs-web-manager
```

You should see: `Docker client initialized successfully`

## Docker Socket Configuration

### Linux/macOS Configuration

The `docker-compose.web.yml` is pre-configured for Linux/macOS:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

### Windows Configuration

For Windows with Docker Desktop, the socket path is already configured:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

If you encounter issues on Windows, you may need to use the named pipe:

```yaml
volumes:
  - //./pipe/docker_engine://./pipe/docker_engine
```

## Security Considerations

### Production Deployment

**⚠️ IMPORTANT**: Mounting the Docker socket gives the container full access to the Docker daemon, which is equivalent to root access on the host system.

For production deployments, consider these security measures:

1. **Docker Socket Proxy** (Recommended):
   ```bash
   # Use a Docker socket proxy to limit API access
   docker run -d \
     --name docker-socket-proxy \
     -v /var/run/docker.sock:/var/run/docker.sock:ro \
     -p 2375:2375 \
     tecnativa/docker-socket-proxy
   ```

2. **Docker API over TCP with TLS**:
   Configure Docker daemon to accept secure TCP connections.

3. **Rootless Docker**:
   Use Docker in rootless mode for additional security.

### User Permissions

The web manager container runs as a non-root user (`webuser`) and is added to the `docker` group for socket access:

```dockerfile
RUN groupadd -g 999 docker || true && \
    useradd -m -u 1000 webuser && \
    usermod -aG docker webuser
```

## Instance Management Features

With Docker socket access enabled, the web manager provides:

### Real Container Operations

- **Create Instance**: Creates real OBS containers with:
  - Automatic port assignment (RDP: 3389, VNC: 5900)
  - Persistent volumes for OBS configuration
  - Network isolation
  - Resource management

- **Start/Stop/Restart**: Full container lifecycle management
- **Remove**: Complete cleanup including volumes
- **Scale**: Create multiple instances simultaneously

### Instance Information

- Real-time container status
- Port mappings and access URLs
- Resource usage monitoring
- Container logs access
- Uptime tracking

## Troubleshooting

### Common Issues

1. **"Docker service not available" Error**:
   ```bash
   # Check if Docker is running
   docker ps
   
   # Check web manager logs
   docker logs obs-web-manager
   
   # Verify socket mount
   docker exec obs-web-manager ls -la /var/run/docker.sock
   ```

2. **Permission Denied Errors**:
   ```bash
   # Check Docker socket permissions
   ls -la /var/run/docker.sock
   
   # Ensure docker group exists and has correct GID
   getent group docker
   ```

3. **"OBS Docker image not found" Error**:
   ```bash
   # Build the main OBS image
   docker build -t obs-docker:latest .
   
   # Verify image exists
   docker images | grep obs-docker
   ```

### Debug Mode

Enable debug logging in the web manager:

```yaml
environment:
  - FLASK_DEBUG=true
  - LOG_LEVEL=DEBUG
```

## Network Configuration

The web manager creates and uses the `obs-network` bridge network:

```yaml
networks:
  obs-network:
    driver: bridge
    name: obs-network
```

All OBS instances are connected to this network for isolation and communication.

## Volume Management

Each OBS instance gets dedicated volumes:

- `obs-config-{instance_name}`: OBS configuration files
- `obs-scenes-{instance_name}`: User-specific OBS scenes and settings

These volumes persist even when containers are removed (unless explicitly cleaned up).

## API Endpoints

With Docker socket access, these endpoints provide real functionality:

- `POST /api/instances/create` - Create new OBS container
- `GET /api/instances` - List all OBS containers
- `POST /api/instances/{name}/start` - Start container
- `POST /api/instances/{name}/stop` - Stop container
- `POST /api/instances/{name}/restart` - Restart container
- `DELETE /api/instances/{name}/remove` - Remove container and volumes
- `POST /api/instances/scale` - Scale instances up/down

## Monitoring and Logs

Access container logs through the web interface or CLI:

```bash
# View instance logs
docker logs obs-{instance_name}

# Follow logs in real-time
docker logs -f obs-{instance_name}
```

## Backup and Recovery

Instance data is stored in Docker volumes. To backup:

```bash
# Backup instance configuration
docker run --rm -v obs-config-{instance_name}:/data -v $(pwd):/backup alpine tar czf /backup/obs-config-{instance_name}.tar.gz -C /data .

# Backup instance scenes
docker run --rm -v obs-scenes-{instance_name}:/data -v $(pwd):/backup alpine tar czf /backup/obs-scenes-{instance_name}.tar.gz -C /data .
```

## Performance Optimization

For better performance with multiple instances:

1. **Resource Limits**: Set CPU and memory limits per container
2. **Storage**: Use fast storage for Docker volumes
3. **Network**: Consider dedicated networks for high-traffic scenarios
4. **Monitoring**: Monitor host resources and container metrics

## Support

For issues related to Docker socket configuration:

1. Check the troubleshooting section above
2. Review Docker daemon logs: `journalctl -u docker.service`
3. Verify network connectivity and permissions
4. Consult Docker documentation for platform-specific issues

---

**Note**: This configuration enables full Docker functionality for the OBS Web Manager. Always follow security best practices for production deployments.
