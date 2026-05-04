# Deploying Vedic AI on a Local Server

Deploy on any Linux machine (home server, office server, spare PC) connected to the internet.
No Docker required — runs as a native Python service managed by systemd.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Linux server | Ubuntu 22.04 / 24.04 recommended |
| Python 3.11+ | Available in standard apt repos |
| Internet access | Outbound only — for Gemini API calls |
| Router admin access | For port forwarding (Step 6) |
| Gemini API key | Free at https://aistudio.google.com/apikey |

---

## Step 1 — Install Python 3.11+

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip git
python3.11 --version   # confirm 3.11 or later
```

---

## Step 2 — Deploy the app

```bash
cd ~
git clone https://github.com/VU3RAZ/vedic-ai.git
cd vedic-ai
make install       # creates .venv and installs all dependencies
make build-index   # downloads 88 MB embedding model once, builds FAISS index
```

`make build-index` takes 2–5 minutes on first run (model download + vector indexing).
All subsequent starts are instant — no internet needed for the app itself.

---

## Step 3 — Configure Gemini API key

```bash
nano configs/models.yaml
```

Set these two lines:
```yaml
llm:
  backend: gemini
  gemini:
    api_key: "AIzaSy...your-key-here..."
```

`configs/models.yaml` is gitignored — your key stays on the server only.

Test the configuration:
```bash
.venv/bin/vedic-ai serve --port 8000
# Open http://localhost:8000 in a browser on the same machine
# Ctrl+C to stop
```

---

## Step 4 — systemd service (auto-start, auto-restart)

Create the service file (replace `rahul` with your actual username):

```bash
sudo nano /etc/systemd/system/vedic-ai.service
```

```ini
[Unit]
Description=Vedic AI — Jyotish Prediction Server
After=network.target

[Service]
Type=simple
User=rahul
WorkingDirectory=/home/rahul/vedic-ai
ExecStart=/home/rahul/vedic-ai/.venv/bin/vedic-ai serve --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vedic-ai
sudo systemctl status vedic-ai
```

Expected output: `● vedic-ai.service - Vedic AI ... active (running)`

Verify locally:
```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"vedic-ai"}
```

---

## Step 5 — Open the server firewall

```bash
sudo ufw allow 8000/tcp
sudo ufw enable          # if not already enabled
sudo ufw status
```

---

## Step 6 — Router port forwarding

This exposes the server to the internet through your router.

1. Find your server's **local IP**:
   ```bash
   hostname -I | awk '{print $1}'
   # e.g. 192.168.1.105
   ```

2. Find your **public IP**:
   ```bash
   curl -s ifconfig.me
   # e.g. 103.x.x.x
   ```

3. Log into your router admin panel (usually `http://192.168.1.1`) and add a port forwarding rule:

   | Setting | Value |
   |---|---|
   | External port | 8000 |
   | Internal IP | your server's local IP (e.g. 192.168.1.105) |
   | Internal port | 8000 |
   | Protocol | TCP |

4. Test from outside your network:
   ```bash
   curl http://YOUR_PUBLIC_IP:8000/health
   ```

> **Tip:** Assign your server a **static local IP** in the router's DHCP settings so the forwarding rule doesn't break if the server reboots.

---

## Step 7 — Free dynamic DNS (stable URL)

Home internet IPs change periodically. DuckDNS gives you a free stable subdomain
that automatically tracks your current IP.

1. Go to **https://www.duckdns.org** and sign in with Google
2. Create a subdomain — e.g. `vedic-ai` → you get `vedic-ai.duckdns.org`
3. Copy your token from the dashboard

Install the auto-updater on the server:

```bash
mkdir -p ~/duckdns
nano ~/duckdns/duck.sh
```

```bash
#!/bin/bash
curl -s "https://www.duckdns.org/update?domains=vedic-ai&token=YOUR_TOKEN&ip=" \
  -o ~/duckdns/duck.log
```

```bash
chmod +x ~/duckdns/duck.sh
~/duckdns/duck.sh                # test it — duck.log should say "OK"

# Run every 5 minutes via cron
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1") | crontab -
```

Your app is now accessible at: **`http://vedic-ai.duckdns.org:8000`**

---

## Step 8 — HTTPS with nginx + Let's Encrypt (recommended)

Free TLS certificate via Certbot. Serves on standard port 443 — no port number in the URL.

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create nginx site config:

```bash
sudo nano /etc/nginx/sites-available/vedic-ai
```

```nginx
server {
    server_name vedic-ai.duckdns.org;

    location / {
        proxy_pass         http://localhost:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_buffering    off;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/vedic-ai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Open ports 80 and 443
sudo ufw allow 80 && sudo ufw allow 443

# Issue free TLS certificate (auto-renews every 90 days)
sudo certbot --nginx -d vedic-ai.duckdns.org
```

App is now live at: **`https://vedic-ai.duckdns.org`**

---

## Useful commands

```bash
# View live logs
sudo journalctl -u vedic-ai -f

# Restart after a config change
sudo systemctl restart vedic-ai

# Pull latest code and restart
cd ~/vedic-ai && git pull && sudo systemctl restart vedic-ai

# Check service status
sudo systemctl status vedic-ai

# Stop the service
sudo systemctl stop vedic-ai
```

---

## Update to a new version

```bash
cd ~/vedic-ai
git pull
.venv/bin/pip install -e ".[engine,retrieval,llm,api]"   # if dependencies changed
sudo systemctl restart vedic-ai
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `make build-index` fails | Check internet connection; delete `data/processed/` and retry |
| Service not starting | `sudo journalctl -u vedic-ai -n 50` — check for Python errors |
| Can't reach from outside | Verify router port forwarding and `sudo ufw status` |
| Gemini 429 errors | Free tier: 15 requests/minute — add delays between bulk requests |
| HTTPS cert fails | Port 80 must be open and reachable from the internet for Certbot |
