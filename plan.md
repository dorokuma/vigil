# Server Monitor — 服务器监控 Telegram Bot

## 项目概述

基于 Telegram Bot 的服务器监控系统，以北京腾讯云服务器为探针，通过 ICMP ping 秒级监控旗下所有服务器的网络质量和系统状态。Go 引擎负责高频采集，Python Bot 负责 Telegram 交互和告警推送，两进程通过 localhost HTTP API + SQLite 通信。出站走 Cloudflare Workers 反代 + long polling。

## 核心约束

- 北京腾讯云服务器 2C2G，公网 IP 但域名无备案
- 底线的底线：不改 Hermes 源码、不动系统钩子
- 项目文件全部集中在 /root/server-monitor/ 下，不散落

## 受监控服务器

共 7 台服务器，代号与地理位置如下：

- hongkong — 香港
- tokyo — 东京
- mumbai — 孟买
- sanjose — 圣何塞
- columbus — 哥伦布
- geek — Geek
- aione — Aione

北京是探针本身。eqi12 和你自己不在监控范围内。

## 架构设计

### 双进程架构

**Go 监控引擎**负责三件事：

- **Ping 管道** — 7 个 goroutine 各自持有一台目标服务器的 Tailscale IP，每秒发 ICMP packet 一次，结果写入内存环形缓冲区。
- **聚合管道** — 每分钟唤醒一次，对每台服务器过去 60 秒样本计算平均延迟、最小/最大延迟、抖动（相邻样本差的均方差）、丢包率、样本数，结果写入 SQLite。
- **HTTP API 管道** — Vigil HTTP 服务监听 localhost:9901，提供 /api/servers（统一状态）、/api/ping/<hostname>（原始 ping 数据）、/health（健康检查）等端点。

**Python Telegram Bot** 负责四组命令：

- /status — 所有服务器状态一览，颜色标注正常/警告/告警。
- /ping — 查看延迟详情（/ping 全部、/ping hongkong 30s 实时曲线、/ping hongkong week 周趋势）。
- /alert — 管理告警规则（/alert list、/alert threshold 200、/alert silence tokyo 2h）。
- /help — 命令列表。

另有一个后台巡检循环每 30 秒检查状态，异常时推送告警。

### 通信方式

Vigil Collector（Python）整合 Pinger + HTTP API + Storage，监听 9901 端口。Bot 通过 localhost:9901 调用 Vigil API。SQLite 位于 /root/server-monitor/data/vigil.db。

### 网络出口

Bot 到 Telegram 走 Cloudflare Workers 反代 + long polling。Worker 绑你的自定义域名，做透明透传。不出 tunnel 不出证书。

## 数据存储

### 内存环形缓冲区

每台服务器一个环形缓冲区，容量 3600 条（1 小时秒级数据）。每条记录 24 字节（时间戳 int64 + RTT float64 + 状态 byte），每台 86KB，7 台共约 600KB。Go struct 与对齐开销后约 3MB，对 2GB 内存零压力。

### SQLite

一张表：ping_aggregates(server TEXT, time_start INTEGER, time_end INTEGER, avg_rtt REAL, min_rtt REAL, max_rtt REAL, jitter REAL, packet_loss REAL, samples INTEGER)。按 (server, time_start) 建索引。每分钟写入 7 条，一天 10080 条，一年约 370 万条。

## 告警策略

- 单次 ping 超时不告警（网络抖动）
- 同一台服务器最近 60 秒丢包率超过 20% 告警
- 同一台服务器连续 5 次 ping 超时告警
- 恢复通知：服务器从告警状态恢复后自动发送
- 告警压缩：同一原因 5 分钟内不重复推送，防止告警风暴

## 项目文件清单

/root/server-monitor/
├── plan.md                    # 本方案文档
├── engine/                    # Go 监控引擎
│   ├── main.go
│   ├── go.mod
│   ├── go.sum
│   └── ping/
│       ├── pinger.go          # ICMP ping 循环与环形缓冲区
│       ├── aggregator.go      # 每分钟聚合逻辑
│       ├── api.go             # HTTP API 端点
│       └── store.go           # SQLite 写入
├── bot/                       # Python Telegram Bot
│   ├── bot.py                 # 主入口与 handler
│   ├── config.py              # 配置
│   └── requirements.txt
├── deploy/                    # 部署
│   ├── vigil-collector.service  # Vigil 采集端 systemd
│   ├── server-bot.service     # Python Bot systemd
│   └── install.sh             # 一键部署
├── cloudflare/
│   └── worker.js              # Workers 反代脚本
└── data/
    └── .gitkeep

## 部署步骤

### Phase 1：Go 引擎

1. 安装 Go 编译环境，编译 engine/
2. setcap cap_net_raw+ep 赋予 ICMP raw socket 权限
3. systemctl 启动 server-monitor 服务
4. journalctl 验证 ping 循环正常

### Phase 2：Python Bot

1. python3 -m venv + pip install python-telegram-bot
2. 配置 BOT_TOKEN 和 WORKER_URL 环境变量
3. systemctl 启动 server-bot 服务
4. 发 /status 命令验证回复

### Phase 3：Cloudflare Worker

1. 在 Workers 面板创建新 Worker
2. 粘贴 worker.js 内容
3. 绑定你的自定义域名
4. curl 验证透传正常

## 验证清单

1. Go 引擎运行 60 秒后，SQLite 出现聚合记录
2. /status 返回 7 台服务器延迟数据，颜色标注正确
3. 模拟断网后 Bot 推送告警到 Telegram
4. /ping xxx week 返回 SQLite 历史聚合
5. /alert threshold 300 生效
6. Worker 转发 Bot 消息成功
