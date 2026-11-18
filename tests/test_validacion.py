"""Validación de parámetros: 422 parametros_invalidos (tarea 3.8). Modo mock, sin leer data/."""
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import instalar

ZONAS = [f"{p}_{l}" for p in ("corta", "media", "profunda") for l in ("izquierda", "centro", "derecha")]


@pytest.fixture(scope="module")
def c() -> TestClient:
    app = FastAPI()
    instalar(app, mock=True)
    return TestClient(app)


def _assert_422(r):
    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["codigo"] == "parametros_invalidos"
    assert cuerpo["detail"]


@pytest.mark.parametrize("ruta", [
    "/api/recomendacion?down=0&yardsToGo=5",
    "/api/recomendacion?down=5&yardsToGo=5",
    "/api/recomendacion?down=3&yardsToGo=0",
    "/api/recomendacion?down=3&yardsToGo=5&zona=xx",
    "/api/recomendacion?down=3&yardsToGo=5&cobertura=Other",
    "/api/recomendacion?yardsToGo=5",
    "/api/recomendacion?down=abc&yardsToGo=5",
    "/api/evidencia?down=0&yardsToGo=5",
    "/api/evidencia?down=3&yardsToGo=0",
    "/api/evidencia?down=3&yardsToGo=5&zona=xx",
    "/api/explicacion?down=3&yardsToGo=5&cobertura=Other",
    "/api/regret/equipos?zona=xx",
])
def test_parametros_invalidos_dan_422(c, ruta):
    _assert_422(c.get(ruta))


@pytest.mark.parametrize("ruta", [
    "/api/recomendacion?down=1&yardsToGo=1",
    "/api/recomendacion?down=4&yardsToGo=10&zona=media_izquierda&cobertura=Man",
    "/api/recomendacion?down=3&yardsToGo=5&zona=media_izquierda&cobertura=Zone",
    "/api/evidencia?down=3&yardsToGo=5&zona=profunda_centro",
    "/api/regret/equipos?zona=corta_derecha",
])
def test_consulta_valida_da_200(c, ruta):
    assert c.get(ruta).status_code == 200


def test_propiedad_validez_de_consulta(c):
    # Feature: la-jugada-correcta, Property 14 (validación de parámetros)
    rng = np.random.default_rng(2021)
    for _ in range(100):
        down = int(rng.integers(-2, 8))
        ytg = int(rng.integers(-3, 30))
        zona = ZONAS[int(rng.integers(0, 9))] if rng.random() < 0.5 else "zz"
        cob = ["Man", "Zone", "Other"][int(rng.integers(0, 3))]
        r = c.get("/api/recomendacion", params={"down": down, "yardsToGo": ytg, "zona": zona, "cobertura": cob})
        valido = 1 <= down <= 4 and ytg >= 1 and zona in ZONAS and cob in ("Man", "Zone")
        if valido:
            assert r.status_code == 200
        else:
            _assert_422(r)
