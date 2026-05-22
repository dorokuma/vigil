"""
Vigil - 存储层（完整版）
含 ping_raw 原始数据表
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
        conn.execute("PRAGMA busy_timeout=5000")
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

                -- Pinger 最新状态
                CREATE TABLE IF NOT EXISTS ping_latest (
                    hostname    TEXT PRIMARY KEY,
                    rtt         REAL DEFAULT 0,
                    min_rtt     REAL DEFAULT 0,
                    max_rtt     REAL DEFAULT 0,
                    loss_pct    REAL DEFAULT 0,
                    last_ok     INTEGER DEFAULT 0,
                    samples     INTEGER DEFAULT 0,
                    updated_at  REAL NOT NULL
                );
                -- Pinger 原始数据（每台保留最近 3600 条）
                CREATE TABLE IF NOT EXISTS ping_raw (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname    TEXT NOT NULL,
                    ts          INTEGER NOT NULL,
                    rtt         REAL DEFAULT 0,
                    ok          INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_ping_raw_ht
                    ON ping_raw(hostname, id);
                -- Pinger 历史聚合（每分钟一条）
                CREATE TABLE IF NOT EXISTS ping_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname    TEXT NOT NULL,
                    time_start  REAL NOT NULL,
                    avg_rtt     REAL DEFAULT 0,
                    min_rtt     REAL DEFAULT 0,
                    max_rtt     REAL DEFAULT 0,
                    jitter      REAL DEFAULT 0,
                    loss_pct    REAL DEFAULT 0,
                    samples     INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_ping_history_ht
                    ON ping_history(hostname, time_start);
            """)
        logger.info("Vigil DB initialized: %s", self.db_path)

    # ========== Agent 数据 ==========

    def save_report(self, hostname, data):
        now = time.time()
        data_json = json.dumps(data, ensure_ascii=False)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO latest (hostname, data, last_seen, is_offline)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(hostname) DO UPDATE SET
                    data = excluded.data, last_seen = excluded.last_seen, is_offline = 0
            """, (hostname, data_json, now))
            last_hist = conn.execute(
                "SELECT MAX(reported_at) FROM history WHERE hostname = ?", (hostname,)
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

    # ========== Pinger 数据 ==========

    def save_ping_raw(self, hostname, ts, rtt, ok):
        """保存一条原始 ping 数据，同时清理超量的旧数据"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO ping_raw (hostname, ts, rtt, ok) VALUES (?, ?, ?, ?)",
                (hostname, ts, rtt, 1 if ok else 0)
            )
            # 只保留最近 3600 条
            conn.execute("""
                DELETE FROM ping_raw WHERE hostname = ? AND id NOT IN (
                    SELECT id FROM ping_raw WHERE hostname = ?
                    ORDER BY id DESC LIMIT 3600
                )
            """, (hostname, hostname))

    def get_ping_raw(self, hostname, n=60):
        """获取最近 n 条原始 ping 数据"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT ts, rtt, ok FROM ping_raw
                WHERE hostname = ? ORDER BY id DESC LIMIT ?
            """, (hostname, n)).fetchall()
            result = [dict(r) for r in rows]
            result.reverse()  # 从旧到新
            return result

    def save_ping_latest(self, hostname, rtt, loss_pct, last_ok, samples,
                         min_rtt=0, max_rtt=0):
        now = time.time()
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO ping_latest (hostname, rtt, min_rtt, max_rtt, loss_pct,
                                         last_ok, samples, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hostname) DO UPDATE SET
                    rtt=excluded.rtt, min_rtt=excluded.min_rtt, max_rtt=excluded.max_rtt,
                    loss_pct=excluded.loss_pct, last_ok=excluded.last_ok,
                    samples=excluded.samples, updated_at=excluded.updated_at
            """, (hostname, rtt, min_rtt, max_rtt, loss_pct,
                  1 if last_ok else 0, samples, now))

    def get_ping_latest_all(self):
        with self._get_conn() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM ping_latest").fetchall()]

    def get_ping_latest(self, hostname):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM ping_latest WHERE hostname = ?", (hostname,)
            ).fetchone()
            return dict(row) if row else None

    def save_ping_history(self, hostname, time_start, avg_rtt, min_rtt,
                          max_rtt, jitter, loss_pct, samples):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO ping_history (hostname, time_start, avg_rtt, min_rtt,
                                          max_rtt, jitter, loss_pct, samples)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (hostname, time_start, avg_rtt, min_rtt, max_rtt,
                  jitter, loss_pct, samples))

    def query_ping_history(self, hostname, since):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM ping_history WHERE hostname = ? AND time_start >= ? ORDER BY time_start ASC",
                (hostname, since)
            ).fetchall()
            return [dict(r) for r in rows]

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
