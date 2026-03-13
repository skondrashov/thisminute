#!/usr/bin/env bash
# One-time setup script for thisminute on Ubuntu 24.04 (GCP e2-micro)
# Run as root: sudo bash /opt/thisminute/deploy/setup.sh
set -euo pipefail

echo "=== thisminute server setup ==="

# 1. System packages
echo "[1/7] Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx certbot python3-certbot-nginx

# 2. Create system user
echo "[2/7] Creating thisminute user..."
if ! id -u thisminute &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin thisminute
fi

# 3. Set ownership
echo "[3/7] Setting permissions..."
chown -R thisminute:thisminute /opt/thisminute
chmod 755 /opt/thisminute

# 4. Python venv + dependencies
echo "[4/7] Setting up Python venv..."
cd /opt/thisminute
python3 -m venv venv
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt

# 5. Data directory
echo "[5/7] Creating data directory..."
mkdir -p /opt/thisminute/data
chown thisminute:thisminute /opt/thisminute/data

# 6. Systemd service
echo "[6/7] Installing systemd service..."
cp deploy/thisminute.service /etc/systemd/system/thisminute.service
systemctl daemon-reload
systemctl enable thisminute
systemctl start thisminute

# 7. Nginx config
echo "[7/7] Configuring nginx..."
# Install HTTP-only config first (SSL comes after certbot)
cat > /etc/nginx/sites-available/thisminute <<'NGINX'
server {
    listen 80;
    server_name thisminute.org www.thisminute.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
}
NGINX
ln -sf /etc/nginx/sites-available/thisminute /etc/nginx/sites-enabled/thisminute
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Verify app is running:  curl http://localhost:8000/api/health"
echo "  2. Set up DNS A records pointing to this VM's IP"
echo "  3. Install SSL:  sudo certbot --nginx -d thisminute.org -d www.thisminute.org"
echo "  4. Replace nginx config with full SSL version:"
echo "     sudo cp /opt/thisminute/deploy/nginx.conf /etc/nginx/sites-available/thisminute"
echo "     sudo nginx -t && sudo systemctl reload nginx"
