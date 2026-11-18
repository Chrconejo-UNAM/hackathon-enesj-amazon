"""Estimación con bootstrap reproducible y semáforo de confianza.

Único lugar donde se calcula el semáforo (design.md, "estimacion.py").
"""
from __future__ import annotations

import numpy as np

from .config import ANCHO_VERDE, N_REMUESTREOS, N_ROJO, N_VERDE, SEMILLA
from .schemas import Estimacion

_BLOQUE = 100


def semaforo(n: int, ancho: float) -> str:
    """rojo: n < N_ROJO; verde: n >= N_VERDE y ancho < ANCHO_VERDE; si no, amarillo."""
    if n < N_ROJO:
        return "rojo"
    if n >= N_VERDE and ancho < ANCHO_VERDE:
        return "verde"
    return "amarillo"


def bootstrap_ic(valores: np.ndarray) -> tuple[float, float]:
    """IC95% percentil de la media; semilla fija, remuestreo en bloques."""
    valores = np.asarray(valores, dtype=float)
    n = len(valores)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        v = float(valores[0])
        return v, v
    rng = np.random.default_rng(SEMILLA)
    medias = np.empty(N_REMUESTREOS)
    for i in range(0, N_REMUESTREOS, _BLOQUE):
        idx = rng.integers(0, n, size=(min(_BLOQUE, N_REMUESTREOS - i), n))
        medias[i:i + idx.shape[0]] = valores[idx].mean(axis=1)
    lo, hi = np.percentile(medias, [2.5, 97.5])
    return float(lo), float(hi)


def construir_estimacion(valores: np.ndarray) -> Estimacion:
    valores = np.asarray(valores, dtype=float)
    n = int(len(valores))
    if n == 0:
        return Estimacion(valor=0.0, ic95=(0.0, 0.0), n=0, concluyente=False, confianza="rojo")
    lo, hi = bootstrap_ic(valores)
    conf = semaforo(n, hi - lo)
    return Estimacion(
        valor=float(valores.mean()),
        ic95=(lo, hi),
        n=n,
        concluyente=conf != "rojo",
        confianza=conf,
    )
