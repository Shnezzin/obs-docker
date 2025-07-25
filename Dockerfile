# Build arguments for customization
ARG OBS_VERSION=31.1.1
ARG UBUNTU_VERSION=24.04
ARG LOCALE=en_US.UTF-8
ARG TIMEZONE=UTC
ARG DESKTOP_ENV=lxde
ARG ENABLE_GPU=false
ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=1000
ARG ADDITIONAL_APT_GET_OPTS="--no-install-recommends"

# Build stage for su-exec utility
FROM ubuntu:${UBUNTU_VERSION} as suexec

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       make \
       gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/su-exec
COPY su-exec.c Makefile ./

RUN make \
    && chmod +x su-exec

# Final stage
FROM ubuntu:${UBUNTU_VERSION}

# Set build arguments as environment variables
ARG OBS_VERSION
ARG UBUNTU_VERSION
ARG LOCALE
ARG TIMEZONE
ARG DESKTOP_ENV
ARG ENABLE_GPU
ARG USERNAME
ARG USER_UID
ARG USER_GID
ARG ADDITIONAL_APT_GET_OPTS

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=${LOCALE} \
    LANGUAGE=${LOCALE%.*}:en \
    LC_ALL=${LOCALE} \
    TZ=${TIMEZONE} \
    HOME=/home/${USERNAME} \
    PATH="/home/${USERNAME}/.local/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    DEFAULT_USER=${USERNAME} \
    DEFAULT_PASSWD=SecurePassword123!

# Install system dependencies
RUN apt-get update && apt-get install -y ${ADDITIONAL_APT_GET_OPTS} \
    # Base packages
    sudo \
    curl \
    wget \
    gnupg2 \
    ca-certificates \
    tzdata \
    locales \
    dbus-x11 \
    supervisor \
    # OBS dependencies
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxtst6 \
    libpulse0 \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    libpci3 \
    # Desktop environment and RDP
    xorg \
    xrdp \
    xorgxrdp \
    tigervnc-standalone-server \
    # Development tools
    git \
    python3 \
    python3-pip \
    python3-venv \
    # Networking tools
    net-tools \
    # Install desktop environment based on build arg
    && case "$DESKTOP_ENV" in \
         "lxde") apt-get install -y ${ADDITIONAL_APT_GET_OPTS} lxde-core lxterminal lxappearance ;; \
         "xfce") apt-get install -y ${ADDITIONAL_APT_GET_OPTS} xfce4 xfce4-goodies ;; \
         "kde") apt-get install -y ${ADDITIONAL_APT_GET_OPTS} kde-plasma-desktop ;; \
         "gnome") apt-get install -y ${ADDITIONAL_APT_GET_OPTS} gnome-session gnome-terminal ;; \
         *) apt-get install -y ${ADDITIONAL_APT_GET_OPTS} lxde-core lxterminal lxappearance ;; \
       esac \
    # Install GPU support if enabled
    && if [ "$ENABLE_GPU" = "true" ]; then \
         apt-get install -y ${ADDITIONAL_APT_GET_OPTS} \
           mesa-utils \
           vainfo \
           intel-media-va-driver \
           i965-va-driver || true; \
       fi \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

# Configure timezone and locale
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && locale-gen ${LOCALE} \
    && echo "LC_ALL=${LOCALE}" > /etc/default/locale \
    && echo "LANG=${LOCALE}" >> /etc/default/locale

# Create groups and users
RUN groupadd -r xrdp \
    && useradd -r -g xrdp xrdp \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && mkdir -p /home/$USERNAME/.local/bin \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME

# Copy su-exec from build stage
COPY --from=suexec /opt/su-exec/su-exec /usr/local/bin/su-exec

# Configure XRDP and desktop environment
RUN echo "startlxde" > /etc/skel/.xsession \
    && install -o root -g xrdp -m 2775 -d /var/run/xrdp \
    && install -o root -g xrdp -m 3777 -d /var/run/xrdp/sockdir \
    && install -o root -g root -m 0755 -d /var/run/dbus \
    && sed -i 's|.*pam_systemd.so|#&|g' /etc/pam.d/common-session \
    && usermod -aG ssl-cert xrdp

# Set supervisord configuration for services
RUN { \
      echo "[supervisord]"; \
      echo "user=root"; \
      echo "nodaemon=true"; \
      echo "logfile=/var/log/supervisor/supervisord.log"; \
      echo "childlogdir=/var/log/supervisor"; \
      echo "[program:dbus]"; \
      echo "command=/usr/bin/dbus-daemon --system --nofork --nopidfile"; \
      echo "[program:xrdp-sesman]"; \
      echo "command=/usr/sbin/xrdp-sesman --nodaemon"; \
      echo "[program:xrdp]"; \
      echo "command=/usr/sbin/xrdp --nodaemon"; \
      echo "user=xrdp"; \
    } > /etc/supervisor/xrdp.conf

# Install OBS Studio
RUN ARCH=$(dpkg --print-architecture) \
    && echo "Installing OBS Studio ${OBS_VERSION} for architecture: $ARCH" \
    && apt-get update \
    && if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "arm64" ]; then \
         # Try official PPA first
         apt-get install -y ${ADDITIONAL_APT_GET_OPTS} software-properties-common \
         && add-apt-repository -y ppa:obsproject/obs-studio \
         && apt-get update \
         && apt-get install -y ${ADDITIONAL_APT_GET_OPTS} obs-studio; \
       else \
         # For other architectures, install from default repos
         apt-get install -y ${ADDITIONAL_APT_GET_OPTS} obs-studio || \
         echo "OBS Studio not available for this architecture"; \
       fi \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Set up application directory
WORKDIR /app

# Copy application code
COPY . .

# Copy scripts and set permissions
COPY scripts/ /scripts/
RUN chmod +x /app/docker-entrypoint.sh \
    && chmod +x /scripts/*.sh \
    && mkdir -p /opt/obs-config /opt/obs-instances /opt/obs-backups \
    && chown -R $USERNAME:$USERNAME /opt/obs-* /app

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /scripts/health-check.sh || exit 1

# Expose ports
EXPOSE 3389 5900 8080

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
