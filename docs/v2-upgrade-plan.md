# Vigil 替代旧 engine — 全新方案

## 核心理念
**吸收能力，不兼容代码。**
Vigil 用自己的方式实现一切，bot.py 直接消费 Vigil 原生格式。

## 旧 engine 的 3 个能力

| 能力 | 旧实现 | Vigil 新实现 |
|------|--------|-------------|
| **ICMP ping** | Go exec `ping -c 1`，60秒/次 | **Vigil Pinger** 升级：10秒 `-c 1` 或保持30秒 `-c 5`，写入内存环形缓冲区 |
| **数据聚合** | Go 每分钟计算，写 SQLite | **Vigil Storage** 加聚合器，每分钟写 vigil.db |
| **状态查询** | Go HTTP API：/status /live /history | **Vigil API** 全新格式：`/api/servers` `/api/server/X` `/api/ping/X` |

## 架构图（替代后）

```
┌──────────── 北京服务器 ───────────────┐
│                                        │
│  Vigil 采集端（单一进程）                │
│  ┌──────────┐  ┌──────────────────┐    │
│  │ Pinger   │→ │ Storage          │    │
│  │ (升级版)  │  │ ┌──────────────┐│    │
│  │ 10秒ping │  │ │ 环形缓冲区    ││    │
│  │ 内存缓存  │  │ │ ping历史表    ││    │
│  └──────────┘  │ │ Agent系统指标  ││    │
│                │ └──────────────┘│    │
│  ┌──────────┐  └──────────────────┘    │
│  │ receiver │        ↓                 │
│  │ Agent接收│  ┌──────────────────┐    │
│  └──────────┘  │ API (Vigil格式)   │    │
│                │ /api/servers      │    │
│  ┌──────────┐  │ /api/server/:name │    │
│  │ alerts   │  │ /api/ping/:name   │    │
│  └──────────┘  └──────────────────┘    │
│                       ↓                │
│  ┌──────────────────────────────────┐  │
│  │ bot.py（直接消费 Vigil API）      │  │
│  │ /status /ping /chart /alert      │  │
│  │ /vigil /mihomo                  │  │
│  └──────────────────────────────────┘  │
│                                        │
└────────────────────────────────────────┘
```

## 改动清单

### 1. Vigil pinger.py — 升级
- 周期：每 10 秒 `ping -c 1`（比旧 engine 的 60 秒密集 6 倍）
- 内存环形缓冲区：保存最近 3600 条（10h @10s）
- 结果同时写入 storage.py 的 ping_data 表
- 聚合器：每分钟从缓冲区计算 avg/min/max/jitter/loss → ping_history

### 2. Vigil storage.py — 加表
```sql
-- 最新 ping 状态（每台服务器一条）
ping_latest(hostname, rtt, loss_pct, last_ok, updated_at)

-- ping 历史聚合（每分钟一条）
ping_history(hostname, time_start, avg_rtt, min_rtt, max_rtt, jitter, loss_pct, samples)
```

### 3. Vigil receiver.py — 加 Vigil 格式 API
```
GET /api/servers  → 所有服务器统一状态（ping + 系统指标）
GET /api/server/<hostname>  → 单台详细数据
GET /api/ping/<hostname>?n=60  → 原始 ping 序列（替代旧 /live）
```

### 4. bot.py — 直接改造
不改 `api_get()` 函数，而是直接在新格式上重写各个命令的数据获取逻辑：
- cmd_status：从 `/api/servers` 读，解析 Vigil 格式
- cmd_ping：从 `/api/ping/<server>?n=N` 读
- cmd_chart：同上
- check_servers：从 `/api/servers` 读，Vigil 自己的告警逻辑
- 删掉 `API_BASE` 配置项

### 5. 旧 engine
```bash
systemctl disable --now srv_mon_new.service
rm -rf /root/server-monitor/engine/
```

## 为什么这样更好

| 对比项 | 兼容方案 | 全新方案 |
|--------|---------|---------|
| 代码复杂度 | 多一层转换 | 直来直去 |
| 数据格式 | 两套（旧+新） | 一套 |
| 出bug排查 | 要查转换层 | 直接查源头 |
| 后续扩展 | 受旧格式限制 | 自由扩展 |
| 重构信心 | "改了这个会破坏兼容吗" | "这就是我们的格式" |
