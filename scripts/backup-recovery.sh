#!/bin/bash
# Backup and Recovery System for OBS Docker Container
# Comprehensive backup solution for configurations, recordings, and data

set -euo pipefail

# Configuration
BACKUP_DIR="/opt/backups"
CONFIG_DIR="/opt/obs-config"
RECORDINGS_DIR="/home/recordings"
BACKUP_CONFIG_FILE="/opt/obs-config/backup-config.json"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] BACKUP: $*" >&2
}

# Initialize backup system
init_backup_system() {
    mkdir -p "$BACKUP_DIR" "$CONFIG_DIR" "$RECORDINGS_DIR"
    
    if [[ ! -f "$BACKUP_CONFIG_FILE" ]]; then
        cat > "$BACKUP_CONFIG_FILE" << 'EOF'
{
  "backup_settings": {
    "auto_backup": true,
    "backup_interval": "daily",
    "retention_days": 30,
    "compression": true,
    "encryption": false,
    "encryption_key": ""
  },
  "backup_targets": {
    "obs_config": {
      "enabled": true,
      "path": "/opt/obs-config",
      "exclude_patterns": ["*.log", "*.tmp", "cache/*"]
    },
    "recordings": {
      "enabled": true,
      "path": "/home/recordings",
      "exclude_patterns": ["*.part", "*.tmp"]
    },
    "user_data": {
      "enabled": true,
      "path": "/home",
      "exclude_patterns": [".cache/*", ".tmp/*", "*.log"]
    },
    "container_config": {
      "enabled": true,
      "path": "/opt/obs-instances",
      "exclude_patterns": ["*/data/*", "*/recordings/*"]
    }
  },
  "storage_backends": {
    "local": {
      "enabled": true,
      "path": "/opt/backups"
    },
    "s3": {
      "enabled": false,
      "bucket": "",
      "region": "us-east-1",
      "access_key": "",
      "secret_key": ""
    },
    "google_cloud": {
      "enabled": false,
      "bucket": "",
      "project_id": "",
      "credentials_file": ""
    }
  },
  "notifications": {
    "email": {
      "enabled": false,
      "smtp_server": "",
      "smtp_port": 587,
      "username": "",
      "password": "",
      "to_address": ""
    },
    "webhook": {
      "enabled": false,
      "url": "",
      "method": "POST"
    }
  }
}
EOF
        log "Backup configuration initialized"
    fi
}

# Create backup
create_backup() {
    local backup_type="${1:-full}"
    local backup_name="obs-backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log "Creating $backup_type backup: $backup_name"
    
    mkdir -p "$backup_path"
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
  "backup_name": "$backup_name",
  "backup_type": "$backup_type",
  "created_at": "$(date -Iseconds)",
  "hostname": "$(hostname)",
  "obs_version": "$(obs --version 2>/dev/null || echo 'Unknown')",
  "container_id": "$(hostname)",
  "files": []
}
EOF
    
    # Backup each enabled target
    local targets
    targets=$(jq -r '.backup_targets | to_entries[] | select(.value.enabled == true) | .key' "$BACKUP_CONFIG_FILE")
    
    for target in $targets; do
        backup_target "$target" "$backup_path" "$backup_type"
    done
    
    # Compress backup if enabled
    local compression_enabled
    compression_enabled=$(jq -r '.backup_settings.compression' "$BACKUP_CONFIG_FILE")
    
    if [[ "$compression_enabled" == "true" ]]; then
        log "Compressing backup..."
        tar -czf "$backup_path.tar.gz" -C "$BACKUP_DIR" "$backup_name"
        rm -rf "$backup_path"
        backup_path="$backup_path.tar.gz"
    fi
    
    # Encrypt backup if enabled
    local encryption_enabled
    encryption_enabled=$(jq -r '.backup_settings.encryption' "$BACKUP_CONFIG_FILE")
    
    if [[ "$encryption_enabled" == "true" ]]; then
        encrypt_backup "$backup_path"
    fi
    
    # Upload to cloud storage
    upload_backup_to_cloud "$backup_path"
    
    # Send notifications
    send_backup_notification "success" "$backup_name"
    
    # Cleanup old backups
    cleanup_old_backups
    
    log "✓ Backup completed successfully: $backup_name"
    echo "$backup_path"
}

# Backup specific target
backup_target() {
    local target="$1"
    local backup_path="$2"
    local backup_type="$3"
    
    local target_path exclude_patterns
    target_path=$(jq -r ".backup_targets.$target.path" "$BACKUP_CONFIG_FILE")
    exclude_patterns=$(jq -r ".backup_targets.$target.exclude_patterns[]" "$BACKUP_CONFIG_FILE" 2>/dev/null || echo "")
    
    if [[ ! -d "$target_path" ]]; then
        log "WARNING: Target path not found: $target_path"
        return 0
    fi
    
    log "Backing up target: $target ($target_path)"
    
    local target_backup_dir="$backup_path/$target"
    mkdir -p "$target_backup_dir"
    
    # Build exclude options for rsync
    local exclude_opts=""
    if [[ -n "$exclude_patterns" ]]; then
        while IFS= read -r pattern; do
            exclude_opts="$exclude_opts --exclude=$pattern"
        done <<< "$exclude_patterns"
    fi
    
    # Perform backup based on type
    case "$backup_type" in
        "full")
            rsync -av $exclude_opts "$target_path/" "$target_backup_dir/"
            ;;
        "incremental")
            local last_backup
            last_backup=$(find "$BACKUP_DIR" -name "obs-backup-*" -type d | sort | tail -2 | head -1)
            if [[ -n "$last_backup" && -d "$last_backup/$target" ]]; then
                rsync -av --link-dest="$last_backup/$target" $exclude_opts "$target_path/" "$target_backup_dir/"
            else
                rsync -av $exclude_opts "$target_path/" "$target_backup_dir/"
            fi
            ;;
        "differential")
            # Find the last full backup
            local last_full_backup
            last_full_backup=$(find "$BACKUP_DIR" -name "*full*" -type d | sort | tail -1)
            if [[ -n "$last_full_backup" && -d "$last_full_backup/$target" ]]; then
                rsync -av --compare-dest="$last_full_backup/$target" $exclude_opts "$target_path/" "$target_backup_dir/"
            else
                rsync -av $exclude_opts "$target_path/" "$target_backup_dir/"
            fi
            ;;
    esac
    
    # Update manifest
    local file_count size
    file_count=$(find "$target_backup_dir" -type f | wc -l)
    size=$(du -sb "$target_backup_dir" | cut -f1)
    
    local manifest_tmp
    manifest_tmp=$(mktemp)
    jq ".files += [{\"target\": \"$target\", \"path\": \"$target_path\", \"file_count\": $file_count, \"size_bytes\": $size}]" "$backup_path/manifest.json" > "$manifest_tmp"
    mv "$manifest_tmp" "$backup_path/manifest.json"
    
    log "✓ Target backed up: $target ($file_count files, $(numfmt --to=iec $size))"
}

# Encrypt backup
encrypt_backup() {
    local backup_path="$1"
    local encryption_key
    encryption_key=$(jq -r '.backup_settings.encryption_key' "$BACKUP_CONFIG_FILE")
    
    if [[ -z "$encryption_key" ]]; then
        log "ERROR: Encryption enabled but no key provided"
        return 1
    fi
    
    log "Encrypting backup..."
    
    openssl enc -aes-256-cbc -salt -in "$backup_path" -out "$backup_path.enc" -k "$encryption_key"
    rm "$backup_path"
    
    log "✓ Backup encrypted"
}

# Upload backup to cloud storage
upload_backup_to_cloud() {
    local backup_path="$1"
    
    # Check S3 upload
    local s3_enabled
    s3_enabled=$(jq -r '.storage_backends.s3.enabled' "$BACKUP_CONFIG_FILE")
    
    if [[ "$s3_enabled" == "true" ]]; then
        upload_to_s3 "$backup_path"
    fi
    
    # Check Google Cloud upload
    local gcs_enabled
    gcs_enabled=$(jq -r '.storage_backends.google_cloud.enabled' "$BACKUP_CONFIG_FILE")
    
    if [[ "$gcs_enabled" == "true" ]]; then
        upload_to_gcs "$backup_path"
    fi
}

# Upload to AWS S3
upload_to_s3() {
    local backup_path="$1"
    local bucket region access_key secret_key
    
    bucket=$(jq -r '.storage_backends.s3.bucket' "$BACKUP_CONFIG_FILE")
    region=$(jq -r '.storage_backends.s3.region' "$BACKUP_CONFIG_FILE")
    access_key=$(jq -r '.storage_backends.s3.access_key' "$BACKUP_CONFIG_FILE")
    secret_key=$(jq -r '.storage_backends.s3.secret_key' "$BACKUP_CONFIG_FILE")
    
    if [[ -z "$bucket" ]]; then
        log "WARNING: S3 enabled but bucket not configured"
        return 0
    fi
    
    log "Uploading backup to S3..."
    
    # Configure AWS credentials
    export AWS_ACCESS_KEY_ID="$access_key"
    export AWS_SECRET_ACCESS_KEY="$secret_key"
    export AWS_DEFAULT_REGION="$region"
    
    local s3_path="obs-backups/$(basename "$backup_path")"
    
    if aws s3 cp "$backup_path" "s3://$bucket/$s3_path"; then
        log "✓ Backup uploaded to S3: s3://$bucket/$s3_path"
    else
        log "ERROR: Failed to upload backup to S3"
    fi
}

# Upload to Google Cloud Storage
upload_to_gcs() {
    local backup_path="$1"
    local bucket project_id credentials_file
    
    bucket=$(jq -r '.storage_backends.google_cloud.bucket' "$BACKUP_CONFIG_FILE")
    project_id=$(jq -r '.storage_backends.google_cloud.project_id' "$BACKUP_CONFIG_FILE")
    credentials_file=$(jq -r '.storage_backends.google_cloud.credentials_file' "$BACKUP_CONFIG_FILE")
    
    if [[ -z "$bucket" ]]; then
        log "WARNING: Google Cloud Storage enabled but bucket not configured"
        return 0
    fi
    
    log "Uploading backup to Google Cloud Storage..."
    
    # Set credentials
    if [[ -f "$credentials_file" ]]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$credentials_file"
    fi
    
    local gcs_path="obs-backups/$(basename "$backup_path")"
    
    if gsutil cp "$backup_path" "gs://$bucket/$gcs_path"; then
        log "✓ Backup uploaded to GCS: gs://$bucket/$gcs_path"
    else
        log "ERROR: Failed to upload backup to Google Cloud Storage"
    fi
}

# Send backup notification
send_backup_notification() {
    local status="$1"
    local backup_name="$2"
    
    # Email notification
    local email_enabled
    email_enabled=$(jq -r '.notifications.email.enabled' "$BACKUP_CONFIG_FILE")
    
    if [[ "$email_enabled" == "true" ]]; then
        send_email_notification "$status" "$backup_name"
    fi
    
    # Webhook notification
    local webhook_enabled
    webhook_enabled=$(jq -r '.notifications.webhook.enabled' "$BACKUP_CONFIG_FILE")
    
    if [[ "$webhook_enabled" == "true" ]]; then
        send_webhook_notification "$status" "$backup_name"
    fi
}

# Send email notification
send_email_notification() {
    local status="$1"
    local backup_name="$2"
    
    local smtp_server smtp_port username password to_address
    smtp_server=$(jq -r '.notifications.email.smtp_server' "$BACKUP_CONFIG_FILE")
    smtp_port=$(jq -r '.notifications.email.smtp_port' "$BACKUP_CONFIG_FILE")
    username=$(jq -r '.notifications.email.username' "$BACKUP_CONFIG_FILE")
    password=$(jq -r '.notifications.email.password' "$BACKUP_CONFIG_FILE")
    to_address=$(jq -r '.notifications.email.to_address' "$BACKUP_CONFIG_FILE")
    
    local subject="OBS Backup $status: $backup_name"
    local body="Backup operation completed with status: $status\nBackup name: $backup_name\nTimestamp: $(date)"
    
    # Use sendmail or similar tool
    if command -v sendmail > /dev/null 2>&1; then
        {
            echo "To: $to_address"
            echo "Subject: $subject"
            echo ""
            echo "$body"
        } | sendmail "$to_address"
    fi
}

# Send webhook notification
send_webhook_notification() {
    local status="$1"
    local backup_name="$2"
    
    local webhook_url webhook_method
    webhook_url=$(jq -r '.notifications.webhook.url' "$BACKUP_CONFIG_FILE")
    webhook_method=$(jq -r '.notifications.webhook.method' "$BACKUP_CONFIG_FILE")
    
    local payload
    payload=$(jq -n \
        --arg status "$status" \
        --arg backup_name "$backup_name" \
        --arg timestamp "$(date -Iseconds)" \
        '{status: $status, backup_name: $backup_name, timestamp: $timestamp}')
    
    curl -X "$webhook_method" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$webhook_url" || true
}

# Cleanup old backups
cleanup_old_backups() {
    local retention_days
    retention_days=$(jq -r '.backup_settings.retention_days' "$BACKUP_CONFIG_FILE")
    
    log "Cleaning up backups older than $retention_days days..."
    
    find "$BACKUP_DIR" -name "obs-backup-*" -type f -mtime +$retention_days -delete
    find "$BACKUP_DIR" -name "obs-backup-*" -type d -mtime +$retention_days -exec rm -rf {} + 2>/dev/null || true
    
    log "✓ Old backups cleaned up"
}

# Restore backup
restore_backup() {
    local backup_name="$1"
    local restore_targets="${2:-all}"
    
    log "Restoring backup: $backup_name"
    
    # Find backup file
    local backup_path
    if [[ -f "$BACKUP_DIR/$backup_name" ]]; then
        backup_path="$BACKUP_DIR/$backup_name"
    elif [[ -f "$BACKUP_DIR/$backup_name.tar.gz" ]]; then
        backup_path="$BACKUP_DIR/$backup_name.tar.gz"
    elif [[ -d "$BACKUP_DIR/$backup_name" ]]; then
        backup_path="$BACKUP_DIR/$backup_name"
    else
        log "ERROR: Backup not found: $backup_name"
        return 1
    fi
    
    # Extract if compressed
    local restore_dir="/tmp/restore-$$"
    mkdir -p "$restore_dir"
    
    if [[ "$backup_path" == *.tar.gz ]]; then
        log "Extracting compressed backup..."
        tar -xzf "$backup_path" -C "$restore_dir"
        backup_path="$restore_dir/$(basename "$backup_name" .tar.gz)"
    elif [[ -d "$backup_path" ]]; then
        cp -r "$backup_path" "$restore_dir/"
        backup_path="$restore_dir/$(basename "$backup_path")"
    fi
    
    # Read manifest
    local manifest_file="$backup_path/manifest.json"
    if [[ ! -f "$manifest_file" ]]; then
        log "ERROR: Backup manifest not found"
        return 1
    fi
    
    log "Backup manifest:"
    jq '.' "$manifest_file"
    
    # Restore targets
    if [[ "$restore_targets" == "all" ]]; then
        restore_targets=$(jq -r '.files[].target' "$manifest_file")
    fi
    
    for target in $restore_targets; do
        restore_target "$target" "$backup_path"
    done
    
    # Cleanup
    rm -rf "$restore_dir"
    
    log "✓ Backup restored successfully"
}

# Restore specific target
restore_target() {
    local target="$1"
    local backup_path="$2"
    
    local target_backup_dir="$backup_path/$target"
    if [[ ! -d "$target_backup_dir" ]]; then
        log "WARNING: Target not found in backup: $target"
        return 0
    fi
    
    local target_path
    target_path=$(jq -r ".backup_targets.$target.path" "$BACKUP_CONFIG_FILE")
    
    log "Restoring target: $target to $target_path"
    
    # Create backup of current data
    if [[ -d "$target_path" ]]; then
        local current_backup="$target_path.backup-$(date +%Y%m%d-%H%M%S)"
        mv "$target_path" "$current_backup"
        log "Current data backed up to: $current_backup"
    fi
    
    # Restore from backup
    mkdir -p "$(dirname "$target_path")"
    cp -r "$target_backup_dir" "$target_path"
    
    log "✓ Target restored: $target"
}

# List available backups
list_backups() {
    log "Available backups:"
    
    find "$BACKUP_DIR" -name "obs-backup-*" \( -type f -o -type d \) | sort | while read -r backup; do
        local backup_name size created_date
        backup_name=$(basename "$backup")
        
        if [[ -f "$backup" ]]; then
            size=$(du -h "$backup" | cut -f1)
            created_date=$(stat -c %y "$backup" | cut -d' ' -f1)
        elif [[ -d "$backup" ]]; then
            size=$(du -sh "$backup" | cut -f1)
            created_date=$(stat -c %y "$backup" | cut -d' ' -f1)
        fi
        
        echo "  $backup_name ($size, $created_date)"
    done
}

# Schedule automatic backups
schedule_backups() {
    local interval="${1:-daily}"
    
    log "Scheduling automatic backups: $interval"
    
    # Create cron job
    local cron_schedule
    case "$interval" in
        "hourly") cron_schedule="0 * * * *" ;;
        "daily") cron_schedule="0 2 * * *" ;;
        "weekly") cron_schedule="0 2 * * 0" ;;
        "monthly") cron_schedule="0 2 1 * *" ;;
        *) log "ERROR: Invalid interval: $interval"; return 1 ;;
    esac
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$cron_schedule $0 auto-backup") | crontab -
    
    log "✓ Automatic backups scheduled: $interval"
}

# Automatic backup (called by cron)
auto_backup() {
    log "Starting automatic backup..."
    
    local auto_backup_enabled
    auto_backup_enabled=$(jq -r '.backup_settings.auto_backup' "$BACKUP_CONFIG_FILE")
    
    if [[ "$auto_backup_enabled" != "true" ]]; then
        log "Automatic backup is disabled"
        return 0
    fi
    
    create_backup "incremental"
}

# Main function
main() {
    init_backup_system
    
    case "${1:-help}" in
        "create")
            create_backup "$2"
            ;;
        "restore")
            restore_backup "$2" "$3"
            ;;
        "list")
            list_backups
            ;;
        "schedule")
            schedule_backups "$2"
            ;;
        "auto-backup")
            auto_backup
            ;;
        "help"|*)
            echo "OBS Backup and Recovery System"
            echo "Usage: $0 {create|restore|list|schedule|auto-backup}"
            echo ""
            echo "Commands:"
            echo "  create [type]                    - Create backup (full|incremental|differential)"
            echo "  restore <backup_name> [targets] - Restore backup"
            echo "  list                            - List available backups"
            echo "  schedule <interval>             - Schedule automatic backups"
            echo "  auto-backup                     - Run automatic backup (used by cron)"
            echo "  help                            - Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 create full"
            echo "  $0 restore obs-backup-20250120-143000"
            echo "  $0 schedule daily"
            ;;
    esac
}

main "$@"
