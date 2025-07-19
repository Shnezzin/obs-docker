#!/bin/bash
# Desktop Environment Manager for OBS Docker Container
# Supports LXDE, XFCE, KDE, and GNOME

set -euo pipefail

# Configuration
DESKTOP_CONFIG_FILE="/opt/obs-config/desktop-config.json"
XSESSION_FILE="/etc/skel/.xsession"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] DESKTOP: $*" >&2
}

# Initialize desktop configuration
init_desktop_config() {
    mkdir -p "$(dirname "$DESKTOP_CONFIG_FILE")"
    
    if [[ ! -f "$DESKTOP_CONFIG_FILE" ]]; then
        cat > "$DESKTOP_CONFIG_FILE" << 'EOF'
{
  "current_desktop": "lxde",
  "available_desktops": {
    "lxde": {
      "name": "LXDE",
      "description": "Lightweight X11 Desktop Environment",
      "session_command": "startlxde",
      "resource_usage": "low",
      "packages": ["lxde-core", "lxde-common", "lxterminal"]
    },
    "xfce": {
      "name": "XFCE",
      "description": "Xfce Desktop Environment",
      "session_command": "startxfce4",
      "resource_usage": "medium",
      "packages": ["xfce4", "xfce4-goodies", "xfce4-terminal"]
    },
    "kde": {
      "name": "KDE Plasma",
      "description": "KDE Plasma Desktop",
      "session_command": "startkde",
      "resource_usage": "high",
      "packages": ["kde-plasma-desktop", "konsole", "dolphin"]
    },
    "gnome": {
      "name": "GNOME",
      "description": "GNOME Desktop Environment",
      "session_command": "gnome-session",
      "resource_usage": "high",
      "packages": ["gnome-session", "gnome-terminal", "nautilus"]
    }
  },
  "customizations": {
    "theme": "default",
    "wallpaper": "/usr/share/pixmaps/obs-wallpaper.jpg",
    "auto_start_obs": true,
    "hide_desktop_icons": false
  }
}
EOF
        log "Desktop configuration initialized"
    fi
}

# Install desktop environment
install_desktop() {
    local desktop_name="$1"
    
    log "Installing desktop environment: $desktop_name"
    
    # Get package list from config
    local packages
    packages=$(jq -r ".available_desktops.$desktop_name.packages[]" "$DESKTOP_CONFIG_FILE" 2>/dev/null)
    
    if [[ -z "$packages" ]]; then
        log "ERROR: Desktop environment '$desktop_name' not found"
        return 1
    fi
    
    # Update package lists
    apt-get update
    
    # Install packages
    local package_list=""
    while IFS= read -r package; do
        package_list="$package_list $package"
    done <<< "$packages"
    
    log "Installing packages: $package_list"
    DEBIAN_FRONTEND=noninteractive apt-get install -y $package_list
    
    # Desktop-specific configurations
    case "$desktop_name" in
        "lxde")
            configure_lxde
            ;;
        "xfce")
            configure_xfce
            ;;
        "kde")
            configure_kde
            ;;
        "gnome")
            configure_gnome
            ;;
    esac
    
    log "✓ Desktop environment '$desktop_name' installed successfully"
}

# Configure LXDE
configure_lxde() {
    log "Configuring LXDE..."
    
    # Create LXDE autostart directory
    mkdir -p /etc/xdg/lxsession/LXDE/
    
    # Configure LXDE session
    cat > /etc/xdg/lxsession/LXDE/desktop.conf << 'EOF'
[Session]
window_manager=openbox-lxde
windows_manager/command=openbox
windows_manager/session=LXDE
disable_autostart=no
polkit/command=lxpolkit
clipboard/command=lxclipboard
xrandr/command=lxrandr
keyring/command=ssh-agent
quit_manager/command=lxsession-logout
quit_manager/image=/usr/share/lxde/images/logout-banner.png
quit_manager/layout=top

[GTK]
sNet/ThemeName=Clearlooks
sNet/IconThemeName=nuoveXT2
sGtk/FontName=Sans 10
iGtk/ToolbarStyle=3
iGtk/ButtonImages=1
iGtk/MenuImages=1
iGtk/CursorThemeSize=18
iXft/Antialias=1
iXft/Hinting=1
iXft/HintStyle=hintslight
iXft/RGBA=rgb

[Mouse]
AccFactor=20
AccThreshold=10
LeftHanded=0
MiddleButtonEmulation=0

[Keyboard]
Delay=500
Interval=30
Beep=1

[State]
guess_default=true

[Dbus]
lxde=true
EOF

    # Set LXDE as default session
    echo "startlxde" > "$XSESSION_FILE"
}

# Configure XFCE
configure_xfce() {
    log "Configuring XFCE..."
    
    # Create XFCE config directories
    mkdir -p /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/
    
    # Configure XFCE session
    cat > /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-session.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-session" version="1.0">
  <property name="general" type="empty">
    <property name="FailsafeSessionName" type="string" value="Failsafe"/>
    <property name="SessionName" type="string" value="Default"/>
    <property name="SaveOnExit" type="bool" value="true"/>
  </property>
  <property name="sessions" type="empty">
    <property name="Failsafe" type="empty">
      <property name="IsFailsafe" type="bool" value="true"/>
      <property name="Count" type="int" value="5"/>
      <property name="Client0_Command" type="array">
        <value type="string" value="xfwm4"/>
        <value type="string" value="--replace"/>
      </property>
      <property name="Client0_Priority" type="int" value="15"/>
      <property name="Client1_Command" type="array">
        <value type="string" value="xfce4-panel"/>
      </property>
      <property name="Client1_Priority" type="int" value="25"/>
      <property name="Client2_Command" type="array">
        <value type="string" value="xfdesktop"/>
      </property>
      <property name="Client2_Priority" type="int" value="35"/>
      <property name="Client3_Command" type="array">
        <value type="string" value="xfce4-session"/>
        <value type="string" value="--restart"/>
      </property>
      <property name="Client3_Priority" type="int" value="40"/>
    </property>
  </property>
</channel>
EOF

    # Set XFCE as default session
    echo "startxfce4" > "$XSESSION_FILE"
}

# Configure KDE
configure_kde() {
    log "Configuring KDE Plasma..."
    
    # Create KDE config directory
    mkdir -p /etc/kde5/
    
    # Configure KDE session
    cat > /etc/kde5/startkderc << 'EOF'
#!/bin/sh
# KDE startup script

export KDE_SESSION_VERSION=5
export KDE_FULL_SESSION=true
export XDG_CURRENT_DESKTOP=KDE

# Start KDE session
exec /usr/bin/startplasma-x11
EOF

    chmod +x /etc/kde5/startkderc
    
    # Set KDE as default session
    echo "/etc/kde5/startkderc" > "$XSESSION_FILE"
}

# Configure GNOME
configure_gnome() {
    log "Configuring GNOME..."
    
    # Create GNOME session file
    cat > /usr/share/xsessions/gnome-custom.desktop << 'EOF'
[Desktop Entry]
Name=GNOME Custom
Comment=This session logs you into GNOME
Exec=gnome-session --session=gnome
TryExec=gnome-session
Icon=
Type=Application
DesktopNames=GNOME
EOF

    # Set GNOME as default session
    echo "gnome-session" > "$XSESSION_FILE"
}

# Switch desktop environment
switch_desktop() {
    local desktop_name="$1"
    
    log "Switching to desktop environment: $desktop_name"
    
    # Check if desktop is available
    local available
    available=$(jq -r ".available_desktops.$desktop_name" "$DESKTOP_CONFIG_FILE")
    
    if [[ "$available" == "null" ]]; then
        log "ERROR: Desktop environment '$desktop_name' not available"
        list_available_desktops
        return 1
    fi
    
    # Check if desktop is installed
    local session_command
    session_command=$(jq -r ".available_desktops.$desktop_name.session_command" "$DESKTOP_CONFIG_FILE")
    
    if ! command -v "${session_command%% *}" > /dev/null 2>&1; then
        log "Desktop environment '$desktop_name' not installed. Installing..."
        install_desktop "$desktop_name"
    fi
    
    # Update current desktop in config
    local config_tmp
    config_tmp=$(mktemp)
    jq ".current_desktop = \"$desktop_name\"" "$DESKTOP_CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$DESKTOP_CONFIG_FILE"
    
    # Update .xsession for all users
    echo "$session_command" > "$XSESSION_FILE"
    
    # Update existing user sessions
    find /home -name ".xsession" -exec sh -c 'echo "'"$session_command"'" > "$1"' _ {} \;
    
    log "✓ Desktop environment switched to: $desktop_name"
    log "Please restart the container or reconnect via RDP to apply changes"
}

# List available desktop environments
list_available_desktops() {
    log "Available desktop environments:"
    
    jq -r '.available_desktops | to_entries[] | "  \(.key): \(.value.name) - \(.value.description) (Resource usage: \(.value.resource_usage))"' "$DESKTOP_CONFIG_FILE"
}

# Show current desktop
show_current_desktop() {
    local current_desktop
    current_desktop=$(jq -r '.current_desktop' "$DESKTOP_CONFIG_FILE")
    
    log "Current desktop environment: $current_desktop"
    
    local desktop_info
    desktop_info=$(jq -r ".available_desktops.$current_desktop" "$DESKTOP_CONFIG_FILE")
    
    if [[ "$desktop_info" != "null" ]]; then
        echo "Desktop details:"
        jq ".available_desktops.$current_desktop" "$DESKTOP_CONFIG_FILE"
    fi
}

# Customize desktop
customize_desktop() {
    local setting="$1"
    local value="$2"
    
    log "Customizing desktop setting: $setting = $value"
    
    case "$setting" in
        "wallpaper")
            set_wallpaper "$value"
            ;;
        "theme")
            set_theme "$value"
            ;;
        "auto_start_obs")
            set_auto_start_obs "$value"
            ;;
        *)
            log "ERROR: Unknown setting: $setting"
            return 1
            ;;
    esac
    
    # Update configuration
    local config_tmp
    config_tmp=$(mktemp)
    jq ".customizations.$setting = \"$value\"" "$DESKTOP_CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$DESKTOP_CONFIG_FILE"
    
    log "✓ Desktop customization applied"
}

# Set wallpaper
set_wallpaper() {
    local wallpaper_path="$1"
    
    log "Setting wallpaper: $wallpaper_path"
    
    # Copy wallpaper if it's a URL
    if [[ "$wallpaper_path" =~ ^https?:// ]]; then
        local wallpaper_file="/usr/share/pixmaps/custom-wallpaper.jpg"
        curl -L "$wallpaper_path" -o "$wallpaper_file"
        wallpaper_path="$wallpaper_file"
    fi
    
    # Set wallpaper for different desktop environments
    local current_desktop
    current_desktop=$(jq -r '.current_desktop' "$DESKTOP_CONFIG_FILE")
    
    case "$current_desktop" in
        "lxde")
            pcmanfm --set-wallpaper="$wallpaper_path" || true
            ;;
        "xfce")
            xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/workspace0/last-image -s "$wallpaper_path" || true
            ;;
        "kde")
            # KDE wallpaper setting requires more complex configuration
            log "KDE wallpaper setting requires manual configuration"
            ;;
        "gnome")
            gsettings set org.gnome.desktop.background picture-uri "file://$wallpaper_path" || true
            ;;
    esac
}

# Set theme
set_theme() {
    local theme_name="$1"
    
    log "Setting theme: $theme_name"
    
    # This is a simplified theme setting - in practice, themes are desktop-specific
    local current_desktop
    current_desktop=$(jq -r '.current_desktop' "$DESKTOP_CONFIG_FILE")
    
    case "$current_desktop" in
        "lxde"|"xfce")
            # GTK theme setting
            mkdir -p /etc/gtk-3.0/
            echo "[Settings]" > /etc/gtk-3.0/settings.ini
            echo "gtk-theme-name=$theme_name" >> /etc/gtk-3.0/settings.ini
            ;;
        "kde")
            log "KDE theme setting requires KDE-specific configuration"
            ;;
        "gnome")
            gsettings set org.gnome.desktop.interface gtk-theme "$theme_name" || true
            ;;
    esac
}

# Set OBS auto-start
set_auto_start_obs() {
    local auto_start="$1"
    
    log "Setting OBS auto-start: $auto_start"
    
    local autostart_dir="/etc/xdg/autostart"
    local obs_desktop_file="$autostart_dir/obs-studio.desktop"
    
    mkdir -p "$autostart_dir"
    
    if [[ "$auto_start" == "true" ]]; then
        cat > "$obs_desktop_file" << 'EOF'
[Desktop Entry]
Type=Application
Name=OBS Studio
Comment=Free and Open Source Streaming/Recording Software
Exec=obs
Icon=obs
StartupNotify=true
NoDisplay=false
Hidden=false
EOF
    else
        rm -f "$obs_desktop_file"
    fi
}

# Optimize desktop for performance
optimize_desktop() {
    local profile="${1:-balanced}"
    
    log "Optimizing desktop for profile: $profile"
    
    case "$profile" in
        "performance")
            # Disable visual effects
            disable_visual_effects
            # Use lightweight desktop
            switch_desktop "lxde"
            ;;
        "quality")
            # Enable visual effects
            enable_visual_effects
            # Use feature-rich desktop
            switch_desktop "xfce"
            ;;
        "balanced")
            # Balanced settings
            switch_desktop "lxde"
            customize_desktop "theme" "clearlooks"
            ;;
    esac
    
    log "✓ Desktop optimized for $profile profile"
}

# Disable visual effects
disable_visual_effects() {
    log "Disabling visual effects for performance..."
    
    # Disable compositing for various desktop environments
    local current_desktop
    current_desktop=$(jq -r '.current_desktop' "$DESKTOP_CONFIG_FILE")
    
    case "$current_desktop" in
        "xfce")
            xfconf-query -c xfwm4 -p /general/use_compositing -s false || true
            ;;
        "kde")
            # Disable KDE effects
            kwriteconfig5 --file kwinrc --group Compositing --key Enabled false || true
            ;;
    esac
}

# Enable visual effects
enable_visual_effects() {
    log "Enabling visual effects..."
    
    local current_desktop
    current_desktop=$(jq -r '.current_desktop' "$DESKTOP_CONFIG_FILE")
    
    case "$current_desktop" in
        "xfce")
            xfconf-query -c xfwm4 -p /general/use_compositing -s true || true
            ;;
        "kde")
            kwriteconfig5 --file kwinrc --group Compositing --key Enabled true || true
            ;;
    esac
}

# Main function
main() {
    init_desktop_config
    
    case "${1:-help}" in
        "install")
            install_desktop "$2"
            ;;
        "switch")
            switch_desktop "$2"
            ;;
        "list")
            list_available_desktops
            ;;
        "current")
            show_current_desktop
            ;;
        "customize")
            customize_desktop "$2" "$3"
            ;;
        "optimize")
            optimize_desktop "$2"
            ;;
        "help"|*)
            echo "OBS Desktop Environment Manager"
            echo "Usage: $0 {install|switch|list|current|customize|optimize}"
            echo ""
            echo "Commands:"
            echo "  install <desktop>              - Install desktop environment"
            echo "  switch <desktop>               - Switch to desktop environment"
            echo "  list                          - List available desktops"
            echo "  current                       - Show current desktop"
            echo "  customize <setting> <value>   - Customize desktop settings"
            echo "  optimize <profile>            - Optimize desktop (performance|quality|balanced)"
            echo "  help                          - Show this help"
            echo ""
            echo "Available desktops: lxde, xfce, kde, gnome"
            echo "Customization settings: wallpaper, theme, auto_start_obs"
            ;;
    esac
}

main "$@"
