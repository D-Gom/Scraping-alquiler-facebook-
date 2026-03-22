"""
Tests for the main pipeline (ejecutar_ciclo).

External services (scraper, Gemini, Telegram) are mocked so the tests run
without network access or API keys.
"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

import config
import database
import main


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Redirect all DB calls to a temporary database via config.DB_PATH."""
    db_path = str(tmp_path / "test_main.db")
    database.init_db(db_path)
    monkeypatch.setattr(config, "DB_PATH", db_path)
    return db_path


SAMPLE_POST = {
    "post_id": "12345678901",
    "url": "https://www.facebook.com/groups/1/posts/12345678901",
    "texto": "Alquilo departamento en Neuquén capital, 2 ambientes, luminoso",
    "imagenes": [],
    "autor": "Juan Pérez",
    "fecha": "2024-01-01",
}


def test_pipeline_no_groups(monkeypatch):
    """If no groups are configured, the cycle should run silently."""
    monkeypatch.setattr("main.config.FACEBOOK_GROUP_URLS", [])
    main.ejecutar_ciclo()  # should not raise


def test_pipeline_duplicate_skipped(monkeypatch, tmp_db):
    """Posts already in the DB should not be processed again."""
    database.guardar_post(
        SAMPLE_POST["post_id"],
        SAMPLE_POST["url"],
        SAMPLE_POST["texto"],
        False,
        tmp_db,
    )
    monkeypatch.setattr("main.config.FACEBOOK_GROUP_URLS", ["https://fb.com/groups/test"])
    monkeypatch.setattr("main.scraper.extraer_posts", lambda url, **kw: [SAMPLE_POST])
    gemini_mock = MagicMock()
    monkeypatch.setattr("main.gemini_analyzer.analizar_post", gemini_mock)

    main.ejecutar_ciclo()

    # Gemini should NOT have been called because the post was a duplicate.
    gemini_mock.assert_not_called()


def test_pipeline_keyword_filter_discards(monkeypatch, tmp_db):
    """Posts that fail the keyword filter are saved as es_match=False, Gemini not called."""
    post = {**SAMPLE_POST, "post_id": "99999", "texto": "Busco departamento en Neuquén"}
    monkeypatch.setattr("main.config.FACEBOOK_GROUP_URLS", ["https://fb.com/groups/test"])
    monkeypatch.setattr("main.scraper.extraer_posts", lambda url, **kw: [post])
    gemini_mock = MagicMock()
    monkeypatch.setattr("main.gemini_analyzer.analizar_post", gemini_mock)

    main.ejecutar_ciclo()

    gemini_mock.assert_not_called()
    assert database.post_existe(post["post_id"], tmp_db)


def test_pipeline_match_sends_notification(monkeypatch, tmp_db):
    """Posts that pass filter AND Gemini → notification sent."""
    post = {**SAMPLE_POST, "post_id": "77777"}
    monkeypatch.setattr("main.config.FACEBOOK_GROUP_URLS", ["https://fb.com/groups/test"])
    monkeypatch.setattr("main.scraper.extraer_posts", lambda url, **kw: [post])
    monkeypatch.setattr(
        "main.gemini_analyzer.analizar_post",
        lambda p: {
            "es_apto": True,
            "razon": "Cumple todos los criterios",
            "precio_estimado": "150000",
            "habitaciones": 2,
        },
    )
    notifier_mock = MagicMock(return_value=True)
    monkeypatch.setattr("main.notifier.enviar_alerta", notifier_mock)

    main.ejecutar_ciclo()

    notifier_mock.assert_called_once()
    assert database.post_existe(post["post_id"], tmp_db)


def test_pipeline_no_match_no_notification(monkeypatch, tmp_db):
    """Posts where Gemini says es_apto=False should NOT trigger a notification."""
    post = {**SAMPLE_POST, "post_id": "88888"}
    monkeypatch.setattr("main.config.FACEBOOK_GROUP_URLS", ["https://fb.com/groups/test"])
    monkeypatch.setattr("main.scraper.extraer_posts", lambda url, **kw: [post])
    monkeypatch.setattr(
        "main.gemini_analyzer.analizar_post",
        lambda p: {
            "es_apto": False,
            "razon": "No cumple requisitos",
            "precio_estimado": None,
            "habitaciones": 1,
        },
    )
    notifier_mock = MagicMock()
    monkeypatch.setattr("main.notifier.enviar_alerta", notifier_mock)

    main.ejecutar_ciclo()

    notifier_mock.assert_not_called()
    assert database.post_existe(post["post_id"], tmp_db)


def test_pipeline_scraper_error_handled(monkeypatch):
    """Errors from the scraper should be caught and not crash the cycle."""
    monkeypatch.setattr("main.config.FACEBOOK_GROUP_URLS", ["https://fb.com/groups/broken"])

    def _raise(*args, **kwargs):
        raise RuntimeError("Scraping failed")

    monkeypatch.setattr("main.scraper.extraer_posts", _raise)
    main.ejecutar_ciclo()  # should not raise
