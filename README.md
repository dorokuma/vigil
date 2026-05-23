<div align="center">
  <h1>🔭 Vigil</h1>
  <p><em>Modern server monitoring with Go agent + Cloudflare stack</em></p>
  <p>
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#security">Security</a> •
    <a href="#full-deploy">Deployment</a> •
    <a href="#license">License</a>
  </p>
  <p>
    <a href="README.zh.md">🇨🇳 中文</a>
  </p>
</div>

---

**Vigil** is a modern server monitoring system. A tiny Go agent runs on each server, actively collects `/proc/` metrics, and pushes them via HTTPS to a central collector. The system includes a beautiful React + TanStack dashboard deployed on Cloudflare Pages, real-time alerts with history persistence (KV), CSV export, and optional protection via Cloudflare Access (email whitelist).

## Features

- **Tiny Go Agent** — ~5MB RAM, zero dependencies, active push
- **Python Collector** — SQLite + threshold + offline detection
- **Modern Dashboard** — React 19 + TanStack Table + Cloudflare Pages
- **Alert History** — Persistent via Cloudflare KV
- **One-click Deploy** — Systemd + Docker + Cloudflare
- **Security** — Token auth + Cloudflare Access (Zero Trust)

## Architecture

```
Server → Go Agent → HTTPS → Python Collector → SQLite → Alerts → Telegram + Web Dashboard (Cloudflare)
```

## Quick Start

```bash
# 1. Build Agent
cd agent && go build -o vigil-agent ./...

# 2. Run Collector
cp bot/config.example.py bot/config.py
python bot/main.py

# 3. Deploy Dashboard
cd dash && npm run build && npx wrangler pages deploy dist
```

## Full Deployment

See detailed guide below.

## License

GPL v3
