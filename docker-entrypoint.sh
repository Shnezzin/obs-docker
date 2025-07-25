#!/bin/bash -e

# Enhanced logging and error handling
set -euxo pipefail

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

log "Starting OBS Docker container initialization..."

# Get user and password from environment variables
USER=${DEFAULT_USER:-developer}
PASSWD=${DEFAULT_PASSWD:?DEFAULT_PASSWD environment variable is not set}
GROUP=${USER}

# Always use UID/GID 1000 for the user (standard for non-root users)
USER_ID=${USER_ID:-1000}
GROUP_ID=${GROUP_ID:-1000}

log "Configuring user: $USER (UID: $USER_ID, GID: $GROUP_ID)"

# Validate password strength (basic check)
if [[ ${#PASSWD} -lt 8 ]]; then
    log "WARNING: Password is less than 8 characters. Consider using a stronger password."
fi

# Clear environment variables for security
unset DEFAULT_USER DEFAULT_PASSWD

# Add group and user
log "Setting up user and group: $USER:$GROUP ($USER_ID:$GROUP_ID)"
if ! getent group $GROUP >/dev/null 2>&1; then
    groupadd -g $GROUP_ID $GROUP
fi
if ! getent passwd $USER >/dev/null 2>&1; then
    useradd -d /home/$USER -m -s /bin/bash -u $USER_ID -g $GROUP_ID $USER
fi

# Revert permissions for security
log "Reverting SUID permissions for security"
if ! sudo chmod u-s /usr/sbin/useradd /usr/sbin/groupadd; then
    log "WARNING: Failed to revert SUID permissions"
fi

# Nach User-/Gruppenhandling:
HOME=/home/$USER
export HOME

# Ensure .xsession exists and is correct
if [[ ! -e $HOME/.xsession ]]; then
    cp /etc/skel/.xsession $HOME/.xsession 2>/dev/null || echo "startlxde" > $HOME/.xsession
fi
echo "startlxde" > $HOME/.xsession
chown $USER:$GROUP $HOME/.xsession
chmod 644 $HOME/.xsession

# Create LXDE autostart directory
mkdir -p $HOME/.config/lxsession/LXDE/
cat > $HOME/.config/lxsession/LXDE/autostart << 'EOF'
@lxpanel --profile LXDE
@pcmanfm --desktop --profile LXDE
@xscreensaver -no-splash
EOF
chown -R $USER:$GROUP $HOME/.config
chmod -R 755 $HOME/.config

# Generate RDP keys if needed
log "Checking RDP keys"
[[ ! -e /etc/xrdp/rsakeys.ini ]] && \
    sudo -u xrdp -g xrdp xrdp-keygen xrdp /etc/xrdp/rsakeys.ini > /dev/null 2>&1

# Configure XRDP for better desktop support
log "Configuring XRDP for ${DESKTOP_ENV}"

# Set VNC password non-interactively
log "Setting up VNC server"
mkdir -p /home/$USER/.vnc
chown $USER:$GROUP /home/$USER/.vnc
chmod 700 /home/$USER/.vnc
echo "$PASSWD" | vncpasswd -f > /home/$USER/.vnc/passwd
chown $USER:$GROUP /home/$USER/.vnc/passwd
chmod 600 /home/$USER/.vnc/passwd

# Set default command if none provided
if [ $# -eq 0 ]; then
    set -- /usr/bin/supervisord -c /etc/supervisor/xrdp.conf
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
