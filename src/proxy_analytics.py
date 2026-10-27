"""Content-free daily aggregates with atomic SQLite updates."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3


class AnalyticsStore:
    def __init__(self, path: str, retention_days: int = 90):
        if retention_days < 1 or path == ":memory:":
            raise ValueError("Use a file database and positive retention")
        self.path = str(Path(path))
        self.retention_days = retention_days
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS daily_metrics (
                day TEXT NOT NULL, metric TEXT NOT NULL, value INTEGER NOT NULL,
                PRIMARY KEY (day, metric))""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            # WAL + NORMAL avoids an fsync for every aggregate update.
            db.execute("PRAGMA synchronous=NORMAL")
            with db:
                yield db
        finally:
            db.close()

    def record(self, metrics: dict[str, int]):
        today = datetime.now(timezone.utc).date()
        cutoff = (today - timedelta(days=self.retention_days - 1)).isoformat()
        with self.connect() as db:
            db.executemany("""INSERT INTO daily_metrics(day, metric, value) VALUES (?, ?, ?)
                ON CONFLICT(day, metric) DO UPDATE SET value = value + excluded.value""",
                           [(today.isoformat(), key, value) for key, value in metrics.items()])
            db.execute("DELETE FROM daily_metrics WHERE day < ?", (cutoff,))

    def report(self, days: int):
        if not 1 <= days <= self.retention_days:
            raise ValueError("Report window exceeds retention")
        cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()
        with self.connect() as db:
            rows = db.execute("SELECT day, metric, value FROM daily_metrics WHERE day >= ? ORDER BY day, metric",
                              (cutoff,)).fetchall()
        totals = {}
        daily = {}
        for day, metric, value in rows:
            totals[metric] = totals.get(metric, 0) + value
            daily.setdefault(day, {})[metric] = value
        return {"scope": "persisted_daily", "days": days, "timezone": "UTC",
                "totals": totals, "daily": daily}
