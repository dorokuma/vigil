"""
Vigil Collector - 配置文件示例
复制为 config.py 并填入实际值
"""
import os

# ==== HTTP 服务 ====
VIGIL_HOST = "0.0.0.0"
VIGIL_PORT = 9901

# Agent 上报认证 Token（建议设置）
VIGIL_TOKEN = os.environ.get("VIGIL_TOKEN", "")

# 可选 HTTPS
# VIGIL_CERTFILE = "/path/to/cert.pem"
# VIGIL_KEYFILE = "/path/to/key.pem"

# ==== 数据库 ====
DB_PATH = os.environ.get("VIGIL_DB_PATH", "/root/server-monitor/data/vigil.db")

# ==== Pinger（延迟检测）====
# 要 ping 的目标服务器列表，格式： "名称": "IP或域名"
PING_HOSTS = {
    # "my-server": "192.168.1.1",
    # "my-vps": "example.com",
}

# Ping 间隔（秒）
PING_INTERVAL = 10

# Ping 超时（秒）
PING_TIMEOUT = 5

# ==== 告警阈值 ====
ALERT_CPU = 80.0
ALERT_MEMORY = 90.0
ALERT_DISK = 85.0
ALERT_OFFLINE_SEC = 180
ALERT_COOLDOWN = 300

# ==== Agent 离线检测 ====
OFFLINE_CHECK_INTERVAL = 60

# ==== 本机标识 ====
LOCAL_HOSTNAME = "beijing"

# ==== 日志 ====
LOG_LEVEL = "INFO"
