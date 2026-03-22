"""Tests for the Gemini analyzer module (mocked API calls)."""

import json
from unittest.mock import MagicMock, patch

import pytest

import gemini_analyzer


SAMPLE_POST = {
    "post_id": "111",
    "url": "https://fb.com/posts/111",
    "texto": "Alquilo departamento neuquén 2 dormitorios",
    "imagenes": [],
    "autor": "Test",
    "fecha": "2024-01-01",
}

VALID_RESPONSE = json.dumps(
    {
        "es_apto": True,
        "razon": "Cumple todos los criterios",
        "precio_estimado": "200000",
        "habitaciones": 2,
    }
)


def _make_mock_response(text: str):
    mock_resp = MagicMock()
    mock_resp.text = text
    return mock_resp


@patch("gemini_analyzer.genai.GenerativeModel")
def test_analizar_post_success(mock_model_cls):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_mock_response(VALID_RESPONSE)
    mock_model_cls.return_value = mock_model

    result = gemini_analyzer.analizar_post(SAMPLE_POST)

    assert result["es_apto"] is True
    assert result["habitaciones"] == 2
    assert result["precio_estimado"] == "200000"


@patch("gemini_analyzer.genai.GenerativeModel")
def test_analizar_post_json_with_markdown_fences(mock_model_cls):
    """Gemini sometimes wraps JSON in markdown code blocks."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_mock_response(
        f"```json\n{VALID_RESPONSE}\n```"
    )
    mock_model_cls.return_value = mock_model

    result = gemini_analyzer.analizar_post(SAMPLE_POST)
    assert result["es_apto"] is True


@patch("gemini_analyzer.genai.GenerativeModel")
def test_analizar_post_invalid_json(mock_model_cls):
    """Invalid JSON response should return es_apto=False with an error reason."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = _make_mock_response("not valid json {")
    mock_model_cls.return_value = mock_model

    result = gemini_analyzer.analizar_post(SAMPLE_POST)
    assert result["es_apto"] is False
    assert "Error al parsear" in result["razon"]


@patch("gemini_analyzer.genai.GenerativeModel")
def test_analizar_post_api_error(mock_model_cls):
    """API errors should be caught and return es_apto=False."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("API Error")
    mock_model_cls.return_value = mock_model

    result = gemini_analyzer.analizar_post(SAMPLE_POST)
    assert result["es_apto"] is False
    assert "Error en análisis Gemini" in result["razon"]
