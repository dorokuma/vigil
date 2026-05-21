"""
Vigil - Agent HTTP 接收端
接收 Agent 上报的监控数据
支持可选的 Token 认证、HTTPS 和后台离线检测
"""
import json
import logging
import ssl
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class VigilHandler(BaseHTTPRequestHandler):
    storage = None
    alert_engine = None
    alert_callback = None
    expected_token = None

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/report":
            self._handle_report()
        elif path == "/health":
            self._handle_health()
        elif path == "/status":
            self._handle_status()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "not found"}')

    def _handle_report(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            # Token 验证
            if VigilHandler.expected_token:
                if data.get("token") != VigilHandler.expected_token:
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error": "invalid token"}')
                    return

            hostname = data.get("hostname", "unknown")
            data_type = data.get("type", "heartbeat")
            report_data = data.get("data", {})

            if data_type == "offline":
                self.storage.mark_offline(hostname)
                logger.warning("Agent reported offline: %s", hostname)
            else:
                self.storage.save_report(hostname, report_data)
                if self.alert_engine and self.alert_callback:
                    alerts = self.alert_engine.check_agent_report(hostname, report_data)
                    for alert in alerts:
                        try:
                            self.alert_callback(alert)
                        except Exception as e:
                            logger.error("Alert push failed: %s", e)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except Exception as e:
            logger.error("Report handler error: %s", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_health(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def _handle_status(self):
        try:
            # 合并 Agent 数据和 Pinger 数据
            agent_records = self.storage.get_latest_all()
            ping_records = self.storage.get_ping_latest_all()
            ping_map = {r["hostname"]: r["data"] for r in ping_records if r.get("data")}

            result = []
            for record in agent_records:
                data = record.get("data", {})
                system = data.get("system", {})
                cpu = data.get("cpu", {})
                memory = data.get("memory", {})
                hostname = record["hostname"]

                item = {
                    "hostname": hostname,
                    "source": "agent",
                    "is_offline": bool(record["is_offline"]),
                    "last_seen": record["last_seen"],
                    "uptime": system.get("uptime_sec", 0),
                    "cpu_percent": round(cpu.get("percent", 0), 1),
                    "memory_percent": round(memory.get("percent", 0), 1),
                    "load": {
                        "1m": cpu.get("load_1", 0),
                        "5m": cpu.get("load_5", 0),
                        "15m": cpu.get("load_15", 0),
                    },
                }

                # 合并 Pinger 数据
                if hostname in ping_map:
                    pinger_data = ping_map[hostname].get("pinger", {})
                    item["rtt"] = pinger_data.get("rtt", 0)
                    item["loss_pct"] = pinger_data.get("loss_pct", 0)

                result.append(item)

            # 只有 Pinger 数据但没有 Agent 数据的服务器
            for r in ping_records:
                hostname = r["hostname"]
                if hostname not in {x["hostname"] for x in result}:
                    pinger_data = r.get("data", {}).get("pinger", {})
                    result.append({
                        "hostname": hostname,
                        "source": "pinger",
                        "is_offline": bool(r.get("is_offline", False)),
                        "last_seen": r["last_seen"],
                        "uptime": 0,
                        "cpu_percent": 0,
                        "memory_percent": 0,
                        "load": {"1m": 0, "5m": 0, "15m": 0},
                        "rtt": pinger_data.get("rtt", 0),
                        "loss_pct": pinger_data.get("loss_pct", 0),
                    })

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
        except Exception as e:
            logger.error("Status handler error: %s", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, fmt, *args):
        logger.debug("HTTP %s", fmt % args)


def start_vigil_server(host, port, storage, alert_engine, alert_callback,
                       token=None, certfile=None, keyfile=None):
    VigilHandler.storage = storage
    VigilHandler.alert_engine = alert_engine
    VigilHandler.alert_callback = alert_callback
    VigilHandler.expected_token = token

    server = HTTPServer((host, port), VigilHandler)

    if certfile and keyfile:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        proto = "HTTPS"
    else:
        proto = "HTTP"

    logger.info("Vigil receiver started: %s://%s:%s (token: %s)",
                proto, host, port, "enabled" if token else "disabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Vigil receiver stopped")
        server.server_close()


def start_offline_checker(storage, alert_engine, alert_callback, check_interval=60):
    """后台守护线程：定期检查离线服务器并触发告警"""
    def _checker():
        while True:
            try:
                records = storage.get_latest_all()
                for record in records:
                    if not record.get("is_offline", False):
                        alerts = alert_engine.check_offline(record["hostname"], record["last_seen"])
                        for alert in alerts:
                            try:
                                alert_callback(alert)
                            except Exception as e:
                                logger.error("Offline alert push failed: %s", e)
                time.sleep(check_interval)
            except Exception as e:
                logger.error("Offline checker error: %s", e)
                time.sleep(check_interval)

    t = threading.Thread(target=_checker, daemon=True)
    t.start()
    logger.info("Offline checker started (every %d seconds)", check_interval)
    return t
