# Stage 1: Builder
FROM ubuntu:22.04 AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    make \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and build su-exec
WORKDIR /opt/su-exec
COPY su-exec.c Makefile ./
RUN make && chmod +x su-exec

# Stage 2: Final Image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    TZ=UTC \
    HOME=/home/developer \
    PATH="/home/developer/.local/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    sudo \
    curl \
    wget \
    gnupg2 \
    ca-certificates \
    tzdata \
    locales \
    dbus-x11 \
    supervisor \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxtst6 \
    libpulse0 \
    libgl1 \
    libglx-mesa0 \
    libpci3 \
    xorg \
    xrdp \
    xorgxrdp \
    tigervnc-standalone-server \
    tigervnc-tools \
    git \
    python3 \
    python3-pip \
    python3-venv \
    net-tools \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure timezone and locale
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata && \
    locale-gen en_US.UTF-8

# Create non-root user
RUN groupadd -g 1000 developer && \
    useradd -u 1000 -g 1000 -m -s /bin/bash developer && \
    echo "developer ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Copy su-exec from builder stage
COPY --from=builder /opt/su-exec/su-exec /usr/local/bin/

# Set up supervisord
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy application code
WORKDIR /app
COPY . .

# Set permissions
RUN chown -R developer:developer /app && \
    chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER developer

# Expose ports
EXPOSE 8080 3389 5900

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
