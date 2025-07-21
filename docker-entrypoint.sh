#!/bin/bash -e

# Enhanced logging and error handling
set -euo pipefail

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

log "Starting OBS Docker container initialization..."

# Get user and password from environment variables
USER=${DEFAULT_USER:-developer}
PASSWD=${DEFAULT_PASSWD:-obs123}
GROUP=${USER}

# Always use UID/GID 1000 for the user (standard for non-root users)
USER_ID=1000
GROUP_ID=1000

log "Configuring user: $USER (UID: $USER_ID, GID: $GROUP_ID)"

# Validate password strength (basic check)
if [[ ${#PASSWD} -lt 8 ]]; then
    log "WARNING: Password is less than 8 characters. Consider using a stronger password."
fi

# Clear environment variables for security
unset DEFAULT_USER DEFAULT_PASSWD

# Add group
log "Setting up group: $GROUP (GID: $GROUP_ID)"
if ! getent group $GROUP >/dev/null 2>&1; then
    if ! groupadd -g $GROUP_ID $GROUP; then
        log "WARNING: Failed to create group $GROUP (may already exist)"
    else
        log "Created group: $GROUP"
    fi
else
    log "Group $GROUP already exists"
fi

# Add user
log "Setting up user: $USER (UID: $USER_ID)"
if ! getent passwd $USER >/dev/null 2>&1; then
    export HOME=/home/$USER
    if ! useradd -d ${HOME} -m -s /bin/bash -u $USER_ID -g $GROUP_ID $USER; then
        log "WARNING: Failed to create user $USER (may already exist)"
        # Check if user with UID 1000 exists but different name
        EXISTING_USER=$(getent passwd $USER_ID | cut -d: -f1 2>/dev/null || echo "")
        if [[ -n "$EXISTING_USER" && "$EXISTING_USER" != "$USER" ]]; then
            log "WARNING: User with UID $USER_ID already exists as '$EXISTING_USER'"
            # Rename existing user to our desired name
            if usermod -l $USER $EXISTING_USER; then
                log "Renamed user '$EXISTING_USER' to '$USER'"
            else
                log "WARNING: Could not rename user '$EXISTING_USER' to '$USER'"
            fi
        fi
    else
        log "Created user: $USER with home directory: $HOME"
    fi
else
    log "User $USER already exists"
fi

# Fix group name for GID 1000 if needed
EXISTING_GROUP=$(getent group 1000 | cut -d: -f1)
if [ "$EXISTING_GROUP" != "developer" ] && [ -n "$EXISTING_GROUP" ]; then
    groupmod -n developer "$EXISTING_GROUP"
fi

# Revert permissions for security
log "Reverting SUID permissions for security"
if ! sudo chmod u-s /usr/sbin/useradd /usr/sbin/groupadd; then
    log "WARNING: Failed to revert SUID permissions"
fi

if (( $# == 0 )); then
    # Set login user name
    log "Configuring RDP access for user: $USER"

    # Set login password
    log "Setting user password"
    if ! echo "${USER}:${PASSWD}" | sudo chpasswd; then
        log "WARNING: Failed to set password for user $USER (may already be set)"
    else
        log "Password set successfully for user $USER"
    fi

    # Setup user environment
    log "Setting up user environment"
    
    # Check if user exists and get correct user info
    if getent passwd ${USER} >/dev/null 2>&1; then
        USER_UID=$(id -u ${USER} 2>/dev/null || echo "1000")
        USER_GID=$(id -g ${USER} 2>/dev/null || echo "1000")
        log "User ${USER} exists with UID: ${USER_UID}, GID: ${USER_GID}"
    else
        log "WARNING: User ${USER} does not exist, skipping environment setup"
        USER_UID="1000"
        USER_GID="1000"
    fi
    
    # Ensure .xsession exists and is correct
    if [[ ! -e ${HOME}/.xsession ]]; then
        cp /etc/skel/.xsession ${HOME}/.xsession 2>/dev/null || echo "startlxde" > ${HOME}/.xsession
    fi
    
    # Force correct .xsession content for LXDE
    echo "startlxde" > ${HOME}/.xsession
    
    # Set proper permissions (only if user exists)
    if getent passwd ${USER} >/dev/null 2>&1; then
        chown ${USER}:${GROUP} ${HOME}/.xsession 2>/dev/null || log "WARNING: Could not set ownership of .xsession"
        chmod 644 ${HOME}/.xsession
    fi
    
    # Create LXDE autostart directory
    mkdir -p ${HOME}/.config/lxsession/LXDE/
    
    # Configure LXDE autostart
    cat > ${HOME}/.config/lxsession/LXDE/autostart << 'EOF'
@lxpanel --profile LXDE
@pcmanfm --desktop --profile LXDE
@xscreensaver -no-splash
EOF
    
    # Set proper permissions for autostart (only if user exists)
    if getent passwd ${USER} >/dev/null 2>&1; then
        chown -R ${USER}:${GROUP} ${HOME}/.config 2>/dev/null || log "WARNING: Could not set ownership of .config"
        chmod -R 755 ${HOME}/.config
    fi
    
    # Generate RDP keys if needed
    log "Checking RDP keys"
    [[ ! -e /etc/xrdp/rsakeys.ini ]] && \
        sudo -u xrdp -g xrdp xrdp-keygen xrdp /etc/xrdp/rsakeys.ini > /dev/null 2>&1

    # Configure XRDP for better desktop support
    log "Configuring XRDP for LXDE"
    
    # Backup original XRDP config
    cp /etc/xrdp/xrdp.ini /etc/xrdp/xrdp.ini.backup
    
    # Update XRDP configuration for LXDE
    cat > /etc/xrdp/xrdp.ini << 'EOF'
[Globals]
max_bpp=24
xserverbpp=24
port=3389
use_vsock=false
security_layer=negotiate
crypt_level=high
certificate=
key_file=
ssl_protocols=TLSv1.2, TLSv1.3
autorun=

[Xvnc]
name=Xvnc
lib=libvnc.so
ip=localhost
port=-1
username=ask
password=ask

[Xorg]
name=Xorg
lib=libxup.so
ip=localhost
port=-1
username=ask
password=ask

[LXDE]
name=LXDE
lib=libxup.so
ip=localhost
port=-1
username=ask
password=ask
xserverbpp=24
max_bpp=24
EOF

    # Health check: verify critical services can start
    log "Performing pre-start health checks"
    if ! pgrep -f dbus > /dev/null 2>&1; then
        log "Starting D-Bus for health check"
        sudo service dbus start || log "WARNING: D-Bus service check failed"
    fi

    # Set VNC password for user
    mkdir -p /home/$USER/.vnc
    chown $USER:$GROUP /home/$USER/.vnc
    chmod 700 /home/$USER/.vnc
    if [ ! -f /home/$USER/.vnc/passwd ]; then
        echo "$PASSWD" | vncpasswd -f > /home/$USER/.vnc/passwd
        chown $USER:$GROUP /home/$USER/.vnc/passwd
        chmod 600 /home/$USER/.vnc/passwd
    fi

    # Ensure .xsession exists and is correct
    if [[ ! -e /home/$USER/.xsession ]]; then
        echo "startlxde" > /home/$USER/.xsession
        chown $USER:$GROUP /home/$USER/.xsession
        chmod 644 /home/$USER/.xsession
    fi

    # Start VNC server as user (falls nicht läuft)
    if ! pgrep -u $USER Xtightvnc > /dev/null 2>&1; then
        sudo -u $USER vncserver :1 -geometry 1920x1080 -depth 24
    fi

    # Starte supervisor (managt xrdp, dbus)
    exec /usr/bin/supervisord -c /etc/supervisor/xrdp.conf

    set -- /usr/bin/supervisord -c /etc/supervisor/xrdp.conf
    if [[ $USER_ID != "0" ]]; then
        [[ ! -e /usr/local/bin/_alt-su ]] && \
            sudo install -g $GROUP_ID -m 4750 $(which gosu || which su-exec) /usr/local/bin/_alt-su
        set -- /usr/local/bin/_alt-su root "$@"
    fi
fi
# Clear sensitive variables
unset PASSWD

log "Starting services with command: $*"
log "Container initialization completed successfully"
log "RDP should be available on port 3389"
log "User $USER created with password"
log "#############################"

# Execute the main command
exec "$@"
