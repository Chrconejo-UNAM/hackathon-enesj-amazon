"""Limpieza, tabla `jugadas` y roster (tarea 3.2). Requisitos 1.10, 1.11, 1.12."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.analytics.carga import cargar_almacen
from backend.analytics.jugadas import (
    clave_nombre, construir_jugadas, construir_roster, limpiar_plays, rango_ytg, segundos_reloj,
)

DATA = Path(__file__).resolve().parent.parent / "data"


def _plays(filas):
    base = dict(playDescription="x", quarter=1, down=1, yardsToGo=10, possessionTeam="TB",
                defensiveTeam="DAL", gameClock="13:33", preSnapHomeScore=0,
                preSnapVisitorScore=0, passResult="C", penaltyYards=np.nan, playResult=5,
                absoluteYardlineNumber=40, pff_passCoverageType="Man", gameId=1)
    return pd.DataFrame([{**base, **f} for f in filas])


GAMES = pd.DataFrame({"gameId": [1], "week": [1], "homeTeamAbbr": ["TB"],
                      "visitorTeamAbbr": ["DAL"]})


def _frames(plays_con_pf):
    filas = []
    for pid in plays_con_pf:
        filas.append(dict(gameId=1, playId=pid, nflId=np.nan, frameId=1, team="football",
                          playDirection="right", x=30.0, y=26.0, event="ball_snap"))
        filas.append(dict(gameId=1, playId=pid, nflId=7.0, frameId=20, team="home",
                          playDirection="right", x=40.0, y=20.0, event="pass_forward"))
    return pd.DataFrame(filas)


def test_limpieza_descarta_down0_y_nulos_y_marca_penalizadas():
    p = _plays([dict(playId=1), dict(playId=2, down=0), dict(playId=3, absoluteYardlineNumber=np.nan),
                dict(playId=4, penaltyYards=5.0), dict(playId=5, penaltyYards=0.0)])
    r = limpiar_plays(p).set_index("playId")
    assert sorted(r.index) == [1, 4, 5]
    assert list(r["penalizada"]) == [False, True, False]


def test_jugadas_solo_pases_con_pass_forward():
    p = _plays([dict(playId=1), dict(playId=2, passResult="S"), dict(playId=3),
                dict(playId=4, passResult="IN", yardsToGo=12)])
    j = construir_jugadas(GAMES, p, _frames([1, 2, 4]))
    assert list(j["playId"]) == [1, 4]  # 2 es sack, 3 no tiene tracking
    f = j.set_index("playId")
    assert f.loc[4, "rango_ytg"] == "11+" and f.loc[1, "rango_ytg"] == "7-10"
    assert f.loc[1, "lado_ofensivo"] == "home" and f.loc[1, "semana"] == 1
    assert f.loc[1, "balon_x"] == 30.0 and f.loc[1, "frame_pass_forward"] == 20
    assert pd.isna(f.loc[1, "frame_pass_arrived"])
    assert f.loc[1, "segundos"] == 813.0


def test_roster_une_players_y_pff_insensible_a_mayusculas():
    p = _plays([dict(playId=1)])
    j = construir_jugadas(GAMES, p, _frames([1]))
    pff = pd.DataFrame({"gameId": [1, 1, 1], "playId": [1, 1, 9], "nflId": [7, 8, 7],
                        "pff_role": ["Pass Route", "Pass Block", "Pass Route"]})
    players = pd.DataFrame({"nflId": [7, 8], "officialPosition": ["WR", "OT"],
                            "displayName": ["O.J. Howard", "Mike Smith Jr."]})
    r = construir_roster(j, players, pff)
    assert len(r) == 2  # la jugada 9 no está en jugadas
    assert set(r["rol"]) == {"pass route", "pass block"}
    assert dict(zip(r["nflId"], r["clave"])) == {7: "O.Howard", 8: "M.Smith"}


def test_utilidades():
    assert segundos_reloj("13:33") == 813.0 and np.isnan(segundos_reloj(None))
    assert [rango_ytg(x) for x in (1, 3, 4, 6, 7, 10, 11, 25)] == [
        "1-3", "1-3", "4-6", "4-6", "7-10", "7-10", "11+", "11+"]
    assert clave_nombre("Odell Beckham Jr.") == "O.Beckham"


@pytest.mark.skipif(not (DATA / "tracking").exists(), reason="falta data/")
def test_tabla_jugadas_real():
    a = cargar_almacen(DATA)
    j = a.jugadas
    assert 7400 < len(j) <= 7565
    assert not (j["down"] == 0).any() and j["down"].between(1, 4).all()
    assert not ((j["gameId"] == 2021091904) & (j["playId"] == 3676)).any()
    assert j["penalizada"].any()
    assert set(j["passResult"]) <= {"C", "I", "IN"}
    assert j[["gameId", "playId"]].duplicated().sum() == 0
    assert j["balon_x"].notna().mean() > 0.99
    assert {"pass route", "pass block"} <= set(a.roster["rol"].dropna())
