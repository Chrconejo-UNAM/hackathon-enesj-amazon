"""Carga mínima real para /api/partidos (tarea 1.5). Requisitos 1.1, 1.4, 1.9, 6.1."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analytics.carga import Estado, lanzar_carga
from backend.api import instalar

DATA = Path(__file__).resolve().parent.parent / "data"

pytestmark = pytest.mark.skipif(not (DATA / "games.csv").exists(), reason="falta data/")


def test_partidos_reales_122():
    app = FastAPI()
    instalar(app, mock=True)  # rutas y middleware; luego se activa el cargador real
    estado = Estado("cargando")
    app.state.estado = estado
    lanzar_carga(app, estado).join(timeout=60)
    assert estado.valor == "listo"
    r = TestClient(app).get("/api/partidos")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 122
    assert {"gameId", "semana", "local", "visitante", "n_pases"} <= set(datos[0])
    assert all(d["n_pases"] > 0 for d in datos)
    assert sum(d["n_pases"] for d in datos) == 4620 + 2755 + 190


def test_503_mientras_carga():
    app = FastAPI()
    instalar(app, mock=True)
    app.state.estado = Estado("cargando")
    r = TestClient(app).get("/api/partidos")
    assert r.status_code == 503 and r.json()["codigo"] == "cargando"
