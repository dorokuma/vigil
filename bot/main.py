"""
Vigil - 监控 Bot 入口
整合 Agent 接收端 + Pinger 延迟检测 + 告警引擎

使用方法：
  1. 复制 config.example.py 为 config.py，填入配置
  2. 运行 python main.py
"""
import asyncio
import logging
import threading
import os
import sys

# 将当前目录加入路径，确保能引入各模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from receiver import start_vigil_server, start_offline_checker
from storage import VigilStorage
from alerts import VigilAlertEngine
from pinger import Pinger

try:
    import httpx  # 用于推送告警到 Cloudflare Dashboard
except ImportError:
    httpx = None

# 尝试加载配置
try:
    import config as cfg
except ImportError:
    cfg = None
    print("WARNING: config.py not found. Using environment variables.")

log_level = getattr(cfg, "LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO"))
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vigil")

# Cloudflare Dashboard 告警推送地址（可选）
CF_ALERT_URL = getattr(cfg, "CF_ALERT_URL", os.environ.get("CF_ALERT_URL", ""))


def main():
    logger.info("=== Vigil Monitor Bot starting ===")

    db_path = getattr(cfg, "DB_PATH", os.environ.get("VIGIL_DB_PATH", "vigil.db"))
    vigil_host = getattr(cfg, "VIGIL_HOST", "0.0.0.0")
    vigil_port = getattr(cfg, "VIGIL_PORT", 9901)
    vigil_token = getattr(cfg, "VIGIL_TOKEN", os.environ.get("VIGIL_TOKEN", ""))
    vigil_certfile = getattr(cfg, "VIGIL_CERTFILE", None)
    vigil_keyfile = getattr(cfg, "VIGIL_KEYFILE", None)

    ping_hosts = getattr(cfg, "PING_HOSTS", {})
    ping_interval = getattr(cfg, "PING_INTERVAL", 30)
    ping_timeout = getattr(cfg, "PING_TIMEOUT", 5)

    offline_check_interval = getattr(cfg, "OFFLINE_CHECK_INTERVAL", 60)

    storage = VigilStorage(db_path)

    alert_config = {
        "cpu_threshold": getattr(cfg, "ALERT_CPU", 80.0),
        "memory_threshold": getattr(cfg, "ALERT_MEMORY", 90.0),
        "disk_threshold": getattr(cfg, "ALERT_DISK", 85.0),
        "rtt_threshold": getattr(cfg, "ALERT_RTT", 300.0),
        "loss_threshold": getattr(cfg, "ALERT_LOSS", 20.0),
        "offline_sec": getattr(cfg, "ALERT_OFFLINE_SEC", 180),
        "cooldown": getattr(cfg, "ALERT_COOLDOWN", 300),
        "consecutive_threshold": getattr(cfg, "CONSECUTIVE_THRESHOLD", 3),
    }
    alert_engine = VigilAlertEngine(alert_config)

    # 告警回调（同时推送到 Telegram + Cloudflare Dashboard）
    def alert_callback(alert):
        icon = "\U0001f6a8" if alert["severity"] == "critical" else "\u26a0\ufe0f"
        msg = f"{icon} [{alert['type']}] {alert['hostname']}: {alert['message']}"
        logger.warning(msg)

        # 推送到 Cloudflare 前端告警历史（如果配置了 URL）
        if CF_ALERT_URL and httpx:
            try:
                httpx.post(CF_ALERT_URL, json=alert, timeout=3)
            except Exception as e:
                logger.debug(f"推送 CF Dashboard 失败: {e}")

    http_thread = threading.Thread(
        target=start_vigil_server,
        args=(vigil_host, vigil_port, storage, alert_engine, alert_callback),
        kwargs={"token": vigil_token, "certfile": vigil_certfile, "keyfile": vigil_keyfile},
        daemon=True,
        name="vigil-http",
    )
    http_thread.start()

    start_offline_checker(storage, alert_engine, alert_callback, offline_check_interval)

    logger.info("Vigil Monitor Bot is running!")
    logger.info("  HTTP receiver: %s:%s", vigil_host, vigil_port)
    logger.info("  Token auth: %s", "enabled" if vigil_token else "disabled")
    logger.info("  Database: %s", db_path)

    if ping_hosts:
        logger.info("  Pinger: %d hosts every %ds", len(ping_hosts), ping_interval)
    else:
        logger.info("  Pinger: disabled (no PING_HOSTS configured)")

    async def run_pinger():
        pinger = Pinger(ping_hosts, ping_interval, ping_timeout, storage)
        await pinger.start()

    if ping_hosts:
        loop = asyncio.new_event_loop()
        threading.Thread(
            target=lambda: loop.run_until_complete(run_pinger()),
            daemon=True,
            name="vigil-pinger",
        ).start()

    try:
        while True:
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Vigil Monitor Bot stopped")


if __name__ == "__main__":
    main()
