# Build arguments for customization
ARG OBS_VERSION=31.1.1
ARG UBUNTU_VERSION=24.04
ARG LOCALE=en_US.UTF-8
ARG TIMEZONE=UTC
ARG DESKTOP_ENV=lxde
ARG ENABLE_GPU=false
ARG ADDITIONAL_APT_GET_OPTS="--no-install-recommends"

# Build stage for su-exec utility
FROM ubuntu:${UBUNTU_VERSION} as build

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y make gcc \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /opt/su-exec
COPY su-exec.c /opt/su-exec/
COPY Makefile /opt/su-exec/

RUN cd /opt/su-exec \
    && make

####################################

# Main image
FROM ubuntu:${UBUNTU_VERSION}

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

COPY --from=build \
    /opt/su-exec/su-exec /usr/sbin/su-exec

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
