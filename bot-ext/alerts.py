"""
Vigil - Alert engine
Checks agent reports against thresholds and generates alerts.
"""
import time
import logging

logger = logging.getLogger(__name__)


class VigilAlertEngine:
    def __init__(self, config):
        self.cpu_threshold = config.get("cpu_threshold", 80.0)
        self.memory_threshold = config.get("memory_threshold", 90.0)
        self.disk_threshold = config.get("disk_threshold", 85.0)
        self.offline_sec = config.get("offline_sec", 180)
        self.cooldown = config.get("cooldown", 300)
        self._cooldowns = {}

    def check(self, hostname, data):
        alerts = []

        cpu = data.get("cpu", {})
        cpu_pct = cpu.get("percent", 0)
        if cpu_pct > self.cpu_threshold:
            alert = self._make_alert(hostname, "cpu_high", "warning",
                f"CPU at {cpu_pct:.1f}% (threshold: {self.cpu_threshold}%)")
            if alert:
                alerts.append(alert)

        mem = data.get("memory", {})
        mem_pct = mem.get("percent", 0)
        if mem_pct > self.memory_threshold:
            alert = self._make_alert(hostname, "memory_high", "warning",
                f"Memory at {mem_pct:.1f}% (threshold: {self.memory_threshold}%)")
            if alert:
                alerts.append(alert)

        for disk in data.get("disks", []):
            disk_pct = disk.get("percent", 0)
            if disk_pct > self.disk_threshold:
                mount = disk.get("mount_point", "/")
                alert = self._make_alert(hostname, "disk_high", "warning",
                    f"Disk {mount} at {disk_pct:.1f}% (threshold: {self.disk_threshold}%)")
                if alert:
                    alerts.append(alert)

        return alerts

    def check_offline(self, hostname, last_seen):
        elapsed = time.time() - last_seen
        if elapsed > self.offline_sec:
            alert = self._make_alert(hostname, "offline", "critical",
                f"Server offline! No report for {elapsed:.0f}s (threshold: {self.offline_sec}s)")
            return [alert] if alert else []
        return []

    def _make_alert(self, hostname, alert_type, severity, message):
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
