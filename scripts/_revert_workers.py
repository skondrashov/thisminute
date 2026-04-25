import subprocess, base64, sys, time

GCLOUD = 'C:/Users/tkond/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd'

def ssh(cmd, timeout=300):
    r = subprocess.run(
        [GCLOUD, 'compute', 'ssh', 'thisminute', '--zone=us-central1-a', '--command', cmd],
        capture_output=True, encoding='utf-8', errors='replace', timeout=timeout
    )
    print('--- STDOUT ---')
    print(r.stdout)
    if r.stderr:
        print('--- STDERR ---')
        print(r.stderr)
    print('--- EXIT ---', r.returncode)
    return r

script = r"""
set +e
echo '=== wait 60s for pipeline startup to finish ==='
sleep 60
echo '=== ps ==='
ps -ef | grep 'uvicorn src.app' | grep -v grep
echo
echo '=== port listening? ==='
ss -tlnp 2>/dev/null | grep 8000 || sudo ss -tlnp | grep 8000
echo
echo '=== INTERNAL TIMING ==='
for endpoint in "/api/health" "/api/stats/domain-distribution?hours=1" "/api/stories?limit=20" "/api/events?limit=20"; do
  echo "--- $endpoint ---"
  { time curl -sS --max-time 10 -o /dev/null -w "HTTP %{http_code}\n" "http://localhost:8000$endpoint" ; } 2>&1
done
echo
echo '=== EXTERNAL TIMING ==='
for endpoint in "/api/stats/domain-distribution" "/api/stories?limit=20"; do
  echo "--- $endpoint ---"
  { time curl -sS --max-time 10 -o /dev/null -w "HTTP %{http_code}\n" "https://thisminute.org$endpoint" ; } 2>&1
done
echo
echo '=== LOCK ERRORS since 2 min ago ==='
sudo journalctl -u thisminute --since "2 minutes ago" --no-pager | grep -ciE "database is locked"
echo
echo '=== MEMORY ==='
free -m
echo '=== UVICORN RSS ==='
for p in $(pgrep -f "uvicorn src.app"); do ps -o pid,rss,cmd -p $p --no-headers; done
"""
b64 = base64.b64encode(script.encode()).decode()
ssh(f"echo {b64} | base64 -d | bash", timeout=240)
