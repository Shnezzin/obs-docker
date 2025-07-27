#!/bin/bash
set -e

# Set VNC password
mkdir -p /home/developer/.vnc
if [ -n "$VNC_PASSWORD" ]; then
    echo "$VNC_PASSWORD" | vncpasswd -f > /home/developer/.vnc/passwd
    chmod 600 /home/developer/.vnc/passwd
fi

# Start supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
