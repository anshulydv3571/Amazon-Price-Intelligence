"""MySQL access layer (SQLAlchemy + pandas). All SQL lives here."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text

from config import DATABASE_URL

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def _read(query: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        df = pd.read_sql_query(text(query), conn, params=params or {})
    for col in ("price", "target_price", "last_alert_price", "current_price",
                "min_price", "max_price", "avg_price", "prev_price", "change_pct"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "checked_at" in df.columns:
        df["checked_at"] = pd.to_datetime(df["checked_at"])
    return df


# ---------- products ----------
def add_product(url: str, title: str, target_price: float | None = None,
                email: str | None = None) -> int:
    """Insert a product, or update it if the URL is already tracked. Returns its id."""
    params = {"url": url, "title": title, "target": target_price, "email": email}
    with get_engine().begin() as conn:
        row = conn.execute(text("SELECT id FROM products WHERE url = :url"), params).first()
        if row:
            conn.execute(
                text("UPDATE products SET title = :title, target_price = :target, "
                     "email = :email, is_active = 1 WHERE id = :id"),
                {**params, "id": row[0]},
            )
            return int(row[0])
        result = conn.execute(
            text("INSERT INTO products (url, title, target_price, email, created_at) "
                 "VALUES (:url, :title, :target, :email, :created)"),
            {**params, "created": datetime.now()},
        )
        return int(result.lastrowid)


def get_products(active_only: bool = False) -> pd.DataFrame:
    query = ("SELECT id, url, title, target_price, email, is_active, last_alert_price, created_at "
             "FROM products")
    if active_only:
        query += " WHERE is_active = 1"
    return _read(query + " ORDER BY id")


def update_product(product_id: int, target_price: float | None, is_active: bool) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE products SET target_price = :t, is_active = :a WHERE id = :id"),
            {"t": target_price, "a": int(is_active), "id": product_id},
        )


def set_last_alert(product_id: int, price: float | None) -> None:
    with get_engine().begin() as conn:
        conn.execute(text("UPDATE products SET last_alert_price = :p WHERE id = :id"),
                     {"p": price, "id": product_id})


def delete_product(product_id: int) -> None:
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM price_history WHERE product_id = :id"), {"id": product_id})
        conn.execute(text("DELETE FROM products WHERE id = :id"), {"id": product_id})


# ---------- price history ----------
def add_price(product_id: int, price: float, checked_at: datetime | None = None) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO price_history (product_id, price, checked_at) "
                 "VALUES (:pid, :price, :ts)"),
            {"pid": product_id, "price": price, "ts": checked_at or datetime.now()},
        )


def get_history(product_id: int) -> pd.DataFrame:
    return _read("SELECT id, product_id, price, checked_at FROM price_history "
                 "WHERE product_id = :pid ORDER BY checked_at, id", {"pid": product_id})


def get_all_history() -> pd.DataFrame:
    return _read("SELECT h.id, h.product_id, p.title, h.price, h.checked_at "
                 "FROM price_history h JOIN products p ON p.id = h.product_id "
                 "ORDER BY h.checked_at, h.id")


# ---------- SQL analytics ----------
def latest_stats() -> pd.DataFrame:
    """One row per product: current price + min / max / avg / number of checks."""
    return _read("""
        SELECT p.id, p.title, p.target_price, p.is_active,
               (SELECT h2.price FROM price_history h2
                 WHERE h2.product_id = p.id
                 ORDER BY h2.checked_at DESC, h2.id DESC LIMIT 1) AS current_price,
               MIN(h.price) AS min_price,
               MAX(h.price) AS max_price,
               ROUND(AVG(h.price), 2) AS avg_price,
               COUNT(h.id) AS checks
        FROM products p
        LEFT JOIN price_history h ON h.product_id = p.id
        GROUP BY p.id, p.title, p.target_price, p.is_active
        ORDER BY p.id
    """)


def biggest_drops(limit: int = 10) -> pd.DataFrame:
    """Largest single-check price drops, using a CTE + LAG() window function (MySQL 8+)."""
    return _read("""
        WITH changes AS (
            SELECT product_id, checked_at, price,
                   LAG(price) OVER (PARTITION BY product_id ORDER BY checked_at, id) AS prev_price
            FROM price_history
        )
        SELECT p.title, c.checked_at, c.prev_price, c.price,
               ROUND(100 * (c.price - c.prev_price) / c.prev_price, 2) AS change_pct
        FROM changes c
        JOIN products p ON p.id = c.product_id
        WHERE c.prev_price IS NOT NULL AND c.price < c.prev_price
        ORDER BY change_pct ASC
        LIMIT :limit
    """, {"limit": limit})
