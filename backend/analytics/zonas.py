"""Zonas del campo: profundidad, lado, código de zona y rangos de yardsToGo (tarea 3.4).

La zona se calcula con la posición del receptor en el frame `pass_forward` respecto al balón
en `ball_snap`. Funciones puras, sin acceso a disco.

* Signo de dirección `s`: +1 si playDirection == "right", -1 si "left".
* Profundidad `p = (x_rec - x_balon) * s`: p < 5 corta (incluye detrás de la línea),
  5 <= p < 15 media, p >= 15 profunda.
* Lado `l = (y_rec - y_balon) * s` (perspectiva ofensiva): l > 5 izquierda, l < -5 derecha,
  en otro caso (|l| <= 5) centro.
"""
from __future__ import annotations

from .config import RANGOS_YTG, UMBRAL_CENTRO, UMBRAL_CORTA, UMBRAL_MEDIA

PROFUNDIDADES = ("corta", "media", "profunda")
LADOS = ("izquierda", "centro", "derecha")
ZONAS = tuple(f"{p}_{l}" for p in PROFUNDIDADES for l in LADOS)   # 9 códigos


def signo_direccion(play_direction: str) -> int:
    """+1 si la ofensiva ataca hacia +x ('right'), -1 si hacia -x ('left')."""
    return 1 if str(play_direction).strip().lower() == "right" else -1


def profundidad_de(p: float) -> str:
    """Profundidad según yardas más allá de la línea de golpeo."""
    if p < UMBRAL_CORTA:
        return "corta"
    if p < UMBRAL_MEDIA:
        return "media"
    return "profunda"


def lado_de(l: float) -> str:
    """Lado desde la perspectiva ofensiva (l > 0 = izquierda de la ofensiva)."""
    if l > UMBRAL_CENTRO:
        return "izquierda"
    if l < -UMBRAL_CENTRO:
        return "derecha"
    return "centro"


def zona_de(x_rec: float, y_rec: float, x_balon: float, y_balon: float,
            play_direction: str) -> str:
    """Código de zona `profundidad_lado` del receptor respecto al balón al snap."""
    s = signo_direccion(play_direction)
    p = (x_rec - x_balon) * s
    l = (y_rec - y_balon) * s
    return f"{profundidad_de(p)}_{lado_de(l)}"


def lado_de_zona(zona: str) -> str:
    """Parte `lado` de un código de zona ('media_izquierda' -> 'izquierda')."""
    return zona.split("_", 1)[1]


def rango_ytg(yards_to_go: int) -> str | None:
    """Rango de yardsToGo ('1-3', '4-6', '7-10', '11+'); None si es menor que 1."""
    for lo, hi, etiqueta in RANGOS_YTG:
        if lo <= yards_to_go <= hi:
            return etiqueta
    return None
