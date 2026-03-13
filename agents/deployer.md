# Deployer Agent

You deploy the thisminute app to the GCP VM. This doc contains everything you need.

## Release Cadence

**Daily releases** ship all committed changes once per day. Manual deploys are allowed for urgent fixes or important UX changes. Every deploy (daily or manual) follows the same procedure: test → deploy → test → verify.

## Infrastructure

| Resource          | Value                                    |
| ----------------- | ---------------------------------------- |
| **GCP Project**   | `thisminute-149101`                      |
| **VM**            | `thisminute` (e2-micro, `us-central1-a`) |
| **Static IP**     | `136.119.53.19`                          |
| **Domain**        | `thisminute.org` (DNS at Squarespace)    |
| **OS**            | Ubuntu 24.04 LTS                         |
| **App path**      | `/opt/thisminute` on the VM              |
| **Service**       | `thisminute.service` (systemd)           |
| **Reverse proxy** | nginx on ports 80/443                    |
| **SSL**           | Let's Encrypt via certbot                |

## gcloud Path (Windows)

The gcloud CLI has spaces in its path. You MUST use Python subprocess to call it:

```python
import subprocess
GCLOUD = 'C:/Users/tkond/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd'

def gcp_ssh(cmd, timeout=120):
    """Run a command on the VM via SSH."""
    r = subprocess.run(
        [GCLOUD, 'compute', 'ssh', 'thisminute', '--zone=us-central1-a', '--command', cmd],
        capture_output=True, text=True, timeout=timeout
    )
    print('STDOUT:', r.stdout)
    if r.stderr: print('STDERR:', r.stderr)
    return r

def gcp_scp(local_path, remote_path, timeout=120):
    """Copy a file to the VM."""
    r = subprocess.run(
        [GCLOUD, 'compute', 'scp', '--zone=us-central1-a', local_path, f'thisminute:{remote_path}'],
        capture_output=True, text=True, timeout=timeout
    )
    print('STDOUT:', r.stdout)
    if r.stderr: print('STDERR:', r.stderr)
    return r
```

Do NOT use `cmd.exe //c "gcloud ..."` — the spaces in the path break it.

## CRLF Warning

Files created on Windows have CRLF line endings. The VM runs Linux and needs LF.
After copying files to the VM, ALWAYS fix line endings before running anything:

```python
# Run this on the VM after copying files:
fix_cmd = "find /opt/thisminute -type f \\( -name '*.sh' -o -name '*.py' -o -name '*.txt' -o -name '*.service' -o -name '*.conf' -o -name '*.html' -o -name '*.css' -o -name '*.js' \\) -exec sed -i 's/\\r$//' {} +"
gcp_ssh(fix_cmd)
```

Or use base64 encoding to pass scripts that avoid the escaping problem:

```python
import base64
script = "#!/bin/bash\nset -euo pipefail\n..."
b64 = base64.b64encode(script.encode()).decode()
gcp_ssh(f"echo {b64} | base64 -d | sudo bash")
```

## Deploy Procedure (Standard Update)

When code has changed locally and needs to go to the VM:

```python
import subprocess, base64

GCLOUD = 'C:/Users/tkond/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd'

# 1. Create tarball (excludes junk)
subprocess.run(['tar', 'czf', '/tmp/thisminute.tar.gz',
    '--exclude=node_modules', '--exclude=test-results',
    '--exclude=data/*.db*', '--exclude=__pycache__', '--exclude=.git',
    '-C', 'C:/Users/tkond/thisminute', '.'])

# 2. SCP to VM
subprocess.run([GCLOUD, 'compute', 'scp', '--zone=us-central1-a',
    'C:/Users/tkond/AppData/Local/Temp/thisminute.tar.gz',
    'thisminute:/tmp/thisminute.tar.gz'])

# 3. Extract, fix CRLF, restart
deploy_script = """#!/bin/bash
set -euo pipefail
sudo tar xzf /tmp/thisminute.tar.gz -C /opt/thisminute
sudo find /opt/thisminute -type f \\( -name '*.sh' -o -name '*.py' -o -name '*.txt' -o -name '*.service' -o -name '*.conf' -o -name '*.html' -o -name '*.css' -o -name '*.js' \\) -exec sed -i 's/\\r$//' {} +
sudo chown -R thisminute:thisminute /opt/thisminute/data
sudo systemctl restart thisminute
sleep 2
curl -s http://localhost:8000/api/health
"""
b64 = base64.b64encode(deploy_script.encode()).decode()
subprocess.run([GCLOUD, 'compute', 'ssh', 'thisminute', '--zone=us-central1-a',
    '--command', f'echo {b64} | base64 -d | bash'])
```

## Deploy Procedure (First-Time / Full Setup)

Same as above but use `deploy/setup.sh` instead of just restarting:

```python
# After step 2 (SCP), run:
setup_script = """#!/bin/bash
set -euo pipefail
sudo tar xzf /tmp/thisminute.tar.gz -C /opt/thisminute
sudo find /opt/thisminute -type f \\( -name '*.sh' -o -name '*.py' -o -name '*.txt' -o -name '*.service' -o -name '*.conf' -o -name '*.html' -o -name '*.css' -o -name '*.js' \\) -exec sed -i 's/\\r$//' {} +
sudo bash /opt/thisminute/deploy/setup.sh
"""
b64 = base64.b64encode(setup_script.encode()).decode()
subprocess.run([GCLOUD, 'compute', 'ssh', 'thisminute', '--zone=us-central1-a',
    '--command', f'echo {b64} | base64 -d | bash'], timeout=300)
```

## SSL Setup (One-Time, After DNS Points to VM)

```python
gcp_ssh('sudo certbot --nginx -d thisminute.org -d www.thisminute.org --non-interactive --agree-tos -m sasha@thisminute.org', timeout=120)
```

## Verification Checklist

After every deploy, run these checks:

```python
# 1. Health check (on VM)
gcp_ssh('curl -s http://localhost:8000/api/health')
# Expected: {"status":"ok","stories":N}

# 2. Public access (from local machine)
subprocess.run(['curl', '-s', 'http://136.119.53.19/api/health'])

# 3. Service status
gcp_ssh('sudo systemctl status thisminute --no-pager | head -15')

# 4. Recent logs
gcp_ssh('sudo journalctl -u thisminute -n 20 --no-pager')
```

## Troubleshooting

| Problem                    | Fix                                                                                                                                 |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Service won't start        | `gcp_ssh('sudo journalctl -u thisminute -n 50 --no-pager')`                                                                         |
| 502 Bad Gateway            | uvicorn not running — check service logs                                                                                            |
| Permission denied on data/ | `gcp_ssh('sudo chown -R thisminute:thisminute /opt/thisminute/data')`                                                               |
| Out of memory              | Add swap: `gcp_ssh('sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile')` |
| SSL cert expired           | `gcp_ssh('sudo certbot renew')`                                                                                                     |
| Need to restart nginx      | `gcp_ssh('sudo nginx -t && sudo systemctl reload nginx')`                                                                           |

## VM Management

```python
# Stop VM (saves money if not using)
subprocess.run([GCLOUD, 'compute', 'instances', 'stop', 'thisminute', '--zone=us-central1-a'])

# Start VM
subprocess.run([GCLOUD, 'compute', 'instances', 'start', 'thisminute', '--zone=us-central1-a'])

# SSH interactively (user does this manually)
# gcloud compute ssh thisminute --zone=us-central1-a
```
