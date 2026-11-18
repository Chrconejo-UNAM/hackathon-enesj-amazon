"""Línea base de situaciones comparables y recomendación de zona (tarea 5.2).

Base: jugadas con zona resuelta, sin penalización, mismo down, mismo rango de yardsToGo y, si se
pide, misma cobertura (`Other` solo cuenta sin filtro). Todo en memoria.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import textos
from .config import MAX_COMPARABLES, N_ROJO
from .estimacion import construir_estimacion
from .schemas import Comparable, RecomendacionOut, SituacionQuery
from .zonas import rango_ytg


def _num(valor) -> float | None:
    return None if pd.isna(valor) else float(valor)


def base_situacion(jugadas: pd.DataFrame, down: int, yards_to_go: int,
                   cobertura: str | None = None) -> pd.DataFrame:
    """Jugadas comparables por down y rango de yardsToGo (y cobertura si se indica)."""
    if jugadas is None or jugadas.empty or "zona" not in jugadas.columns:
        return pd.DataFrame()
    m = (jugadas["zona"].notna() & ~jugadas["penalizada"].astype(bool)
         & (jugadas["down"] == down) & (jugadas["rango_ytg"] == rango_ytg(yards_to_go)))
    base = jugadas[m]
    if cobertura:
        base = base[base["cobertura"] == cobertura]
    return base


def estimaciones_por_zona(base: pd.DataFrame) -> dict:
    if base.empty:
        return {}
    return {z: construir_estimacion(g["playResult"].to_numpy(float))
            for z, g in base.groupby("zona")}


def mejor_zona(por_zona: dict) -> str | None:
    """Mayor valor entre zonas con n >= N_ROJO (o n > 0 si ninguna llega); desempate por zona."""
    cand = {z: e for z, e in por_zona.items() if e.n >= N_ROJO} or \
           {z: e for z, e in por_zona.items() if e.n > 0}
    if not cand:
        return None
    return min(cand, key=lambda z: (-cand[z].valor, z))


def comparables_de(base: pd.DataFrame, zona: str | None, yards_to_go: int) -> list[Comparable]:
    """Hasta MAX_COMPARABLES jugadas de la zona, por cercanía de yardsToGo y (gameId, playId)."""
    if zona is None or base.empty:
        return []
    g = base[base["zona"] == zona].copy()
    g["_d"] = (g["yardsToGo"] - yards_to_go).abs()
    g = g.sort_values(["_d", "gameId", "playId"]).head(MAX_COMPARABLES)
    cols = lambda c: g[c] if c in g.columns else pd.Series([np.nan] * len(g), index=g.index)
    out = []
    for gid, pid, eq, sem, dn, ytg, z, cob, res, se, sa in zip(
            g["gameId"], g["playId"], g["equipo"], g["semana"], g["down"], g["yardsToGo"],
            g["zona"], g["cobertura"], g["playResult"], cols("sep_elegido"),
            cols("sep_mas_abierto")):
        out.append(Comparable(
            gameId=int(gid), playId=int(pid), equipo=str(eq), semana=int(sem), down=int(dn),
            yardsToGo=int(ytg), zona=z, cobertura=None if pd.isna(cob) else str(cob),
            playResult=float(res), sep_elegido=_num(se), sep_mas_abierto=_num(sa)))
    return out


def recomendar(jugadas: pd.DataFrame, q: SituacionQuery) -> RecomendacionOut:
    base = base_situacion(jugadas, q.down, q.yardsToGo, q.cobertura)
    por_zona = estimaciones_por_zona(base)
    mejor = mejor_zona(por_zona)
    objetivo = q.zona or mejor
    est = por_zona.get(objetivo) if objetivo else None
    if est is None:
        est = construir_estimacion(np.empty(0))
    if mejor is None:
        accion = textos.accion_sin_muestra()
    elif objetivo == mejor:
        accion = textos.accion_atacar(mejor)
    elif est.n == 0:
        accion = textos.accion_zona_vacia(mejor, objetivo)
    else:
        accion = textos.accion_mejor_otra(mejor, por_zona[mejor].valor - est.valor, objetivo)
    return RecomendacionOut(accion=accion, porque=textos.porque(est), estimacion=est,
                            comparables=comparables_de(base, objetivo, q.yardsToGo))
