"""
Vigil - HTTP 接收端 + API
接收 Agent 上报 + 提供 Vigil 原生格式 API
吸收旧 engine 的 API 能力（用自己的格式）
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
    pinger = None  # Pinger 实例（同步接口）

    # ── 路由 ──────────────────────────────────────────────

    def do_GET(self):
        path = urlparse(self.path).path
        handlers = {
            "/health": self._handle_health,
            "/status": self._handle_agent_status,
            "/api/servers": self._handle_api_servers,
        }
        # /api/server/<name>
        if path.startswith("/api/server/"):
            handlers[path] = lambda: self._handle_api_server(path[12:])
        # /api/ping/<name>
        elif path.startswith("/api/ping/"):
            handlers[path] = lambda: self._handle_api_ping(path[11:])

        handler = handlers.get(path, self._handle_404)
        handler()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/report":
            self._handle_report()
        else:
            self._handle_404()

    # ── Agent 上报 ───────────────────────────────────────

    def _handle_report(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            if VigilHandler.expected_token:
                if data.get("token") != VigilHandler.expected_token:
                    self._json_response(401, {"error": "invalid token"})
                    return

            hostname = data.get("hostname", "unknown")
            data_type = data.get("type", "heartbeat")
            report_data = data.get("data", {})

            if data_type == "offline":
                self.storage.mark_offline(hostname)
                logger.warning("Agent offline: %s", hostname)
            else:
                self.storage.save_report(hostname, report_data)
                if self.alert_engine and self.alert_callback:
                    for alert in self.alert_engine.check_agent_report(hostname, report_data):
                        try:
                            self.alert_callback(alert)
                        except Exception as e:
                            logger.error("Alert push failed: %s", e)

            self._json_response(200, {"status": "ok"})
        except Exception as e:
            logger.error("Report error: %s", e)
            self._json_response(500, {"error": str(e)})

    # ── 健康检查 ─────────────────────────────────────────

    def _handle_health(self):
        self._json_response(200, {"status": "ok", "service": "vigil"})

    # ── Agent 状态（旧格式兼容？不用——这是Vigil自己的格式）──

    def _handle_agent_status(self):
        """返回所有 Agent 的状态（只有装了 Agent 的服务器才有数据）"""
        try:
            records = self.storage.get_latest_all()
            result = []
            for r in records:
                data = r.get("data", {})
                cpu = data.get("cpu", {})
                mem = data.get("memory", {})
                sys = data.get("system", {})
                result.append({
                    "hostname": r["hostname"],
                    "is_offline": bool(r["is_offline"]),
                    "last_seen": r["last_seen"],
                    "cpu_percent": round(cpu.get("percent", 0), 1),
                    "memory_percent": round(mem.get("percent", 0), 1),
                    "uptime": sys.get("uptime_sec", 0),
                    "load": {
                        "1m": cpu.get("load_1", 0),
                        "5m": cpu.get("load_5", 0),
                        "15m": cpu.get("load_15", 0),
                    },
                })
            self._json_response(200, result)
        except Exception as e:
            logger.error("Status error: %s", e)
            self._json_response(500, {"error": str(e)})

    # ── Vigil 统一 API ──────────────────────────────────

    def _handle_api_servers(self):
        """统一服务器状态 API — 合并 ping + Agent 数据"""
        try:
            ping_data = self.storage.get_ping_latest_all() if self.storage else []
            agent_data = self.storage.get_latest_all() if self.storage else []

            # 建索引
            ping_map = {r["hostname"]: r for r in ping_data}
            agent_map = {r["hostname"]: r for r in agent_data}

            # 从 pinger 取服务器列表
            all_hostnames = []
            if self.pinger:
                all_hostnames = [s["name"] for s in self.pinger.get_servers()]

            # 也加上有 Agent 数据的
            for h in agent_map:
                if h not in all_hostnames:
                    all_hostnames.append(h)

            result = []
            for hostname in all_hostnames:
                p = ping_map.get(hostname, {})
                a = agent_map.get(hostname, {})
                a_data = a.get("data", {}) if a else {}

                # 在线判断：取最近 6 次 ping（1 分钟窗口），连续失败 >= 3 才算离线
                # 避免单次网络抖动导致频繁闪烁
                is_offline = False
                if self.pinger:
                    recent = self.pinger.get_recent(hostname, 6)
                    if recent:
                        fails = sum(1 for r in recent if not r["ok"])
                        is_offline = fails >= 3
                elif p:
                    is_offline = not bool(p.get("last_ok", 0))
                elif a:
                    is_offline = bool(a.get("is_offline", False))

                item = {
                    "hostname": hostname,
                    "online": not is_offline,
                    "rtt": round(p["rtt"], 1) if (p and p.get("last_ok") and p.get("rtt", 0) > 0) else None,
                    "loss_pct": round(p["loss_pct"], 1) if (p and p.get("last_ok")) else None,
                    "last_ping": p.get("updated_at", 0) if p else 0,
                    "cpu_percent": round(
                        a_data.get("cpu", {}).get("percent", 0), 1
                    ) if a_data else None,
                    "memory_percent": round(
                        a_data.get("memory", {}).get("percent", 0), 1
                    ) if a_data else None,
                    "disks": a_data.get("disks", []) if a_data else [],
                    "uptime": a_data.get("system", {}).get("uptime_sec", 0) if a_data else 0,
                }
                result.append(item)

            self._json_response(200, result)
        except Exception as e:
            logger.error("API servers error: %s", e)
            self._json_response(500, {"error": str(e)})

    def _handle_api_server(self, hostname: str):
        """单台服务器详情"""
        try:
            ping_data = self.storage.get_ping_latest(hostname) if self.storage else None
            agent_data = self.storage.get_latest(hostname) if self.storage else None

            result = {"hostname": hostname, "online": True}

            if ping_data:
                last_ok = bool(ping_data.get("last_ok", 0))
                result["ping"] = {
                    "rtt": round(ping_data["rtt"], 1) if (last_ok and ping_data.get("rtt", 0) > 0) else None,
                    "min_rtt": round(ping_data["min_rtt"], 1) if last_ok else None,
                    "max_rtt": round(ping_data["max_rtt"], 1) if last_ok else None,
                    "loss_pct": round(ping_data["loss_pct"], 1) if last_ok else None,
                    "last_ok": last_ok,
                    "updated_at": ping_data.get("updated_at", 0),
                }

            # 在线判断：取最近 6 次 ping（1 分钟窗口），连续失败 >= 3 才算离线
            if self.pinger:
                recent = self.pinger.get_recent(hostname, 6)
                if recent:
                    fails = sum(1 for r in recent if not r["ok"])
                    result["online"] = not (fails >= 3)
            elif ping_data:
                result["online"] = bool(ping_data.get("last_ok", 0))

            if agent_data:
                ad = agent_data.get("data", {})
                result["agent"] = {
                    "cpu": ad.get("cpu", {}),
                    "memory": ad.get("memory", {}),
                    "disks": ad.get("disks", []),
                    "network": ad.get("network", []),
                    "system": ad.get("system", {}),
                    "last_seen": agent_data.get("last_seen", 0),
                }

            self._json_response(200, result)
        except Exception as e:
            logger.error("API server error: %s", e)
            self._json_response(500, {"error": str(e)})

    def _handle_api_ping(self, hostname: str):
        """原始 ping 数据序列（兼容旧 /live 用途）"""
        try:
            # 先从 pinger 内存缓存读（快速）
            entries = []
            if self.pinger:
                entries = self.pinger.get_recent(hostname, 120)
            else:
                # 从数据库读
                parts = urlparse(self.path).query
                n = 60
                if parts:
                    for q in parts.split("&"):
                        if q.startswith("n="):
                            try:
                                n = int(q[2:])
                            except ValueError:
                                pass
                raw = self.storage.get_ping_raw(hostname, n) if self.storage else []
                entries = [{"ts": r["ts"], "rtt": r["rtt"], "ok": bool(r["ok"])} for r in raw]

            self._json_response(200, {
                "server": hostname,
                "data": entries,
            })
        except Exception as e:
            logger.error("API ping error: %s", e)
            self._json_response(500, {"error": str(e)})

    # ── 工具 ─────────────────────────────────────────────

    def _handle_404(self):
        self._json_response(404, {"error": "not found"})

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, fmt, *args):
        logger.debug("HTTP %s", fmt % args)


def start_vigil_server(host, port, storage, alert_engine, alert_callback,
                       token=None, certfile=None, keyfile=None, pinger=None):
    """启动 Vigil HTTP 服务"""
    VigilHandler.storage = storage
    VigilHandler.alert_engine = alert_engine
    VigilHandler.alert_callback = alert_callback
    VigilHandler.expected_token = token
    VigilHandler.pinger = pinger

    server = HTTPServer((host, port), VigilHandler)

    if certfile and keyfile:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        proto = "HTTPS"
    else:
        proto = "HTTP"

    logger.info("Vigil server started: %s://%s:%s (token: %s, pinger: %s)",
                proto, host, port, "enabled" if token else "disabled",
                "attached" if pinger else "none")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Vigil server stopped")
        server.server_close()


def start_offline_checker(storage, alert_engine, alert_callback, check_interval=60):
    """后台守护线程：定期检查离线服务器"""
    def _checker():
        while True:
            try:
                records = storage.get_latest_all() if storage else []
                for record in records:
                    if not record.get("is_offline", False):
                        for alert in alert_engine.check_offline(
                                record["hostname"], record["last_seen"]):
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
