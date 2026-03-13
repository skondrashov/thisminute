# Deploying thisminute to GCP

## Architecture

```
thisminute.org --> nginx (80/443) --> uvicorn (8000) --> FastAPI + SQLite
```

Single GCP e2-micro VM running Ubuntu 24.04. Cost: ~$0-3/month (free tier).

## Step 1: Create the VM

1. Go to **GCP Console > Compute Engine > Create Instance**
2. Settings:
    - **Name**: `thisminute`
    - **Region**: `us-central1-a` (free tier eligible)
    - **Machine type**: `e2-micro` (2 vCPU shared, 1GB RAM)
    - **Boot disk**: Ubuntu 24.04 LTS, 30GB standard persistent disk
    - **Firewall**: Check both "Allow HTTP" and "Allow HTTPS"

## Step 2: Reserve a static IP

1. Go to **VPC Network > IP addresses**
2. Find your VM's ephemeral IP and click **Reserve** (promote to static)
3. Note the IP address

## Step 3: DNS setup

At your domain registrar for `thisminute.org`:

| Type | Name  | Value            |
| ---- | ----- | ---------------- |
| A    | `@`   | `<VM static IP>` |
| A    | `www` | `<VM static IP>` |

Wait for DNS propagation (usually 5-30 minutes, can take up to 48h).

## Step 4: Deploy

SSH into the VM and run:

```bash
# SSH in
gcloud compute ssh thisminute --zone=us-central1-a

# Clone the repo
sudo git clone https://github.com/YOUR_USER/thisminute.git /opt/thisminute

# Run setup
sudo bash /opt/thisminute/deploy/setup.sh
```

Verify the app is running:

```bash
curl http://localhost:8000/api/health
# Should return: {"status":"ok","stories":0}
```

## Step 5: SSL certificate

Once DNS is pointing to the VM:

```bash
sudo certbot --nginx -d thisminute.org -d www.thisminute.org
```

Follow the prompts (enter email, agree to ToS). Certbot will automatically modify the nginx config to add SSL.

Optionally, replace with the full SSL config from the repo:

```bash
sudo cp /opt/thisminute/deploy/nginx.conf /etc/nginx/sites-available/thisminute
sudo nginx -t && sudo systemctl reload nginx
```

Verify auto-renewal:

```bash
sudo certbot renew --dry-run
```

## Step 6: Verify

```bash
# Service running
sudo systemctl status thisminute

# Health check via nginx
curl https://thisminute.org/api/health

# Stories endpoint
curl https://thisminute.org/api/stories | head -c 200

# Scraper logs
sudo journalctl -u thisminute -f

# Wait 15 min, then check story count increased
curl https://thisminute.org/api/health
```

## Updating after code changes

```bash
gcloud compute ssh thisminute --zone=us-central1-a
sudo bash /opt/thisminute/deploy/update.sh
```

## Useful commands

```bash
# View logs
sudo journalctl -u thisminute -n 100
sudo journalctl -u thisminute -f          # follow live

# Restart
sudo systemctl restart thisminute

# Stop/start
sudo systemctl stop thisminute
sudo systemctl start thisminute

# Nginx
sudo nginx -t                              # test config
sudo systemctl reload nginx

# SSL renewal (auto via cron, but can run manually)
sudo certbot renew
```

## Troubleshooting

**App won't start**: Check logs with `journalctl -u thisminute -n 50`. Common issues:

- Missing Python packages: `sudo /opt/thisminute/venv/bin/pip install -r requirements.txt`
- Permission issues: `sudo chown -R thisminute:thisminute /opt/thisminute/data`

**502 Bad Gateway**: uvicorn isn't running. Check `systemctl status thisminute`.

**SSL errors**: Verify DNS points to the VM (`dig thisminute.org`), then re-run certbot.

**Out of memory (e2-micro = 1GB)**: Check with `free -h`. If needed, add swap:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
