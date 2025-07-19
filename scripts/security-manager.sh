#!/bin/bash
# Security Manager for OBS Docker Container
# Implements SSL/TLS, VPN, and enhanced authentication

set -euo pipefail

# Configuration
SECURITY_DIR="/opt/security"
SSL_DIR="$SECURITY_DIR/ssl"
VPN_DIR="$SECURITY_DIR/vpn"
AUTH_DIR="$SECURITY_DIR/auth"
CONFIG_FILE="$SECURITY_DIR/security-config.json"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] SECURITY: $*" >&2
}

# Initialize security configuration
init_security() {
    mkdir -p "$SECURITY_DIR" "$SSL_DIR" "$VPN_DIR" "$AUTH_DIR"
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        cat > "$CONFIG_FILE" << 'EOF'
{
  "ssl": {
    "enabled": false,
    "cert_file": "/opt/security/ssl/server.crt",
    "key_file": "/opt/security/ssl/server.key",
    "ca_file": "/opt/security/ssl/ca.crt",
    "auto_renew": true
  },
  "vpn": {
    "enabled": false,
    "type": "wireguard",
    "config_file": "/opt/security/vpn/wg0.conf",
    "allowed_ips": ["10.0.0.0/24"]
  },
  "authentication": {
    "mfa_enabled": false,
    "totp_secret": "",
    "failed_attempts_limit": 5,
    "lockout_duration": 300,
    "password_policy": {
      "min_length": 12,
      "require_uppercase": true,
      "require_lowercase": true,
      "require_numbers": true,
      "require_symbols": true
    }
  },
  "firewall": {
    "enabled": true,
    "allowed_ports": [3389, 22, 80, 443],
    "blocked_countries": [],
    "rate_limiting": true
  }
}
EOF
        log "Security configuration initialized"
    fi
}

# Generate SSL certificates
generate_ssl_cert() {
    local domain="${1:-localhost}"
    
    log "Generating SSL certificate for $domain..."
    
    # Generate private key
    openssl genrsa -out "$SSL_DIR/server.key" 2048
    
    # Generate certificate signing request
    openssl req -new -key "$SSL_DIR/server.key" -out "$SSL_DIR/server.csr" -subj "/C=US/ST=State/L=City/O=Organization/CN=$domain"
    
    # Generate self-signed certificate
    openssl x509 -req -days 365 -in "$SSL_DIR/server.csr" -signkey "$SSL_DIR/server.key" -out "$SSL_DIR/server.crt"
    
    # Set proper permissions
    chmod 600 "$SSL_DIR/server.key"
    chmod 644 "$SSL_DIR/server.crt"
    
    # Update configuration
    local config_tmp
    config_tmp=$(mktemp)
    jq '.ssl.enabled = true' "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ SSL certificate generated successfully"
}

# Configure SSL for XRDP
configure_xrdp_ssl() {
    log "Configuring XRDP with SSL..."
    
    # Backup original XRDP config
    cp /etc/xrdp/xrdp.ini /etc/xrdp/xrdp.ini.backup
    
    # Update XRDP configuration for SSL
    cat >> /etc/xrdp/xrdp.ini << EOF

[Globals]
ssl_protocols=TLSv1.2, TLSv1.3
certificate=$SSL_DIR/server.crt
key_file=$SSL_DIR/server.key
security_layer=tls
crypt_level=high
EOF
    
    # Restart XRDP service
    supervisorctl restart xrdp || systemctl restart xrdp || true
    
    log "✓ XRDP SSL configuration applied"
}

# Setup WireGuard VPN
setup_wireguard() {
    local server_ip="$1"
    local client_count="${2:-5}"
    
    log "Setting up WireGuard VPN..."
    
    # Install WireGuard
    apt-get update && apt-get install -y wireguard
    
    # Generate server keys
    wg genkey | tee "$VPN_DIR/server_private.key" | wg pubkey > "$VPN_DIR/server_public.key"
    
    # Create server configuration
    cat > "$VPN_DIR/wg0.conf" << EOF
[Interface]
PrivateKey = $(cat "$VPN_DIR/server_private.key")
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

EOF
    
    # Generate client configurations
    for i in $(seq 1 "$client_count"); do
        local client_private client_public
        client_private=$(wg genkey)
        client_public=$(echo "$client_private" | wg pubkey)
        
        # Add peer to server config
        cat >> "$VPN_DIR/wg0.conf" << EOF
[Peer]
PublicKey = $client_public
AllowedIPs = 10.0.0.$((i+1))/32

EOF
        
        # Create client config
        cat > "$VPN_DIR/client$i.conf" << EOF
[Interface]
PrivateKey = $client_private
Address = 10.0.0.$((i+1))/24
DNS = 8.8.8.8

[Peer]
PublicKey = $(cat "$VPN_DIR/server_public.key")
Endpoint = $server_ip:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
    done
    
    # Enable IP forwarding
    echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
    sysctl -p
    
    # Start WireGuard
    wg-quick up "$VPN_DIR/wg0.conf"
    
    # Update configuration
    local config_tmp
    config_tmp=$(mktemp)
    jq '.vpn.enabled = true' "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ WireGuard VPN configured successfully"
    log "Client configurations saved in $VPN_DIR/client*.conf"
}

# Setup Multi-Factor Authentication
setup_mfa() {
    local user="$1"
    
    log "Setting up MFA for user: $user"
    
    # Install Google Authenticator
    apt-get update && apt-get install -y libpam-google-authenticator
    
    # Generate TOTP secret
    local totp_secret
    totp_secret=$(head -c 32 /dev/urandom | base32)
    
    # Configure PAM for MFA
    if ! grep -q "auth required pam_google_authenticator.so" /etc/pam.d/xrdp-sesman; then
        echo "auth required pam_google_authenticator.so" >> /etc/pam.d/xrdp-sesman
    fi
    
    # Create user MFA config
    mkdir -p "/home/$user/.google_authenticator"
    cat > "/home/$user/.google_authenticator" << EOF
$totp_secret
" RATE_LIMIT 3 30
" WINDOW_SIZE 17
" DISALLOW_REUSE
" TOTP_AUTH
EOF
    
    chown -R "$user:$user" "/home/$user/.google_authenticator"
    chmod 600 "/home/$user/.google_authenticator"
    
    # Update configuration
    local config_tmp
    config_tmp=$(mktemp)
    jq ".authentication.mfa_enabled = true | .authentication.totp_secret = \"$totp_secret\"" "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ MFA configured for user: $user"
    log "TOTP Secret: $totp_secret"
    log "Add this to your authenticator app"
}

# Configure firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Install UFW
    apt-get update && apt-get install -y ufw
    
    # Reset firewall
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Get allowed ports from config
    local allowed_ports
    allowed_ports=$(jq -r '.firewall.allowed_ports[]' "$CONFIG_FILE")
    
    for port in $allowed_ports; do
        ufw allow "$port"
        log "Allowed port: $port"
    done
    
    # Enable rate limiting for SSH and RDP
    ufw limit 22/tcp
    ufw limit 3389/tcp
    
    # Enable firewall
    ufw --force enable
    
    # Update configuration
    local config_tmp
    config_tmp=$(mktemp)
    jq '.firewall.enabled = true' "$CONFIG_FILE" > "$config_tmp"
    mv "$config_tmp" "$CONFIG_FILE"
    
    log "✓ Firewall configured successfully"
}

# Password policy enforcement
enforce_password_policy() {
    local password="$1"
    
    local min_length require_uppercase require_lowercase require_numbers require_symbols
    min_length=$(jq -r '.authentication.password_policy.min_length' "$CONFIG_FILE")
    require_uppercase=$(jq -r '.authentication.password_policy.require_uppercase' "$CONFIG_FILE")
    require_lowercase=$(jq -r '.authentication.password_policy.require_lowercase' "$CONFIG_FILE")
    require_numbers=$(jq -r '.authentication.password_policy.require_numbers' "$CONFIG_FILE")
    require_symbols=$(jq -r '.authentication.password_policy.require_symbols' "$CONFIG_FILE")
    
    # Check length
    if [[ ${#password} -lt $min_length ]]; then
        log "ERROR: Password must be at least $min_length characters long"
        return 1
    fi
    
    # Check uppercase
    if [[ "$require_uppercase" == "true" ]] && [[ ! "$password" =~ [A-Z] ]]; then
        log "ERROR: Password must contain uppercase letters"
        return 1
    fi
    
    # Check lowercase
    if [[ "$require_lowercase" == "true" ]] && [[ ! "$password" =~ [a-z] ]]; then
        log "ERROR: Password must contain lowercase letters"
        return 1
    fi
    
    # Check numbers
    if [[ "$require_numbers" == "true" ]] && [[ ! "$password" =~ [0-9] ]]; then
        log "ERROR: Password must contain numbers"
        return 1
    fi
    
    # Check symbols
    if [[ "$require_symbols" == "true" ]] && [[ ! "$password" =~ [^a-zA-Z0-9] ]]; then
        log "ERROR: Password must contain symbols"
        return 1
    fi
    
    log "✓ Password meets policy requirements"
    return 0
}

# Security audit
security_audit() {
    log "Performing security audit..."
    
    local issues=0
    
    # Check SSL configuration
    local ssl_enabled
    ssl_enabled=$(jq -r '.ssl.enabled' "$CONFIG_FILE")
    if [[ "$ssl_enabled" != "true" ]]; then
        log "WARNING: SSL is not enabled"
        ((issues++))
    fi
    
    # Check VPN configuration
    local vpn_enabled
    vpn_enabled=$(jq -r '.vpn.enabled' "$CONFIG_FILE")
    if [[ "$vpn_enabled" != "true" ]]; then
        log "WARNING: VPN is not enabled"
        ((issues++))
    fi
    
    # Check MFA
    local mfa_enabled
    mfa_enabled=$(jq -r '.authentication.mfa_enabled' "$CONFIG_FILE")
    if [[ "$mfa_enabled" != "true" ]]; then
        log "WARNING: Multi-factor authentication is not enabled"
        ((issues++))
    fi
    
    # Check firewall
    local firewall_enabled
    firewall_enabled=$(jq -r '.firewall.enabled' "$CONFIG_FILE")
    if [[ "$firewall_enabled" != "true" ]]; then
        log "WARNING: Firewall is not enabled"
        ((issues++))
    fi
    
    # Check for default passwords
    if grep -q "xrdppasswd\|password123\|admin" /etc/passwd 2>/dev/null; then
        log "WARNING: Default passwords detected"
        ((issues++))
    fi
    
    # Check file permissions
    if find /opt -type f -perm /o+w 2>/dev/null | grep -q .; then
        log "WARNING: World-writable files found in /opt"
        ((issues++))
    fi
    
    log "Security audit completed. Issues found: $issues"
    return $issues
}

# Generate security report
generate_security_report() {
    local report_file="/opt/security/security-report-$(date +%Y%m%d-%H%M%S).json"
    
    log "Generating security report..."
    
    cat > "$report_file" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "ssl": {
    "enabled": $(jq '.ssl.enabled' "$CONFIG_FILE"),
    "certificate_expiry": "$(openssl x509 -enddate -noout -in "$SSL_DIR/server.crt" 2>/dev/null | cut -d= -f2 || echo "N/A")"
  },
  "vpn": {
    "enabled": $(jq '.vpn.enabled' "$CONFIG_FILE"),
    "active_connections": $(wg show 2>/dev/null | grep -c "peer" || echo 0)
  },
  "authentication": {
    "mfa_enabled": $(jq '.authentication.mfa_enabled' "$CONFIG_FILE"),
    "failed_attempts": $(grep "authentication failure" /var/log/auth.log 2>/dev/null | wc -l || echo 0)
  },
  "firewall": {
    "enabled": $(jq '.firewall.enabled' "$CONFIG_FILE"),
    "active_rules": $(ufw status numbered 2>/dev/null | grep -c "ALLOW" || echo 0)
  },
  "system": {
    "last_update": "$(stat -c %y /var/log/apt/history.log 2>/dev/null | cut -d' ' -f1 || echo "Unknown")",
    "open_ports": $(netstat -tuln 2>/dev/null | grep LISTEN | wc -l || echo 0)
  }
}
EOF
    
    log "✓ Security report generated: $report_file"
}

# Main function
main() {
    init_security
    
    case "${1:-help}" in
        "ssl")
            generate_ssl_cert "$2"
            configure_xrdp_ssl
            ;;
        "vpn")
            setup_wireguard "$2" "$3"
            ;;
        "mfa")
            setup_mfa "$2"
            ;;
        "firewall")
            setup_firewall
            ;;
        "audit")
            security_audit
            ;;
        "report")
            generate_security_report
            ;;
        "check-password")
            enforce_password_policy "$2"
            ;;
        "help"|*)
            echo "OBS Security Manager"
            echo "Usage: $0 {ssl|vpn|mfa|firewall|audit|report|check-password}"
            echo ""
            echo "Commands:"
            echo "  ssl [domain]                    - Generate SSL certificate and configure XRDP"
            echo "  vpn <server_ip> [client_count]  - Setup WireGuard VPN"
            echo "  mfa <username>                  - Setup multi-factor authentication"
            echo "  firewall                        - Configure firewall rules"
            echo "  audit                           - Perform security audit"
            echo "  report                          - Generate security report"
            echo "  check-password <password>       - Check password against policy"
            echo "  help                            - Show this help"
            ;;
    esac
}

main "$@"
