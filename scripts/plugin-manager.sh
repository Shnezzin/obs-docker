#!/bin/bash
# OBS Plugin Manager - Install and manage OBS Studio plugins
# Supports both native OBS and Flatpak installations

set -euo pipefail

# Configuration
PLUGIN_DIR="/opt/obs-plugins"
FLATPAK_PLUGIN_DIR="$HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins"
CONFIG_FILE="/opt/obs-config/plugins.json"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] PLUGIN: $*" >&2
}

# Create directories
mkdir -p "$PLUGIN_DIR" "$FLATPAK_PLUGIN_DIR" "$(dirname "$CONFIG_FILE")"

# Initialize plugin config if not exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    cat > "$CONFIG_FILE" << 'EOF'
{
  "plugins": {},
  "repositories": {
    "obs-websocket": {
      "url": "https://github.com/obsproject/obs-websocket/releases/latest",
      "type": "github_release",
      "description": "WebSocket API for OBS Studio"
    },
    "obs-browser": {
      "url": "https://github.com/obsproject/obs-browser/releases/latest", 
      "type": "github_release",
      "description": "Browser source plugin"
    },
    "streamfx": {
      "url": "https://github.com/Xaymar/obs-StreamFX/releases/latest",
      "type": "github_release", 
      "description": "Advanced effects and filters"
    },
    "obs-backgroundremoval": {
      "url": "https://github.com/royshil/obs-backgroundremoval/releases/latest",
      "type": "github_release",
      "description": "AI background removal"
    },
    "obs-multi-rtmp": {
      "url": "https://github.com/sorayuki/obs-multi-rtmp/releases/latest",
      "type": "github_release",
      "description": "Multi-platform streaming"
    }
  }
}
EOF
fi

# Detect OBS installation type
detect_obs_type() {
    if command -v obs > /dev/null 2>&1; then
        echo "native"
    elif flatpak list | grep -q "com.obsproject.Studio" 2>/dev/null; then
        echo "flatpak"
    else
        echo "none"
    fi
}

# Download plugin from GitHub release
download_github_plugin() {
    local plugin_name="$1"
    local repo_url="$2"
    local temp_dir="/tmp/obs-plugin-$plugin_name"
    
    log "Downloading $plugin_name from GitHub..."
    
    # Get latest release info
    local api_url="${repo_url/github.com/api.github.com/repos}"
    api_url="${api_url/releases\/latest/releases/latest}"
    
    local download_url
    download_url=$(curl -s "$api_url" | jq -r '.assets[] | select(.name | contains("linux") or contains("ubuntu") or contains(".deb")) | .browser_download_url' | head -1)
    
    if [[ -z "$download_url" || "$download_url" == "null" ]]; then
        log "ERROR: Could not find suitable download for $plugin_name"
        return 1
    fi
    
    mkdir -p "$temp_dir"
    cd "$temp_dir"
    
    log "Downloading from: $download_url"
    curl -L -o "plugin.archive" "$download_url"
    
    # Extract based on file type
    if file plugin.archive | grep -q "Debian"; then
        dpkg-deb -x plugin.archive extracted/
    elif file plugin.archive | grep -q "gzip"; then
        tar -xzf plugin.archive
    elif file plugin.archive | grep -q "Zip"; then
        unzip -q plugin.archive
    else
        log "WARNING: Unknown archive format for $plugin_name"
        return 1
    fi
    
    echo "$temp_dir"
}

# Install plugin for native OBS
install_native_plugin() {
    local plugin_name="$1"
    local temp_dir="$2"
    
    log "Installing $plugin_name for native OBS..."
    
    # Find plugin files
    local plugin_files
    plugin_files=$(find "$temp_dir" -name "*.so" -o -name "obs-*" -type f)
    
    if [[ -z "$plugin_files" ]]; then
        log "ERROR: No plugin files found for $plugin_name"
        return 1
    fi
    
    # Copy to plugin directory
    mkdir -p "$PLUGIN_DIR/$plugin_name"
    cp -r "$temp_dir"/* "$PLUGIN_DIR/$plugin_name/"
    
    # Update plugin registry
    local config_tmp
    config_tmp=$(mktemp)
    jq ".plugins[\"$plugin_name\"] = {\"status\": \"installed\", \"type\": \"native\", \"installed_at\": \"$(date -Iseconds)\"}" "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ $plugin_name installed successfully"
}

# Install plugin for Flatpak OBS
install_flatpak_plugin() {
    local plugin_name="$1"
    local temp_dir="$2"
    
    log "Installing $plugin_name for Flatpak OBS..."
    
    # Create Flatpak plugin directory
    mkdir -p "$FLATPAK_PLUGIN_DIR/$plugin_name"
    cp -r "$temp_dir"/* "$FLATPAK_PLUGIN_DIR/$plugin_name/"
    
    # Update plugin registry
    local config_tmp
    config_tmp=$(mktemp)
    jq ".plugins[\"$plugin_name\"] = {\"status\": \"installed\", \"type\": \"flatpak\", \"installed_at\": \"$(date -Iseconds)\"}" "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ $plugin_name installed for Flatpak OBS"
}

# Install plugin
install_plugin() {
    local plugin_name="$1"
    
    if [[ -z "$plugin_name" ]]; then
        log "ERROR: Plugin name required"
        return 1
    fi
    
    # Check if plugin exists in repository
    local repo_url
    repo_url=$(jq -r ".repositories[\"$plugin_name\"].url" "$CONFIG_FILE")
    
    if [[ "$repo_url" == "null" ]]; then
        log "ERROR: Plugin '$plugin_name' not found in repository"
        list_available_plugins
        return 1
    fi
    
    # Check if already installed
    local status
    status=$(jq -r ".plugins[\"$plugin_name\"].status" "$CONFIG_FILE")
    
    if [[ "$status" == "installed" ]]; then
        log "Plugin '$plugin_name' is already installed"
        return 0
    fi
    
    # Detect OBS type
    local obs_type
    obs_type=$(detect_obs_type)
    
    if [[ "$obs_type" == "none" ]]; then
        log "ERROR: OBS Studio not found"
        return 1
    fi
    
    # Download plugin
    local temp_dir
    temp_dir=$(download_github_plugin "$plugin_name" "$repo_url")
    
    if [[ $? -ne 0 ]]; then
        log "ERROR: Failed to download $plugin_name"
        return 1
    fi
    
    # Install based on OBS type
    case "$obs_type" in
        "native")
            install_native_plugin "$plugin_name" "$temp_dir"
            ;;
        "flatpak")
            install_flatpak_plugin "$plugin_name" "$temp_dir"
            ;;
    esac
    
    # Cleanup
    rm -rf "$temp_dir"
}

# Remove plugin
remove_plugin() {
    local plugin_name="$1"
    
    if [[ -z "$plugin_name" ]]; then
        log "ERROR: Plugin name required"
        return 1
    fi
    
    local status
    status=$(jq -r ".plugins[\"$plugin_name\"].status" "$CONFIG_FILE")
    
    if [[ "$status" != "installed" ]]; then
        log "Plugin '$plugin_name' is not installed"
        return 1
    fi
    
    local plugin_type
    plugin_type=$(jq -r ".plugins[\"$plugin_name\"].type" "$CONFIG_FILE")
    
    # Remove plugin files
    case "$plugin_type" in
        "native")
            rm -rf "$PLUGIN_DIR/$plugin_name"
            ;;
        "flatpak")
            rm -rf "$FLATPAK_PLUGIN_DIR/$plugin_name"
            ;;
    esac
    
    # Update plugin registry
    local config_tmp
    config_tmp=$(mktemp)
    jq "del(.plugins[\"$plugin_name\"])" "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ $plugin_name removed successfully"
}

# List available plugins
list_available_plugins() {
    log "Available plugins:"
    jq -r '.repositories | to_entries[] | "  \(.key): \(.value.description)"' "$CONFIG_FILE"
}

# List installed plugins
list_installed_plugins() {
    log "Installed plugins:"
    jq -r '.plugins | to_entries[] | select(.value.status == "installed") | "  \(.key) (\(.value.type)) - installed \(.value.installed_at)"' "$CONFIG_FILE"
}

# Update all plugins
update_plugins() {
    log "Updating all installed plugins..."
    
    local plugins
    plugins=$(jq -r '.plugins | to_entries[] | select(.value.status == "installed") | .key' "$CONFIG_FILE")
    
    for plugin in $plugins; do
        log "Updating $plugin..."
        remove_plugin "$plugin"
        install_plugin "$plugin"
    done
}

# Main function
main() {
    case "${1:-help}" in
        "install")
            install_plugin "$2"
            ;;
        "remove")
            remove_plugin "$2"
            ;;
        "list")
            list_installed_plugins
            ;;
        "available")
            list_available_plugins
            ;;
        "update")
            update_plugins
            ;;
        "help"|*)
            echo "OBS Plugin Manager"
            echo "Usage: $0 {install|remove|list|available|update} [plugin_name]"
            echo ""
            echo "Commands:"
            echo "  install <plugin>   - Install a plugin"
            echo "  remove <plugin>    - Remove a plugin"
            echo "  list              - List installed plugins"
            echo "  available         - List available plugins"
            echo "  update            - Update all installed plugins"
            echo "  help              - Show this help"
            ;;
    esac
}

main "$@"
