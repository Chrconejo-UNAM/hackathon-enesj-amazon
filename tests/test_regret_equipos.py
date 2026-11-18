"""Tarea 7.3: GET /api/regret/equipos?zona= con Almacen sintético. Valida: Requisitos 5.8, 5.9, 5.10."""
import os

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analytics.carga import Almacen, ServicioReal
from backend.api import instalar


def _servicio():
    jugadas = pd.DataFrame({
        "equipo": ["A", "A", "B", "B", "C", "D"],
        "zona": ["corta_centro", "media_izquierda", "corta_centro", "corta_centro",
                 "media_izquierda", "corta_centro"],
        "regret": [1.0, 3.0, 5.0, 7.0, 2.0, float("nan")],
    })
    return ServicioReal(Almacen([], jugadas=jugadas))


def test_orden_descendente_y_sin_regret_fuera():
    r = _servicio().regret_equipos(None)
    assert [e.equipo for e in r] == ["B", "A", "C"]  # D sin regret no aparece
    assert [e.estimacion.n for e in r] == [2, 2, 1]


def test_filtro_zona_excluye_equipos_sin_jugadas():
    r = _servicio().regret_equipos("media_izquierda")
    assert [e.equipo for e in r] == ["A", "C"]
    assert r[0].estimacion.valor == 3.0


def test_endpoint_contrato_y_422():
    os.environ.pop("LJC_MOCK_CARGANDO", None)
    app = FastAPI()
    instalar(app, mock=True)  # estado "listo", sin lanzar la carga real
    app.state.servicio = _servicio()
    c = TestClient(app)
    ok = c.get("/api/regret/equipos", params={"zona": "corta_centro"})
    assert ok.status_code == 200
    cuerpo = ok.json()
    assert [e["equipo"] for e in cuerpo] == ["B", "A"]
    assert "estimacion" in cuerpo[0]
    mal = c.get("/api/regret/equipos", params={"zona": "xx"})
    assert mal.status_code == 422
    assert mal.json()["codigo"] == "parametros_invalidos"
