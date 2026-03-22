"""
Gemini AI analysis module (Phase 4).

Downloads post images (if any) and sends text + images to the Google Gemini
multimodal API to determine whether the rental matches the user's criteria.

The response is expected as a JSON object with the following fields:
    {
        "es_apto": true | false,
        "razon": "short explanation",
        "precio_estimado": "value as string or null",
        "habitaciones": 1
    }
"""

import io
import json
import re
from typing import Any

import requests
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

import config

# Configure the Gemini client once at import time.
genai.configure(api_key=config.GEMINI_API_KEY)


def _build_system_prompt() -> str:
    criterios: list[str] = [f"mínimo {config.MIN_DORMITORIOS} dormitorio(s)"]
    if config.ACEPTA_MASCOTAS:
        criterios.append("acepta mascotas")
    if config.MAX_PRECIO:
        criterios.append(f"precio máximo ARS {config.MAX_PRECIO:,}")
    if config.BARRIOS_PREFERIDOS:
        criterios.append("barrios preferidos: " + ", ".join(config.BARRIOS_PREFERIDOS))

    criterios_str = "; ".join(criterios)

    return (
        "Eres un asistente experto en bienes raíces de la ciudad de Neuquén, Argentina. "
        "Analiza la siguiente publicación de Facebook (texto e imágenes adjuntas). "
        f"Criterios del usuario: {criterios_str}. "
        "Determina si es un alquiler DISPONIBLE en Neuquén Capital que cumpla con esos criterios. "
        "Evalúa las fotos para confirmar el estado y características del inmueble. "
        'Responde estrictamente en formato JSON (sin markdown, sin bloques de código): '
        '{"es_apto": true/false, "razon": "explicación breve", '
        '"precio_estimado": "valor o null", "habitaciones": número_entero}'
    )


def _descargar_imagen(url: str) -> bytes | None:
    """Download an image from *url* and return its bytes, or None on failure."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


def analizar_post(post: dict[str, Any]) -> dict[str, Any]:
    """
    Send *post* text and images to Gemini and return the parsed JSON result.

    Parameters
    ----------
    post:
        A post dict with at least ``texto`` and ``imagenes`` keys.

    Returns
    -------
    dict with keys ``es_apto`` (bool), ``razon`` (str),
    ``precio_estimado`` (str | None), ``habitaciones`` (int).
    On any error returns ``{"es_apto": False, "razon": "<error description>",
    "precio_estimado": null, "habitaciones": 0}``.
    """
    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        },
    )

    system_prompt = _build_system_prompt()
    parts: list[Any] = [system_prompt, f"\n\nTexto de la publicación:\n{post['texto']}"]

    # Attach up to 5 images to keep the request size manageable.
    for img_url in post.get("imagenes", [])[:5]:
        img_bytes = _descargar_imagen(img_url)
        if img_bytes:
            parts.append({"mime_type": "image/jpeg", "data": img_bytes})

    try:
        response = model.generate_content(parts)
        raw = response.text.strip()

        # Strip any accidental markdown code fences.
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)

        # Normalize field types.
        return {
            "es_apto": bool(result.get("es_apto", False)),
            "razon": str(result.get("razon", "")),
            "precio_estimado": result.get("precio_estimado"),
            "habitaciones": int(result.get("habitaciones", 0)),
        }
    except json.JSONDecodeError as exc:
        return {
            "es_apto": False,
            "razon": f"Error al parsear respuesta de Gemini: {exc}",
            "precio_estimado": None,
            "habitaciones": 0,
        }
    except Exception as exc:
        return {
            "es_apto": False,
            "razon": f"Error en análisis Gemini: {exc}",
            "precio_estimado": None,
            "habitaciones": 0,
        }
