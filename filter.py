"""
Keyword filter module (Phase 3).

Applies a fast heuristic filter based on positive and negative keyword lists
before sending posts to the more expensive Gemini analysis.
"""

import re

# Palabras que deben aparecer en el texto para considerar el post relevante.
PALABRAS_POSITIVAS: list[str] = [
    "alquiler",
    "alquilo",
    "se alquila",
    "dueño directo",
    "inmobiliaria",
    "nqn",
    "neuquen",
    "neuquén",
    "departamento",
    "casa",
    "monoambiente",
    "ph",
]

# Palabras que descartan el post inmediatamente.
PALABRAS_NEGATIVAS: list[str] = [
    "busco",
    "necesito",
    "cipolletti",
    "centenario",
    "plottier",
    "vista alegre",
    "rincón de los sauces",
    "vendo",
    "venta",
    "se vende",
    "permuta",
    "temporario",
    "vacacional",
]


def _normalizar(texto: str) -> str:
    """Lowercase and strip accents for more robust matching."""
    texto = texto.lower()
    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for original, reemplazo in reemplazos.items():
        texto = texto.replace(original, reemplazo)
    return texto


def _contiene_palabra(texto_normalizado: str, palabra: str) -> bool:
    """Return True if *palabra* appears as a whole word in *texto_normalizado*."""
    palabra_norm = _normalizar(palabra)
    pattern = r"\b" + re.escape(palabra_norm) + r"\b"
    return bool(re.search(pattern, texto_normalizado))


def pasar_filtro(texto: str) -> bool:
    """
    Return True if the post text passes the heuristic keyword filter.

    A post passes when:
    - It contains at least one positive keyword, AND
    - It contains no negative keywords.
    """
    texto_norm = _normalizar(texto)

    for neg in PALABRAS_NEGATIVAS:
        if _contiene_palabra(texto_norm, neg):
            return False

    for pos in PALABRAS_POSITIVAS:
        if _contiene_palabra(texto_norm, pos):
            return True

    return False
