"""Carga de tracking en hilos y frames de eventos (tarea 3.1). Requisitos 1.1, 1.5, 1.6, 1.8, 1.9."""
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI

from backend.analytics.carga import (
    Estado, cargar_almacen, cargar_tracking, filtrar_eventos, lanzar_carga,
)
from backend.analytics.config import COLS_TRACKING
from backend.api import instalar

DATA = Path(__file__).resolve().parent.parent / "data"


def _frames(filas):
    return pd.DataFrame(filas, columns=["gameId", "playId", "event", "frameId"]).assign(
        nflId=1.0, team="home", playDirection="left", x=0.0, y=0.0)[COLS_TRACKING]


def test_filtra_eventos_y_descarta_el_resto():
    f = _frames([(1, 1, "None", 1), (1, 1, "ball_snap", 2), (1, 1, "tackle", 3),
                 (1, 1, "pass_forward", 4), (1, 1, "pass_arrived", 5)])
    assert sorted(filtrar_eventos(f)["event"]) == ["ball_snap", "pass_arrived", "pass_forward"]


def test_autoevent_solo_si_falta_el_principal():
    f = _frames([
        (1, 1, "ball_snap", 1), (1, 1, "autoevent_ballsnap", 1),          # principal existe
        (1, 1, "autoevent_passforward", 9),                                # falta pass_forward
        (1, 2, "autoevent_ballsnap", 1), (1, 2, "pass_forward", 8),        # falta ball_snap
    ])
    r = filtrar_eventos(f)
    assert not r["event"].str.startswith("autoevent").any()
    p1 = r[r.playId == 1]
    assert sorted(p1["event"]) == ["ball_snap", "pass_forward"]
    assert sorted(r[r.playId == 2]["event"]) == ["ball_snap", "pass_forward"]


def test_cargar_tracking_en_hilos_une_archivos(tmp_path):
    (tmp_path / "tracking").mkdir()
    for g in (10, 11):
        df = _frames([(g, 1, "ball_snap", 1), (g, 1, "None", 2)])
        df["extra"] = 5  # columna que usecols debe ignorar
        df.to_csv(tmp_path / "tracking" / f"tracking_{g}.csv", index=False)
    r = cargar_tracking(tmp_path, [10, 11], max_workers=2)
    assert set(r["gameId"]) == {10, 11} and len(r) == 2
    assert list(r.columns) == COLS_TRACKING


def test_falta_archivo_da_estado_error_sin_rutas(tmp_path):
    (tmp_path / "tracking").mkdir()
    pd.DataFrame({"gameId": [1], "week": [1], "homeTeamAbbr": ["A"],
                  "visitorTeamAbbr": ["B"]}).to_csv(tmp_path / "games.csv", index=False)
    pd.DataFrame({"gameId": [1], "playId": [1], "passResult": ["C"]}).to_csv(
        tmp_path / "plays.csv", index=False)
    app = FastAPI()
    instalar(app, mock=True)
    estado = Estado("cargando")
    app.state.estado = estado
    lanzar_carga(app, estado, tmp_path).join(timeout=10)
    assert estado.valor == "error"
    assert str(tmp_path) not in estado.mensaje and "\\" not in estado.mensaje


@pytest.mark.skipif(not (DATA / "tracking").exists(), reason="falta data/")
def test_carga_real_completa():
    t0 = time.time()
    a = cargar_almacen(DATA)
    seg = time.time() - t0
    fr = a.frames_eventos
    assert set(fr["event"]) == {"ball_snap", "pass_forward", "pass_arrived"}
    assert fr["gameId"].nunique() == 122
    # El diseño cuenta 550,804 filas con los autoevent duplicados; sin ellos quedan ~380 mil.
    assert 300_000 < len(fr) < 550_804
    assert seg < 60
    # pass_forward (con sustituto) cubre ~99.96 % de los pases C, I e IN
    plays = pd.read_csv(DATA / "plays.csv", usecols=["gameId", "playId", "passResult"])
    pases = plays[plays.passResult.isin(["C", "I", "IN"])]
    con = fr[fr.event == "pass_forward"][["gameId", "playId"]].drop_duplicates()
    cub = pases.merge(con, on=["gameId", "playId"]).shape[0] / len(pases)
    assert cub > 0.999
