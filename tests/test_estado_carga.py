"""Pruebas de humo: /health y 503 mientras carga (tarea 1.8). Requisitos 9.2, 9.3."""
from pathlib import Path

import pytest

DIST = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


def test_health_responde_ok_mientras_carga(cliente_cargando):
    r = cliente_cargando.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.parametrize("ruta", ["/api/resumen", "/api/partidos"])
def test_api_responde_503_cargando(cliente_cargando, ruta):
    r = cliente_cargando.get(ruta)
    assert r.status_code == 503
    cuerpo = r.json()
    assert cuerpo["codigo"] == "cargando"
    assert cuerpo["detail"]


@pytest.mark.skipif(not DIST.is_dir(), reason="no existe dashboard/dist")
def test_archivo_estatico_se_sirve_mientras_carga(cliente_cargando):
    r = cliente_cargando.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
