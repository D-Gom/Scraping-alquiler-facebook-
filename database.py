"""
Database module.

Manages the SQLite database that stores processed posts to avoid duplicates.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Optional

import config


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a SQLite connection. Uses config.DB_PATH by default."""
    path = db_path if db_path is not None else config.DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Create the database schema if it does not exist yet."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts_procesados (
                post_id       TEXT PRIMARY KEY,
                url           TEXT,
                texto         TEXT,
                fecha_procesado TEXT NOT NULL,
                es_match      INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def post_existe(post_id: str, db_path: Optional[str] = None) -> bool:
    """Return True if *post_id* was already processed."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM posts_procesados WHERE post_id = ?", (post_id,)
        ).fetchone()
    return row is not None


def guardar_post(
    post_id: str,
    url: str,
    texto: str,
    es_match: bool,
    db_path: Optional[str] = None,
) -> None:
    """Insert or replace a post record in the database."""
    fecha = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO posts_procesados
                (post_id, url, texto, fecha_procesado, es_match)
            VALUES (?, ?, ?, ?, ?)
            """,
            (post_id, url, texto, fecha, int(es_match)),
        )
        conn.commit()
