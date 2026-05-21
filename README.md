<div align="center">
  <h1>🔭 Vigil</h1>
  <p><em>Lightweight server monitoring agent with active push mode</em></p>
  <p>
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#security">Security & HTTPS</a> •
    <a href="#docker">Docker Deployment</a> •
    <a href="#metrics">Metrics</a> •
    <a href="#license">License</a>
  </p>
  <p>
    <a href="README.zh.md">🇨🇳 中文</a>
  </p>
</div>

---

**Vigil** is a lightweight server monitoring system that runs a tiny Go agent on each server. Instead of traditional centralized polling (ping/SNMP), each agent actively reads `/proc/` metrics and pushes them via HTTP/HTTPS to a central collector.

## Features

- **Single binary agent** — Go compiled, ~5MB RAM, zero dependencies, one `scp` to deploy
- **Dual architecture** — Pre-built for `linux/amd64` and `linux/arm64`
- **Active push mode** — No open inbound ports needed on monitored servers
- **Systemd managed** — Auto-restart on crash, logs via journalctl
- **Minimal collector** — Python 3 HTTP/HTTPS server, SQLite storage, no external database
- **Token authentication** — Optional shared secret for secure /report endpoint
- **HTTPS support** — Native TLS (just pass certfile/keyfile)
- **Threshold + Offline alerts** — CPU/memory/disk + automatic offline detection via background checker
- **GitHub Actions CI** — Auto-build on tag push, ready-to-use binaries in Releases

## Architecture

```
Every server --> Agent (Go) --> HTTP/HTTPS POST /report --> Collector (Python) --> SQLite --> Alerts --> Telegram
```

| Component | Language | Role |
|-----------|----------|------|
| **Agent** | Go | Runs on each server, collects `/proc/*` metrics, pushes to collector (supports https://) |
| **Collector** | Python 3 | Receives reports via HTTP/HTTPS, stores in SQLite, evaluates alert rules |
| **Storage** | SQLite | Embedded, zero-config, keeps 7-day history per server |
| **Alert Engine** | Python | Threshold-based CPU/Memory/Disk/Offline alerts with cooldown |

## Quick Start

### 1. Build the Agent

```bash
cd agent
go mod tidy

# AMD64 (most cloud VPS)
GOOS=linux GOARCH=amd64 go build -o vigil-agent-linux-amd64 ./...

# ARM64 (Oracle ARM, Apple Silicon servers)
GOOS=linux GOARCH=arm64 go build -o vigil-agent-linux-arm64 ./...
```

### 2. Configure the Agent

On each target server, create `/etc/vigil/config.json`:

```json
{
    "server_url": "https://your-collector:9901",
    "interval": 30,
    "hostname": "my-server-01",
    "token": "super-secret-123"   // optional but recommended
}
```

Or leave `hostname` empty to auto-detect from OS.

### 3. Install as a systemd Service

```bash
cp vigil-agent-linux-* /usr/local/bin/vigil-agent
chmod +x /usr/local/bin/vigil-agent
mkdir -p /etc/vigil
cp deploy/vigil-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vigil-agent
```

Or use the one-liner install script:

```bash
bash deploy/install.sh amd64 my-server-01 https://your-collector:9901
```

### 4. Set up the Collector

Integrate the collector components into your Python bot:

```python
from receiver import start_vigil_server, start_offline_checker
from storage import VigilStorage
from alerts import VigilAlertEngine

storage = VigilStorage("/path/to/vigil.db")
engine = VigilAlertEngine({
    "cpu_threshold": 80,
    "memory_threshold": 90,
    "disk_threshold": 85,
    "offline_sec": 180,
    "cooldown": 300,
})

def alert_callback(alert):
    print(f"ALERT: {alert['hostname']} - {alert['message']}")

# Start HTTPS + Token server
start_vigil_server("0.0.0.0", 9901, storage, engine, alert_callback,
                   token="super-secret-123",
                   certfile="/path/to/fullchain.pem",
                   keyfile="/path/to/privkey.pem")

# Enable automatic offline alerts (runs in background thread)
start_offline_checker(storage, engine, alert_callback, check_interval=60)
```

### 5. Or Run the Complete Bot

Clone this repo and use the ready-to-run `bot/` module:

```bash
cp bot/config.example.py bot/config.py
# edit bot/config.py with your settings
python bot/main.py
```

The bot includes:
- **Pinger** — ping-based latency and packet loss detection for any hosts
- **Receiver** — HTTP/HTTPS server receiving agent reports
- **Alert Engine** — threshold-based alerts for both agent data and ping results
- **Offline Checker** — background thread that detects silent agents

See `bot/` for the full source.

## Security & HTTPS 🔒

**Token Authentication** (strongly recommended)
- Set the same `token` in agent config.json and collector
- Collector rejects requests with wrong/missing token (returns 401)
- Works over both HTTP and HTTPS

**HTTPS Support**
- Pass `certfile` and `keyfile` (PEM format) to `start_vigil_server`
- Agent automatically uses TLS when `server_url` starts with `https://`
- No code changes needed in Go agent

**Offline Auto-Detection**
- `start_offline_checker(...)` runs a daemon thread that checks `last_seen` every N seconds
- Triggers **critical** alerts when an agent stops reporting

## Docker Deployment 🐳

### Quick Start with Docker Compose

```bash
# 1. Clone the repo
git clone https://github.com/dorokuma/vigil.git
cd vigil/deploy

# 2. Generate self-signed certificate (or bring your own)
./generate-selfsigned-cert.sh your-server-ip-or-domain

# 3. Create your integration script (your-bot.py)
#    See bot-ext/ for receiver.py, storage.py, alerts.py

# 4. Edit docker-compose.yml (set TOKEN, paths, etc.)

# 5. Start everything
docker compose up -d

# Check logs
docker compose logs -f
```

See `deploy/docker-compose.yml` for the full example (includes healthcheck, volume mounts for DB and certs).

**Production tips:**
- Use real certificates (Let's Encrypt via certbot)
- Mount persistent volume for `vigil.db`
- Set strong `TOKEN` via environment variable
- Run behind reverse proxy (Nginx/Traefik) for extra security if needed

## Metrics

All metrics are read from `/proc/` — no external commands, no sudo, no dependencies.

| Metric | Source | Unit |
|--------|--------|------|
| CPU usage | `/proc/stat` (delta) | % |
| System load | `/proc/loadavg` | 1/5/15 min |
| Memory | `/proc/meminfo` (MemAvailable) | MB, % |
| Disk usage | `statfs()` syscall | GB, % |
| Network traffic | `/proc/net/dev` (delta) | bytes, bps |
| Uptime | `/proc/uptime` | seconds |
| Process count | `/proc/[0-9]*` | integer |
| Kernel version | `/proc/version` | string |

## Agent Report Format

```json
{
    "hostname": "server-01",
    "type": "heartbeat",
    "data": {
        "cpu": {
            "percent": 45.2,
            "load_1": 2.1,
            "load_5": 1.8,
            "load_15": 1.5
        },
        "memory": {
            "total_mb": 16000,
            "used_mb": 8000,
            "avail_mb": 8000,
            "percent": 50.0
        },
        "disks": [{
            "mount_point": "/",
            "total_gb": 100,
            "used_gb": 60,
            "free_gb": 40,
            "percent": 60.0
        }],
        "network": [{
            "interface": "eth0",
            "rx_bytes": 123456789,
            "tx_bytes": 98765432,
            "rx_speed_bps": 1000000,
            "tx_speed_bps": 500000
        }],
        "system": {
            "hostname": "server-01",
            "uptime_sec": 3600,
            "process_cnt": 200,
            "kernel_version": "Linux version 6.12.74+deb13+1-arm64 ...",
            "timestamp": 1700000000
        }
    }
}
```

## Telegram Alert Integration

```python
async def push_alert(alert):
    icon = "\U0001f6a8" if alert["severity"] == "critical" else "\u26a0\ufe0f"
    text = f"{icon} {alert['hostname']}\n{alert['message']}"
    await application.bot.send_message(chat_id=YOUR_CHAT_ID, text=text)
```

## Why Vigil?

**Instead of LLM-Wiki / traditional RAG** — this is a real monitoring system for real servers. No "incremental knowledge compilation," no "graph-based retrieval." Just a Go binary that reads `/proc/` and pushes JSON.

## License

GPL v3
