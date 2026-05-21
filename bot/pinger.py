"""
Vigil - Pinger 模块
主动 ping 各服务器，检测延迟和在线率
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class Pinger:
    """延迟检测器"""

    def __init__(self, hosts: dict, interval: int = 30, timeout: int = 5, storage=None):
        """
        hosts: { "hostname": "ip_or_domain", ... }
        interval: 每 N 秒检测一轮
        timeout: 单次 ping 超时（秒）
        storage: VigilStorage 实例，用于保存结果
        """
        self.hosts = hosts
        self.interval = interval
        self.timeout = timeout
        self.storage = storage

    async def start(self):
        """启动循环检测"""
        logger.info("Pinger started: %d hosts every %ds", len(self.hosts), self.interval)
        while True:
            t0 = time.time()
            tasks = [self._ping_one(name, addr) for name, addr in self.hosts.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error("Ping error: %s", result)
                    continue
                if self.storage and result:
                    self._save_ping_result(result)

            elapsed = time.time() - t0
            sleep_time = max(1, self.interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def _ping_one(self, hostname: str, address: str) -> dict | None:
        """对单个服务器执行 ping"""
        # Linux: ping -c 5 -W timeout address
        #  -c 5: 发 5 个包
        #  -W timeout: 超时秒数 (Linux)
        cmd = ["ping", "-c", "5", "-W", str(self.timeout), address]

        try:
            t0 = time.time()
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout * 5 + 5
            )
            elapsed = time.time() - t0
            output = stdout.decode(errors="replace")

            # 解析 ping 输出
            lines = output.strip().split("\n")
            last_line = lines[-1] if lines else ""

            # 统计发送/接收
            sent = 5
            received = 0
            for line in lines:
                if "bytes from" in line and "time=" in line:
                    received += 1

            loss_pct = (sent - received) / sent * 100.0

            # 提取 RTT
            rtt = 0.0
            if "min/avg/max" in last_line or "min/avg/max/mdev" in last_line:
                # Linux 格式: rtt min/avg/max/mdev = 10.123/20.456/30.789/5.012 ms
                import re
                match = re.search(r"= [\d.]+/([\d.]+)/[\d.]+/", last_line)
                if match:
                    rtt = float(match.group(1))

            return {
                "hostname": hostname,
                "address": address,
                "rtt": rtt,
                "loss_pct": loss_pct,
                "sent": sent,
                "received": received,
                "timestamp": time.time(),
                "alive": received > 0,
            }

        except asyncio.TimeoutError:
            logger.warning("Ping timeout: %s (%s)", hostname, address)
            return {
                "hostname": hostname,
                "address": address,
                "rtt": 0,
                "loss_pct": 100.0,
                "sent": 5,
                "received": 0,
                "timestamp": time.time(),
                "alive": False,
            }
        except Exception as e:
            logger.error("Ping failed: %s (%s): %s", hostname, address, e)
            return None

    def _save_ping_result(self, result: dict):
        """把 ping 结果存入 storage"""
        try:
            # 以 pinger_ 前缀存储，区别于 Agent 上报的数据
            data = {
                "pinger": {
                    "rtt": result["rtt"],
                    "loss_pct": result["loss_pct"],
                    "alive": result["alive"],
                }
            }
            self.storage.save_ping_result(result["hostname"], data)
        except Exception as e:
            logger.error("Save ping result error: %s", e)
