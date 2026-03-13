"""Deploy thisminute to GCP VM.

Usage:
    python scripts/deploy.py          # deploy and restart
    python scripts/deploy.py --check  # verify deployment only
"""
import base64
import os
import subprocess
import sys
import tarfile
import tempfile

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCLOUD = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd",
)
VM = "thisminute"
ZONE = "us-central1-a"
REMOTE_APP = "/opt/thisminute"

EXCLUDE_DIRS = {"node_modules", "test-results", "__pycache__", ".git", "data", "e2e"}
EXCLUDE_EXTS = {".db", ".db-journal", ".db-wal"}


def gcp_ssh(cmd, timeout=120):
    r = subprocess.run(
        [GCLOUD, "compute", "ssh", VM, f"--zone={ZONE}", "--command", cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    return r


def gcp_scp(local, remote, timeout=120):
    r = subprocess.run(
        [GCLOUD, "compute", "scp", f"--zone={ZONE}", local, f"{VM}:{remote}"],
        capture_output=True, text=True, timeout=timeout,
    )
    return r


def make_tarball():
    """Create tarball from PROJECT_DIR, reading files fresh from disk."""
    tar_path = os.path.join(tempfile.gettempdir(), "thisminute_deploy.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        for root, dirs, files in os.walk(PROJECT_DIR):
            # Skip excluded directories
            rel_root = os.path.relpath(root, PROJECT_DIR).replace("\\", "/")
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS
                       and f"{rel_root}/{d}" != "src/js"]
            for fname in files:
                if any(fname.endswith(ext) for ext in EXCLUDE_EXTS):
                    continue
                full = os.path.join(root, fname)
                arcname = os.path.relpath(full, PROJECT_DIR).replace("\\", "/")
                tar.add(full, arcname=arcname)
    return tar_path


def verify_tarball(tar_path, check_strings=None):
    """Verify tarball contains expected files and content."""
    with tarfile.open(tar_path) as tar:
        members = tar.getnames()
        required = ["src/app.py", "static/js/app.js", "static/index.html"]
        for f in required:
            if f not in members:
                print(f"ERROR: {f} missing from tarball")
                return False

        # Verify specific content if requested
        if check_strings:
            for filepath, needle in check_strings.items():
                try:
                    content = tar.extractfile(filepath).read().decode()
                    if needle not in content:
                        print(f"ERROR: '{needle}' not found in {filepath}")
                        return False
                    print(f"  OK: '{needle}' found in {filepath}")
                except KeyError:
                    print(f"ERROR: {filepath} not in tarball")
                    return False

    print(f"Tarball OK: {len(members)} files, {os.path.getsize(tar_path) // 1024}KB")
    return True


# The deploy script is stored as a static file to avoid escape issues.
# Note: health check is done from local machine, not in this SSH session,
# because the SSH connection can timeout during the 30s restart wait.
DEPLOY_SCRIPT = b"""#!/bin/bash
set -euo pipefail

echo "=== Extracting ==="
sudo tar xzf /tmp/thisminute_deploy.tar.gz -C /opt/thisminute

echo "=== Fixing CRLF ==="
sudo find /opt/thisminute -type f \\( -name '*.py' -o -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.sh' -o -name '*.txt' -o -name '*.conf' -o -name '*.service' \\) -exec sed -i 's/\\r$//' {} +

echo "=== Fixing permissions ==="
sudo chown -R thisminute:thisminute /opt/thisminute/data

echo "=== Restarting ==="
sudo systemctl restart thisminute

# Fix WAL/SHM file ownership after restart (created by new process)
sleep 2
sudo chown -R thisminute:thisminute /opt/thisminute/data
echo "=== Restart issued ==="
"""


def deploy():
    src_js = os.path.join(PROJECT_DIR, "src", "js")
    if os.path.isdir(src_js):
        print("=== Building frontend ===")
        r = subprocess.run(["npm", "run", "build"], cwd=PROJECT_DIR, capture_output=True, text=True, shell=True)
        if r.returncode != 0:
            print(f"BUILD FAILED:\n{r.stderr}")
            sys.exit(1)
        print("Build OK")
    else:
        print("=== Skipping frontend build (src/js/ not found, using pre-built static/js/app.js) ===")

    print("=== Building tarball ===")
    tar_path = make_tarball()

    print("=== Verifying tarball ===")
    if not verify_tarball(tar_path):
        print("ABORT: tarball verification failed")
        sys.exit(1)

    print("=== Uploading ===")
    r = gcp_scp(tar_path, "/tmp/thisminute_deploy.tar.gz")
    if r.returncode != 0:
        print(f"SCP failed: {r.stderr}")
        sys.exit(1)
    print("Upload OK")

    print("=== Deploying ===")
    b64 = base64.b64encode(DEPLOY_SCRIPT).decode()
    r = gcp_ssh(f"echo {b64} | base64 -d | bash")
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    if r.returncode != 0:
        print(f"DEPLOY FAILED (rc={r.returncode})")
        sys.exit(1)

    # Health check from local machine (avoids SSH timeout during restart)
    import time
    import urllib.request
    print("=== Health check (waiting for restart...) ===")
    for attempt in range(12):  # 12 attempts * 5s = 60s max
        time.sleep(5)
        try:
            req = urllib.request.urlopen("https://thisminute.org/api/health", timeout=5)
            data = req.read().decode()
            print(data)
            print("=== Deploy complete ===")
            break
        except Exception:
            print(f"  attempt {attempt+1}/12...")
    else:
        print("HEALTH CHECK FAILED after 60s")
        sys.exit(1)

    print("=== DONE ===")


def check():
    print("=== Checking VM health ===")
    r = gcp_ssh("curl -sf http://localhost:8000/api/health")
    print(r.stdout)
    r = gcp_ssh("sudo systemctl status thisminute --no-pager | head -10")
    print(r.stdout)


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        deploy()
