"""Numeración de jugadas por partido y GET /api/partido/{gameId}/jugada/{n} (tarea 7.1).

Orden cronológico: (quarter, gameClock descendente, playId), numerado de 1 a n_pases.
Cada jugada n solo usa datos de esa jugada (nunca de las posteriores).
"""
from __future__ import annotations

import pandas as pd

from .schemas import (ErrorApi, EstadoPartido, JugadaOut, JugadaRespuesta, Jugador,
                      PartidoItem, SeparacionJugador)
from .separacion import ids_elegibles, separaciones


def jugadas_ordenadas(jugadas: pd.DataFrame, game_id: int) -> pd.DataFrame:
    """Jugadas del partido en orden cronológico, con columna `n` (1..n_pases)."""
    if jugadas is None or jugadas.empty:
        return pd.DataFrame()
    d = jugadas[jugadas["gameId"] == game_id].copy()
    d["_neg"] = -d["segundos"]
    d = d.sort_values(["quarter", "_neg", "playId"], kind="mergesort").drop(columns="_neg")
    d = d.reset_index(drop=True)
    d["n"] = d.index + 1
    return d


def jugadas_hasta(jugadas: pd.DataFrame, game_id: int, hasta: int | None = None) -> pd.DataFrame:
    """Jugadas ordenadas del partido con n <= hasta (todas si hasta es None).

    Punto de entrada para cualquier cálculo con corte temporal (acumulado, alertas).
    """
    d = jugadas_ordenadas(jugadas, game_id)
    if d.empty or hasta is None:
        return d
    return d[d["n"] <= hasta].reset_index(drop=True)


def partidos_con_n_pases(partidos: list[PartidoItem], jugadas: pd.DataFrame) -> list[PartidoItem]:
    """Reemplaza n_pases provisional por el conteo real de la tabla `jugadas`.

    Sin tabla de jugadas se conserva el valor provisional de la carga.
    """
    if jugadas is None or jugadas.empty:
        return list(partidos)
    conteo = jugadas.groupby("gameId").size()
    return [p.model_copy(update={"n_pases": int(conteo.get(p.gameId, 0))}) for p in partidos]


def _tiempo(reloj) -> str:
    partes = str(reloj).strip().split(":")
    return ":".join(partes[:2]) if len(partes) >= 2 else str(reloj)


def _entero(v) -> int | None:
    return None if pd.isna(v) else int(v)


def _flotante(v) -> float | None:
    return None if pd.isna(v) else float(v)


def _jugador(roster_play: pd.DataFrame, nfl_id) -> Jugador | None:
    if pd.isna(nfl_id):
        return None
    nid = int(nfl_id)
    fila = roster_play[roster_play["nflId"] == nid]
    nombre, pos = str(nid), None
    if not fila.empty:
        if isinstance(fila["displayName"].iat[0], str):
            nombre = fila["displayName"].iat[0]
        p = fila["officialPosition"].iat[0]
        pos = p if isinstance(p, str) else None
    return Jugador(nflId=nid, nombre=nombre, posicion=pos)


def _separaciones(fila, roster_play: pd.DataFrame, frames: pd.DataFrame,
                  elegido, mas_abierto) -> list[SeparacionJugador]:
    """Separación de cada receptor elegible en el frame pass_forward de esta jugada."""
    if pd.isna(elegido) or frames is None or frames.empty or pd.isna(fila["frame_pass_forward"]):
        return []
    f = frames[(frames["gameId"] == fila["gameId"]) & (frames["playId"] == fila["playId"])
               & (frames["event"] == "pass_forward") & (frames["frameId"] == fila["frame_pass_forward"])
               & frames["nflId"].notna()]
    if f.empty:
        return []
    equipos_of = {fila["equipo"], fila["lado_ofensivo"]}
    equipos_de = {fila["defensa"], "away" if fila["lado_ofensivo"] == "home" else "home"}
    of = f[f["team"].isin(equipos_of)].drop_duplicates("nflId")
    de = f[f["team"].isin(equipos_de) & ~f["team"].isin(equipos_of)]
    roles = dict(zip(roster_play["nflId"], roster_play["rol"]))
    roles_of = {int(i): roles.get(i) for i in of["nflId"]}
    ids = [i for i in ids_elegibles(roles_of, int(elegido)) if i in roles_of]
    if not ids:
        return []
    pos = of.assign(nflId=of["nflId"].astype("int64")).set_index("nflId").loc[ids, ["x", "y"]]
    seps = separaciones(pos.to_numpy(float), de[["x", "y"]].to_numpy(float))
    sal = []
    for i, s in zip(ids, seps):
        if pd.isna(s):
            continue
        sal.append(SeparacionJugador(
            nflId=i, nombre=(_jugador(roster_play, i).nombre), separacion=float(s),
            es_elegido=i == int(elegido),
            es_mas_abierto=not pd.isna(mas_abierto) and i == int(mas_abierto)))
    return sal


def jugada_respuesta(almacen, game_id: int, n: int) -> JugadaRespuesta:
    """Jugada n del partido, con 404 `partido_no_encontrado` / `jugada_no_encontrada`."""
    partido = next((p for p in almacen.partidos if p.gameId == game_id), None)
    if partido is None:
        raise ErrorApi(404, "Partido no encontrado", "partido_no_encontrado")
    d = jugadas_ordenadas(almacen.jugadas, game_id)
    n_pases = len(d)
    if n < 1 or n > n_pases:
        raise ErrorApi(404, "Jugada no encontrada", "jugada_no_encontrada")
    f = d.iloc[n - 1]
    ros = almacen.roster
    if ros is not None and not ros.empty:
        rp = ros[(ros["gameId"] == f["gameId"]) & (ros["playId"] == f["playId"])]
    else:
        rp = pd.DataFrame(columns=["nflId", "rol", "displayName", "officialPosition"])
    get = lambda c: f[c] if c in f.index else None  # noqa: E731
    elegido, abierto = get("receptor_id"), get("receptor_mas_abierto_id")
    zona = get("zona")
    jugada = JugadaOut(
        n=n, down=int(f["down"]), yardsToGo=int(f["yardsToGo"]),
        zona=zona if isinstance(zona, str) else None,
        marcador={"local": int(f["marcador_local"]), "visitante": int(f["marcador_visitante"])},
        reloj={"quarter": int(f["quarter"]), "tiempo": _tiempo(f["gameClock"])},
        receptor_elegido=_jugador(rp, elegido) if elegido is not None else None,
        receptor_mas_abierto=_jugador(rp, abierto) if abierto is not None else None,
        separaciones=(_separaciones(f, rp, almacen.frames_eventos, elegido, abierto)
                      if elegido is not None else []),
        regret=_flotante(get("regret")) if get("regret") is not None else None,
        resultado={"pase": str(f["passResult"]), "yardas": int(f["playResult"]),
                   "texto": str(f["playDescription"])},
    )
    estado = EstadoPartido(gameId=game_id, n=n, n_pases=n_pases, hay_siguiente=n < n_pases,
                           semana=partido.semana, local=partido.local, visitante=partido.visitante)
    return JugadaRespuesta(estado=estado, jugada=jugada)
