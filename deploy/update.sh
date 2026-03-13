#!/usr/bin/env bash
# Redeploy thisminute after code changes
# Run as root: sudo bash /opt/thisminute/deploy/update.sh
set -euo pipefail

echo "=== Updating thisminute ==="

cd /opt/thisminute

echo "[1/4] Pulling latest code..."
git pull

echo "[2/4] Updating dependencies..."
venv/bin/pip install --quiet -r requirements.txt

echo "[3/4] Restarting service..."
systemctl restart thisminute

echo "[4/4] Checking status..."
sleep 2
systemctl status thisminute --no-pager

echo ""
echo "=== Update complete ==="
echo "Health check: curl http://localhost:8000/api/health"
