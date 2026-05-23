<div align="center">
  <h1>🔭 Vigil</h1>
  <p><em>Lightweight server monitoring agent with active push mode</em></p>
  <p>
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#security">Security & HTTPS</a> •
    <a href="#docker">Docker Deployment</a> •
    <a href="#full-deploy">Full Deployment Guide</a> •
    <a href="#metrics">Metrics</a> •
    <a href="#license">License</a>
  </p>
  <p>
    <a href="README.zh.md">🇨🇳 中文</a>
  </p>
</div>

---

**Vigil** is a lightweight server monitoring system. Each server runs a tiny Go agent that actively reads `/proc/` metrics and pushes them via HTTP/HTTPS to a central collector (no inbound ports needed on monitored servers).

## Features

- **Single binary agent** — Go compiled, ~5MB RAM, zero dependencies
- **Dual architecture** — Pre-built `linux/amd64` + `linux/arm64`
- **Active push mode** — No open ports required on target servers
- **Systemd managed** — Auto-restart + journalctl logs
- **Minimal collector** — Python 3 + SQLite (no external DB)
- **Token auth + HTTPS** — Built-in security
- **Threshold + Offline alerts** — CPU/Memory/Disk + automatic offline detection
- **Modern Dashboard** — React + TanStack + Cloudflare Pages (free tier)

## Architecture

```
Server → Agent (Go) → HTTPS POST → Collector (Python + SQLite) → Alerts → Telegram + Web Dashboard
```

## Quick Start

### 1. Build the Agent

```bash
cd agent && go build -o vigil-agent ./...
```

### 2. Configure Agent

Create `/etc/vigil/config.json`:

```json
{
  "server_url": "https://your-collector:9901",
  "interval": 30,
  "hostname": "my-server-01",
  "token": "super-secret-123"
}
```

### 3. Install as systemd service

```bash
bash deploy/install.sh amd64 my-server-01 https://your-collector:9901
```

### 4. Run the Collector

```bash
cp bot/config.example.py bot/config.py
# edit config.py
python bot/main.py
```

## Docker Deployment

```bash
cd deploy
./generate-selfsigned-cert.sh your-domain.com
# edit docker-compose.yml
docker compose up -d
```

## Full Deployment (Recommended)

1. Deploy Dashboard → `cd dash && npm run build && npx wrangler pages deploy dist`
2. Run Bot → `python bot/main.py` (with `CF_ALERT_URL`)
3. Deploy Agents → `bash deploy/install.sh`
4. (Optional) Protect with Cloudflare Access (email whitelist)

See detailed guide in README.

## License

GPL v3
