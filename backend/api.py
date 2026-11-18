"""Rutas /api/..., manejadores de error y middleware de estado de carga."""
import logging
import os
from typing import Annotated

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .analytics.carga import Estado, lanzar_carga  # Estado se reexporta desde aquí
from .analytics.mock import ServicioMock
from .analytics.schemas import (
    Acumulado, Alerta, ChatIn, ChatOut, EquipoEstimacion, ErrorApi, Evidencia,
    ExplicacionOut, JugadaRespuesta, PartidoItem, RecomendacionOut, Resumen,
    SituacionQuery, Zona,
)

log = logging.getLogger("ljc")

Down = Annotated[int, Query(ge=1, le=4)]
Ytg = Annotated[int, Query(ge=1, le=99)]
ZonaQ = Annotated[Zona | None, Query()]
CoberturaQ = Annotated[str | None, Query(pattern="^(Man|Zone)$")]
HastaQ = Annotated[int | None, Query()]


def _error(status: int, detail: str, codigo: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail, "codigo": codigo})


def _servicio(request: Request):
    return request.app.state.servicio


router = APIRouter(prefix="/api")


@router.get("/resumen", response_model=Resumen)
def resumen(request: Request):
    return _servicio(request).resumen()


@router.get("/partidos", response_model=list[PartidoItem])
def partidos(request: Request):
    return _servicio(request).partidos()


@router.get("/partido/{gameId}/jugada/{n}", response_model=JugadaRespuesta)
def jugada(request: Request, gameId: int, n: int):
    return _servicio(request).jugada(gameId, n)


@router.get("/partido/{gameId}/acumulado", response_model=Acumulado)
def acumulado(request: Request, gameId: int, hasta: HastaQ = None):
    return _servicio(request).acumulado(gameId, hasta)


@router.get("/partido/{gameId}/alertas", response_model=list[Alerta])
def alertas(request: Request, gameId: int, hasta: HastaQ = None):
    return _servicio(request).alertas(gameId, hasta)


@router.get("/recomendacion", response_model=RecomendacionOut)
def recomendacion(request: Request, down: Down, yardsToGo: Ytg,
                  zona: ZonaQ = None, cobertura: CoberturaQ = None):
    q = SituacionQuery(down=down, yardsToGo=yardsToGo, zona=zona, cobertura=cobertura)
    return _servicio(request).recomendacion(q)


@router.get("/regret/equipos", response_model=list[EquipoEstimacion])
def regret_equipos(request: Request, zona: ZonaQ = None):
    return _servicio(request).regret_equipos(zona)


@router.get("/evidencia", response_model=Evidencia)
def evidencia(request: Request, down: Down, yardsToGo: Ytg, zona: ZonaQ = None):
    return _servicio(request).evidencia(down, yardsToGo, zona)


@router.get("/explicacion", response_model=ExplicacionOut)
def explicacion(request: Request, down: Down, yardsToGo: Ytg,
                zona: ZonaQ = None, cobertura: CoberturaQ = None):
    q = SituacionQuery(down=down, yardsToGo=yardsToGo, zona=zona, cobertura=cobertura)
    return _servicio(request).explicacion(q)


@router.post("/chat", response_model=ChatOut)
def chat(request: Request, cuerpo: ChatIn):
    return _servicio(request).chat(cuerpo.gameId, cuerpo.hasta, cuerpo.mensaje)


def instalar(app: FastAPI, mock: bool | None = None) -> None:
    """Registra rutas, manejadores y middleware. Llamar ANTES de montar StaticFiles.

    Con mock (LJC_MOCK=1) no se lanza el cargador y el estado nace en 'listo'.
    """
    if mock is None:
        mock = os.environ.get("LJC_MOCK") == "1"
    if mock:
        cargando = os.environ.get("LJC_MOCK_CARGANDO") == "1"
        app.state.estado = Estado("cargando" if cargando else "listo")
        app.state.servicio = ServicioMock()
    else:
        # Servicio mock hasta que el hilo de fondo cargue los datos reales (tarea 1.5).
        estado = Estado("cargando")
        app.state.estado = estado
        app.state.servicio = ServicioMock()
        lanzar_carga(app, estado)

    @app.middleware("http")
    async def estado_de_carga(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            est = request.app.state.estado
            if est.valor == "cargando":
                return _error(503, "Cargando datos, intenta de nuevo en unos segundos", "cargando")
            if est.valor == "error":
                return _error(503, est.mensaje or "Error al cargar los datos", "error_de_carga")
        return await call_next(request)

    @app.exception_handler(ErrorApi)
    async def _h_error_api(request: Request, exc: ErrorApi):
        return _error(exc.status, exc.detail, exc.codigo)

    @app.exception_handler(RequestValidationError)
    async def _h_validacion(request: Request, exc: RequestValidationError):
        partes = []
        for e in exc.errors():
            campo = ".".join(str(x) for x in e.get("loc", ()) if x not in ("query", "path", "body"))
            partes.append(f"{campo or 'parámetro'}: {str(e.get('msg', 'valor inválido'))[:120]}")
        return _error(422, "; ".join(partes) or "Parámetros inválidos", "parametros_invalidos")

    @app.exception_handler(StarletteHTTPException)
    async def _h_http(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api/"):
            codigo = "no_encontrado" if exc.status_code == 404 else "error_http"
            return _error(exc.status_code, str(exc.detail), codigo)
        return await http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _h_inesperado(request: Request, exc: Exception):
        log.error("Error no controlado en %s (%s)", request.url.path, type(exc).__name__)
        return _error(500, "Error interno", "error_interno")

    app.include_router(router)
