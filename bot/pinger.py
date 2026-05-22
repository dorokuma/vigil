"""
Vigil - Pinger 升级版
每 10 秒并发 ping 所有服务器
结果写入 SQLite（ping_raw + ping_latest）
每分钟聚合（ping_history）
"""
import asyncio
import logging
import time
import re

logger = logging.getLogger(__name__)

# 受监控服务器（继承自旧 engine 的能力，不是代码）
SERVERS = [
    {"name": "hongkong",  "address": "103.48.169.189"},
    {"name": "tokyo",     "address": "158.179.184.242"},
    {"name": "mumbai",    "address": "144.24.108.241"},
    {"name": "sanjose",   "address": "2603:c024:c000:8e5e:91b:c01:e04e:390e"},
    {"name": "columbus",  "address": "2603:c024:c000:8e5e:4d5c:2789:2bd8:668"},
    {"name": "aione",     "address": "23.173.216.45"},
    {"name": "singapore", "address": "2a12:bec0:16e:33f::"},
]


class Pinger:
    """Vigil 升级版 Pinger — 吸收旧 engine 的 ping 能力"""

    def __init__(self, storage=None):
        self.storage = storage
        self._running = False
        self._task = None
        # 内存缓存最近 120 条（用于 /api/ping/ 快速响应）
        self.recent_cache = {s["name"]: [] for s in SERVERS}

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Pinger started: %d servers every 10s", len(SERVERS))

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self):
        last_agg = 0
        await self._ping_all()
        last_agg = time.time()

        while self._running:
            await asyncio.sleep(10)
            await self._ping_all()
            now = time.time()
            if now - last_agg >= 60:
                await self._aggregate()
                last_agg = now

    async def _ping_all(self):
        tasks = [self._ping_one(s) for s in SERVERS]
        await asyncio.gather(*tasks, return_exceptions=True)

    def _parse_rtt(self, output: str) -> tuple:
        """解析 ping 输出，返回 (rtt, success)"""
        for line in output.split("\n"):
            m = re.search(r"time=([0-9.]+)\s*ms", line)
            if m:
                return float(m.group(1)), True
        return 0.0, False

    async def _ping_one(self, server: dict):
        hostname = server["name"]
        address = server["address"]
        use_ping6 = ":" in address

        try:
            cmd = ["ping6" if use_ping6 else "ping", "-c", "1"]
            if not use_ping6:
                cmd += ["-W", "5"]
            cmd.append(address)

            t0 = time.time()
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
            ts = int(t0 * 1000)
            output = stdout.decode(errors="replace")

            rtt, ok = self._parse_rtt(output)
            entry = {"ts": ts, "rtt": rtt, "ok": ok}
        except Exception as e:
            logger.debug("Ping %s error: %s", hostname, e)
            ts = int(time.time() * 1000)
            entry = {"ts": ts, "rtt": 0, "ok": False}

        # 入内存缓存（最近 120 条）
        buf = self.recent_cache[hostname]
        buf.append(entry)
        if len(buf) > 120:
            buf.pop(0)

        # 写入 SQLite
        if self.storage:
            try:
                self.storage.save_ping_raw(hostname, ts, entry["rtt"], entry["ok"])
                self.storage.save_ping_latest(
                    hostname, entry["rtt"], 0.0 if entry["ok"] else 100.0,
                    entry["ok"], 1
                )
            except Exception as e:
                logger.error("Storage write error: %s", e)

    async def _aggregate(self):
        """每分钟聚合，写入 ping_history"""
        if not self.storage:
            return
        now_ts = int(time.time())

        for s in SERVERS:
            hostname = s["name"]
            raw = await self._get_raw_from_db(hostname, 6)
            if not raw:
                continue

            rtts = [r["rtt"] for r in raw if r["ok"] and r["rtt"] > 0]
            total = len(raw)
            success = len(rtts)
            loss_pct = (total - success) / total * 100 if total > 0 else 0

            if rtts:
                avg_rtt = sum(rtts) / len(rtts)
                min_rtt = min(rtts)
                max_rtt = max(rtts)
                jitter = sum(abs(rtts[i] - rtts[i-1])
                             for i in range(1, len(rtts))) / len(rtts) if len(rtts) > 1 else 0
            else:
                avg_rtt = min_rtt = max_rtt = jitter = 0

            try:
                self.storage.save_ping_history(
                    hostname, now_ts, avg_rtt, min_rtt, max_rtt,
                    jitter, loss_pct, total
                )
            except Exception as e:
                logger.error("Aggregate write error: %s", e)

    async def _get_raw_from_db(self, hostname, n):
        """从数据库读取原始 ping 数据（异步包装）"""
        if not self.storage:
            return []
        try:
            return self.storage.get_ping_raw(hostname, n)
        except Exception as e:
            logger.error("DB read error: %s", e)
            return []

    # ── API 接口 ──

    def get_recent(self, hostname: str, n: int = 60) -> list:
        """返回最近 n 条 ping 数据（从内存缓存，同步）"""
        buf = self.recent_cache.get(hostname, [])
        return buf[-n:]

    def get_servers(self) -> list:
        return SERVERS
