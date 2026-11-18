"""Fixtures compartidas. Ejecutar con: python -m pytest"""
import pytest
from fastapi.testclient import TestClient

from backend.api import Estado


@pytest.fixture
def cliente_cargando():
    """Cliente (httpx) sobre la app real con el Estado_de_Carga forzado a 'cargando'."""
    from backend.main import app

    previo = getattr(app.state, "estado", None)
    app.state.estado = Estado("cargando")
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.state.estado = previo
