# Vigil 🔭

Lightweight server monitoring agent with active push mode.

Instead of traditional centralized polling (ping/SNMP), **Vigil runs a tiny Go agent on each server** that reads `/proc/` metrics and pushes them via HTTP to a central collector.

## Architecture

```
Every server -> Agent (Go binary) -> HTTP POST /report -> Collector -> SQLite -> Alert Engine -> Telegram
```

- **Agent**: Single Go binary, ~5MB RAM, zero dependencies
- **Collector**: Python 3 HTTP server (receiver.py + storage.py + alerts.py)
- **Storage**: SQLite, no external database required
- **Alerting**: Threshold-based CPU/Memory/Disk alerts

## Quick Start

### 1. Build the Agent

```bash
cd agent
go mod tidy

# Build for AMD64
GOOS=linux GOARCH=amd64 go build -o vigil-agent-linux-amd64 ./...

# Build for ARM64
GOOS=linux GOARCH=arm64 go build -o vigil-agent-linux-arm64 ./...
```

### 2. Configure

Create `/etc/vigil/config.json` on the target server:

```json
{
    "server_url": "http://your-collector:9901",
    "interval": 30,
    "hostname": "my-server-01"
}
```

### 3. Install as a systemd service

```bash
cp vigil-agent-linux-* /usr/local/bin/vigil-agent
chmod +x /usr/local/bin/vigil-agent
mkdir -p /etc/vigil
# write config.json as above
cp deploy/vigil-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vigil-agent
```

Or use the install script:

```bash
bash deploy/install.sh amd64 my-server-01 http://your-collector:9901
```

### 4. Set up the Collector

See `bot-ext/` for the Python receiver components. Integrate into your bot:

```python
from receiver import start_vigil_server
from storage import VigilStorage
from alerts import VigilAlertEngine

storage = VigilStorage("/path/to/vigil.db")
engine = VigilAlertEngine({"cpu_threshold": 80, "memory_threshold": 90})

def alert_callback(alert):
    print(f"ALERT: {alert['message']}")

start_vigil_server("0.0.0.0", 9901, storage, engine, alert_callback)
```

## Collected Metrics

| Metric | Source | Unit |
|--------|--------|------|
| CPU usage | `/proc/stat` delta | % |
| System load | `/proc/loadavg` | 1/5/15 min |
| Memory | `/proc/meminfo` (MemAvailable) | MB, % |
| Disk | `statfs()` syscall | GB, % |
| Network traffic | `/proc/net/dev` delta | bytes, bps |
| Uptime | `/proc/uptime` | seconds |
| Process count | `/proc/[0-9]*` count | integer |

## Agent Report Format

```json
{
    "hostname": "server-01",
    "type": "heartbeat",
    "data": {
        "cpu": { "percent": 45.2, "load_1": 2.1, "load_5": 1.8, "load_15": 1.5 },
        "memory": { "total_mb": 16000, "used_mb": 8000, "avail_mb": 8000, "percent": 50.0 },
        "disks": [{ "mount_point": "/", "total_gb": 100, "used_gb": 60, "free_gb": 40, "percent": 60.0 }],
        "network": [{ "interface": "eth0", "rx_bytes": 123456789, "tx_bytes": 98765432, "rx_speed_bps": 1000000, "tx_speed_bps": 500000 }],
        "system": { "hostname": "server-01", "uptime_sec": 3600, "process_cnt": 200, "kernel_version": "Linux ...", "timestamp": 1700000000 }
    }
}
```

## Telegram Alerts

Example alert callback for Telegram:

```python
async def push_alert(alert):
    icon = "\U0001f6a8" if alert["severity"] == "critical" else "\u26a0\ufe0f"
    text = f"{icon} {alert['hostname']}\n{alert['message']}"
    await application.bot.send_message(chat_id=YOUR_CHAT_ID, text=text)
```

## License

GPL v3
