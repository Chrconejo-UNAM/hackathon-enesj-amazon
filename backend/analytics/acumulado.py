"""Regret acumulado de un partido hasta la jugada `hasta` (corte temporal, tarea 7.2).

Numeración propia (quarter, -segundos, playId), igual que partido.py. Solo se usan
jugadas con n <= hasta; nada posterior influye en el resultado.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .estimacion import construir_estimacion
from .schemas import Acumulado, AcumuladoLado, AcumuladoZona, ErrorApi
from .zonas import lado_de_zona


def _numerar(jugadas: pd.DataFrame, game_id: int) -> pd.DataFrame:
    d = jugadas[jugadas["gameId"] == game_id]
    d = d.assign(_neg=-d["segundos"]).sort_values(["quarter", "_neg", "playId"], kind="mergesort")
    d = d.drop(columns="_neg").reset_index(drop=True)
    d["n"] = np.arange(1, len(d) + 1)
    return d


def acumulado_hasta(almacen, game_id: int, hasta: int | None) -> Acumulado:
    if not any(p.gameId == game_id for p in almacen.partidos):
        raise ErrorApi(404, "Partido no encontrado", "partido_no_encontrado")
    d = _numerar(almacen.jugadas, game_id)
    n_pases = len(d)
    h = n_pases if hasta is None else hasta
    if h < 1 or h > n_pases:
        raise ErrorApi(404, "Jugada no encontrada", "jugada_no_encontrada")
    df = d[d["n"] <= h]
    df = df[df["regret"].notna()]
    regrets = df["regret"].to_numpy(float)

    por_zona = []
    if len(df):
        for z, g in df[df["zona"].notna()].groupby("zona"):
            v = g["regret"].to_numpy(float)
            por_zona.append(AcumuladoZona(zona=z, total_yd=round(float(v.sum()), 2),
                                          estimacion=construir_estimacion(v)))
        lados = df[df["zona"].notna()].assign(_lado=lambda x: x["zona"].map(lado_de_zona))
        por_lado = [AcumuladoLado(lado=l, total_yd=round(float(g["regret"].sum()), 2),
                                  estimacion=construir_estimacion(g["regret"].to_numpy(float)))
                    for l, g in lados.groupby("_lado")]
    else:
        por_lado = []
    return Acumulado(hasta=h, n_con_regret=int(len(regrets)),
                     total_yd=round(float(regrets.sum()), 2),
                     estimacion=construir_estimacion(regrets),
                     por_zona=por_zona, por_lado=por_lado)
