"""Forma del contrato: cada respuesta valida contra el response_model de su ruta (tarea 5.9).
Modo mock siempre; datos reales se omiten si falta data/. Requisito 9.6."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from backend.analytics.carga import Estado, lanzar_carga
from backend.api import instalar, router

DATA = Path(__file__).resolve().parent.parent / "data"
MODELOS = {r.path: r.response_model for r in router.routes if isinstance(r, APIRoute)}


def _rutas(gid: int) -> list[tuple[str, str]]:
    q = "down=3&yardsToGo=5"
    return [
        ("/api/resumen", "/api/resumen"),
        ("/api/partidos", "/api/partidos"),
        ("/api/partido/{gameId}/jugada/{n}", f"/api/partido/{gid}/jugada/1"),
        ("/api/partido/{gameId}/acumulado", f"/api/partido/{gid}/acumulado?hasta=3"),
        ("/api/partido/{gameId}/alertas", f"/api/partido/{gid}/alertas?hasta=3"),
        ("/api/recomendacion", f"/api/recomendacion?{q}&zona=media_izquierda&cobertura=Man"),
        ("/api/regret/equipos", "/api/regret/equipos"),
        ("/api/evidencia", f"/api/evidencia?{q}&zona=media_izquierda"),
        ("/api/explicacion", f"/api/explicacion?{q}"),
    ]


def _validar(c: TestClient, gid: int, permitir_404_jugada: bool = False) -> None:
    for plantilla, url in _rutas(gid):
        r = c.get(url)
        if permitir_404_jugada and "/jugada/" in url and r.status_code == 404:
            assert r.json()["codigo"] in ("jugada_no_encontrada", "partido_no_encontrado")
            continue
        assert r.status_code == 200, (url, r.status_code, r.text[:200])
        TypeAdapter(MODELOS[plantilla]).validate_python(r.json())
    r = c.post("/api/chat", json={"gameId": gid, "hasta": 2, "mensaje": "hola"})
    assert r.status_code == 200, r.text[:200]
    TypeAdapter(MODELOS["/api/chat"]).validate_python(r.json())


def test_contrato_mock():
    app = FastAPI()
    instalar(app, mock=True)
    _validar(TestClient(app), 2021090900)


@pytest.fixture(scope="session")
def cliente_real() -> TestClient:
    app = FastAPI()
    instalar(app, mock=True)
    estado = Estado("cargando")
    app.state.estado = estado
    lanzar_carga(app, estado).join(timeout=300)
    assert estado.valor == "listo"
    return TestClient(app)


@pytest.mark.skipif(not (DATA / "games.csv").exists(), reason="falta data/")
def test_contrato_datos_reales(cliente_real):
    gid = cliente_real.get("/api/partidos").json()[0]["gameId"]
    _validar(cliente_real, gid, permitir_404_jugada=True)
