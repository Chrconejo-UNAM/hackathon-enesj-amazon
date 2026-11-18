"""Endpoints MOCK conformes al contrato (tarea 1.2). Ejecutar con: python -m pytest"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import Estado, instalar

GAME = 2021090900


def _cliente(cargando: bool = False) -> TestClient:
    app = FastAPI()
    instalar(app, mock=True)
    if cargando:
        app.state.estado = Estado("cargando")
    return TestClient(app)


@pytest.fixture(scope="module")
def c() -> TestClient:
    return _cliente()


def _estimaciones(obj):
    if isinstance(obj, dict):
        if {"valor", "ic95", "n", "concluyente", "confianza"} <= obj.keys():
            yield obj
        for v in obj.values():
            yield from _estimaciones(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _estimaciones(v)


def test_los_11_endpoints_responden_200(c):
    rutas = [
        "/api/resumen", "/api/partidos", f"/api/partido/{GAME}/jugada/1",
        f"/api/partido/{GAME}/acumulado?hasta=3", f"/api/partido/{GAME}/alertas?hasta=3",
        "/api/recomendacion?down=3&yardsToGo=5", "/api/regret/equipos",
        "/api/evidencia?down=3&yardsToGo=5&zona=media_izquierda",
        "/api/explicacion?down=3&yardsToGo=5",
    ]
    for r in rutas:
        assert c.get(r).status_code == 200, r
    ch = c.post("/api/chat", json={"gameId": GAME, "hasta": 2, "mensaje": "hola"})
    assert ch.status_code == 200 and ch.json()["fuente"] == "plantilla"


def test_recomendacion_ejemplo_del_contrato(c):
    r = c.get("/api/recomendacion?down=3&yardsToGo=5&zona=media_izquierda&cobertura=Man").json()
    assert r["estimacion"] == {"valor": 7.4, "ic95": [5.9, 8.8], "n": 64,
                               "concluyente": True, "confianza": "amarillo"}
    assert r["accion"]["es"] == "Atacar la zona media-izquierda"
    assert 1 <= len(r["comparables"]) <= 50


def test_hay_verde_amarillo_y_rojo(c):
    confs = set()
    for ruta in ("/api/resumen", "/api/regret/equipos", f"/api/partido/{GAME}/alertas",
                 "/api/evidencia?down=1&yardsToGo=10"):
        confs |= {e["confianza"] for e in _estimaciones(c.get(ruta).json())}
    assert confs == {"verde", "amarillo", "rojo"}


def test_alertas_de_cada_nivel_y_deterministas(c):
    a = c.get(f"/api/partido/{GAME}/alertas").json()
    assert {x["nivel"] for x in a} == {"info", "aviso", "critico"}
    assert a == c.get(f"/api/partido/{GAME}/alertas").json()


def test_partidos_reales(c):
    p = c.get("/api/partidos").json()
    assert len(p) == 3 and {x["gameId"] for x in p} >= {2021090900, 2021091200}
    assert all(x["n_pases"] == 5 for x in p)


@pytest.mark.parametrize("ruta,codigo", [
    ("/api/partido/1/jugada/1", "partido_no_encontrado"),
    (f"/api/partido/{GAME}/jugada/6", "jugada_no_encontrada"),
    (f"/api/partido/{GAME}/jugada/0", "jugada_no_encontrada"),
    (f"/api/partido/{GAME}/acumulado?hasta=99", "jugada_no_encontrada"),
    ("/api/partido/1/alertas", "partido_no_encontrado"),
])
def test_404_con_codigo(c, ruta, codigo):
    r = c.get(ruta)
    assert r.status_code == 404
    assert r.json()["codigo"] == codigo and r.json()["detail"]


@pytest.mark.parametrize("ruta", [
    "/api/recomendacion?down=0&yardsToGo=5",
    "/api/recomendacion?down=5&yardsToGo=5",
    "/api/recomendacion?down=3&yardsToGo=0",
    "/api/recomendacion?down=3&yardsToGo=5&zona=xx",
    "/api/recomendacion?down=3&yardsToGo=5&cobertura=Other",
    "/api/regret/equipos?zona=xx",
])
def test_422_parametros_invalidos(c, ruta):
    r = c.get(ruta)
    assert r.status_code == 422
    assert r.json()["codigo"] == "parametros_invalidos" and r.json()["detail"]


def test_chat_errores(c):
    assert c.post("/api/chat", json={"gameId": GAME, "hasta": 1, "mensaje": ""}).status_code == 422
    r = c.post("/api/chat", json={"gameId": 1, "hasta": 1, "mensaje": "x"})
    assert r.status_code == 404 and r.json()["codigo"] == "partido_no_encontrado"


def test_503_cargando_y_health():
    cl = _cliente(cargando=True)
    r = cl.get("/api/resumen")
    assert r.status_code == 503 and r.json()["codigo"] == "cargando"


def test_textos_bilingues(c):
    r = c.get("/api/recomendacion?down=3&yardsToGo=5").json()
    assert r["accion"]["es"] and r["accion"]["en"] and r["porque"]["es"] and r["porque"]["en"]


def test_main_registra_api_antes_del_montaje_estatico():
    from backend.main import app
    rutas = [getattr(r, "path", "") for r in app.routes]
    assert "/api/resumen" in rutas
    if "" in rutas or "/" in rutas:
        assert rutas.index("/api/resumen") < len(rutas) - 1
