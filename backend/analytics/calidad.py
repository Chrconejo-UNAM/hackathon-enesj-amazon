"""Calidad de la inferencia de receptor (tarea 3.3).

`pct_objetivo_inferido` (contrato, 0 a 100) = 100 * jugadas con origen "pass_arrived" /
jugadas con receptor (decisión del diseño, pregunta abierta 3). Diagnóstico interno
(no forma parte del contrato): `pct_texto` y `pct_sin_receptor` sobre todas las jugadas.
Sin jugadas con receptor, `pct_objetivo_inferido` es 0.0.
"""
from __future__ import annotations

import pandas as pd


def pct_objetivo_desde_jugadas(jugadas: pd.DataFrame) -> float:
    """Mismo cálculo sobre la tabla `jugadas` enriquecida (columna `origen_receptor`)."""
    if jugadas is None or jugadas.empty or "origen_receptor" not in jugadas.columns:
        return 0.0
    origen = jugadas["origen_receptor"]
    con = int(origen.notna().sum())
    return 100.0 * int((origen == "pass_arrived").sum()) / con if con else 0.0


def resumen_calidad(receptores: pd.DataFrame) -> dict[str, float]:
    """receptores: salida de receptor.inferir_receptores (columna `origen`)."""
    total = len(receptores)
    con = int(receptores["origen"].notna().sum())
    n_arrived = int((receptores["origen"] == "pass_arrived").sum())
    n_texto = int((receptores["origen"] == "texto").sum())
    return {
        "pct_objetivo_inferido": 100.0 * n_arrived / con if con else 0.0,
        "pct_texto": 100.0 * n_texto / total if total else 0.0,
        "pct_sin_receptor": 100.0 * (total - con) / total if total else 0.0,
    }
