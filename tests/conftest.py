import os
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, text

SQLITE_SCHEMA = """
CREATE TABLE products (
  id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  target_price REAL, email TEXT, is_active INTEGER NOT NULL DEFAULT 1,
  last_alert_price REAL, created_at TEXT);
CREATE TABLE price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL,
  price REAL NOT NULL, checked_at TEXT NOT NULL);
"""


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    """Point db.py at a throw-away SQLite file (same SQL, no MySQL needed)."""
    import db
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    with engine.begin() as conn:
        for stmt in SQLITE_SCHEMA.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
    monkeypatch.setattr(db, "_engine", engine)
    return db
