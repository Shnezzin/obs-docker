# Build arguments for customization
ARG OBS_VERSION=31.1.1
ARG UBUNTU_VERSION=24.04
ARG LOCALE=en_US.UTF-8
ARG TIMEZONE=UTC
ARG DESKTOP_ENV=lxde
ARG ENABLE_GPU=false
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

# Build stage for Python dependencies
FROM python:3.11-slim as python-base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Install Poetry
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && chmod +x /opt/poetry/bin/poetry \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements to cache them in docker layer
COPY web/pyproject.toml web/poetry.lock* ./

# Install runtime dependencies
RUN poetry install --no-dev --no-root

# Final stage
FROM ubuntu:${UBUNTU_VERSION}

# Set build arguments
ARG OBS_VERSION=31.1.1
ARG UBUNTU_VERSION=24.04
ARG LOCALE=en_US.UTF-8
ARG TIMEZONE=UTC
ARG DESKTOP_ENV=lxde
ARG ENABLE_GPU=false
ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=1000

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=${LOCALE} \
    LANGUAGE=${LOCALE%.*}:en \
    LC_ALL=${LOCALE} \
    TZ=${TIMEZONE} \
    HOME=/home/${USERNAME} \
    PATH="/home/${USERNAME}/.local/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Base packages
    sudo \
    curl \
    wget \
    gnupg2 \
    ca-certificates \
    tzdata \
    locales \
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
    # Desktop environment
    lxde-core \
    lxterminal \
    lxappearance \
    xrdp \
    xorgxrdp \
    # Development tools
    git \
    python3 \
    python3-pip \
    python3-venv \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

# Configure timezone and locale
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && update-locale LANG=$LANG LC_ALL=$LC_ALL LANGUAGE=$LANGUAGE

# Create non-root user and setup permissions
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && mkdir -p /home/$USERNAME/.local/bin \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME

# Copy su-exec from build stage
COPY --from=suexec /opt/su-exec/su-exec /usr/local/bin/su-exec

# Copy Python dependencies from python-base
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

# Set up application directory
WORKDIR /app

# Copy application code
COPY . .

# Set up volumes and permissions
RUN mkdir -p /opt/obs-config /opt/obs-instances /opt/obs-backups \
    && chown -R $USERNAME:$USERNAME /opt/obs-* \
    && chmod +x /app/docker-entrypoint.sh /app/docker-entrypoint-vnc.sh

# Switch to non-root user
USER $USERNAME

# Expose ports
EXPOSE 8080 3389 5900

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Copy build arguments to environment for runtime access
ARG LOCALE
ARG TIMEZONE
ARG OBS_VERSION
ARG ADDITIONAL_APT_GET_OPTS

# Create non-root user early for security
RUN groupadd -r xrdp && useradd -r -g xrdp xrdp

# Configure locale path based on build argument
RUN echo "path-include=/usr/share/locale/${LOCALE%.*}/LC_MESSAGES/*.mo" > /etc/dpkg/dpkg.cfg.d/includes \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y $ADDITIONAL_APT_GET_OPTS \
      dbus-x11 \
      fonts-noto-cjk \
      ibus \
      ibus-gtk \
      ibus-gtk3 \
      ibus-gtk4 \
      ibus-mozc \
      im-config \
      language-pack-en \
      language-pack-en-base \
      qt6-base-dev \
      sudo \
      supervisor \
      tzdata \
      wget \
      xorg \
      xorgxrdp \
      xrdp \
      curl \
      jq \
      bc \
      netstat-nat \
      nginx \
      openssl \
      ca-certificates \
    && if [ "$ENABLE_GPU" = "true" ]; then \
         apt-get install -y \
           nvidia-utils-535 \
           libnvidia-encode-535 \
           mesa-utils \
           vainfo \
           intel-media-va-driver \
           i965-va-driver || true; \
       fi \
    && case "$DESKTOP_ENV" in \
         "lxde") apt-get install -y lxde ;; \
         "xfce") apt-get install -y xfce4 xfce4-goodies ;; \
         "kde") apt-get install -y kde-plasma-desktop ;; \
         "gnome") apt-get install -y gnome-session gnome-terminal ;; \
         *) apt-get install -y lxde ;; \
       esac

# Set timezone and locale dynamically
RUN rm -f /etc/localtime \
    && ln -sf /usr/share/zoneinfo/${TIMEZONE} /etc/localtime \
    && echo "${TIMEZONE}" > /etc/timezone
RUN locale-gen ${LOCALE} \
    && echo "LC_ALL=${LOCALE}" > /etc/default/locale \
    && echo "LANG=${LOCALE}" >> /etc/default/locale
ENV LANG=${LOCALE} \
    LANGUAGE=${LOCALE%.*}:ja \
    LC_ALL=${LOCALE}

# Set default vars
ENV DEFAULT_USER=developer \
    DEFAULT_PASSWD=xrdppasswd

# Set more restrictive sudoers - only allow specific commands
RUN echo "ALL ALL=(ALL) NOPASSWD: /usr/sbin/useradd, /usr/sbin/groupadd, /usr/bin/chpasswd" >> /etc/sudoers.d/LIMITED

# Change permission so that non-root user can add users and groups
RUN chmod u+s /usr/sbin/useradd \
    && chmod u+s /usr/sbin/groupadd

# Expose RDP port
EXPOSE 3389

RUN echo "startlxde" > /etc/skel/.xsession \
    && install -o root -g xrdp -m 2775 -d /var/run/xrdp \
    && install -o root -g xrdp -m 3777 -d /var/run/xrdp/sockdir \
    && install -o root -g root -m 0755 -d /var/run/dbus \
    && install -o root -g root -m 0644 /dev/null /etc/securetty \
    && sed -i 's|.*pam_systemd.so|#&|g' /etc/pam.d/common-session \
    && sed -i 's|\[Session\]|&\npolkit/command=|' /etc/xdg/lxsession/LXDE/desktop.conf \
    && usermod -aG ssl-cert xrdp \
    && ln -s /usr/share/lxde/wallpapers/lxde_blue.jpg /etc/alternatives/desktop-background

# Set supervisord conf for xrdp service
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

# Install OBS with architecture detection
WORKDIR /tmp

# Install OBS Studio using official repositories and Flatpak for better multi-arch support
RUN ARCH=$(dpkg --print-architecture) \
    && echo "Installing OBS Studio ${OBS_VERSION} for architecture: $ARCH" \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
       flatpak \
       software-properties-common \
       gpg-agent \
    && flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo \
    && if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "arm64" ]; then \
         # Try official PPA first (Ubuntu 24.04+)
         add-apt-repository -y ppa:obsproject/obs-studio || true; \
         apt-get update || true; \
         apt-get install -y obs-studio || \
         # Fallback to Flatpak if PPA fails
         flatpak install -y flathub com.obsproject.Studio; \
       else \
         # For other architectures, use Flatpak
         flatpak install -y flathub com.obsproject.Studio; \
       fi \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get clean \
    && rm -rf /var/cache/apt/archives/* \
    && rm -rf /var/lib/apt/lists/*

# Copy scripts
COPY docker-entrypoint.sh /usr/local/bin/
COPY scripts/ /scripts/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /scripts/*.sh

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /scripts/health-check.sh

ENTRYPOINT ["docker-entrypoint.sh"]

RUN apt-get update && \
    apt-get install -y xrdp tigervnc-standalone-server lxde supervisor dbus-x11 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 3389 5901
