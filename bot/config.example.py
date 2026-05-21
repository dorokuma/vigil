"""
Vigil Bot - 配置文件示例
复制为 config.py 并填入实际值
"""
import os

# ==== Telegram Bot ====
# 从 @BotFather 获取
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ==== Vigil HTTP 接收端 ====
VIGIL_HOST = "0.0.0.0"
VIGIL_PORT = 9901

# 可选：Agent 上报认证 Token
VIGIL_TOKEN = os.environ.get("VIGIL_TOKEN", "")

# 可选：HTTPS 证书路径（不配则走 HTTP）
# VIGIL_CERTFILE = "/path/to/cert.pem"
# VIGIL_KEYFILE = "/path/to/key.pem"

# ==== SQLite 存储 ====
DB_PATH = os.environ.get("VIGIL_DB_PATH", "vigil.db")

# ==== Pinger（延迟检测）====
# 要 ping 的服务器列表
PING_HOSTS = {
    # "server-alias": "192.168.1.1",
    # "my-server": "example.com",
}

# Ping 间隔（秒）
PING_INTERVAL = 30

# Ping 超时（秒）
PING_TIMEOUT = 5

# ==== 告警阈值 ====
ALERT_CPU = 80.0        # CPU > 80%
ALERT_MEMORY = 90.0     # 内存 > 90%
ALERT_DISK = 85.0       # 磁盘 > 85%
ALERT_OFFLINE_SEC = 180 # 超过 180 秒没上报视为离线
ALERT_RTT = 300.0       # 延迟 > 300ms 告警
ALERT_LOSS = 20.0       # 丢包率 > 20% 告警
ALERT_COOLDOWN = 300    # 同类告警冷却时间（秒）

# 连续失败告警阈值（连续 N 次超阈值才告警）
CONSECUTIVE_THRESHOLD = 3

# ==== 离线检测 ====
OFFLINE_CHECK_INTERVAL = 60  # 每 60 秒检查一次

# ==== Cloudflare Dashboard 告警历史推送（可选）====
# 设置后，真实告警会自动推送到网页版 "告警历史" 页面
# CF_ALERT_URL = "https://your-dash.pages.dev/api/alerts"

# ==== 日志 ====
LOG_LEVEL = "INFO"
