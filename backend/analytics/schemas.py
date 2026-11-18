"""Modelos Pydantic del contrato de API (ver design.md, "Data Models")."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Confianza = Literal["verde", "amarillo", "rojo"]
Profundidad = Literal["corta", "media", "profunda"]
Lado = Literal["izquierda", "centro", "derecha"]
Zona = Literal[
    "corta_izquierda", "corta_centro", "corta_derecha",
    "media_izquierda", "media_centro", "media_derecha",
    "profunda_izquierda", "profunda_centro", "profunda_derecha",
]
Cobertura = Literal["Man", "Zone"]
NivelAlerta = Literal["info", "aviso", "critico"]
Fuente = Literal["ia", "plantilla"]


class ErrorApi(Exception):
    """Error controlado que se serializa como {"detail", "codigo"}."""

    def __init__(self, status: int, detail: str, codigo: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.codigo = codigo


class ErrorOut(BaseModel):
    """Respuesta_de_Error."""
    detail: str
    codigo: str


class Texto(BaseModel):
    es: str
    en: str


class Estimacion(BaseModel):
    valor: float
    ic95: tuple[float, float]
    n: int = Field(ge=0)
    concluyente: bool
    confianza: Confianza


class SituacionQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    down: int = Field(ge=1, le=4)
    yardsToGo: int = Field(ge=1, le=99)
    zona: Zona | None = None
    cobertura: Cobertura | None = None


class Comparable(BaseModel):
    gameId: int
    playId: int
    equipo: str
    semana: int
    down: int
    yardsToGo: int
    zona: Zona
    cobertura: str | None
    playResult: float
    sep_elegido: float | None
    sep_mas_abierto: float | None


class RecomendacionOut(BaseModel):
    accion: Texto
    porque: Texto
    estimacion: Estimacion
    comparables: list[Comparable] = Field(max_length=50)


class Jugador(BaseModel):
    nflId: int
    nombre: str
    posicion: str | None


class SeparacionJugador(BaseModel):
    nflId: int
    nombre: str
    separacion: float
    es_elegido: bool
    es_mas_abierto: bool


class JugadaOut(BaseModel):
    n: int
    down: int
    yardsToGo: int
    zona: Zona | None
    marcador: dict[str, int]              # {"local": 7, "visitante": 3} antes del snap
    reloj: dict[str, int | str]           # {"quarter": 2, "tiempo": "13:33"}
    receptor_elegido: Jugador | None
    receptor_mas_abierto: Jugador | None
    separaciones: list[SeparacionJugador]
    regret: float | None = Field(default=None, ge=0)
    resultado: dict                       # {"pase": "C", "yardas": 12, "texto": "..."}


class EstadoPartido(BaseModel):
    gameId: int
    n: int
    n_pases: int
    hay_siguiente: bool
    semana: int
    local: str
    visitante: str


class JugadaRespuesta(BaseModel):
    estado: EstadoPartido
    jugada: JugadaOut


class PartidoItem(BaseModel):
    gameId: int
    semana: int
    local: str
    visitante: str
    n_pases: int = Field(ge=0)


class CalidadDatos(BaseModel):
    pct_objetivo_inferido: float = Field(ge=0, le=100)


class Resumen(BaseModel):
    titulo: Texto
    linea: Texto
    regret_liga: Estimacion
    calidad_datos: CalidadDatos


class AcumuladoZona(BaseModel):
    zona: Zona
    total_yd: float
    estimacion: Estimacion


class AcumuladoLado(BaseModel):
    lado: Lado
    total_yd: float
    estimacion: Estimacion


class Acumulado(BaseModel):
    hasta: int
    n_con_regret: int = Field(ge=0)
    total_yd: float
    estimacion: Estimacion
    por_zona: list[AcumuladoZona]
    por_lado: list[AcumuladoLado]


class Alerta(BaseModel):
    id: str
    nivel: NivelAlerta
    titulo: Texto
    texto: Texto
    estimacion: Estimacion


class EquipoEstimacion(BaseModel):
    equipo: str
    estimacion: Estimacion


class BinDistribucion(BaseModel):
    """Bin de 5 yd [desde, hasta). El último bin (desde=40) tiene hasta=None y acumula 40 o más."""
    desde: int
    hasta: int | None
    n: int = Field(ge=0)


class DistribucionZona(BaseModel):
    zona: Zona
    bins: list[BinDistribucion]


class ValorZona(BaseModel):
    zona: Zona
    estimacion: Estimacion


class ValorCobertura(BaseModel):
    cobertura: Literal["Man", "Zone", "Otra"]
    estimacion: Estimacion


class RegretZona(BaseModel):
    zona: Zona
    estimacion: Estimacion


class Evidencia(BaseModel):
    distribucion: list[DistribucionZona]
    valor_por_zona: list[ValorZona]
    valor_por_cobertura: list[ValorCobertura]
    regret_por_zona: list[RegretZona]


class ExplicacionOut(BaseModel):
    texto: Texto
    fuente: Fuente


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gameId: int
    hasta: int = Field(ge=1)
    mensaje: str = Field(min_length=1, max_length=500)


class ChatOut(BaseModel):
    respuesta: str
    fuente: Fuente
