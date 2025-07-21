#!/bin/bash -e

# Enhanced logging and error handling
set -euo pipefail

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

log "Starting OBS Docker container initialization with VNC..."

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

# Revert permissions for security
log "Reverting SUID permissions for security"
if ! sudo chmod u-s /usr/sbin/useradd /usr/sbin/groupadd; then
    log "WARNING: Failed to revert SUID permissions"
fi

if (( $# == 0 )); then
    # Set login user name
    log "Configuring VNC access for user: $USER"

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
    
    # Install VNC server if not already installed
    log "Installing VNC server..."
    apt-get update && apt-get install -y tightvncserver xvfb
    
    # Create VNC startup script
    cat > /usr/local/bin/start-vnc.sh << 'EOF'
#!/bin/bash
export DISPLAY=:1
Xvfb :1 -screen 0 1920x1080x24 &
sleep 2
startlxde &
EOF
    chmod +x /usr/local/bin/start-vnc.sh
    
    # Create VNC password file
    mkdir -p /home/${USER}/.vnc
    echo "${PASSWD}" | vncpasswd -f > /home/${USER}/.vnc/passwd
    chown -R ${USER}:${GROUP} /home/${USER}/.vnc
    chmod 600 /home/${USER}/.vnc/passwd
    
    # Set supervisord conf for VNC service
    cat > /etc/supervisor/vnc.conf << 'EOF'
[supervisord]
user=root
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
childlogdir=/var/log/supervisor

[program:dbus]
command=/usr/bin/dbus-daemon --system --nofork --nopidfile

[program:vncserver]
command=/usr/bin/vncserver :1 -geometry 1920x1080 -depth 24 -localhost no
user=developer
environment=DISPLAY=":1",HOME="/home/developer"
autostart=true
autorestart=true
EOF

    # Health check: verify critical services can start
    log "Performing pre-start health checks"
    if ! pgrep -f dbus > /dev/null 2>&1; then
        log "Starting D-Bus for health check"
        sudo service dbus start || log "WARNING: D-Bus service check failed"
    fi

    set -- /usr/bin/supervisord -c /etc/supervisor/vnc.conf
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
log "VNC should be available on port 5901"
log "User $USER created with password"
log "#############################"

# Execute the main command
exec "$@" 