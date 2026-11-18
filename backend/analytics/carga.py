"""Carga real en memoria (tareas 1.5 y 3.1): games, plays y frames de eventos del tracking.

Solo lectura de data/. El tracking se lee en hilos con usecols y se filtra de inmediato
a los eventos de interés; los frames crudos nunca se retienen.
"""
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from .config import COLS_TRACKING, EVENTOS
from .jugadas import (COLS_PFF, COLS_PLAYERS, COLS_PLAYS, construir_jugadas,
                      construir_roster)
from .acumulado import acumulado_hasta
from .comparables import recomendar
from .evidencia import evidencia
from .mock import ServicioMock
from .partido import jugada_respuesta, partidos_con_n_pases
from .regret import regret_por_equipo
from .regret import resumen as resumen_regret
from .schemas import Evidencia, PartidoItem, RecomendacionOut, Resumen, SituacionQuery
from .separacion import enriquecer_jugadas

log = logging.getLogger("ljc")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PASES_LANZADOS = ("C", "I", "IN")


class Estado:
    """Estado de carga: 'cargando', 'listo' o 'error'."""

    def __init__(self, valor: str = "cargando", mensaje: str = ""):
        self.valor = valor
        self.mensaje = mensaje


class Almacen:
    """Datos reales cargados en memoria."""

    def __init__(self, partidos: list[PartidoItem], frames_eventos: pd.DataFrame | None = None,
                 jugadas: pd.DataFrame | None = None, roster: pd.DataFrame | None = None):
        self.partidos = partidos
        # Tabla `jugadas` (un Pase_Lanzado válido por fila) y roster por jugada (tarea 3.2).
        self.jugadas = jugadas if jugadas is not None else pd.DataFrame()
        self.roster = roster if roster is not None else pd.DataFrame()
        # Frames de ball_snap, pass_forward y pass_arrived (todos los jugadores y el balón).
        self.frames_eventos = (frames_eventos if frames_eventos is not None
                               else pd.DataFrame(columns=COLS_TRACKING))


# Evento sustituto -> evento principal
_SUSTITUTOS = {"autoevent_ballsnap": "ball_snap", "autoevent_passforward": "pass_forward"}
_LLAVE = ["gameId", "playId"]


def filtrar_eventos(frames: pd.DataFrame) -> pd.DataFrame:
    """Deja solo los frames de eventos. Por jugada, usa autoevent_* únicamente si falta el
    evento principal, y lo renombra al principal para que el resto del código use un solo nombre."""
    ev = frames[frames["event"].isin(EVENTOS)].copy()
    if ev.empty:
        return ev.reset_index(drop=True)
    idx = pd.MultiIndex.from_frame(ev[_LLAVE])
    for aux, principal in _SUSTITUTOS.items():
        con_principal = pd.MultiIndex.from_frame(
            ev.loc[ev["event"] == principal, _LLAVE].drop_duplicates())
        sobra = ((ev["event"] == aux) & idx.isin(con_principal)).to_numpy()
        ev = ev[~sobra]
        idx = idx[~sobra]
        ev.loc[ev["event"] == aux, "event"] = principal
    return ev.reset_index(drop=True)


def leer_tracking(ruta: Path) -> pd.DataFrame:
    """Lee un tracking_*.csv con usecols y lo reduce a los frames de eventos."""
    return filtrar_eventos(pd.read_csv(ruta, usecols=COLS_TRACKING))


def cargar_tracking(data_dir: Path, game_ids, max_workers: int | None = None) -> pd.DataFrame:
    """Lee el tracking de cada partido en hilos. Si falta un archivo, lanza FileNotFoundError
    (el mensaje no incluye rutas)."""
    rutas = [data_dir / "tracking" / f"tracking_{int(g)}.csv" for g in game_ids]
    faltan = [r for r in rutas if not r.exists()]
    if faltan:
        raise FileNotFoundError(f"Faltan {len(faltan)} archivos de tracking")
    workers = max_workers or min(8, os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        partes = list(pool.map(leer_tracking, rutas))
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=COLS_TRACKING)


def construir_partidos(games: pd.DataFrame, plays: pd.DataFrame) -> list[PartidoItem]:
    """Un PartidoItem por partido; n_pases provisional = jugadas con passResult C, I o IN."""
    pases = plays[plays["passResult"].isin(PASES_LANZADOS)].groupby("gameId").size()
    items = []
    for fila in games.sort_values("gameId").itertuples(index=False):
        items.append(PartidoItem(
            gameId=int(fila.gameId), semana=int(fila.week),
            local=str(fila.homeTeamAbbr), visitante=str(fila.visitorTeamAbbr),
            n_pases=int(pases.get(fila.gameId, 0)),
        ))
    return items


def cargar_almacen(data_dir: Path = DATA_DIR) -> Almacen:
    games = pd.read_csv(data_dir / "games.csv",
                        usecols=["gameId", "week", "homeTeamAbbr", "visitorTeamAbbr"])
    plays = pd.read_csv(data_dir / "plays.csv", usecols=COLS_PLAYS)
    players = pd.read_csv(data_dir / "players.csv", usecols=COLS_PLAYERS)
    pff = pd.read_csv(data_dir / "pffScoutingData.csv", usecols=COLS_PFF)
    frames = cargar_tracking(data_dir, games["gameId"].unique())
    jugadas = construir_jugadas(games, plays, frames)
    roster = construir_roster(jugadas, players, pff)
    jugadas = enriquecer_jugadas(jugadas, roster, frames)
    return Almacen(construir_partidos(games, plays), frames, jugadas, roster)


class ServicioReal(ServicioMock):
    """Reemplaza endpoints por datos reales; el resto sigue en mock hasta su tarea."""

    def __init__(self, almacen: Almacen):
        self.almacen = almacen

    def partidos(self) -> list[PartidoItem]:
        return partidos_con_n_pases(self.almacen.partidos, self.almacen.jugadas)

    def jugada(self, game_id: int, n: int):
        return jugada_respuesta(self.almacen, game_id, n)

    def recomendacion(self, q: SituacionQuery) -> RecomendacionOut:
        return recomendar(self.almacen.jugadas, q)

    def evidencia(self, down: int, yards_to_go: int, zona: str | None) -> Evidencia:
        return evidencia(self.almacen.jugadas, down, yards_to_go, zona)

    def resumen(self) -> Resumen:
        return resumen_regret(self.almacen.jugadas)

    def acumulado(self, game_id: int, hasta: int | None):
        return acumulado_hasta(self.almacen, game_id, hasta)

    def regret_equipos(self, zona: str | None):
        return regret_por_equipo(self.almacen.jugadas, zona)

    def alertas(self, game_id: int, hasta: int | None):
        from .alertas import alertas_partido
        return alertas_partido(self.almacen, game_id, hasta)


def lanzar_carga(app, estado: Estado, data_dir: Path = DATA_DIR) -> threading.Thread:
    """Carga en un hilo de fondo. Actualiza `estado` y, al terminar, `app.state.servicio`."""

    def _tarea():
        try:
            almacen = cargar_almacen(data_dir)
            app.state.servicio = ServicioReal(almacen)
            estado.valor = "listo"
        except Exception as exc:  # mensaje sin rutas absolutas ni credenciales
            log.error("Fallo la carga de datos (%s)", type(exc).__name__)
            estado.mensaje = "No se pudieron cargar los datos"
            estado.valor = "error"

    hilo = threading.Thread(target=_tarea, name="carga-datos", daemon=True)
    hilo.start()
    return hilo
