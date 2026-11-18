"""Series de GET /api/evidencia (tarea 5.3).

Base: misma situación (down y rango de yardsToGo), sin penalizadas y SIN filtrar cobertura.
Situación sin datos: cuatro series vacías (HTTP 200).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .comparables import base_situacion
from .estimacion import construir_estimacion
from .schemas import (BinDistribucion, DistribucionZona, Evidencia, RegretZona,
                      ValorCobertura, ValorZona)
from .zonas import ZONAS

BIN_MIN, BIN_MAX, BIN_ANCHO = -10, 40, 5


def bins_distribucion(resultados) -> list[BinDistribucion]:
    """Bins de 5 yd de -10 a 40; el último (desde=40, hasta=None) acumula 40 o más.
    Valores menores que -10 se acumulan en el primer bin para que la suma sea siempre n."""
    v = np.asarray(resultados, dtype=float)
    n_bins = (BIN_MAX - BIN_MIN) // BIN_ANCHO                      # 10 bins finitos
    idx = np.floor((v - BIN_MIN) / BIN_ANCHO).astype(int) if len(v) else np.empty(0, int)
    idx = np.clip(idx, 0, n_bins)                                  # n_bins = bin "40+"
    cont = np.bincount(idx, minlength=n_bins + 1)
    bins = [BinDistribucion(desde=BIN_MIN + BIN_ANCHO * i, hasta=BIN_MIN + BIN_ANCHO * (i + 1),
                            n=int(cont[i])) for i in range(n_bins)]
    bins.append(BinDistribucion(desde=BIN_MAX, hasta=None, n=int(cont[n_bins])))
    return bins


def _est(valores) -> object:
    return construir_estimacion(np.asarray(valores, dtype=float))


def evidencia(jugadas: pd.DataFrame, down: int, yards_to_go: int, zona: str | None) -> Evidencia:
    base = base_situacion(jugadas, down, yards_to_go, None)
    if base.empty:
        return Evidencia(distribucion=[], valor_por_zona=[], valor_por_cobertura=[],
                         regret_por_zona=[])
    distribucion, valor_zona, regret_zona = [], [], []
    for z in ZONAS:
        g = base[base["zona"] == z]
        if g.empty:
            continue
        distribucion.append(DistribucionZona(zona=z, bins=bins_distribucion(g["playResult"])))
        valor_zona.append(ValorZona(zona=z, estimacion=_est(g["playResult"])))
        if "regret" in g.columns:
            r = g["regret"].dropna()
            if len(r):
                regret_zona.append(RegretZona(zona=z, estimacion=_est(r)))
    objetivo = base[base["zona"] == zona] if zona else base
    cob = objetivo["cobertura"] if len(objetivo) else pd.Series([], dtype=object)
    cobertura = [ValorCobertura(cobertura=nombre, estimacion=_est(
        objetivo.loc[mask, "playResult"])) for nombre, mask in (
        ("Man", cob == "Man"), ("Zone", cob == "Zone"), ("Otra", ~cob.isin(["Man", "Zone"])))]
    return Evidencia(distribucion=distribucion, valor_por_zona=valor_zona,
                     valor_por_cobertura=cobertura, regret_por_zona=regret_zona)
