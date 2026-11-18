"""Resumen real (tarea 5.4): regret.py y GET /api/resumen con Almacen sintético.

Requisitos 5.7, 14.1 a 14.4.
"""
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analytics.carga import Almacen, ServicioReal
from backend.analytics.regret import regret_por_equipo, regret_por_lado, regret_por_zona
from backend.analytics.schemas import Resumen
from backend.analytics.zonas import ZONAS
from backend.api import Estado, instalar

SEMILLA = 2021


def _jugadas(filas) -> pd.DataFrame:
    """filas: (equipo, zona, regret, origen_receptor)."""
    return pd.DataFrame([dict(gameId=1, playId=i, equipo=e, zona=z, regret=g, origen_receptor=o)
                         for i, (e, z, g, o) in enumerate(filas)])


def _cliente(jugadas) -> TestClient:
    app = FastAPI()
    instalar(app, mock=True)
    app.state.servicio = ServicioReal(Almacen([], jugadas=jugadas))
    app.state.estado = Estado("listo")
    return TestClient(app)


def test_resumen_forma_titulo_y_calidad():
    filas = ([("TB", "media_izquierda", 2.0, "texto")] * 98
             + [("DAL", "corta_centro", 1.0, "pass_arrived")] * 2
             + [("DAL", "corta_centro", None, None)] * 5)       # sin receptor: fuera del regret
    r = _cliente(_jugadas(filas)).get("/api/resumen")
    assert r.status_code == 200
    d = r.json()
    Resumen.model_validate(d)
    e = d["regret_liga"]
    assert e["n"] == 100 and abs(e["valor"] - 1.98) < 1e-9
    assert f"n={e['n']}" in d["titulo"]["es"] and "IC95%" in d["titulo"]["es"]
    assert "pierden 2.0 yd" in d["titulo"]["es"]
    assert "n=100" in d["titulo"]["en"] and "95% CI" in d["titulo"]["en"]
    assert "Contrafactual estimado" in d["linea"]["es"]
    assert d["calidad_datos"]["pct_objetivo_inferido"] == 2.0     # 2 de 100 con receptor


def test_resumen_no_concluyente_y_vacio():
    d = _cliente(_jugadas([("TB", "corta_centro", 1.0, "texto")] * 5)).get("/api/resumen").json()
    assert d["regret_liga"]["concluyente"] is False
    assert "Aún no es concluyente" in d["linea"]["es"] and "Not conclusive yet" in d["linea"]["en"]
    for j in (pd.DataFrame(), _jugadas([("TB", "corta_centro", None, None)])):
        d = _cliente(j).get("/api/resumen").json()
        assert d["regret_liga"]["n"] == 0 and d["regret_liga"]["confianza"] == "rojo"
        assert d["calidad_datos"]["pct_objetivo_inferido"] == 0.0
        assert "Aún no es concluyente" in d["linea"]["es"]


def test_agregaciones_por_equipo_zona_y_lado():
    j = _jugadas([("AAA", "media_izquierda", 3.0, "texto")] * 2
                 + [("BBB", "media_izquierda", 3.0, "texto")]
                 + [("CCC", "corta_derecha", 5.0, "texto")]
                 + [("BBB", "corta_izquierda", 1.0, "texto")])
    eq = regret_por_equipo(j)
    assert [e.equipo for e in eq] == ["CCC", "AAA", "BBB"]        # valor desc, empate por equipo
    assert [e.equipo for e in regret_por_equipo(j, "media_izquierda")] == ["AAA", "BBB"]
    assert regret_por_equipo(j, "profunda_centro") == []
    assert regret_por_zona(j)["media_izquierda"].n == 3
    lados = regret_por_lado(j)
    assert lados["izquierda"].n == 4 and lados["derecha"].n == 1 and "centro" not in lados


def test_propiedad_regret_liga_es_la_media():
    # Feature: la-jugada-correcta, Property 9: regret_liga es la media de todos los regret
    rng = np.random.default_rng(SEMILLA)
    for _ in range(100):
        n = int(rng.integers(1, 60))
        vals = rng.uniform(0, 10, n)
        filas = [(str(rng.choice(["TB", "DAL", "BUF"])), str(rng.choice(ZONAS)), float(v), "texto")
                 for v in vals]
        d = _cliente(_jugadas(filas)).get("/api/resumen").json()
        assert d["regret_liga"]["n"] == n
        assert abs(d["regret_liga"]["valor"] - vals.mean()) < 1e-9
