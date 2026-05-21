"""
Vigil - SQLite storage layer
Stores agent reports in SQLite for history and alerting.
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
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS latest (
                    hostname    TEXT PRIMARY KEY,
                    data        TEXT NOT NULL,
                    last_seen   REAL NOT NULL,
                    is_offline  INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname    TEXT NOT NULL,
                    data        TEXT NOT NULL,
                    reported_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_history_hostname
                    ON history(hostname, reported_at);
            """)
        logger.info("Database initialized: %s", self.db_path)

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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

    def clean_old_history(self, keep_days=7):
        cutoff = time.time() - keep_days * 86400
        with self._get_conn() as conn:
            deleted = conn.execute("DELETE FROM history WHERE reported_at < ?", (cutoff,)).rowcount
        if deleted > 0:
            logger.info("Cleaned %d old history records", deleted)
