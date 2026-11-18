"""Limpieza de plays y tabla `jugadas` con features por jugada (tarea 3.2).

Todo ocurre en memoria; no se lee ni escribe disco aquí. Supuestos:

* Pase_Lanzado: `passResult` en C, I o IN **y** al menos un frame `pass_forward` en el
  tracking (el cargador ya sustituyó `autoevent_passforward` cuando faltaba el principal).
  Sacks (S) y scrambles (R) quedan fuera, porque casi no tienen `pass_forward`.
* Limpieza (Req. 1.10 y 1.11): se descartan nulos en down, yardsToGo, absoluteYardlineNumber,
  quarter, gameClock, preSnapHomeScore, preSnapVisitorScore y passResult, y `down` == 0
  (conversiones de dos puntos). Las jugadas penalizadas (`penaltyYards` != 0, nulo = 0) se
  conservan con `penalizada=True`; solo se excluyen del valor en yardas (Req. 1.12).
* `gameClock` llega como "MM:SS" (se tolera "MM:SS:CC"); `segundos` son los segundos
  restantes del cuarto. El orden cronológico (quarter, -segundos, playId) lo aplica partido.py.
* `equipo` es `possessionTeam`. `lado_ofensivo` es "home" si el equipo ofensivo es el local del
  partido y "away" si es el visitante; coincide con la columna `team` del tracking
  ("home"/"away"/"football"), que es como se separa ofensiva y defensiva en los frames.
* `cobertura` es `pff_passCoverageType` tal cual (Man, Zone u Other; puede ser nulo).
* `rol` del roster es `pff_role` en minúsculas y sin espacios sobrantes, porque el CSV real
  usa "Pass Route" y "Pass Block" con mayúsculas y la documentación otras formas.
* Posición del balón al snap: primera fila `team == "football"` del frame `ball_snap`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RANGOS_YTG

PASES_LANZADOS = ("C", "I", "IN")
REQUERIDAS = ["down", "yardsToGo", "absoluteYardlineNumber", "quarter", "gameClock",
              "preSnapHomeScore", "preSnapVisitorScore", "passResult"]
COLS_PLAYS = ["gameId", "playId", "playDescription", "quarter", "down", "yardsToGo",
              "possessionTeam", "defensiveTeam", "gameClock", "preSnapHomeScore",
              "preSnapVisitorScore", "passResult", "penaltyYards", "playResult",
              "absoluteYardlineNumber", "pff_passCoverageType"]
COLS_GAMES = ["gameId", "week", "homeTeamAbbr", "visitorTeamAbbr"]
COLS_PLAYERS = ["nflId", "officialPosition", "displayName"]
COLS_PFF = ["gameId", "playId", "nflId", "pff_role"]

_LLAVE = ["gameId", "playId"]
_SUFIJOS = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def segundos_reloj(valor) -> float:
    """'13:33' -> 813.0 (segundos restantes del cuarto). Nulo o ilegible -> NaN."""
    if not isinstance(valor, str):
        return float("nan")
    partes = valor.strip().split(":")
    try:
        if len(partes) >= 2:
            return int(partes[0]) * 60.0 + int(partes[1])
    except ValueError:
        pass
    return float("nan")


def rango_ytg(yards_to_go: int) -> str | None:
    """Rango de yardsToGo según config.RANGOS_YTG ('1-3', '4-6', '7-10', '11+')."""
    for lo, hi, etiqueta in RANGOS_YTG:
        if lo <= yards_to_go <= hi:
            return etiqueta
    return None


def clave_nombre(display_name: str) -> str:
    """'O.J. Howard' -> 'O.Howard'; 'Odell Beckham Jr.' -> 'O.Beckham'. Sin sufijos."""
    partes = [p for p in str(display_name).split() if p.lower() not in _SUFIJOS]
    if not partes:
        return ""
    return f"{partes[0][0]}.{partes[-1]}"


def limpiar_plays(plays: pd.DataFrame) -> pd.DataFrame:
    """Descarta nulos de contexto y down == 0; agrega `penalizada` (no descarta penalizadas)."""
    df = plays.dropna(subset=REQUERIDAS)
    df = df[df["down"].between(1, 4)].copy()
    df["penalizada"] = df["penaltyYards"].fillna(0) != 0
    return df.reset_index(drop=True)


def _frames_clave(frames: pd.DataFrame, evento: str, nombre: str) -> pd.DataFrame:
    """Primer frameId de un evento por jugada."""
    f = frames.loc[frames["event"] == evento, _LLAVE + ["frameId"]]
    return (f.groupby(_LLAVE, as_index=False)["frameId"].min()
            .rename(columns={"frameId": nombre}))


def _balon_snap(frames: pd.DataFrame) -> pd.DataFrame:
    b = frames[(frames["event"] == "ball_snap") & (frames["team"] == "football")]
    b = b.sort_values(_LLAVE + ["frameId"]).drop_duplicates(_LLAVE)
    return b[_LLAVE + ["x", "y", "playDirection"]].rename(
        columns={"x": "balon_x", "y": "balon_y"})


def construir_jugadas(games: pd.DataFrame, plays: pd.DataFrame,
                      frames: pd.DataFrame) -> pd.DataFrame:
    """Una fila por Pase_Lanzado válido (passResult C/I/IN con frame pass_forward).

    Columnas: gameId, playId, semana, local, visitante, equipo, defensa, lado_ofensivo, down,
    yardsToGo, rango_ytg, cobertura, playResult, penalizada, quarter, gameClock, segundos,
    marcador_local, marcador_visitante, playDescription, passResult, balon_x, balon_y,
    playDirection, frame_ball_snap, frame_pass_forward, frame_pass_arrived.
    Los frames_* son el frameId del evento (nulo si no existe); los datos de los frames viven
    en `Almacen.frames_eventos`.
    """
    limpias = limpiar_plays(plays)
    limpias = limpias[limpias["passResult"].isin(PASES_LANZADOS)]
    j = limpias.merge(
        games[COLS_GAMES].rename(columns={"week": "semana", "homeTeamAbbr": "local",
                                          "visitorTeamAbbr": "visitante"}),
        on="gameId", how="inner")
    # Solo jugadas con pass_forward en el tracking
    j = j.merge(_frames_clave(frames, "pass_forward", "frame_pass_forward"), on=_LLAVE)
    j = j.merge(_frames_clave(frames, "ball_snap", "frame_ball_snap"), on=_LLAVE, how="left")
    j = j.merge(_frames_clave(frames, "pass_arrived", "frame_pass_arrived"), on=_LLAVE, how="left")
    j = j.merge(_balon_snap(frames), on=_LLAVE, how="left")

    j["equipo"] = j["possessionTeam"]
    j["defensa"] = j["defensiveTeam"]
    j["lado_ofensivo"] = np.where(j["equipo"] == j["local"], "home", "away")
    j["down"] = j["down"].astype(int)
    j["yardsToGo"] = j["yardsToGo"].astype(int)
    j["rango_ytg"] = j["yardsToGo"].map(rango_ytg)
    j["cobertura"] = j["pff_passCoverageType"]
    j["segundos"] = j["gameClock"].map(segundos_reloj)
    j = j.rename(columns={"preSnapHomeScore": "marcador_local",
                          "preSnapVisitorScore": "marcador_visitante"})
    cols = ["gameId", "playId", "semana", "local", "visitante", "equipo", "defensa",
            "lado_ofensivo", "down", "yardsToGo", "rango_ytg", "cobertura", "playResult",
            "penalizada", "quarter", "gameClock", "segundos", "marcador_local",
            "marcador_visitante", "playDescription", "passResult", "balon_x", "balon_y",
            "playDirection", "frame_ball_snap", "frame_pass_forward", "frame_pass_arrived"]
    return j[cols].sort_values(_LLAVE).reset_index(drop=True)


def construir_roster(jugadas: pd.DataFrame, players: pd.DataFrame,
                     pff: pd.DataFrame) -> pd.DataFrame:
    """Roster por jugada: pff_scoutingData unido con players y con la tabla `jugadas`.

    Columnas: gameId, playId, nflId, rol (pff_role en minúsculas), displayName,
    officialPosition, clave (inicial.Apellido sin sufijos). Solo jugadas presentes en
    `jugadas`. El cruce con el equipo (ofensivo/defensivo) lo hace el tracking (`team`).
    """
    r = pff[COLS_PFF].merge(jugadas[_LLAVE], on=_LLAVE)
    r = r.merge(players[COLS_PLAYERS].drop_duplicates("nflId"), on="nflId", how="left")
    r["rol"] = r["pff_role"].astype("string").str.strip().str.lower()
    r["clave"] = r["displayName"].map(
        lambda n: clave_nombre(n) if isinstance(n, str) else "")
    return r.drop(columns=["pff_role"]).reset_index(drop=True)
