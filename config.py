"""
Configuration module.

Loads settings from a .env file (or environment variables) and exposes them
as typed constants used across all other modules.
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_list(key: str, default: str = "") -> list[str]:
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Facebook ---
FACEBOOK_GROUP_URLS: list[str] = _get_list("FACEBOOK_GROUP_URLS")
MAX_POSTS_PER_GROUP: int = int(os.getenv("MAX_POSTS_PER_GROUP", "20"))

# --- Criterios de búsqueda ---
MAX_PRECIO: int = int(os.getenv("MAX_PRECIO", "0"))
BARRIOS_PREFERIDOS: list[str] = _get_list("BARRIOS_PREFERIDOS")
ACEPTA_MASCOTAS: bool = os.getenv("ACEPTA_MASCOTAS", "false").lower() == "true"
MIN_DORMITORIOS: int = int(os.getenv("MIN_DORMITORIOS", "1"))

# --- Google Gemini ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# --- Telegram ---
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Base de datos ---
DB_PATH: str = os.getenv("DB_PATH", "alquileres.db")

# --- Programación ---
INTERVALO_MINUTOS: int = int(os.getenv("INTERVALO_MINUTOS", "60"))

# --- Validation warnings ---
_REQUIRED: list[tuple[str, str]] = [
    ("FACEBOOK_GROUP_URLS", "no hay grupos de Facebook configurados"),
    ("GEMINI_API_KEY", "el análisis con Gemini no funcionará"),
    ("TELEGRAM_BOT_TOKEN", "las notificaciones de Telegram no funcionarán"),
    ("TELEGRAM_CHAT_ID", "las notificaciones de Telegram no funcionarán"),
]

for _env_key, _hint in _REQUIRED:
    if not os.getenv(_env_key):
        logger.warning("Config: %s no está definido — %s.", _env_key, _hint)
