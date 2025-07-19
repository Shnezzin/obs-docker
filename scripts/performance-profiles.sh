#!/bin/bash
# Performance Profiles Manager for OBS Docker Container
# Optimizes container resources based on use case

set -euo pipefail

# Configuration
PROFILES_DIR="/opt/obs-config/profiles"
CURRENT_PROFILE_FILE="/opt/obs-config/current-profile"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] PERF: $*" >&2
}

# Initialize profiles
init_profiles() {
    mkdir -p "$PROFILES_DIR"
    
    # Streaming Profile
    cat > "$PROFILES_DIR/streaming.json" << 'EOF'
{
  "name": "streaming",
  "description": "Optimized for live streaming",
  "resources": {
    "cpu_limit": "2.0",
    "memory": "4G",
    "cpu_shares": 1024
  },
  "obs_settings": {
    "output_mode": "Simple",
    "video_bitrate": 6000,
    "audio_bitrate": 160,
    "encoder": "x264",
    "preset": "veryfast",
    "profile": "high",
    "keyframe_interval": 2,
    "canvas_resolution": "1920x1080",
    "output_resolution": "1920x1080",
    "fps": 60
  },
  "system_tweaks": {
    "nice_priority": -10,
    "io_priority": "rt",
    "cpu_governor": "performance"
  }
}
EOF

    # Recording Profile
    cat > "$PROFILES_DIR/recording.json" << 'EOF'
{
  "name": "recording",
  "description": "Optimized for high-quality recording",
  "resources": {
    "cpu_limit": "4.0",
    "memory": "8G",
    "cpu_shares": 2048
  },
  "obs_settings": {
    "output_mode": "Advanced",
    "video_bitrate": 50000,
    "audio_bitrate": 320,
    "encoder": "x264",
    "preset": "slow",
    "profile": "high",
    "keyframe_interval": 0,
    "canvas_resolution": "1920x1080",
    "output_resolution": "1920x1080",
    "fps": 60,
    "recording_format": "mkv",
    "recording_quality": "lossless"
  },
  "system_tweaks": {
    "nice_priority": -15,
    "io_priority": "rt",
    "cpu_governor": "performance"
  }
}
EOF

    # Low Resource Profile
    cat > "$PROFILES_DIR/low-resource.json" << 'EOF'
{
  "name": "low-resource",
  "description": "Optimized for systems with limited resources",
  "resources": {
    "cpu_limit": "1.0",
    "memory": "2G",
    "cpu_shares": 512
  },
  "obs_settings": {
    "output_mode": "Simple",
    "video_bitrate": 2500,
    "audio_bitrate": 128,
    "encoder": "x264",
    "preset": "ultrafast",
    "profile": "baseline",
    "keyframe_interval": 2,
    "canvas_resolution": "1280x720",
    "output_resolution": "1280x720",
    "fps": 30
  },
  "system_tweaks": {
    "nice_priority": 0,
    "io_priority": "be",
    "cpu_governor": "powersave"
  }
}
EOF

    # GPU Accelerated Profile
    cat > "$PROFILES_DIR/gpu-accelerated.json" << 'EOF'
{
  "name": "gpu-accelerated",
  "description": "Optimized for GPU-accelerated encoding",
  "resources": {
    "cpu_limit": "2.0",
    "memory": "6G",
    "cpu_shares": 1024,
    "gpu_enabled": true
  },
  "obs_settings": {
    "output_mode": "Advanced",
    "video_bitrate": 8000,
    "audio_bitrate": 192,
    "encoder": "nvenc_h264",
    "preset": "quality",
    "profile": "high",
    "keyframe_interval": 2,
    "canvas_resolution": "1920x1080",
    "output_resolution": "1920x1080",
    "fps": 60,
    "gpu_priority": "high"
  },
  "system_tweaks": {
    "nice_priority": -10,
    "io_priority": "rt",
    "cpu_governor": "performance"
  }
}
EOF

    # Multi-stream Profile
    cat > "$PROFILES_DIR/multi-stream.json" << 'EOF'
{
  "name": "multi-stream",
  "description": "Optimized for streaming to multiple platforms",
  "resources": {
    "cpu_limit": "6.0",
    "memory": "12G",
    "cpu_shares": 3072
  },
  "obs_settings": {
    "output_mode": "Advanced",
    "video_bitrate": 6000,
    "audio_bitrate": 160,
    "encoder": "x264",
    "preset": "fast",
    "profile": "high",
    "keyframe_interval": 2,
    "canvas_resolution": "1920x1080",
    "output_resolution": "1920x1080",
    "fps": 60,
    "multi_output": true
  },
  "system_tweaks": {
    "nice_priority": -15,
    "io_priority": "rt",
    "cpu_governor": "performance"
  }
}
EOF

    log "Performance profiles initialized"
}

# Apply system tweaks
apply_system_tweaks() {
    local profile_file="$1"
    
    local nice_priority
    local io_priority
    local cpu_governor
    
    nice_priority=$(jq -r '.system_tweaks.nice_priority' "$profile_file")
    io_priority=$(jq -r '.system_tweaks.io_priority' "$profile_file")
    cpu_governor=$(jq -r '.system_tweaks.cpu_governor' "$profile_file")
    
    log "Applying system tweaks..."
    
    # Set CPU governor
    if [[ "$cpu_governor" != "null" ]]; then
        echo "$cpu_governor" | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true
        log "CPU governor set to: $cpu_governor"
    fi
    
    # Set process priority
    if [[ "$nice_priority" != "null" ]]; then
        renice "$nice_priority" $$ 2>/dev/null || true
        log "Process priority set to: $nice_priority"
    fi
    
    # Set I/O priority
    if [[ "$io_priority" != "null" ]] && command -v ionice > /dev/null 2>&1; then
        case "$io_priority" in
            "rt") ionice -c 1 -p $$ || true ;;
            "be") ionice -c 2 -p $$ || true ;;
            "idle") ionice -c 3 -p $$ || true ;;
        esac
        log "I/O priority set to: $io_priority"
    fi
}

# Generate OBS configuration
generate_obs_config() {
    local profile_file="$1"
    local obs_config_dir="/opt/obs-config/obs-studio/basic/profiles/Untitled"
    
    mkdir -p "$obs_config_dir"
    
    log "Generating OBS configuration..."
    
    # Extract settings
    local output_mode video_bitrate audio_bitrate encoder preset profile_setting
    local canvas_res output_res fps
    
    output_mode=$(jq -r '.obs_settings.output_mode' "$profile_file")
    video_bitrate=$(jq -r '.obs_settings.video_bitrate' "$profile_file")
    audio_bitrate=$(jq -r '.obs_settings.audio_bitrate' "$profile_file")
    encoder=$(jq -r '.obs_settings.encoder' "$profile_file")
    preset=$(jq -r '.obs_settings.preset' "$profile_file")
    profile_setting=$(jq -r '.obs_settings.profile' "$profile_file")
    canvas_res=$(jq -r '.obs_settings.canvas_resolution' "$profile_file")
    output_res=$(jq -r '.obs_settings.output_resolution' "$profile_file")
    fps=$(jq -r '.obs_settings.fps' "$profile_file")
    
    # Generate basic.ini
    cat > "$obs_config_dir/basic.ini" << EOF
[General]
Name=Untitled

[Video]
BaseCX=${canvas_res%x*}
BaseCY=${canvas_res#*x}
OutputCX=${output_res%x*}
OutputCY=${output_res#*x}
FPSType=0
FPSCommon=${fps}

[Output]
Mode=${output_mode}

[SimpleOutput]
VBitrate=${video_bitrate}
ABitrate=${audio_bitrate}
Encoder=${encoder}
UseAdvanced=true
Preset=${preset}
Profile=${profile_setting}

[AdvOut]
TrackIndex=1
Encoder=${encoder}
ApplyServiceSettings=true
UseAdvanced=true
Preset=${preset}
Profile=${profile_setting}
KeyframeInterval=$(jq -r '.obs_settings.keyframe_interval // 0' "$profile_file")

[Audio]
SampleRate=44100
ChannelSetup=Stereo
EOF

    log "✓ OBS configuration generated"
}

# Apply Docker resource limits
apply_docker_limits() {
    local profile_file="$1"
    local container_name="${CONTAINER_NAME:-obs-studio-container}"
    
    local cpu_limit memory cpu_shares
    cpu_limit=$(jq -r '.resources.cpu_limit' "$profile_file")
    memory=$(jq -r '.resources.memory' "$profile_file")
    cpu_shares=$(jq -r '.resources.cpu_shares' "$profile_file")
    
    log "Applying Docker resource limits..."
    
    # Update container resources
    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        if [[ "$cpu_limit" != "null" ]]; then
            docker update --cpus="$cpu_limit" "$container_name" 2>/dev/null || true
        fi
        
        if [[ "$memory" != "null" ]]; then
            docker update --memory="$memory" "$container_name" 2>/dev/null || true
        fi
        
        if [[ "$cpu_shares" != "null" ]]; then
            docker update --cpu-shares="$cpu_shares" "$container_name" 2>/dev/null || true
        fi
        
        log "✓ Docker resource limits applied"
    else
        log "WARNING: Container $container_name not found"
    fi
}

# Apply performance profile
apply_profile() {
    local profile_name="$1"
    local profile_file="$PROFILES_DIR/$profile_name.json"
    
    if [[ ! -f "$profile_file" ]]; then
        log "ERROR: Profile '$profile_name' not found"
        list_profiles
        return 1
    fi
    
    log "Applying performance profile: $profile_name"
    
    # Apply system tweaks
    apply_system_tweaks "$profile_file"
    
    # Generate OBS configuration
    generate_obs_config "$profile_file"
    
    # Apply Docker resource limits
    apply_docker_limits "$profile_file"
    
    # Save current profile
    echo "$profile_name" > "$CURRENT_PROFILE_FILE"
    
    log "✓ Performance profile '$profile_name' applied successfully"
    log "Restart OBS Studio to apply new settings"
}

# List available profiles
list_profiles() {
    log "Available performance profiles:"
    
    for profile_file in "$PROFILES_DIR"/*.json; do
        if [[ -f "$profile_file" ]]; then
            local name description
            name=$(jq -r '.name' "$profile_file")
            description=$(jq -r '.description' "$profile_file")
            echo "  $name: $description"
        fi
    done
}

# Show current profile
show_current_profile() {
    if [[ -f "$CURRENT_PROFILE_FILE" ]]; then
        local current_profile
        current_profile=$(cat "$CURRENT_PROFILE_FILE")
        log "Current profile: $current_profile"
        
        local profile_file="$PROFILES_DIR/$current_profile.json"
        if [[ -f "$profile_file" ]]; then
            echo "Profile details:"
            jq '.' "$profile_file"
        fi
    else
        log "No profile currently applied"
    fi
}

# Monitor system performance
monitor_performance() {
    log "Monitoring system performance..."
    
    while true; do
        local cpu_usage memory_usage load_avg
        cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
        memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
        load_avg=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
        
        log "CPU: ${cpu_usage}% | Memory: ${memory_usage}% | Load: ${load_avg}"
        
        # Check for performance issues
        if (( $(echo "$cpu_usage > 90.0" | bc -l) )); then
            log "WARNING: High CPU usage detected"
        fi
        
        if (( $(echo "$memory_usage > 90.0" | bc -l) )); then
            log "WARNING: High memory usage detected"
        fi
        
        sleep 30
    done
}

# Optimize for current workload
auto_optimize() {
    log "Auto-optimizing based on current workload..."
    
    local cpu_usage memory_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    
    # Determine optimal profile
    if (( $(echo "$cpu_usage > 80.0" | bc -l) )) || (( $(echo "$memory_usage > 80.0" | bc -l) )); then
        log "High resource usage detected, applying low-resource profile"
        apply_profile "low-resource"
    elif command -v nvidia-smi > /dev/null 2>&1; then
        log "GPU detected, applying GPU-accelerated profile"
        apply_profile "gpu-accelerated"
    else
        log "Applying balanced streaming profile"
        apply_profile "streaming"
    fi
}

# Main function
main() {
    init_profiles
    
    case "${1:-help}" in
        "apply")
            apply_profile "$2"
            ;;
        "list")
            list_profiles
            ;;
        "current")
            show_current_profile
            ;;
        "monitor")
            monitor_performance
            ;;
        "auto")
            auto_optimize
            ;;
        "help"|*)
            echo "OBS Performance Profiles Manager"
            echo "Usage: $0 {apply|list|current|monitor|auto}"
            echo ""
            echo "Commands:"
            echo "  apply <profile>    - Apply a performance profile"
            echo "  list              - List available profiles"
            echo "  current           - Show current profile"
            echo "  monitor           - Monitor system performance"
            echo "  auto              - Auto-optimize based on workload"
            echo "  help              - Show this help"
            echo ""
            echo "Available profiles:"
            echo "  streaming         - Optimized for live streaming"
            echo "  recording         - Optimized for high-quality recording"
            echo "  low-resource      - Optimized for limited resources"
            echo "  gpu-accelerated   - Optimized for GPU encoding"
            echo "  multi-stream      - Optimized for multi-platform streaming"
            ;;
    esac
}

main "$@"
