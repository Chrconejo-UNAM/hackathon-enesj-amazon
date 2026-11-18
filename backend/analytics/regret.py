"""Agregación de Regret por liga, equipo, zona y lado, y GET /api/resumen (tarea 5.4).

El Regret por jugada ya viene calculado en la columna `regret` (separacion.py). Aquí solo se
agrega: toda estimación pasa por `construir_estimacion` (única fuente del semáforo).
Las jugadas sin regret (sin receptor o sin medición) quedan fuera.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .calidad import pct_objetivo_desde_jugadas
from .estimacion import construir_estimacion
from .schemas import (CalidadDatos, Estimacion, EquipoEstimacion, Resumen, Texto)
from .zonas import ZONAS, lado_de_zona


def _con_regret(jugadas: pd.DataFrame) -> pd.DataFrame:
    if jugadas is None or jugadas.empty or "regret" not in jugadas.columns:
        return pd.DataFrame(columns=["equipo", "zona", "regret"])
    return jugadas[jugadas["regret"].notna()]


def _est(valores) -> Estimacion:
    return construir_estimacion(np.asarray(valores, dtype=float))


def regret_liga(jugadas: pd.DataFrame) -> Estimacion:
    """Estimación sobre todas las jugadas con regret (incluye penalizadas)."""
    return _est(_con_regret(jugadas)["regret"])


def regret_por_equipo(jugadas: pd.DataFrame, zona: str | None = None) -> list[EquipoEstimacion]:
    """Orden: regret promedio descendente y luego equipo. Sin jugadas en el filtro, no aparece."""
    d = _con_regret(jugadas)
    if zona is not None:
        d = d[d["zona"] == zona]
    filas = [EquipoEstimacion(equipo=str(e), estimacion=_est(g["regret"]))
             for e, g in d.groupby("equipo")]
    return sorted(filas, key=lambda f: (-f.estimacion.valor, f.equipo))


def regret_por_zona(jugadas: pd.DataFrame) -> dict[str, Estimacion]:
    d = _con_regret(jugadas)
    return {z: _est(d.loc[d["zona"] == z, "regret"]) for z in ZONAS if (d["zona"] == z).any()}


def regret_por_lado(jugadas: pd.DataFrame) -> dict[str, Estimacion]:
    d = _con_regret(jugadas)
    if d.empty:
        return {}
    lados = d["zona"].map(lado_de_zona)
    return {l: _est(d.loc[lados == l, "regret"]) for l in ("izquierda", "centro", "derecha")
            if (lados == l).any()}


def resumen(jugadas: pd.DataFrame) -> Resumen:
    est = regret_liga(jugadas)
    if est.n == 0:
        titulo = Texto(es="Aún no hay jugadas con regret medible (n=0)",
                       en="No plays with measurable regret yet (n=0)")
    else:
        v, lo, hi = f"{est.valor:.1f}", f"{est.ic95[0]:.1f}", f"{est.ic95[1]:.1f}"
        titulo = Texto(
            es=f"Los quarterbacks pierden {v} yd de separación por pase "
               f"(IC95% {lo} a {hi}, n={est.n})",
            en=f"Quarterbacks lose {v} yd of separation per pass "
               f"(95% CI {lo} to {hi}, n={est.n})")
    es = "Contrafactual estimado: lanzar al receptor más abierto en lugar del elegido."
    en = "Estimated counterfactual: throwing to the most open receiver instead of the chosen one."
    if not est.concluyente:
        es += " Aún no es concluyente."
        en += " Not conclusive yet."
    return Resumen(titulo=titulo, linea=Texto(es=es, en=en), regret_liga=est,
                   calidad_datos=CalidadDatos(
                       pct_objetivo_inferido=pct_objetivo_desde_jugadas(jugadas)))
