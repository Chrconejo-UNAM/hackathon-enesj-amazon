"""La Jugada Correcta. Ejecuta: uvicorn backend.main:app --reload"""
import os
from pathlib import Path


def cargar_env():
    f = Path(__file__).resolve().parent.parent / ".env"
    if f.exists():
        for linea in f.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


cargar_env()  # antes de importar o usar boto3

from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

app = FastAPI(title="La Jugada Correcta")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Rutas /api/... : siempre antes del montaje estático.
# Con LJC_MOCK=1 sirve datos mock y el estado nace en "listo".
from .api import instalar  # noqa: E402

instalar(app)

# Debe ser el ÚLTIMO montaje y solo si existe el build del dashboard.
_DIST = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="dashboard")
