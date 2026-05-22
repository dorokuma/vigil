# Vigil - Bot 配置示例
# 复制为 config.py 并修改

# ==== HTTP 服务 ====
VIGIL_HOST = "0.0.0.0"
VIGIL_PORT = 9901
# 可选 Token 认证
# VIGIL_TOKEN = "your-secret-token"
# 可选 HTTPS
# VIGIL_CERTFILE = "/path/to/cert.pem"
# VIGIL_KEYFILE = "/path/to/key.pem"

# ==== 数据库 ====
DB_PATH = "vigil.db"

# ==== 告警阈值 ====
ALERT_CPU = 80.0       # CPU 使用率超过此值告警
ALERT_MEMORY = 85.0    # 内存使用率超过此值告警
ALERT_DISK = 90.0      # 磁盘使用率超过此值告警

# ==== Agent 离线检测 ====
OFFLINE_CHECK_INTERVAL = 60  # 每 60 秒检查一次

# ==== 日志 ====
LOG_LEVEL = "INFO"
