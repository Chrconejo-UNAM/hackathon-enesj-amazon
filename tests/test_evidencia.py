"""Evidencia real (tarea 5.3): evidencia.py y GET /api/evidencia con Almacen sintético.

Requisitos 4.1 y 4.5.
"""
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analytics.carga import Almacen, ServicioReal
from backend.analytics.evidencia import bins_distribucion
from backend.analytics.schemas import Evidencia
from backend.analytics.zonas import ZONAS, rango_ytg
from backend.api import Estado, instalar

SEMILLA = 2021
Q = dict(down=3, yardsToGo=5)


def _jugadas(filas) -> pd.DataFrame:
    """filas: (zona, playResult, cobertura, regret, penalizada, down, yardsToGo)."""
    regs = [dict(gameId=2021090900, playId=i + 1, equipo="TB", semana=1, down=d, yardsToGo=y,
                 rango_ytg=rango_ytg(y), cobertura=c, playResult=float(r), penalizada=p,
                 zona=z, regret=g, sep_elegido=2.0, sep_mas_abierto=3.0)
            for i, (z, r, c, g, p, d, y) in enumerate(filas)]
    return pd.DataFrame(regs)


def _g(zona, n, valor, cob="Man", regret=1.0, pen=False, down=3, ytg=5):
    return [(zona, valor, cob, regret, pen, down, ytg)] * n


def _cliente(jugadas) -> TestClient:
    app = FastAPI()
    instalar(app, mock=True)
    app.state.servicio = ServicioReal(Almacen([], jugadas=jugadas))
    app.state.estado = Estado("listo")
    return TestClient(app)


def _conteos(bins):
    return {b.desde: b.n for b in bins}


def test_bins_bordes_y_ultimo_acumulado():
    b = bins_distribucion([-10, -5, 0, 4.9, 5, 39.9, 40, 41, 80])
    assert len(b) == 11 and b[0].desde == -10 and b[0].hasta == -5
    assert b[-1].desde == 40 and b[-1].hasta is None
    c = _conteos(b)
    assert c[-10] == 1 and c[-5] == 1 and c[0] == 2 and c[5] == 1 and c[35] == 1
    assert c[40] == 3                       # 40 exacto, 41 y 80 caen en el bin acumulado
    assert sum(c.values()) == 9


def test_bins_menor_que_menos_10_va_al_primer_bin():
    assert _conteos(bins_distribucion([-25]))[-10] == 1


def test_forma_y_series():
    j = _jugadas(_g("media_izquierda", 40, 8, "Man", 2.0) + _g("media_izquierda", 35, 4, "Zone", 1.0)
                 + _g("media_izquierda", 5, 6, "Other", 0.5) + _g("corta_centro", 30, 3, "Man", 0.0)
                 + _g("profunda_derecha", 10, 50, pen=True))
    r = _cliente(j).get("/api/evidencia", params={**Q, "zona": "media_izquierda"})
    assert r.status_code == 200
    d = r.json()
    Evidencia.model_validate(d)
    assert set(d) == {"distribucion", "valor_por_zona", "valor_por_cobertura", "regret_por_zona"}
    assert {x["zona"] for x in d["distribucion"]} == {"media_izquierda", "corta_centro"}  # sin penalizadas
    assert all(len(x["bins"]) == 11 for x in d["distribucion"])
    vz = {x["zona"]: x["estimacion"] for x in d["valor_por_zona"]}
    assert vz["media_izquierda"]["n"] == 80 and vz["corta_centro"]["valor"] == 3.0
    cob = {x["cobertura"]: x["estimacion"] for x in d["valor_por_cobertura"]}
    assert [x["cobertura"] for x in d["valor_por_cobertura"]] == ["Man", "Zone", "Otra"]
    assert (cob["Man"]["n"], cob["Zone"]["n"], cob["Otra"]["n"]) == (40, 35, 5)
    assert cob["Man"]["valor"] == 8.0
    rz = {x["zona"]: x["estimacion"] for x in d["regret_por_zona"]}
    assert rz["corta_centro"]["valor"] == 0.0 and rz["media_izquierda"]["n"] == 80


def test_cobertura_sin_zona_usa_todas_las_zonas():
    j = _jugadas(_g("media_izquierda", 10, 8, "Man") + _g("corta_centro", 20, 2, "Man"))
    d = _cliente(j).get("/api/evidencia", params=Q).json()
    assert d["valor_por_cobertura"][0]["estimacion"]["n"] == 30


def test_estado_vacio_http_200():
    j = _jugadas(_g("media_izquierda", 40, 8, down=1))
    r = _cliente(j).get("/api/evidencia", params=Q)
    assert r.status_code == 200
    assert r.json() == {"distribucion": [], "valor_por_zona": [], "valor_por_cobertura": [],
                        "regret_por_zona": []}
    assert _cliente(pd.DataFrame()).get("/api/evidencia", params=Q).json()["distribucion"] == []


def test_parametros_invalidos_422():
    c = _cliente(_jugadas(_g("media_izquierda", 3, 1)))
    for p in ({"down": 0, "yardsToGo": 5}, {"down": 5, "yardsToGo": 5}, {"down": 3, "yardsToGo": 0},
              {**Q, "zona": "xx"}):
        r = c.get("/api/evidencia", params=p)
        assert r.status_code == 422 and r.json()["codigo"] == "parametros_invalidos"


def test_propiedad_bins_suman_n_de_la_zona():
    # Feature: la-jugada-correcta, Property 3: la distribución conserva todas las jugadas
    rng = np.random.default_rng(SEMILLA)
    for _ in range(100):
        filas = []
        for z in ZONAS:
            for v in rng.integers(-30, 90, int(rng.integers(0, 15))):
                filas.append((z, v, "Man", 1.0, False, 3, 5))
        if not filas:
            continue
        d = _cliente(_jugadas(filas)).get("/api/evidencia", params=Q).json()
        vz = {x["zona"]: x["estimacion"]["n"] for x in d["valor_por_zona"]}
        for x in d["distribucion"]:
            assert sum(b["n"] for b in x["bins"]) == vz[x["zona"]]
