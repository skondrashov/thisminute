"""Deploy and run bright_side backfill on production VM."""

import subprocess
import base64
import sys

GCLOUD = "C:/Users/tkond/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"

def gcp_ssh(cmd, timeout=300):
    r = subprocess.run(
        [GCLOUD, "compute", "ssh", "thisminute", "--zone=us-central1-a", "--command", cmd],
        capture_output=True, timeout=timeout, encoding="utf-8", errors="replace",
    )
    if r.stdout:
        print(r.stdout, end="")
    if r.stderr:
        print("STDERR:", r.stderr[:1000], end="")
    return r

def main():
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 72
    dry_run = "--dry-run" in sys.argv

    script = f"""#!/bin/bash
set -euo pipefail
cd /opt/thisminute
PYBIN=/opt/thisminute/venv/bin/python3
if [ ! -f "$PYBIN" ]; then
    PYBIN=python3
fi
echo "Python: $PYBIN"
echo "Hours: {hours}"
sudo -u thisminute env $(cat /opt/thisminute/.env 2>/dev/null | xargs) $PYBIN /opt/thisminute/scripts/backfill_bright_side.py --hours {hours} --batch-size 20 --db /opt/thisminute/data/thisminute.db {"--dry-run" if dry_run else ""}
"""

    b64 = base64.b64encode(script.encode()).decode()
    r = gcp_ssh(f"echo {b64} | base64 -d | bash", timeout=600)
    print(f"\nExit code: {r.returncode}")

if __name__ == "__main__":
    main()
