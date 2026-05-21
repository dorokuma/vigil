<div align="center">
  <h1>🔭 Vigil</h1>
  <p><em>轻量级服务器主动推送监控系统</em></p>
  <p>
    <a href="#features-">特性</a> •
    <a href="#architecture-">架构</a> •
    <a href="#quick-start-">快速开始</a> •
    <a href="#metrics-">采集指标</a> •
    <a href="#license-">许可证</a>
  </p>
  <p>
    <a href="README.md">🇬🇧 English</a>
  </p>
</div>

---

**Vigil** 是一个轻量级服务器监控系统。与传统中心化轮询（ping/SNMP）不同，Vigil 在每台服务器上运行一个极小的 Go Agent，主动读取 `/proc/` 指标并通过 HTTP 推送到中心采集端。

## 特性 ✨

- **单二进制 Agent** — Go 编译，~5MB 内存占用，零依赖，scp 过去就能跑
- **双架构支持** — 预编译 `linux/amd64` 和 `linux/arm64` 两个版本
- **主动推送模式** — 被监控服务器无需开放任何入站端口
- **Systemd 托管** — 崩溃自动重启，日志通过 journalctl 查看
- **极简采集端** — Python 3 HTTP 服务 + SQLite，不需要外部数据库
- **阈值告警** — CPU/内存/磁盘超限自动推送 Telegram
- **CI 自动编译** — 打 tag 推送到 GitHub 自动编译，Releases 页直接下载

## 架构 🏗

```
每台服务器 --> Agent (Go) --> HTTP POST /report --> 采集端 (Python) --> SQLite --> 告警 --> Telegram
```

| 组件 | 语言 | 作用 |
|------|------|------|
| **Agent** | Go | 运行在各服务器上，采集 `/proc/*` 指标，推送到采集端 |
| **采集端** | Python 3 | 接收上报数据，存入 SQLite，计算告警规则 |
| **存储** | SQLite | 嵌入式零配置，每台服务器保留 7 天历史 |
| **告警引擎** | Python | 基于阈值的 CPU/内存/磁盘/离线告警，带冷却防刷 |

## 快速开始 🚀

### 1. 编译 Agent

```bash
cd agent
go mod tidy

# AMD64（大多数云服务器）
GOOS=linux GOARCH=amd64 go build -o vigil-agent-linux-amd64 ./...

# ARM64（Oracle ARM、Apple Silicon 服务器）
GOOS=linux GOARCH=arm64 go build -o vigil-agent-linux-arm64 ./...
```

### 2. 配置 Agent

在每台目标服务器上创建 `/etc/vigil/config.json`：

```json
{
    "server_url": "http://your-collector:9901",
    "interval": 30,
    "hostname": "my-server-01"
}
```

`hostname` 留空会自动使用系统主机名。

### 3. 安装为 systemd 服务

```bash
cp vigil-agent-linux-* /usr/local/bin/vigil-agent
chmod +x /usr/local/bin/vigil-agent
mkdir -p /etc/vigil
cp deploy/vigil-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vigil-agent
```

或用一键安装脚本：

```bash
bash deploy/install.sh amd64 my-server-01 http://your-collector:9901
```

### 4. 配置采集端

将采集端组件集成到你的 Python Bot 中：

```python
from receiver import start_vigil_server
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
    print(f"告警: {alert['hostname']} - {alert['message']}")

start_vigil_server("0.0.0.0", 9901, storage, engine, alert_callback)
```

完整源码见 `bot-ext/` 目录。

## 采集指标 📊

所有指标通过读取 `/proc/` 获取，不依赖外部命令。

| 指标 | 数据来源 | 单位 |
|------|---------|------|
| CPU 使用率 | `/proc/stat`（差值计算） | % |
| 系统负载 | `/proc/loadavg` | 1/5/15 分钟 |
| 内存使用 | `/proc/meminfo`（MemAvailable） | MB, % |
| 磁盘使用 | `statfs()` 系统调用 | GB, % |
| 网络流量 | `/proc/net/dev`（差值计算） | bytes, bps |
| 运行时间 | `/proc/uptime` | 秒 |
| 进程数 | `/proc/[0-9]*` 计数 | 个 |
| 内核版本 | `/proc/version` | 字符串 |

## Agent 上报数据格式

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
            "kernel_version": "Linux version 6.12.74 ...",
            "timestamp": 1700000000
        }
    }
}
```

## Telegram 告警集成

```python
async def push_alert(alert):
    icon = "🚨" if alert["severity"] == "critical" else "⚠️"
    text = f"{icon} {alert['hostname']}\n{alert['message']}"
    await application.bot.send_message(chat_id=你的聊天ID, text=text)
```

## 为什么用 Vigil？

**相比 LLM-Wiki 或传统 RAG**——这是一个真正服务于真实服务器的监控系统。没有"增量知识编译"，没有"图谱检索"。只是一个读取 `/proc/` 并推送 JSON 的 Go 二进制。

## 许可证

GPL v3
