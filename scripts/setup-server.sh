#!/usr/bin/env bash
# setup-server.sh — one-shot provisioning for Ubuntu 22.04 LTS
# Run as root on a fresh Yandex Cloud (or any Ubuntu 22.04) VM:
#   curl -fsSL https://raw.githubusercontent.com/valdinociluca-hue/spare-parts-ai-backend/main/deploy/scripts/setup-server.sh | bash
# Or: bash setup-server.sh

set -euo pipefail

DOMAIN="${DOMAIN:-api.lvtrade.ru}"
EMAIL="${CERTBOT_EMAIL:-admin@lvtrade.ru}"

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
die()  { echo "ERROR: $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root (sudo bash setup-server.sh)"

# ── System updates ──────────────────────────────────────────────────────────
log "Updating system packages..."
apt-get update -q
apt-get upgrade -y -q
apt-get install -y -q \
    curl git vim htop ufw fail2ban \
    ca-certificates gnupg lsb-release

# ── Docker ──────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    log "Installing Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -q
    apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
    log "Docker installed: $(docker --version)"
else
    log "Docker already installed: $(docker --version)"
fi

# ── Nginx ──────────────────────────────────────────────────────────────────
if ! command -v nginx &>/dev/null; then
    log "Installing Nginx..."
    apt-get install -y -q nginx
    systemctl enable nginx
    log "Nginx installed: $(nginx -v 2>&1)"
else
    log "Nginx already installed"
fi

# ── Certbot ────────────────────────────────────────────────────────────────
if ! command -v certbot &>/dev/null; then
    log "Installing Certbot..."
    apt-get install -y -q certbot python3-certbot-nginx
    log "Certbot installed: $(certbot --version)"
else
    log "Certbot already installed"
fi

# ── Firewall ───────────────────────────────────────────────────────────────
log "Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
log "UFW status: active"

# ── Fail2ban ───────────────────────────────────────────────────────────────
log "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port    = ssh
EOF
systemctl enable --now fail2ban

# ── App directory ──────────────────────────────────────────────────────────
APP_DIR="/opt/spare-parts"
log "Creating app directory at $APP_DIR..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# ── Clone repo (if not already present) ────────────────────────────────────
if [[ ! -d "$APP_DIR/.git" ]]; then
    log "Cloning spare-parts-ai-backend..."
    # User should set GITHUB_TOKEN or use SSH key before running
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        git clone "https://${GITHUB_TOKEN}@github.com/valdinociluca-hue/spare-parts-ai-backend.git" .
    else
        git clone "https://github.com/valdinociluca-hue/spare-parts-ai-backend.git" .
    fi
else
    log "Repo already present, skipping clone"
fi

# ── Webroot for Let's Encrypt challenge ────────────────────────────────────
mkdir -p /var/www/certbot

# ── Nginx: temp HTTP-only config for Certbot challenge ─────────────────────
log "Installing Nginx config (HTTP only for initial cert)..."
cat > /etc/nginx/sites-available/spare-parts <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://\$host\$request_uri; }
}
EOF
ln -sf /etc/nginx/sites-available/spare-parts /etc/nginx/sites-enabled/spare-parts
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── TLS certificate ────────────────────────────────────────────────────────
if [[ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
    log "Obtaining TLS certificate for ${DOMAIN}..."
    certbot certonly --webroot -w /var/www/certbot \
        -d "${DOMAIN}" \
        --email "${EMAIL}" \
        --agree-tos --non-interactive
    log "Certificate obtained."
else
    log "Certificate already exists for ${DOMAIN}"
fi

# ── Nginx: full SSL config ─────────────────────────────────────────────────
log "Installing full Nginx SSL config..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_SRC="$APP_DIR/deploy/nginx/spare-parts.conf"
if [[ -f "$NGINX_SRC" ]]; then
    cp "$NGINX_SRC" /etc/nginx/sites-available/spare-parts
    nginx -t && systemctl reload nginx
    log "Nginx SSL config installed."
else
    log "WARNING: $NGINX_SRC not found — manual Nginx config required."
fi

# ── Certbot auto-renewal cron ──────────────────────────────────────────────
log "Setting up certbot auto-renewal..."
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && systemctl reload nginx") | crontab -

# ── .env check ────────────────────────────────────────────────────────────
if [[ ! -f "$APP_DIR/.env" ]]; then
    log "WARNING: $APP_DIR/.env not found."
    log "Copy deploy/.env.production to $APP_DIR/.env and fill in all secrets before running deploy.sh"
fi

# ── Done ──────────────────────────────────────────────────────────────────
log ""
log "======================================================"
log " Server setup complete!"
log "======================================================"
log ""
log " Next steps:"
log "   1. Copy .env.production to $APP_DIR/.env and fill secrets"
log "   2. Run: bash $APP_DIR/deploy/scripts/deploy.sh"
log ""
