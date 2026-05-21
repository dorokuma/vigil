"""
Vigil - SQLite 存储层
存储 Agent 上报数据 + Pinger 检测结果
"""
import sqlite3
import json
import time
import logging
import os

logger = logging.getLogger(__name__)


class VigilStorage:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                -- Agent 上报数据（最新一条）
                CREATE TABLE IF NOT EXISTS latest (
                    hostname    TEXT PRIMARY KEY,
                    data        TEXT NOT NULL,
                    last_seen   REAL NOT NULL,
                    is_offline  INTEGER DEFAULT 0
                );
                -- Agent 历史数据（每5分钟采样）
                CREATE TABLE IF NOT EXISTS history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname    TEXT NOT NULL,
                    data        TEXT NOT NULL,
                    reported_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_history_hostname
                    ON history(hostname, reported_at);

                -- Pinger 检测结果（最新一条）
                CREATE TABLE IF NOT EXISTS ping_latest (
                    hostname    TEXT PRIMARY KEY,
                    data        TEXT NOT NULL,
                    last_seen   REAL NOT NULL,
                    is_offline  INTEGER DEFAULT 0
                );
                -- Pinger 历史数据
                CREATE TABLE IF NOT EXISTS ping_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname    TEXT NOT NULL,
                    data        TEXT NOT NULL,
                    checked_at  REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ping_history_hostname
                    ON ping_history(hostname, checked_at);

                -- 离线告警记录
                CREATE TABLE IF NOT EXISTS offline_alerts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname    TEXT NOT NULL,
                    alerted_at  REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_offline_alerts_hostname
                    ON offline_alerts(hostname, alerted_at);
            """)
        logger.info("Database initialized: %s", self.db_path)

    # ========== Agent 数据 ==========

    def save_report(self, hostname, data):
        now = time.time()
        data_json = json.dumps(data, ensure_ascii=False)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO latest (hostname, data, last_seen, is_offline)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(hostname) DO UPDATE SET
                    data = excluded.data,
                    last_seen = excluded.last_seen,
                    is_offline = 0
            """, (hostname, data_json, now))

            # 每5分钟写一次历史
            last_hist = conn.execute(
                "SELECT MAX(reported_at) FROM history WHERE hostname = ?",
                (hostname,)
            ).fetchone()[0]
            if last_hist is None or (now - last_hist) >= 300:
                conn.execute(
                    "INSERT INTO history (hostname, data, reported_at) VALUES (?, ?, ?)",
                    (hostname, data_json, now)
                )

    def mark_offline(self, hostname):
        with self._get_conn() as conn:
            conn.execute("UPDATE latest SET is_offline = 1 WHERE hostname = ?", (hostname,))

    def get_latest_all(self):
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM latest").fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["data"] = json.loads(item["data"]) if item["data"] else {}
                result.append(item)
            return result

    def get_latest(self, hostname):
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM latest WHERE hostname = ?", (hostname,)).fetchone()
            if row:
                item = dict(row)
                item["data"] = json.loads(item["data"]) if item["data"] else {}
                return item
            return None

    def get_history(self, hostname, limit=100):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM history WHERE hostname = ? ORDER BY reported_at DESC LIMIT ?",
                (hostname, limit)
            ).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["data"] = json.loads(item["data"]) if item["data"] else {}
                result.append(item)
            return result

    # ========== Pinger 数据 ==========

    def save_ping_result(self, hostname, data):
        now = time.time()
        data_json = json.dumps(data, ensure_ascii=False)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO ping_latest (hostname, data, last_seen, is_offline)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(hostname) DO UPDATE SET
                    data = excluded.data,
                    last_seen = excluded.last_seen,
                    is_offline = 0
            """, (hostname, data_json, now))

            # 每5分钟写一次历史
            last_hist = conn.execute(
                "SELECT MAX(checked_at) FROM ping_history WHERE hostname = ?",
                (hostname,)
            ).fetchone()[0]
            if last_hist is None or (now - last_hist) >= 300:
                conn.execute(
                    "INSERT INTO ping_history (hostname, data, checked_at) VALUES (?, ?, ?)",
                    (hostname, data_json, now)
                )

    def mark_ping_offline(self, hostname):
        with self._get_conn() as conn:
            conn.execute("UPDATE ping_latest SET is_offline = 1 WHERE hostname = ?", (hostname,))

    def get_ping_latest_all(self):
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM ping_latest").fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["data"] = json.loads(item["data"]) if item["data"] else {}
                result.append(item)
            return result

    def get_ping_latest(self, hostname):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM ping_latest WHERE hostname = ?", (hostname,)
            ).fetchone()
            if row:
                item = dict(row)
                item["data"] = json.loads(item["data"]) if item["data"] else {}
                return item
            return None

    # ========== 历史清理 ==========

    def clean_old_history(self, keep_days=7):
        cutoff = time.time() - keep_days * 86400
        with self._get_conn() as conn:
            for table in ["history", "ping_history"]:
                deleted = conn.execute(
                    f"DELETE FROM {table} WHERE reported_at < ?", (cutoff,)
                ).rowcount
                if deleted > 0:
                    logger.info("Cleaned %d old records from %s", deleted, table)
