#!/usr/bin/env bash
set -euo pipefail

# Fix CRLF line endings on all deploy scripts
for f in /opt/thisminute/deploy/*.sh; do
    sed -i 's/\r$//' "$f"
done

# Fix CRLF on service file and nginx conf too
sed -i 's/\r$//' /opt/thisminute/deploy/thisminute.service
sed -i 's/\r$//' /opt/thisminute/deploy/nginx.conf

# Fix CRLF on requirements.txt and all Python files
sed -i 's/\r$//' /opt/thisminute/requirements.txt
find /opt/thisminute/src -name '*.py' -exec sed -i 's/\r$//' {} +

# Now run the actual setup
bash /opt/thisminute/deploy/setup.sh
