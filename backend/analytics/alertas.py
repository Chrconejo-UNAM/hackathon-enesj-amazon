"""Alertas deterministas de GET /api/partido/{gameId}/alertas?hasta=n (tarea 7.4).

Sin LLM ni aleatoriedad. Solo usa jugadas con n <= hasta (corte propio, orden cronológico
por quarter, reloj descendente y playId). Orden: gravedad y luego id.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (ALERTA_MIN_JUGADAS, ALERTA_RACHA_N, ALERTA_RACHA_REGRET,
                     ALERTA_REGRET_AVISO, ALERTA_REGRET_CRITICO, ALERTA_ZONA_MIN_N,
                     ALERTA_ZONA_REGRET)
from .estimacion import construir_estimacion
from .schemas import Alerta, ErrorApi, Texto

_GRAVEDAD = {"critico": 0, "aviso": 1, "info": 2}
_NO_CONCL = Texto(es=" Aún no es concluyente.", en=" Not conclusive yet.")


def _corte(jugadas: pd.DataFrame, game_id: int, hasta: int) -> pd.DataFrame:
    """Jugadas del partido numeradas cronológicamente y cortadas en n <= hasta."""
    d = jugadas[jugadas["gameId"] == game_id].copy()
    d["_neg"] = -d["segundos"]
    d = d.sort_values(["quarter", "_neg", "playId"], kind="mergesort").reset_index(drop=True)
    d["n"] = d.index + 1
    return d[d["n"] <= hasta].reset_index(drop=True)


def _alerta(id_: str, nivel: str, titulo: Texto, texto: Texto, est) -> Alerta:
    if not est.concluyente:
        nivel = "info"
        texto = Texto(es=texto.es + _NO_CONCL.es, en=texto.en + _NO_CONCL.en)
    return Alerta(id=id_, nivel=nivel, titulo=titulo, texto=texto, estimacion=est)


def calcular_alertas(d: pd.DataFrame) -> list[Alerta]:
    """Alertas a partir de las jugadas ya cortadas (columnas n, zona, regret)."""
    if "regret" in d.columns:
        r = d[d["regret"].notna()]
    else:
        r = d.iloc[0:0].assign(regret=pd.Series(dtype=float))
    vals = r["regret"].to_numpy(dtype=float)
    n = len(vals)
    est = construir_estimacion(vals)
    out: list[Alerta] = []

    if n < ALERTA_MIN_JUGADAS:
        out.append(_alerta(
            "datos_insuficientes", "info",
            Texto(es="Datos insuficientes", en="Not enough data"),
            Texto(es=f"Solo {n} jugadas con regret medible (n={n}); se necesitan "
                     f"{ALERTA_MIN_JUGADAS}.",
                  en=f"Only {n} plays with measurable regret (n={n}); "
                     f"{ALERTA_MIN_JUGADAS} are needed."), est))
    elif est.valor >= ALERTA_REGRET_AVISO:
        nivel = "critico" if est.valor >= ALERTA_REGRET_CRITICO else "aviso"
        out.append(_alerta(
            "regret_alto", nivel, Texto(es="Regret alto", en="High regret"),
            Texto(es=f"El regret promedio acumulado es {est.valor:.1f} yd (n={n}).",
                  en=f"Cumulative average regret is {est.valor:.1f} yd (n={n})."), est))

    for zona in sorted(z for z in r["zona"].dropna().unique()):
        v = r.loc[r["zona"] == zona, "regret"].to_numpy(dtype=float)
        if len(v) >= ALERTA_ZONA_MIN_N and v.mean() >= ALERTA_ZONA_REGRET:
            ez = construir_estimacion(v)
            out.append(_alerta(
                f"zona_ciega:{zona}", "aviso",
                Texto(es=f"Zona ciega: {zona}", en=f"Blind zone: {zona}"),
                Texto(es=f"El regret en {zona} es {ez.valor:.1f} yd (n={len(v)}).",
                      en=f"Regret in {zona} is {ez.valor:.1f} yd (n={len(v)})."), ez))

    if n >= ALERTA_RACHA_N:
        ult = vals[-ALERTA_RACHA_N:]
        if bool(np.all(ult >= ALERTA_RACHA_REGRET)):
            er = construir_estimacion(ult)
            out.append(_alerta(
                "racha", "info", Texto(es="Racha de pases", en="Streak of passes"),
                Texto(es=f"Las últimas {ALERTA_RACHA_N} jugadas tienen regret de "
                         f"{ALERTA_RACHA_REGRET:.1f} yd o más (n={ALERTA_RACHA_N}).",
                      en=f"The last {ALERTA_RACHA_N} plays each have regret of "
                         f"{ALERTA_RACHA_REGRET:.1f} yd or more (n={ALERTA_RACHA_N})."), er))

    return sorted(out, key=lambda a: (_GRAVEDAD[a.nivel], a.id))


def alertas_partido(almacen, game_id: int, hasta: int | None) -> list[Alerta]:
    """Alertas del partido hasta la jugada `hasta` (por defecto, partido completo)."""
    if not any(p.gameId == game_id for p in almacen.partidos):
        raise ErrorApi(404, "Partido no encontrado", "partido_no_encontrado")
    j = almacen.jugadas
    n_pases = int((j["gameId"] == game_id).sum()) if j is not None and not j.empty else 0
    if hasta is None:
        hasta = n_pases
    if hasta < 1 or hasta > n_pases:
        raise ErrorApi(404, "Jugada no encontrada", "jugada_no_encontrada")
    return calcular_alertas(_corte(j, game_id, hasta))
