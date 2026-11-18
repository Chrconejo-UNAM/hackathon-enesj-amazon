"""Tarea 7.5: corte temporal, 404 y orden del ranking vía HTTP (Almacen sintético)."""
import os

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analytics.carga import Almacen, ServicioReal
from backend.analytics.schemas import PartidoItem
from backend.api import instalar

N = 30


def _jugadas(alterar_desde=None):
    filas = []
    for i in range(N):
        post = alterar_desde is not None and i >= alterar_desde
        filas.append(dict(gameId=1, playId=i + 1, quarter=1, segundos=900.0 - i,
                          zona="media_centro" if i % 2 else "corta_izquierda",
                          regret=(9.0 if post else float(i % 4)),
                          equipo="A" if i % 3 else "B", gameClock="10:00", down=1,
                          yardsToGo=10, marcador_local=0, marcador_visitante=3,
                          passResult="C", playResult=5, playDescription="x"))
    return pd.DataFrame(filas)


def _cliente(jugadas):
    os.environ.pop("LJC_MOCK_CARGANDO", None)
    app = FastAPI()
    instalar(app, mock=True)
    p = [PartidoItem(gameId=1, semana=1, local="A", visitante="B", n_pases=N)]
    app.state.servicio = ServicioReal(Almacen(p, None, jugadas))
    return TestClient(app)


def test_corte_temporal_no_depende_de_jugadas_posteriores():
    n = 15
    a, b = _cliente(_jugadas()), _cliente(_jugadas(alterar_desde=n))
    for ruta in (f"/api/partido/1/jugada/{n}", f"/api/partido/1/acumulado?hasta={n}",
                 f"/api/partido/1/alertas?hasta={n}"):
        ra, rb = a.get(ruta), b.get(ruta)
        assert ra.status_code == rb.status_code == 200, (ruta, ra.text, rb.text)
        assert ra.json() == rb.json(), ruta


def test_404_con_codigo():
    c = _cliente(_jugadas())
    for ruta in ("/api/partido/99/jugada/1", "/api/partido/1/jugada/0",
                 f"/api/partido/1/jugada/{N + 1}", "/api/partido/99/acumulado",
                 f"/api/partido/1/acumulado?hasta={N + 1}", "/api/partido/99/alertas"):
        r = c.get(ruta)
        assert r.status_code == 404, (ruta, r.status_code, r.text)
        body = r.json()
        assert "detail" in body and "codigo" in body, ruta


def test_ranking_descendente():
    r = _cliente(_jugadas()).get("/api/regret/equipos")
    assert r.status_code == 200
    vals = [e["estimacion"]["valor"] for e in r.json()]
    assert len(vals) >= 2 and vals == sorted(vals, reverse=True)
