"""
Vigil Main — 采集端入口
整合 Pinger + Storage + Alerts + HTTP API
吸收旧 engine 全部能力
"""
import asyncio
import logging
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage import VigilStorage
from alerts import VigilAlertEngine
from receiver import start_vigil_server, start_offline_checker
from pinger import Pinger

try:
    import config as cfg
except ImportError:
    cfg = None
    print("WARNING: config.py not found, using env vars")

log_level = getattr(cfg, "LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO"))
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vigil")


def main():
    logger.info("=== Vigil Collector starting ===")

    # ── 配置 ──
    db_path = getattr(cfg, "DB_PATH", os.environ.get("VIGIL_DB_PATH", "vigil.db"))
    host = getattr(cfg, "VIGIL_HOST", "0.0.0.0")
    port = getattr(cfg, "VIGIL_PORT", 9901)
    token = getattr(cfg, "VIGIL_TOKEN", os.environ.get("VIGIL_TOKEN", ""))
    certfile = getattr(cfg, "VIGIL_CERTFILE", None)
    keyfile = getattr(cfg, "VIGIL_KEYFILE", None)

    alert_config = {
        "cpu_threshold": getattr(cfg, "ALERT_CPU", 80.0),
        "memory_threshold": getattr(cfg, "ALERT_MEMORY", 90.0),
        "disk_threshold": getattr(cfg, "ALERT_DISK", 85.0),
        "offline_sec": getattr(cfg, "ALERT_OFFLINE_SEC", 180),
        "cooldown": getattr(cfg, "ALERT_COOLDOWN", 300),
    }

    # ── 初始化组件 ──
    storage = VigilStorage(db_path)
    alert_engine = VigilAlertEngine(alert_config)

    # 告警回调
    def alert_callback(alert):
        icon = "\U0001f6a8" if alert["severity"] == "critical" else "\u26a0\ufe0f"
        logger.warning("%s [%s] %s: %s", icon, alert["type"],
                       alert["hostname"], alert["message"])

    # ── 启动 Pinger（吸收旧 engine 的 ping 能力）──
    ping_hosts = getattr(cfg, "PING_HOSTS", {})
    ping_interval = getattr(cfg, "PING_INTERVAL", 10)
    ping_timeout = getattr(cfg, "PING_TIMEOUT", 5)

    pinger = Pinger(hosts=ping_hosts, storage=storage)

    async def run_pinger_async():
        await pinger.start()
        try:
            await pinger._task
        except asyncio.CancelledError:
            pass

    def run_pinger():
        asyncio.run(run_pinger_async())

    pinger_thread = threading.Thread(target=run_pinger, daemon=True, name="vigil-pinger")
    pinger_thread.start()
    logger.info("Pinger thread started")

    # ── 启动 HTTP 服务 ──
    http_thread = threading.Thread(
        target=start_vigil_server,
        args=(host, port, storage, alert_engine, alert_callback),
        kwargs={"token": token, "certfile": certfile, "keyfile": keyfile, "pinger": pinger},
        daemon=True,
        name="vigil-http",
    )
    http_thread.start()

    # ── 启动离线检查 ──
    start_offline_checker(storage, alert_engine, alert_callback, 60)

    logger.info("=== Vigil Collector is running ===")
    logger.info("  HTTP: %s:%s", host, port)
    logger.info("  Pinger: %d servers every 10s", len(pinger.get_servers()))
    logger.info("  DB: %s", db_path)
    logger.info("  Token: %s", "enabled" if token else "disabled")

    # 保持主线程存活
    try:
        while True:
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Vigil Collector stopped")


if __name__ == "__main__":
    main()
