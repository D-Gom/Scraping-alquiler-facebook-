"""Tests for the database module."""

import os
import tempfile

import pytest

import database


@pytest.fixture()
def tmp_db(tmp_path):
    """Return a path to a temporary SQLite database."""
    db_path = str(tmp_path / "test.db")
    database.init_db(db_path)
    return db_path


def test_init_db_creates_table(tmp_db):
    with database.get_connection(tmp_db) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_procesados'"
        ).fetchall()
    assert len(rows) == 1


def test_post_no_existe_inicialmente(tmp_db):
    assert not database.post_existe("post_123", tmp_db)


def test_guardar_y_verificar_post(tmp_db):
    database.guardar_post("post_456", "http://fb.com/1", "texto de prueba", True, tmp_db)
    assert database.post_existe("post_456", tmp_db)


def test_guardar_post_no_match(tmp_db):
    database.guardar_post("post_789", "http://fb.com/2", "otro texto", False, tmp_db)
    assert database.post_existe("post_789", tmp_db)
    with database.get_connection(tmp_db) as conn:
        row = conn.execute(
            "SELECT es_match FROM posts_procesados WHERE post_id = ?", ("post_789",)
        ).fetchone()
    assert row["es_match"] == 0


def test_guardar_post_idempotente(tmp_db):
    database.guardar_post("post_dup", "http://fb.com/3", "texto", True, tmp_db)
    # Inserting again should not raise.
    database.guardar_post("post_dup", "http://fb.com/3", "texto actualizado", False, tmp_db)
    with database.get_connection(tmp_db) as conn:
        rows = conn.execute(
            "SELECT * FROM posts_procesados WHERE post_id = ?", ("post_dup",)
        ).fetchall()
    assert len(rows) == 1
    # The last value should win (INSERT OR REPLACE semantics).
    assert rows[0]["es_match"] == 0
