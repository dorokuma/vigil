"""
Vigil - Agent HTTP receiver
Receives monitoring data from agents via HTTP POST.
"""
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class VigilHandler(BaseHTTPRequestHandler):
    storage = None
    alert_engine = None
    alert_callback = None

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


def start_vigil_server(host, port, storage, alert_engine, alert_callback):
    VigilHandler.storage = storage
    VigilHandler.alert_engine = alert_engine
    VigilHandler.alert_callback = alert_callback

    server = HTTPServer((host, port), VigilHandler)
    logger.info("Vigil receiver started: http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Vigil receiver stopped")
        server.server_close()
