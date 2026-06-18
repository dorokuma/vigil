"""
Vigil - 告警引擎
支持 Agent 上报数据（CPU/内存/磁盘）和 Pinger 数据（延迟/丢包）
"""
import time
import logging

logger = logging.getLogger(__name__)


class VigilAlertEngine:
    def __init__(self, config: dict):
        # Agent 阈值
        self.cpu_threshold = config.get("cpu_threshold", 80.0)
        self.memory_threshold = config.get("memory_threshold", 90.0)
        self.disk_threshold = config.get("disk_threshold", 85.0)

        # Pinger 阈值
        self.rtt_threshold = config.get("rtt_threshold", 300.0)
        self.loss_threshold = config.get("loss_threshold", 20.0)
        self.consecutive_threshold = config.get("consecutive_threshold", 3)

        # 离线阈值
        self.offline_sec = config.get("offline_sec", 180)

        # 冷却
        self.cooldown = config.get("cooldown", 300)

        # 内部状态
        self._cooldowns = {}
        self._consecutive_loss = {}
        self._consecutive_rtt = {}

    def check_agent_report(self, hostname: str, data: dict) -> list[dict]:
        """检查 Agent 上报数据，返回告警列表"""
        alerts = []

        # CPU
        cpu = data.get("cpu", {})
        cpu_pct = cpu.get("percent", 0)
        if cpu_pct > self.cpu_threshold:
            alert = self._make_alert(hostname, "cpu_high", "warning",
                f"CPU at {cpu_pct:.1f}% (threshold: {self.cpu_threshold}%)")
            if alert:
                alerts.append(alert)

        # 内存
        mem = data.get("memory", {})
        mem_pct = mem.get("percent", 0)
        if mem_pct > self.memory_threshold:
            alert = self._make_alert(hostname, "memory_high", "warning",
                f"Memory at {mem_pct:.1f}% (threshold: {self.memory_threshold}%)")
            if alert:
                alerts.append(alert)

        # 磁盘
        for disk in data.get("disks", []):
            disk_pct = disk.get("percent", 0)
            if disk_pct > self.disk_threshold:
                mount = disk.get("mount_point", "/")
                alert = self._make_alert(hostname, "disk_high", "warning",
                    f"Disk {mount} at {disk_pct:.1f}% (threshold: {self.disk_threshold}%)")
                if alert:
                    alerts.append(alert)

        return alerts

    def check_pinger_result(self, hostname: str, data: dict) -> list[dict]:
        """检查 Pinger 检测结果，返回告警列表"""
        alerts = []
        pinger = data.get("pinger", {})

        rtt = pinger.get("rtt", 0)
        loss_pct = pinger.get("loss_pct", 0)
        alive = pinger.get("alive", False)

        if not alive:
            # 完全离线（丢包 100%）
            consecutive = self._consecutive_loss.get(hostname, 0) + 1
            self._consecutive_loss[hostname] = consecutive
            if consecutive >= self.consecutive_threshold:
                alert = self._make_alert(hostname, "offline", "critical",
                    f"Server offline! Loss {loss_pct:.0f}% (consecutive {consecutive})")
                if alert:
                    alerts.append(alert)
                    self._consecutive_loss[hostname] = 0
        else:
            self._consecutive_loss[hostname] = 0

            # 高丢包（部分丢包但不是全丢）
            if loss_pct > self.loss_threshold:
                consecutive = self._consecutive_loss.get(f"{hostname}_loss", 0) + 1
                self._consecutive_loss[f"{hostname}_loss"] = consecutive
                if consecutive >= self.consecutive_threshold:
                    alert = self._make_alert(hostname, "high_loss", "warning",
                        f"Packet loss {loss_pct:.1f}% (threshold: {self.loss_threshold}%)")
                    if alert:
                        alerts.append(alert)
                        self._consecutive_loss[f"{hostname}_loss"] = 0
            else:
                self._consecutive_loss[f"{hostname}_loss"] = 0

            # 高延迟
            if rtt > 0 and rtt >= self.rtt_threshold:
                consecutive = self._consecutive_rtt.get(hostname, 0) + 1
                self._consecutive_rtt[hostname] = consecutive
                if consecutive >= self.consecutive_threshold:
                    alert = self._make_alert(hostname, "high_rtt", "warning",
                        f"RTT {rtt:.0f}ms (threshold: {self.rtt_threshold}ms)")
                    if alert:
                        alerts.append(alert)
                        self._consecutive_rtt[hostname] = 0
            else:
                self._consecutive_rtt[hostname] = 0

        return alerts

    def check_offline(self, hostname: str, last_seen: float) -> list[dict]:
        """检查服务器是否离线（Agent 长时间未上报）"""
        elapsed = time.time() - last_seen
        if elapsed > self.offline_sec:
            alert = self._make_alert(hostname, "agent_offline", "critical",
                f"Agent offline! No report for {elapsed:.0f}s (threshold: {self.offline_sec}s)")
            return [alert] if alert else []
        return []

    def _make_alert(self, hostname: str, alert_type: str,
                    severity: str, message: str) -> dict | None:
        """创建告警（带冷却检查）"""
        now = time.time()
        key = (hostname, alert_type)
        last_time = self._cooldowns.get(key, 0)
        if now - last_time < self.cooldown:
            return None
        self._cooldowns[key] = now
        return {
            "hostname": hostname,
            "type": alert_type,
            "severity": severity,
            "message": message,
            "timestamp": now,
        }
