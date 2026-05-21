"""
Vigil - Agent HTTP receiver
Receives monitoring data from agents via HTTP POST.
Supports optional token auth, HTTPS, and background offline checking.
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

            # Token auth check (if enabled)
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
                    alerts = self.alert_engine.check(hostname, report_data)
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
            records = self.storage.get_latest_all()
            result = []
            for record in records:
                data = record.get("data", {})
                system = data.get("system", {})
                cpu = data.get("cpu", {})
                memory = data.get("memory", {})
                result.append({
                    "hostname": record["hostname"],
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


def start_vigil_server(host, port, storage, alert_engine, alert_callback, token=None, certfile=None, keyfile=None):
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

    logger.info("Vigil receiver started: %s://%s:%s (token: %s)", proto, host, port, "enabled" if token else "disabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Vigil receiver stopped")
        server.server_close()


def start_offline_checker(storage, alert_engine, alert_callback, check_interval=60):
    """后台守护线程：定期检查离线服务器并自动触发 critical 告警"""
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
