#!/bin/bash
# Cloud Integration Script for OBS Docker Container
# Supports AWS S3, Google Cloud Storage, and popular streaming platforms

set -euo pipefail

# Configuration
CONFIG_FILE="/opt/obs-config/cloud-config.json"
RECORDINGS_DIR="/home/recordings"
BACKUP_DIR="/opt/backups"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] CLOUD: $*" >&2
}

# Initialize cloud config
init_cloud_config() {
    mkdir -p "$(dirname "$CONFIG_FILE")" "$RECORDINGS_DIR" "$BACKUP_DIR"
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        cat > "$CONFIG_FILE" << 'EOF'
{
  "storage": {
    "aws_s3": {
      "enabled": false,
      "bucket": "",
      "region": "us-east-1",
      "access_key": "",
      "secret_key": "",
      "auto_upload": false
    },
    "google_cloud": {
      "enabled": false,
      "bucket": "",
      "project_id": "",
      "credentials_file": "",
      "auto_upload": false
    }
  },
  "streaming": {
    "twitch": {
      "enabled": false,
      "stream_key": "",
      "server": "rtmp://live.twitch.tv/live/"
    },
    "youtube": {
      "enabled": false,
      "stream_key": "",
      "server": "rtmp://a.rtmp.youtube.com/live2/"
    },
    "facebook": {
      "enabled": false,
      "stream_key": "",
      "server": "rtmps://live-api-s.facebook.com:443/rtmp/"
    },
    "custom": {
      "enabled": false,
      "stream_key": "",
      "server": ""
    }
  },
  "settings": {
    "auto_backup_recordings": true,
    "delete_after_upload": false,
    "compression_enabled": true,
    "encryption_enabled": false
  }
}
EOF
        log "Cloud configuration initialized at $CONFIG_FILE"
    fi
}

# AWS S3 Functions
setup_aws_s3() {
    local bucket="$1"
    local region="$2"
    local access_key="$3"
    local secret_key="$4"
    
    log "Setting up AWS S3 integration..."
    
    # Install AWS CLI if not present
    if ! command -v aws > /dev/null 2>&1; then
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        ./aws/install
        rm -rf aws awscliv2.zip
    fi
    
    # Configure AWS credentials
    mkdir -p ~/.aws
    cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $access_key
aws_secret_access_key = $secret_key
EOF
    
    cat > ~/.aws/config << EOF
[default]
region = $region
output = json
EOF
    
    # Update config
    local config_tmp
    config_tmp=$(mktemp)
    jq ".storage.aws_s3.enabled = true | .storage.aws_s3.bucket = \"$bucket\" | .storage.aws_s3.region = \"$region\"" "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ AWS S3 configured successfully"
}

# Upload to AWS S3
upload_to_s3() {
    local file_path="$1"
    local bucket
    bucket=$(jq -r '.storage.aws_s3.bucket' "$CONFIG_FILE")
    
    if [[ "$bucket" == "null" || -z "$bucket" ]]; then
        log "ERROR: AWS S3 bucket not configured"
        return 1
    fi
    
    local filename
    filename=$(basename "$file_path")
    local s3_path="obs-recordings/$(date +%Y/%m/%d)/$filename"
    
    log "Uploading $filename to S3..."
    
    if aws s3 cp "$file_path" "s3://$bucket/$s3_path"; then
        log "✓ Successfully uploaded to S3: s3://$bucket/$s3_path"
        
        # Delete local file if configured
        local delete_after_upload
        delete_after_upload=$(jq -r '.settings.delete_after_upload' "$CONFIG_FILE")
        if [[ "$delete_after_upload" == "true" ]]; then
            rm "$file_path"
            log "Local file deleted after upload"
        fi
        
        return 0
    else
        log "ERROR: Failed to upload to S3"
        return 1
    fi
}

# Google Cloud Storage Functions
setup_google_cloud() {
    local bucket="$1"
    local project_id="$2"
    local credentials_file="$3"
    
    log "Setting up Google Cloud Storage integration..."
    
    # Install Google Cloud SDK
    if ! command -v gsutil > /dev/null 2>&1; then
        curl https://sdk.cloud.google.com | bash
        source ~/.bashrc
    fi
    
    # Authenticate
    if [[ -f "$credentials_file" ]]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$credentials_file"
        gcloud auth activate-service-account --key-file="$credentials_file"
    fi
    
    # Update config
    local config_tmp
    config_tmp=$(mktemp)
    jq ".storage.google_cloud.enabled = true | .storage.google_cloud.bucket = \"$bucket\" | .storage.google_cloud.project_id = \"$project_id\"" "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ Google Cloud Storage configured successfully"
}

# Upload to Google Cloud Storage
upload_to_gcs() {
    local file_path="$1"
    local bucket
    bucket=$(jq -r '.storage.google_cloud.bucket' "$CONFIG_FILE")
    
    if [[ "$bucket" == "null" || -z "$bucket" ]]; then
        log "ERROR: Google Cloud Storage bucket not configured"
        return 1
    fi
    
    local filename
    filename=$(basename "$file_path")
    local gcs_path="obs-recordings/$(date +%Y/%m/%d)/$filename"
    
    log "Uploading $filename to Google Cloud Storage..."
    
    if gsutil cp "$file_path" "gs://$bucket/$gcs_path"; then
        log "✓ Successfully uploaded to GCS: gs://$bucket/$gcs_path"
        
        # Delete local file if configured
        local delete_after_upload
        delete_after_upload=$(jq -r '.settings.delete_after_upload' "$CONFIG_FILE")
        if [[ "$delete_after_upload" == "true" ]]; then
            rm "$file_path"
            log "Local file deleted after upload"
        fi
        
        return 0
    else
        log "ERROR: Failed to upload to Google Cloud Storage"
        return 1
    fi
}

# Configure streaming platforms
setup_streaming() {
    local platform="$1"
    local stream_key="$2"
    local server="$3"
    
    log "Setting up $platform streaming..."
    
    # Update config
    local config_tmp
    config_tmp=$(mktemp)
    jq ".streaming.$platform.enabled = true | .streaming.$platform.stream_key = \"$stream_key\" | .streaming.$platform.server = \"$server\"" "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ $platform streaming configured"
}

# Generate OBS streaming configuration
generate_obs_streaming_config() {
    local obs_config_dir="/opt/obs-config/obs-studio"
    mkdir -p "$obs_config_dir/basic/profiles/Untitled/basic.ini"
    
    # Get enabled streaming platforms
    local platforms
    platforms=$(jq -r '.streaming | to_entries[] | select(.value.enabled == true) | .key' "$CONFIG_FILE")
    
    for platform in $platforms; do
        local server
        local stream_key
        server=$(jq -r ".streaming.$platform.server" "$CONFIG_FILE")
        stream_key=$(jq -r ".streaming.$platform.stream_key" "$CONFIG_FILE")
        
        log "Configuring OBS for $platform streaming"
        
        # Create OBS service configuration
        cat > "$obs_config_dir/basic/profiles/Untitled/service.json" << EOF
{
    "type": "rtmp_custom",
    "settings": {
        "server": "$server",
        "key": "$stream_key",
        "use_auth": false
    }
}
EOF
    done
}

# Auto-upload recordings
auto_upload_recordings() {
    log "Checking for new recordings to upload..."
    
    # Find new recording files
    local recordings
    recordings=$(find "$RECORDINGS_DIR" -name "*.mp4" -o -name "*.mkv" -o -name "*.flv" -mtime -1)
    
    if [[ -z "$recordings" ]]; then
        log "No new recordings found"
        return 0
    fi
    
    # Check which storage providers are enabled
    local aws_enabled
    local gcs_enabled
    aws_enabled=$(jq -r '.storage.aws_s3.enabled' "$CONFIG_FILE")
    gcs_enabled=$(jq -r '.storage.google_cloud.enabled' "$CONFIG_FILE")
    
    for recording in $recordings; do
        log "Processing recording: $(basename "$recording")"
        
        # Compress if enabled
        local compression_enabled
        compression_enabled=$(jq -r '.settings.compression_enabled' "$CONFIG_FILE")
        if [[ "$compression_enabled" == "true" ]]; then
            compress_recording "$recording"
        fi
        
        # Upload to enabled storage providers
        if [[ "$aws_enabled" == "true" ]]; then
            upload_to_s3 "$recording"
        fi
        
        if [[ "$gcs_enabled" == "true" ]]; then
            upload_to_gcs "$recording"
        fi
    done
}

# Compress recording
compress_recording() {
    local input_file="$1"
    local output_file="${input_file%.*}_compressed.${input_file##*.}"
    
    log "Compressing $(basename "$input_file")..."
    
    if command -v ffmpeg > /dev/null 2>&1; then
        ffmpeg -i "$input_file" -c:v libx264 -crf 23 -c:a aac -b:a 128k "$output_file" -y
        
        if [[ -f "$output_file" ]]; then
            mv "$output_file" "$input_file"
            log "✓ Recording compressed successfully"
        fi
    else
        log "WARNING: ffmpeg not available, skipping compression"
    fi
}

# Backup OBS configuration
backup_obs_config() {
    local backup_name="obs-config-$(date +%Y%m%d-%H%M%S).tar.gz"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log "Creating OBS configuration backup..."
    
    tar -czf "$backup_path" -C /opt obs-config/ 2>/dev/null || true
    
    if [[ -f "$backup_path" ]]; then
        log "✓ Configuration backup created: $backup_name"
        
        # Upload backup to cloud if enabled
        local aws_enabled
        local gcs_enabled
        aws_enabled=$(jq -r '.storage.aws_s3.enabled' "$CONFIG_FILE")
        gcs_enabled=$(jq -r '.storage.google_cloud.enabled' "$CONFIG_FILE")
        
        if [[ "$aws_enabled" == "true" ]]; then
            upload_to_s3 "$backup_path"
        fi
        
        if [[ "$gcs_enabled" == "true" ]]; then
            upload_to_gcs "$backup_path"
        fi
    fi
}

# Main function
main() {
    init_cloud_config
    
    case "${1:-help}" in
        "setup-s3")
            setup_aws_s3 "$2" "$3" "$4" "$5"
            ;;
        "setup-gcs")
            setup_google_cloud "$2" "$3" "$4"
            ;;
        "setup-streaming")
            setup_streaming "$2" "$3" "$4"
            ;;
        "upload")
            auto_upload_recordings
            ;;
        "backup")
            backup_obs_config
            ;;
        "generate-obs-config")
            generate_obs_streaming_config
            ;;
        "help"|*)
            echo "OBS Cloud Integration"
            echo "Usage: $0 {setup-s3|setup-gcs|setup-streaming|upload|backup|generate-obs-config}"
            echo ""
            echo "Commands:"
            echo "  setup-s3 <bucket> <region> <access_key> <secret_key>  - Configure AWS S3"
            echo "  setup-gcs <bucket> <project_id> <credentials_file>    - Configure Google Cloud Storage"
            echo "  setup-streaming <platform> <stream_key> <server>      - Configure streaming platform"
            echo "  upload                                                 - Upload recordings to cloud"
            echo "  backup                                                 - Backup OBS configuration"
            echo "  generate-obs-config                                   - Generate OBS streaming config"
            echo "  help                                                   - Show this help"
            ;;
    esac
}

main "$@"
