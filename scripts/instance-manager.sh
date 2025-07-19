#!/bin/bash
# Multi-Instance Manager for OBS Docker Container
# Orchestrates multiple OBS containers for different users/purposes

set -euo pipefail

# Configuration
INSTANCES_DIR="/opt/obs-instances"
INSTANCE_CONFIG_FILE="/opt/obs-config/instances.json"
BASE_PORT=3389
BASE_WEB_PORT=8080

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INSTANCE: $*" >&2
}

# Initialize instance management
init_instance_manager() {
    mkdir -p "$INSTANCES_DIR"
    
    if [[ ! -f "$INSTANCE_CONFIG_FILE" ]]; then
        cat > "$INSTANCE_CONFIG_FILE" << 'EOF'
{
  "instances": {},
  "global_settings": {
    "max_instances": 10,
    "base_rdp_port": 3389,
    "base_web_port": 8080,
    "resource_limits": {
      "default_cpu": "1.0",
      "default_memory": "2G",
      "max_cpu_per_instance": "4.0",
      "max_memory_per_instance": "8G"
    },
    "networking": {
      "network_name": "obs-network",
      "subnet": "172.20.0.0/16"
    }
  },
  "templates": {
    "streaming": {
      "description": "Optimized for streaming",
      "resources": {"cpu": "2.0", "memory": "4G"},
      "environment": {"PERFORMANCE_PROFILE": "streaming"},
      "desktop": "lxde"
    },
    "recording": {
      "description": "Optimized for recording",
      "resources": {"cpu": "4.0", "memory": "8G"},
      "environment": {"PERFORMANCE_PROFILE": "recording"},
      "desktop": "xfce"
    },
    "multi-stream": {
      "description": "Multi-platform streaming",
      "resources": {"cpu": "6.0", "memory": "12G"},
      "environment": {"PERFORMANCE_PROFILE": "multi-stream"},
      "desktop": "xfce"
    }
  }
}
EOF
        log "Instance manager configuration initialized"
    fi
}

# Create Docker network for instances
create_obs_network() {
    local network_name
    local subnet
    network_name=$(jq -r '.global_settings.networking.network_name' "$INSTANCE_CONFIG_FILE")
    subnet=$(jq -r '.global_settings.networking.subnet' "$INSTANCE_CONFIG_FILE")
    
    if ! docker network ls | grep -q "$network_name"; then
        log "Creating Docker network: $network_name"
        docker network create --driver bridge --subnet="$subnet" "$network_name"
        log "✓ Network created successfully"
    fi
}

# Generate instance configuration
generate_instance_config() {
    local instance_name="$1"
    local template="${2:-streaming}"
    local user="${3:-developer}"
    local password="${4:-$(openssl rand -base64 12)}"
    
    local instance_dir="$INSTANCES_DIR/$instance_name"
    mkdir -p "$instance_dir"
    
    # Get next available ports
    local rdp_port web_port
    rdp_port=$(get_next_port "$BASE_PORT")
    web_port=$(get_next_port "$BASE_WEB_PORT")
    
    # Get template configuration
    local template_config
    template_config=$(jq ".templates.$template" "$INSTANCE_CONFIG_FILE")
    
    if [[ "$template_config" == "null" ]]; then
        log "ERROR: Template '$template' not found"
        return 1
    fi
    
    # Create instance configuration
    cat > "$instance_dir/config.json" << EOF
{
  "name": "$instance_name",
  "template": "$template",
  "user": "$user",
  "password": "$password",
  "ports": {
    "rdp": $rdp_port,
    "web": $web_port
  },
  "resources": $(echo "$template_config" | jq '.resources'),
  "environment": $(echo "$template_config" | jq '.environment'),
  "desktop": $(echo "$template_config" | jq -r '.desktop'),
  "status": "created",
  "created_at": "$(date -Iseconds)",
  "container_name": "obs-$instance_name"
}
EOF
    
    # Create instance-specific docker-compose file
    cat > "$instance_dir/docker-compose.yml" << EOF
version: '3.8'

services:
  obs-$instance_name:
    build:
      context: ../../
      dockerfile: Dockerfile
      args:
        - OBS_VERSION=31.1.1
        - UBUNTU_VERSION=24.04
        - LOCALE=en_US.UTF-8
        - TIMEZONE=UTC
        - DESKTOP_ENV=$(echo "$template_config" | jq -r '.desktop')
        - ENABLE_GPU=false
    container_name: obs-$instance_name
    restart: unless-stopped
    
    ports:
      - "$rdp_port:3389"
      - "$web_port:8080"
    
    volumes:
      - ./data:/home:rw
      - ./config:/opt/obs-config
      - ./recordings:/home/recordings
    
    environment:
      - USER=$user
      - PASSWD=$password
      - GROUP=$user
      - DISPLAY=:1
      - TZ=UTC
      - LANG=en_US.UTF-8
$(echo "$template_config" | jq -r '.environment | to_entries[] | "      - \(.key)=\(.value)"')
    
    deploy:
      resources:
        limits:
          memory: $(echo "$template_config" | jq -r '.resources.memory')
          cpus: '$(echo "$template_config" | jq -r '.resources.cpu')'
        reservations:
          memory: 512M
          cpus: '0.5'
    
    networks:
      - obs-network

networks:
  obs-network:
    external: true
EOF
    
    # Create data directories
    mkdir -p "$instance_dir/data" "$instance_dir/config" "$instance_dir/recordings"
    
    log "✓ Instance configuration generated: $instance_name"
}

# Get next available port
get_next_port() {
    local base_port="$1"
    local port=$base_port
    
    while netstat -tuln 2>/dev/null | grep -q ":$port "; do
        ((port++))
    done
    
    echo "$port"
}

# Create new instance
create_instance() {
    local instance_name="$1"
    local template="${2:-streaming}"
    local user="${3:-developer}"
    local password="$4"
    
    log "Creating instance: $instance_name"
    
    # Check if instance already exists
    if [[ -d "$INSTANCES_DIR/$instance_name" ]]; then
        log "ERROR: Instance '$instance_name' already exists"
        return 1
    fi
    
    # Check instance limit
    local max_instances current_instances
    max_instances=$(jq -r '.global_settings.max_instances' "$INSTANCE_CONFIG_FILE")
    current_instances=$(jq -r '.instances | length' "$INSTANCE_CONFIG_FILE")
    
    if [[ $current_instances -ge $max_instances ]]; then
        log "ERROR: Maximum number of instances ($max_instances) reached"
        return 1
    fi
    
    # Create network if needed
    create_obs_network
    
    # Generate configuration
    generate_instance_config "$instance_name" "$template" "$user" "$password"
    
    # Update global instance registry
    local config_tmp instance_config
    config_tmp=$(mktemp)
    instance_config=$(cat "$INSTANCES_DIR/$instance_name/config.json")
    
    jq ".instances[\"$instance_name\"] = $instance_config" "$INSTANCE_CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$INSTANCE_CONFIG_FILE"
    
    log "✓ Instance '$instance_name' created successfully"
    log "RDP Port: $(jq -r ".instances[\"$instance_name\"].ports.rdp" "$INSTANCE_CONFIG_FILE")"
    log "Web Port: $(jq -r ".instances[\"$instance_name\"].ports.web" "$INSTANCE_CONFIG_FILE")"
}

# Start instance
start_instance() {
    local instance_name="$1"
    local instance_dir="$INSTANCES_DIR/$instance_name"
    
    if [[ ! -d "$instance_dir" ]]; then
        log "ERROR: Instance '$instance_name' not found"
        return 1
    fi
    
    log "Starting instance: $instance_name"
    
    cd "$instance_dir"
    docker-compose up -d
    
    # Update status
    update_instance_status "$instance_name" "running"
    
    log "✓ Instance '$instance_name' started successfully"
}

# Stop instance
stop_instance() {
    local instance_name="$1"
    local instance_dir="$INSTANCES_DIR/$instance_name"
    
    if [[ ! -d "$instance_dir" ]]; then
        log "ERROR: Instance '$instance_name' not found"
        return 1
    fi
    
    log "Stopping instance: $instance_name"
    
    cd "$instance_dir"
    docker-compose down
    
    # Update status
    update_instance_status "$instance_name" "stopped"
    
    log "✓ Instance '$instance_name' stopped successfully"
}

# Remove instance
remove_instance() {
    local instance_name="$1"
    local instance_dir="$INSTANCES_DIR/$instance_name"
    
    if [[ ! -d "$instance_dir" ]]; then
        log "ERROR: Instance '$instance_name' not found"
        return 1
    fi
    
    log "Removing instance: $instance_name"
    
    # Stop instance first
    stop_instance "$instance_name" || true
    
    # Remove container and volumes
    cd "$instance_dir"
    docker-compose down -v
    
    # Remove instance directory
    rm -rf "$instance_dir"
    
    # Update global registry
    local config_tmp
    config_tmp=$(mktemp)
    jq "del(.instances[\"$instance_name\"])" "$INSTANCE_CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$INSTANCE_CONFIG_FILE"
    
    log "✓ Instance '$instance_name' removed successfully"
}

# Update instance status
update_instance_status() {
    local instance_name="$1"
    local status="$2"
    
    local config_tmp
    config_tmp=$(mktemp)
    jq ".instances[\"$instance_name\"].status = \"$status\" | .instances[\"$instance_name\"].updated_at = \"$(date -Iseconds)\"" "$INSTANCE_CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$INSTANCE_CONFIG_FILE"
}

# List instances
list_instances() {
    log "OBS Container Instances:"
    echo
    
    jq -r '.instances | to_entries[] | "  \(.key): \(.value.status) (Template: \(.value.template), RDP: \(.value.ports.rdp), Web: \(.value.ports.web))"' "$INSTANCE_CONFIG_FILE"
    
    echo
    local total_instances
    total_instances=$(jq -r '.instances | length' "$INSTANCE_CONFIG_FILE")
    log "Total instances: $total_instances"
}

# Show instance details
show_instance() {
    local instance_name="$1"
    
    local instance_info
    instance_info=$(jq ".instances[\"$instance_name\"]" "$INSTANCE_CONFIG_FILE")
    
    if [[ "$instance_info" == "null" ]]; then
        log "ERROR: Instance '$instance_name' not found"
        return 1
    fi
    
    log "Instance details: $instance_name"
    echo "$instance_info" | jq '.'
}

# Scale instances
scale_instances() {
    local template="$1"
    local count="$2"
    
    log "Scaling instances with template '$template' to $count instances"
    
    for i in $(seq 1 "$count"); do
        local instance_name="${template}-${i}"
        
        if ! jq -e ".instances[\"$instance_name\"]" "$INSTANCE_CONFIG_FILE" > /dev/null 2>&1; then
            create_instance "$instance_name" "$template" "user$i"
            start_instance "$instance_name"
        fi
    done
    
    log "✓ Scaling completed"
}

# Monitor instances
monitor_instances() {
    log "Monitoring instances..."
    
    while true; do
        local instances
        instances=$(jq -r '.instances | keys[]' "$INSTANCE_CONFIG_FILE")
        
        for instance in $instances; do
            local container_name
            container_name=$(jq -r ".instances[\"$instance\"].container_name" "$INSTANCE_CONFIG_FILE")
            
            if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
                update_instance_status "$instance" "running"
            else
                update_instance_status "$instance" "stopped"
            fi
        done
        
        sleep 30
    done
}

# Load balancer configuration
setup_load_balancer() {
    log "Setting up load balancer..."
    
    # Create nginx configuration for load balancing
    cat > "$INSTANCES_DIR/nginx.conf" << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream obs_instances {
        least_conn;
EOF

    # Add running instances to upstream
    local instances
    instances=$(jq -r '.instances | to_entries[] | select(.value.status == "running") | "\(.value.ports.web)"' "$INSTANCE_CONFIG_FILE")
    
    for port in $instances; do
        echo "        server localhost:$port;" >> "$INSTANCES_DIR/nginx.conf"
    done
    
    cat >> "$INSTANCES_DIR/nginx.conf" << 'EOF'
    }
    
    server {
        listen 80;
        
        location / {
            proxy_pass http://obs_instances;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
EOF

    # Start nginx load balancer
    docker run -d \
        --name obs-load-balancer \
        -p 80:80 \
        -v "$INSTANCES_DIR/nginx.conf:/etc/nginx/nginx.conf:ro" \
        --network obs-network \
        nginx:alpine
    
    log "✓ Load balancer configured and started"
}

# Main function
main() {
    init_instance_manager
    
    case "${1:-help}" in
        "create")
            create_instance "$2" "$3" "$4" "$5"
            ;;
        "start")
            start_instance "$2"
            ;;
        "stop")
            stop_instance "$2"
            ;;
        "remove")
            remove_instance "$2"
            ;;
        "list")
            list_instances
            ;;
        "show")
            show_instance "$2"
            ;;
        "scale")
            scale_instances "$2" "$3"
            ;;
        "monitor")
            monitor_instances
            ;;
        "load-balancer")
            setup_load_balancer
            ;;
        "help"|*)
            echo "OBS Multi-Instance Manager"
            echo "Usage: $0 {create|start|stop|remove|list|show|scale|monitor|load-balancer}"
            echo ""
            echo "Commands:"
            echo "  create <name> [template] [user] [password]  - Create new instance"
            echo "  start <name>                               - Start instance"
            echo "  stop <name>                                - Stop instance"
            echo "  remove <name>                              - Remove instance"
            echo "  list                                       - List all instances"
            echo "  show <name>                                - Show instance details"
            echo "  scale <template> <count>                   - Scale instances"
            echo "  monitor                                    - Monitor instances"
            echo "  load-balancer                              - Setup load balancer"
            echo "  help                                       - Show this help"
            echo ""
            echo "Available templates: streaming, recording, multi-stream"
            ;;
    esac
}

main "$@"
