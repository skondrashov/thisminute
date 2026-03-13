"""Helper to run merge_events.py on the VM via SSH."""
import subprocess
import sys
import os

GCLOUD = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd",
)

r = subprocess.run(
    [GCLOUD, "compute", "ssh", "thisminute", "--zone=us-central1-a", "--command",
     "sudo -u thisminute /opt/thisminute/venv/bin/python /opt/thisminute/scripts/merge_events.py"],
    capture_output=True, text=True, timeout=300,
)
print(r.stdout, flush=True)
if r.stderr:
    print(r.stderr, flush=True)
sys.exit(r.returncode)
