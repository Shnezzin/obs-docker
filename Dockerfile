FROM ubuntu:22.04 as build

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y make gcc

RUN mkdir /opt/su-exec
COPY su-exec.c /opt/su-exec/
COPY Makefile /opt/su-exec/

RUN cd /opt/su-exec \
    && make

####################################

FROM ubuntu:22.04

ARG ADDITIONAL_APT_GET_OPTS="--no-install-recommends"

RUN echo 'path-include=/usr/share/locale/de/LC_MESSAGES/*.mo' > /etc/dpkg/dpkg.cfg.d/includes \
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
      language-pack-de \
      language-pack-de-base \
      lxde \
      qt6-base-dev \
      sudo \
      supervisor \
      tzdata \
      wget \
      xorg \
      xorgxrdp \
      xrdp

COPY --from=build \
    /opt/su-exec/su-exec /usr/sbin/su-exec

# Set locale
RUN cp /usr/share/zoneinfo/Europe/Berlin /etc/localtime \
    && echo 'Europe/Berlin' > /etc/timezone
RUN locale-gen de_DE.UTF-8 \
    && echo 'LC_ALL=de_DE.UTF-8' > /etc/default/locale \
    && echo 'LANG=de_DE.UTF-8' >> /etc/default/locale
ENV LANG=de_DE.UTF-8 \
    LANGUAGE=de_DE:ja \
    LC_ALL=de_DE.UTF-8

# Set default vars
ENV DEFAULT_USER=developer \
    DEFAULT_PASSWD=xrdppasswd

# Set sudoers for any user
RUN echo "ALL ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/ALL

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

# Install OBS

WORKDIR /root
RUN wget https://github.com/Pi-Apps-Coders/files/releases/download/large-files/obs-studio-30.0.0-1-arm64-jammy.deb \
  && apt install -y /root/obs-studio-30.0.0-1-arm64-jammy.deb
RUN apt-get clean \
    && rm -rf /var/cache/apt/archives/* \
    && rm -rf /var/lib/apt/lists/*

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
