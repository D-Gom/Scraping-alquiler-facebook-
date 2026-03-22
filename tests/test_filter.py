"""Tests for the keyword filter module."""

import pytest

from filter import pasar_filtro


# --- Should PASS ---
@pytest.mark.parametrize(
    "texto",
    [
        "Alquilo departamento en Neuquén capital, 2 ambientes",
        "SE ALQUILA casa - dueño directo - NQN",
        "Inmobiliaria ofrece departamento neuquen centro",
        "Alquiler monoambiente neuquén",
        "Departamento ph en Neuquén, consultar precio",
    ],
)
def test_pasar_filtro_positivo(texto):
    assert pasar_filtro(texto) is True


# --- Should FAIL ---
@pytest.mark.parametrize(
    "texto",
    [
        "Busco departamento en Neuquén, 2 dormitorios",
        "Necesito alquiler urgente en Neuquén",
        "Alquilo casa en Cipolletti, zona norte",
        "Se vende departamento en Neuquén",
        "Alquilo departamento temporario en Neuquén",
        "Alquilo casa en Plottier",
        "Alquilo en centenario",
    ],
)
def test_pasar_filtro_negativo(texto):
    assert pasar_filtro(texto) is False


def test_texto_sin_palabras_clave():
    assert pasar_filtro("Hola, ¿cómo estás?") is False


def test_caso_insensible():
    assert pasar_filtro("ALQUILO DEPARTAMENTO EN NEUQUÉN CAPITAL") is True


def test_palabra_negativa_tiene_prioridad():
    # "alquilo" is positive but "busco" is negative → should fail.
    assert pasar_filtro("Busco alquilo departamento neuquén") is False
