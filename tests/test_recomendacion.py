"""Recomendación real (tarea 5.2): comparables.py y GET /api/recomendacion con Almacen sintético.

Requisitos 2.1 a 2.4, 2.7, 2.8, 4.2, 4.3. Las propiedades usan numpy.random.default_rng con
semilla fija (100 iteraciones).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analytics.carga import Almacen, ServicioReal
from backend.analytics.comparables import recomendar
from backend.analytics.schemas import SituacionQuery
from backend.analytics.zonas import ZONAS, rango_ytg
from backend.api import Estado, instalar

DATA = Path(__file__).resolve().parent.parent / "data"
SEMILLA = 2021


def _jugadas(filas) -> pd.DataFrame:
    """filas: (zona, playResult, cobertura, penalizada, down, yardsToGo)."""
    regs = []
    for i, (zona, res, cob, pen, down, ytg) in enumerate(filas):
        regs.append(dict(gameId=2021090900 + i // 50, playId=i + 1, equipo="TB", semana=1,
                         down=down, yardsToGo=ytg, rango_ytg=rango_ytg(ytg), cobertura=cob,
                         playResult=float(res), penalizada=pen, zona=zona,
                         sep_elegido=2.0, sep_mas_abierto=3.0))
    return pd.DataFrame(regs)


def _grupo(zona, n, valor, cob="Man", down=3, ytg=5, pen=False):
    return [(zona, valor, cob, pen, down, ytg)] * n


def _cliente(jugadas: pd.DataFrame) -> TestClient:
    app = FastAPI()
    instalar(app, mock=True)
    app.state.servicio = ServicioReal(Almacen([], jugadas=jugadas))
    app.state.estado = Estado("listo")
    return TestClient(app)


Q = dict(down=3, yardsToGo=5)


def test_zona_ganadora_y_forma_del_contrato():
    j = _jugadas(_grupo("media_izquierda", 40, 8) + _grupo("corta_centro", 40, 4)
                 + _grupo("profunda_derecha", 5, 30))        # n < 30: no puede ganar
    r = _cliente(j).get("/api/recomendacion", params=Q)
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"accion", "porque", "estimacion", "comparables"}
    assert d["accion"]["es"] == "Atacar la zona media-izquierda"
    assert d["estimacion"]["n"] == 40 and d["estimacion"]["valor"] == 8.0
    assert d["estimacion"]["confianza"] == "amarillo"
    assert "no es EPA oficial" in d["porque"]["es"] and "not official EPA" in d["porque"]["en"]
    assert "yardas esperadas" in d["porque"]["es"]
    assert {c["zona"] for c in d["comparables"]} == {"media_izquierda"}
    assert {"gameId", "playId", "equipo", "semana", "down", "yardsToGo", "zona", "cobertura",
            "playResult", "sep_elegido", "sep_mas_abierto"} == set(d["comparables"][0])


def test_zona_consultada_distinta_de_la_mejor():
    j = _jugadas(_grupo("media_izquierda", 40, 8) + _grupo("corta_centro", 40, 4))
    d = _cliente(j).get("/api/recomendacion", params={**Q, "zona": "corta_centro"}).json()
    assert d["accion"]["es"] == "La mejor zona es media-izquierda (+4.0 yd frente a corta-centro)"
    assert d["estimacion"]["valor"] == 4.0


def test_desempate_por_zona_alfabetica():
    j = _jugadas(_grupo("media_derecha", 30, 6) + _grupo("corta_izquierda", 30, 6))
    d = _cliente(j).get("/api/recomendacion", params=Q).json()
    assert d["accion"]["es"] == "Atacar la zona corta-izquierda"


def test_sin_zona_con_n_30_usa_la_de_mayor_n_positivo():
    j = _jugadas(_grupo("media_derecha", 10, 5) + _grupo("corta_izquierda", 3, 9))
    d = _cliente(j).get("/api/recomendacion", params=Q).json()
    assert d["accion"]["es"] == "Atacar la zona corta-izquierda"
    assert d["estimacion"]["confianza"] == "rojo" and not d["estimacion"]["concluyente"]
    assert "Aún no es concluyente" in d["porque"]["es"]


def test_estado_vacio_http_200():
    j = _jugadas(_grupo("media_izquierda", 40, 8, down=1))
    r = _cliente(j).get("/api/recomendacion", params=Q)
    assert r.status_code == 200
    d = r.json()
    assert d["estimacion"] == {"valor": 0.0, "ic95": [0.0, 0.0], "n": 0,
                               "concluyente": False, "confianza": "rojo"}
    assert d["comparables"] == []
    assert "No hay muestra" in d["accion"]["es"]


def test_almacen_sin_jugadas_responde_vacio():
    d = _cliente(pd.DataFrame()).get("/api/recomendacion", params=Q).json()
    assert d["estimacion"]["n"] == 0 and d["comparables"] == []


def test_penalizadas_se_excluyen():
    j = _jugadas(_grupo("media_izquierda", 35, 8) + _grupo("media_izquierda", 20, 50, pen=True))
    d = _cliente(j).get("/api/recomendacion", params=Q).json()
    assert d["estimacion"]["n"] == 35 and d["estimacion"]["valor"] == 8.0


def test_cobertura_other_solo_cuenta_sin_filtro():
    j = _jugadas(_grupo("media_izquierda", 30, 8, cob="Man") + _grupo("media_izquierda", 30, 2, cob="Other")
                 + _grupo("media_izquierda", 30, 5, cob="Zone"))
    c = _cliente(j)
    assert c.get("/api/recomendacion", params=Q).json()["estimacion"]["n"] == 90
    man = c.get("/api/recomendacion", params={**Q, "cobertura": "Man"}).json()["estimacion"]
    assert man["n"] == 30 and man["valor"] == 8.0
    assert c.get("/api/recomendacion", params={**Q, "cobertura": "Zone"}).json()["estimacion"]["n"] == 30
    assert c.get("/api/recomendacion", params={**Q, "cobertura": "Other"}).status_code == 422


def test_comparables_max_50_y_orden_por_cercania():
    filas = [("media_izquierda", 5, "Man", False, 3, 4)] * 30 + \
            [("media_izquierda", 5, "Man", False, 3, 6)] * 30 + \
            [("media_izquierda", 5, "Man", False, 3, 5)] * 5
    d = _cliente(_jugadas(filas)).get("/api/recomendacion", params=Q).json()
    comp = d["comparables"]
    assert len(comp) == 50
    assert [c["yardsToGo"] for c in comp[:5]] == [5] * 5
    claves = [(abs(c["yardsToGo"] - 5), c["gameId"], c["playId"]) for c in comp]
    assert claves == sorted(claves)


def test_rango_ytg_mismo_rango_no_misma_distancia():
    j = _jugadas(_grupo("media_izquierda", 30, 8, ytg=4) + _grupo("media_izquierda", 30, 8, ytg=9))
    assert _cliente(j).get("/api/recomendacion", params=Q).json()["estimacion"]["n"] == 30


def test_propiedad_la_zona_recomendada_maximiza_el_valor():
    # Feature: la-jugada-correcta, Property 2: mejor zona entre las de n >= 30
    rng = np.random.default_rng(SEMILLA)
    for _ in range(100):
        filas = []
        for z in ZONAS:
            n = int(rng.integers(0, 60))
            filas += _grupo(z, n, float(rng.integers(-5, 20)))
        if not filas:
            continue
        q = SituacionQuery(**Q)
        rec = recomendar(_jugadas(filas), q)
        por_zona = {z: [f[1] for f in filas if f[0] == z] for z in ZONAS}
        grandes = {z: np.mean(v) for z, v in por_zona.items() if len(v) >= 30}
        chicas = {z: np.mean(v) for z, v in por_zona.items() if len(v) > 0}
        ref = grandes or chicas
        if not ref:
            assert rec.estimacion.n == 0
            continue
        mejor = min(ref, key=lambda z: (-ref[z], z))
        assert {c.zona for c in rec.comparables} == {mejor}


@pytest.mark.skipif(not (DATA / "games.csv").exists(), reason="falta data/")
def test_recomendacion_con_datos_reales():
    from backend.analytics.carga import cargar_almacen
    alm = cargar_almacen()
    j = alm.jugadas
    assert (j["regret"].dropna() >= 0).all()
    assert j["zona"].notna().sum() > 6000
    rec = recomendar(j, SituacionQuery(down=3, yardsToGo=5, cobertura="Man"))
    assert rec.estimacion.n > 0 and len(rec.comparables) <= 50
