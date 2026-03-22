"""
Telegram notification module (Phase 5).

Sends an alert to the configured Telegram chat when a matching rental is found.
Uses the Telegram Bot API directly via ``requests`` to keep the dependency
surface small (no need for the full python-telegram-bot async runtime here).
"""

from typing import Any

import requests

import config

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"


def _api_url(method: str) -> str:
    return TELEGRAM_API_BASE.format(token=config.TELEGRAM_BOT_TOKEN, method=method)


def _escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


def enviar_alerta(post: dict[str, Any], analisis: dict[str, Any]) -> bool:
    """
    Send a Telegram alert for a matching rental post.

    Parameters
    ----------
    post:
        The scraped post dict (``post_id``, ``url``, ``texto``, ``imagenes``,
        ``autor``, ``fecha``).
    analisis:
        The Gemini analysis result (``es_apto``, ``razon``, ``precio_estimado``,
        ``habitaciones``).

    Returns
    -------
    True if the alert was sent successfully, False otherwise.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[Notificador] Token o Chat ID de Telegram no configurados. Omitiendo alerta.")
        return False

    precio = analisis.get("precio_estimado") or "No especificado"
    habitaciones = analisis.get("habitaciones", "?")
    razon = analisis.get("razon", "")

    mensaje = (
        "🏠 *Nuevo alquiler encontrado\\!*\n\n"
        f"📝 *Razón del match:* {_escape_markdown_v2(razon)}\n"
        f"💰 *Precio estimado:* {_escape_markdown_v2(str(precio))}\n"
        f"🛏 *Dormitorios:* {habitaciones}\n"
        f"👤 *Autor:* {_escape_markdown_v2(post.get('autor', 'Desconocido'))}\n"
        f"🔗 [Ver publicación]({_escape_markdown_v2(post.get('url', ''))})"
    )

    chat_id = config.TELEGRAM_CHAT_ID
    imagenes = post.get("imagenes", [])

    # If there are images, send a media group (up to 10); otherwise send a text message.
    if imagenes:
        media_group = []
        for i, img_url in enumerate(imagenes[:10]):
            media_item: dict[str, Any] = {
                "type": "photo",
                "media": img_url,
            }
            if i == 0:
                media_item["caption"] = mensaje
                media_item["parse_mode"] = "MarkdownV2"
            media_group.append(media_item)

        try:
            resp = requests.post(
                _api_url("sendMediaGroup"),
                json={"chat_id": chat_id, "media": media_group},
                timeout=30,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as exc:
            print(f"[Notificador] Error enviando media group: {exc}")
            # Fall through to plain text message.

    # Plain text fallback (or when there are no images).
    try:
        resp = requests.post(
            _api_url("sendMessage"),
            json={
                "chat_id": chat_id,
                "text": mensaje,
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        print(f"[Notificador] Error enviando mensaje: {exc}")
        return False
