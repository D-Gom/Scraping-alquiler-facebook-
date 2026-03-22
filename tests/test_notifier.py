"""Tests for the Telegram notifier module (mocked HTTP calls)."""

from unittest.mock import MagicMock, patch

import pytest

import notifier


SAMPLE_POST = {
    "post_id": "111",
    "url": "https://www.facebook.com/groups/123/posts/111",
    "texto": "Alquilo departamento en Neuquén, 2 dormitorios",
    "imagenes": [],
    "autor": "Juan Pérez",
    "fecha": "2024-01-01",
}

SAMPLE_ANALISIS = {
    "es_apto": True,
    "razon": "Cumple todos los criterios",
    "precio_estimado": "200000",
    "habitaciones": 2,
}


# ---------------------------------------------------------------------------
# _escape_markdown_v2
# ---------------------------------------------------------------------------

class TestEscapeMarkdownV2:
    def test_escapes_special_chars(self):
        assert notifier._escape_markdown_v2("hello.world") == "hello\\.world"
        assert notifier._escape_markdown_v2("1+1=2") == "1\\+1\\=2"
        assert notifier._escape_markdown_v2("(test)") == "\\(test\\)"

    def test_plain_text_unchanged(self):
        assert notifier._escape_markdown_v2("Hola Mundo") == "Hola Mundo"


# ---------------------------------------------------------------------------
# _escape_markdown_v2_url
# ---------------------------------------------------------------------------

class TestEscapeMarkdownV2Url:
    def test_escapes_closing_paren(self):
        assert notifier._escape_markdown_v2_url("http://a.com/x)y") == "http://a.com/x\\)y"

    def test_escapes_backslash(self):
        assert notifier._escape_markdown_v2_url("http://a.com/x\\y") == "http://a.com/x\\\\y"

    def test_does_not_escape_dots_or_slashes(self):
        url = "https://www.facebook.com/groups/123/posts/456"
        assert notifier._escape_markdown_v2_url(url) == url

    def test_does_not_escape_query_string(self):
        url = "https://fb.com/p?a=1&b=2"
        assert notifier._escape_markdown_v2_url(url) == url


# ---------------------------------------------------------------------------
# enviar_alerta — missing config
# ---------------------------------------------------------------------------

def test_enviar_alerta_no_token(monkeypatch):
    monkeypatch.setattr("notifier.config.TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr("notifier.config.TELEGRAM_CHAT_ID", "123")
    result = notifier.enviar_alerta(SAMPLE_POST, SAMPLE_ANALISIS)
    assert result is False


def test_enviar_alerta_no_chat_id(monkeypatch):
    monkeypatch.setattr("notifier.config.TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setattr("notifier.config.TELEGRAM_CHAT_ID", "")
    result = notifier.enviar_alerta(SAMPLE_POST, SAMPLE_ANALISIS)
    assert result is False


# ---------------------------------------------------------------------------
# enviar_alerta — text message (no images)
# ---------------------------------------------------------------------------

def test_enviar_alerta_text_success(monkeypatch):
    monkeypatch.setattr("notifier.config.TELEGRAM_BOT_TOKEN", "testtoken")
    monkeypatch.setattr("notifier.config.TELEGRAM_CHAT_ID", "42")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("notifier.requests.post", return_value=mock_resp) as mock_post:
        result = notifier.enviar_alerta(SAMPLE_POST, SAMPLE_ANALISIS)

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "sendMessage" in call_kwargs[0][0]
    payload = call_kwargs[1]["json"]
    assert payload["chat_id"] == "42"
    assert "MarkdownV2" == payload["parse_mode"]
    # URL must appear unescaped (dots not escaped) inside the message
    assert "https://www.facebook.com/groups/123/posts/111" in payload["text"]


def test_enviar_alerta_text_request_error(monkeypatch):
    import requests as req_lib

    monkeypatch.setattr("notifier.config.TELEGRAM_BOT_TOKEN", "testtoken")
    monkeypatch.setattr("notifier.config.TELEGRAM_CHAT_ID", "42")

    with patch("notifier.requests.post", side_effect=req_lib.RequestException("fail")):
        result = notifier.enviar_alerta(SAMPLE_POST, SAMPLE_ANALISIS)

    assert result is False


# ---------------------------------------------------------------------------
# enviar_alerta — media group (with images)
# ---------------------------------------------------------------------------

def test_enviar_alerta_media_group_success(monkeypatch):
    monkeypatch.setattr("notifier.config.TELEGRAM_BOT_TOKEN", "testtoken")
    monkeypatch.setattr("notifier.config.TELEGRAM_CHAT_ID", "42")

    post_with_images = {
        **SAMPLE_POST,
        "imagenes": ["https://fbcdn.net/img1.jpg", "https://fbcdn.net/img2.jpg"],
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("notifier.requests.post", return_value=mock_resp) as mock_post:
        result = notifier.enviar_alerta(post_with_images, SAMPLE_ANALISIS)

    assert result is True
    mock_post.assert_called_once()
    assert "sendMediaGroup" in mock_post.call_args[0][0]


def test_enviar_alerta_media_group_fallback_to_text(monkeypatch):
    """When sendMediaGroup fails, notifier should fall back to sendMessage."""
    import requests as req_lib

    monkeypatch.setattr("notifier.config.TELEGRAM_BOT_TOKEN", "testtoken")
    monkeypatch.setattr("notifier.config.TELEGRAM_CHAT_ID", "42")

    post_with_images = {**SAMPLE_POST, "imagenes": ["https://fbcdn.net/img1.jpg"]}

    ok_resp = MagicMock()
    ok_resp.raise_for_status.return_value = None

    call_count = {"n": 0}

    def _side_effect(url, **kwargs):
        call_count["n"] += 1
        if "sendMediaGroup" in url:
            raise req_lib.RequestException("media group failed")
        return ok_resp

    with patch("notifier.requests.post", side_effect=_side_effect) as mock_post:
        result = notifier.enviar_alerta(post_with_images, SAMPLE_ANALISIS)

    assert result is True
    assert call_count["n"] == 2  # sendMediaGroup + sendMessage fallback


def test_enviar_alerta_limits_images_to_10(monkeypatch):
    monkeypatch.setattr("notifier.config.TELEGRAM_BOT_TOKEN", "testtoken")
    monkeypatch.setattr("notifier.config.TELEGRAM_CHAT_ID", "42")

    images = [f"https://fbcdn.net/img{i}.jpg" for i in range(15)]
    post_many_images = {**SAMPLE_POST, "imagenes": images}

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("notifier.requests.post", return_value=mock_resp) as mock_post:
        notifier.enviar_alerta(post_many_images, SAMPLE_ANALISIS)

    payload = mock_post.call_args[1]["json"]
    sent_urls = [item["media"] for item in payload["media"]]
    assert len(sent_urls) == 10
    # Must be the first 10 images, in order.
    assert sent_urls == images[:10]
