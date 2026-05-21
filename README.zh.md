<div align="center">
  <h1>🔭 Vigil</h1>
  <p><em>轻量级服务器主动推送监控系统</em></p>
  <p>
    <a href="#features-">特性</a> •
    <a href="#architecture-">架构</a> •
    <a href="#quick-start-">快速开始</a> •
    <a href="#security-">安全与 HTTPS</a> •
    <a href="#docker-">Docker 部署</a> •
    <a href="#metrics-">采集指标</a> •
    <a href="#license-">许可证</a>
  </p>
  <p>
    <a href="README.md">🇬🇧 English</a>
  </p>
</div>

---

**Vigil** 是一个轻量级服务器监控系统。与传统中心化轮询（ping/SNMP）不同，Vigil 在每台服务器上运行一个极小的 Go Agent，主动读取 `/proc/` 指标并通过 HTTP/HTTPS 推送到中心采集端。

## 特性 ✨

- **单二进制 Agent** — Go 编译，~5MB 内存占用，零依赖，scp 过去就能跑
- **双架构支持** — 预编译 `linux/amd64` 和 `linux/arm64` 两个版本
- **主动推送模式** — 被监控服务器无需开放任何入站端口
- **Systemd 托管** — 崩溃自动重启，日志通过 journalctl 查看
- **极简采集端** — Python 3 HTTP/HTTPS 服务 + SQLite，不需要外部数据库
- **Token 认证** — 可选共享密钥保护 /report 接口
- **HTTPS 支持** — 原生 TLS（传入 certfile/keyfile 即可）
- **阈值 + 离线告警** — CPU/内存/磁盘 + 后台自动检测离线
- **CI 自动编译** — 打 tag 推送到 GitHub 自动编译，Releases 页直接下载

## 架构 🏗

```
每台服务器 --> Agent (Go) --> HTTP/HTTPS POST /report --> 采集端 (Python) --> SQLite --> 告警 --> Telegram
```

| 组件 | 语言 | 作用 |
|------|------|------|
| **Agent** | Go | 运行在各服务器上，采集 `/proc/*` 指标，推送到采集端（支持 https://） |
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
    "server_url": "https://your-collector:9901",
    "interval": 30,
    "hostname": "my-server-01",
    "token": "super-secret-123"   // 可选但推荐
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
bash deploy/install.sh amd64 my-server-01 https://your-collector:9901
```

### 4. 配置采集端

将采集端组件集成到你的 Python Bot 中：

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
    print(f"告警: {alert['hostname']} - {alert['message']}")

# 启动 HTTPS + Token 服务器
start_vigil_server("0.0.0.0", 9901, storage, engine, alert_callback,
                   token="super-secret-123",
                   certfile="/path/to/fullchain.pem",
                   keyfile="/path/to/privkey.pem")

# 启用自动离线告警（后台线程）
start_offline_checker(storage, engine, alert_callback, check_interval=60)
```

### 5. 或直接运行完整 Bot

克隆本仓库，直接使用 `bot/` 模块：

```bash
cp bot/config.example.py bot/config.py
# 编辑 bot/config.py 填入你的配置
python bot/main.py
```

Bot 包含以下功能：
- **Pinger** — 基于 ping 的延迟和丢包检测
- **Receiver** — 接收 Agent 上报数据的 HTTP/HTTPS 服务
- **Alert Engine** — 对 Agent 数据和 Pinger 结果进行阈值告警
- **Offline Checker** — 后台线程自动检测离线服务器

完整源码见 `bot/` 目录。

## 安全与 HTTPS 🔒

**Token 认证**（生产环境强烈推荐）
- 在 Agent 的 config.json 和采集端设置相同的 `token`
- 采集端会拒绝 token 不匹配的请求（返回 401）
- HTTP 和 HTTPS 都支持

**HTTPS 支持**
- 调用 `start_vigil_server` 时传入 `certfile` 和 `keyfile`（PEM 格式）
- Agent 遇到 `https://` 开头的 server_url 会自动使用 TLS
- Go Agent 无需任何修改

**离线自动检测**
- `start_offline_checker(...)` 启动守护线程，每 N 秒检查 `last_seen`
- 超过阈值自动触发 **critical** 级别离线告警

## Docker 部署 🐳

### 使用 Docker Compose 快速部署

```bash
# 1. 克隆仓库
git clone https://github.com/dorokuma/vigil.git
cd vigil/deploy

# 2. 生成自签名证书（或使用真实证书）
./generate-selfsigned-cert.sh your-server-ip-or-domain

# 3. 创建你的集成脚本（your-bot.py）
#    参考 bot-ext/ 目录里的 receiver.py、storage.py、alerts.py

# 4. 编辑 docker-compose.yml（修改 TOKEN、路径等）

# 5. 启动服务
docker compose up -d

# 查看日志
docker compose logs -f
```

完整示例见 `deploy/docker-compose.yml`（包含健康检查、数据库持久化、证书挂载）。

**生产环境建议：**
- 使用真实证书（Let's Encrypt + certbot）
- 为 `vigil.db` 挂载持久化卷
- 通过环境变量设置强密码 TOKEN
- 如需更强安全，可在前面加 Nginx/Traefik 反向代理

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
