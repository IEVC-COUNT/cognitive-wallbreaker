"""
认知破壁机 V6.0 — SQLite 公共事件数据库
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "public.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS public_events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            query TEXT NOT NULL,
            result TEXT NOT NULL DEFAULT '',
            mode TEXT NOT NULL DEFAULT 'v4',
            topology_json TEXT,
            stats_json TEXT,
            created_at TEXT NOT NULL,
            ip_hash TEXT NOT NULL,
            anonymous_id TEXT NOT NULL DEFAULT '',
            view_count INTEGER NOT NULL DEFAULT 0,
            like_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS event_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            outcome_text TEXT NOT NULL DEFAULT '',
            accuracy_score INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES public_events(id)
        );

        CREATE TABLE IF NOT EXISTS anonymous_memory (
            anonymous_id TEXT PRIMARY KEY,
            memory_json TEXT NOT NULL DEFAULT '{}',
            event_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_created ON public_events(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_events_anon ON public_events(anonymous_id);
        CREATE INDEX IF NOT EXISTS idx_outcomes_event ON event_outcomes(event_id);
    """)
    conn.commit()
    conn.close()
