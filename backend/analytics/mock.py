"""Datos MOCK deterministas con la forma exacta del contrato (LJC_MOCK=1).

Son la única fuente de verdad compartida con el frontend (ver tasks.md,
"Datos mock compartidos"). Sin aleatoriedad: mismos datos en cada llamada.
"""
import math

from .schemas import (
    Acumulado, AcumuladoLado, AcumuladoZona, Alerta, BinDistribucion, CalidadDatos,
    ChatOut, Comparable, DistribucionZona, EquipoEstimacion, ErrorApi, Estimacion,
    EstadoPartido, Evidencia, ExplicacionOut, JugadaOut, JugadaRespuesta, Jugador,
    PartidoItem, RecomendacionOut, RegretZona, Resumen, SeparacionJugador,
    SituacionQuery, Texto, ValorCobertura, ValorZona,
)

ZONAS = [
    "corta_izquierda", "corta_centro", "corta_derecha",
    "media_izquierda", "media_centro", "media_derecha",
    "profunda_izquierda", "profunda_centro", "profunda_derecha",
]

_PROF = {"corta": ("corta", "short"), "media": ("media", "mid"), "profunda": ("profunda", "deep")}
_LADO = {"izquierda": ("izquierda", "left"), "centro": ("centro", "center"), "derecha": ("derecha", "right")}


def _etiqueta(zona: str) -> Texto:
    p, l = zona.split("_")
    return Texto(es=f"{_PROF[p][0]}-{_LADO[l][0]}", en=f"{_PROF[p][1]}-{_LADO[l][1]}")


def _est(valor: float, lo: float, hi: float, n: int) -> Estimacion:
    """Estimación con el semáforo del contrato (n<30 rojo; n>=100 y ancho<1.0 verde)."""
    if n < 30:
        conf = "rojo"
    elif n >= 100 and (hi - lo) < 1.0:
        conf = "verde"
    else:
        conf = "amarillo"
    return Estimacion(valor=round(valor, 2), ic95=(round(lo, 2), round(hi, 2)), n=n,
                      concluyente=conf != "rojo", confianza=conf)


# ---------------------------------------------------------------- partidos
# (gameId, semana, local, visitante, jugadores [(nflId, nombre, posicion)])
_PARTIDOS = {
    2021090900: (1, "TB", "DAL", [(1001, "Chris Godwin", "WR"), (1002, "Mike Evans", "WR"), (1003, "Rob Gronkowski", "TE")]),
    2021091200: (1, "ATL", "PHI", [(2001, "Calvin Ridley", "WR"), (2002, "Kyle Pitts", "TE"), (2003, "Cordarrelle Patterson", "RB")]),
    2021091201: (1, "BUF", "PIT", [(3001, "Stefon Diggs", "WR"), (3002, "Emmanuel Sanders", "WR"), (3003, "Dawson Knox", "TE")]),
}

# (down, yardsToGo, zona, quarter, tiempo, marcador local, visitante,
#  separación del elegido, regret, pase, yardas, índice elegido, texto)
_JUGADAS = [
    (1, 10, "corta_centro", 1, "14:21", 0, 0, 3.1, 0.0, "C", 6, 0, "pass short middle complete"),
    (2, 4, "media_izquierda", 1, "11:02", 0, 0, 2.2, 1.9, "C", 12, 0, "pass short left complete"),
    (3, 5, "media_izquierda", 2, "08:47", 3, 0, 1.4, 3.3, "I", 0, 1, "pass deep left incomplete"),
    (1, 10, "profunda_derecha", 3, "10:15", 3, 7, 2.6, 0.7, "C", 27, 2, "pass deep right complete"),
    (4, 2, "corta_derecha", 4, "03:30", 10, 7, 2.9, 2.4, "I", 0, 1, "pass short right incomplete"),
]

N_PASES = len(_JUGADAS)


def _jugada(game_id: int, n: int) -> JugadaOut:
    sem, _, _, jug = _PARTIDOS[game_id]
    d, ytg, zona, q, t, ml, mv, sep, reg, pase, yd, idx, texto = _JUGADAS[n - 1]
    jugadores = [Jugador(nflId=j[0], nombre=j[1], posicion=j[2]) for j in jug]
    elegido = jugadores[idx]
    # Si el regret es 0 el elegido es el más abierto; si no, es otro receptor.
    abierto = elegido if reg == 0 else jugadores[(idx + 1) % 3]
    seps = {}
    for j in jugadores:
        if j.nflId == elegido.nflId:
            seps[j.nflId] = sep
        elif j.nflId == abierto.nflId:
            seps[j.nflId] = round(sep + reg, 2)
        else:
            seps[j.nflId] = max(0.0, round(sep - 0.5, 2))
    return JugadaOut(
        n=n, down=d, yardsToGo=ytg, zona=zona,
        marcador={"local": ml, "visitante": mv},
        reloj={"quarter": q, "tiempo": t},
        receptor_elegido=elegido, receptor_mas_abierto=abierto,
        separaciones=[SeparacionJugador(
            nflId=j.nflId, nombre=j.nombre, separacion=seps[j.nflId],
            es_elegido=j.nflId == elegido.nflId, es_mas_abierto=j.nflId == abierto.nflId)
            for j in jugadores],
        regret=reg,
        resultado={"pase": pase, "yardas": yd, "texto": texto},
    )


def _partido(game_id: int):
    if game_id not in _PARTIDOS:
        raise ErrorApi(404, "Partido no encontrado", "partido_no_encontrado")
    return _PARTIDOS[game_id]


def _validar_n(n: int) -> None:
    if n < 1 or n > N_PASES:
        raise ErrorApi(404, "Jugada no encontrada", "jugada_no_encontrada")


# ---------------------------------------------------------------- recomendación
# zona -> (valor, ic_lo, ic_hi, n). La mejor zona con n>=30 es media_izquierda.
_VALOR_ZONA = {
    "corta_izquierda": (4.6, 3.5, 5.7, 112),
    "corta_centro": (5.2, 4.9, 5.5, 400),          # verde
    "corta_derecha": (4.4, 3.3, 5.5, 98),
    "media_izquierda": (7.4, 5.9, 8.8, 64),        # amarillo
    "media_centro": (6.8, 5.0, 8.5, 58),
    "media_derecha": (6.1, 4.2, 8.0, 41),
    "profunda_izquierda": (6.5, 1.9, 11.1, 31),
    "profunda_centro": (6.9, 2.8, 11.0, 33),
    "profunda_derecha": (9.5, 0.0, 19.0, 12),      # rojo
}


def _est_zona(zona: str) -> Estimacion:
    return _est(*_VALOR_ZONA[zona])


def _mejor_zona() -> str:
    cand = {z: v for z, v in _VALOR_ZONA.items() if v[3] >= 30}
    return max(sorted(cand), key=lambda z: cand[z][0])


def _fmt(e: Estimacion) -> tuple[str, str, str, int]:
    return f"{e.valor:.1f}", f"{e.ic95[0]:.1f}", f"{e.ic95[1]:.1f}", e.n


class ServicioMock:
    """Implementa el protocolo de servicio usado por api.py."""

    # -- resumen y partidos
    def resumen(self) -> Resumen:
        return Resumen(
            titulo=Texto(
                es="Los quarterbacks pierden 1.3 yd de separación por pase (IC95% 1.2 a 1.4, n=2340)",
                en="Quarterbacks lose 1.3 yd of separation per pass (95% CI 1.2 to 1.4, n=2340)"),
            linea=Texto(
                es="Contrafactual estimado: lanzar al receptor más abierto en lugar del elegido.",
                en="Estimated counterfactual: throwing to the most open receiver instead of the chosen one."),
            regret_liga=_est(1.3, 1.2, 1.4, 2340),
            calidad_datos=CalidadDatos(pct_objetivo_inferido=0.3),
        )

    def partidos(self) -> list[PartidoItem]:
        return [PartidoItem(gameId=g, semana=v[0], local=v[1], visitante=v[2], n_pases=N_PASES)
                for g, v in sorted(_PARTIDOS.items())]

    # -- partido
    def jugada(self, game_id: int, n: int) -> JugadaRespuesta:
        sem, local, visitante, _ = _partido(game_id)
        _validar_n(n)
        return JugadaRespuesta(
            estado=EstadoPartido(gameId=game_id, n=n, n_pases=N_PASES, hay_siguiente=n < N_PASES,
                                 semana=sem, local=local, visitante=visitante),
            jugada=_jugada(game_id, n))

    def _hasta(self, game_id: int, hasta: int | None) -> int:
        _partido(game_id)
        h = N_PASES if hasta is None else hasta
        _validar_n(h)
        return h

    @staticmethod
    def _est_regret(valores: list[float]) -> Estimacion:
        n = len(valores)
        if n == 0:
            return _est(0.0, 0.0, 0.0, 0)
        m = sum(valores) / n
        mitad = 1.96 * 0.9 / math.sqrt(n)
        return _est(m, max(0.0, m - mitad), m + mitad, n)

    def acumulado(self, game_id: int, hasta: int | None) -> Acumulado:
        h = self._hasta(game_id, hasta)
        datos = [(j[2], j[8]) for j in _JUGADAS[:h]]
        regrets = [r for _, r in datos]
        por_zona, por_lado = [], []
        for z in ZONAS:
            r = [x for zz, x in datos if zz == z]
            if r:
                por_zona.append(AcumuladoZona(zona=z, total_yd=round(sum(r), 2), estimacion=self._est_regret(r)))
        for lado in ("izquierda", "centro", "derecha"):
            r = [x for zz, x in datos if zz.split("_")[1] == lado]
            if r:
                por_lado.append(AcumuladoLado(lado=lado, total_yd=round(sum(r), 2), estimacion=self._est_regret(r)))
        return Acumulado(hasta=h, n_con_regret=len(regrets), total_yd=round(sum(regrets), 2),
                         estimacion=self._est_regret(regrets), por_zona=por_zona, por_lado=por_lado)

    def alertas(self, game_id: int, hasta: int | None) -> list[Alerta]:
        self._hasta(game_id, hasta)
        return [
            Alerta(id="regret_alto", nivel="critico",
                   titulo=Texto(es="Regret alto", en="High regret"),
                   texto=Texto(es="El regret promedio acumulado supera 3.0 yd.",
                               en="Cumulative average regret exceeds 3.0 yd."),
                   estimacion=_est(3.2, 2.9, 3.6, 120)),
            Alerta(id="zona_ciega:media_izquierda", nivel="aviso",
                   titulo=Texto(es="Zona ciega: media-izquierda", en="Blind zone: mid-left"),
                   texto=Texto(es="El regret en media-izquierda supera 2.5 yd.",
                               en="Regret in mid-left exceeds 2.5 yd."),
                   estimacion=_est(2.7, 1.8, 3.6, 45)),
            Alerta(id="racha", nivel="info",
                   titulo=Texto(es="Racha de pases", en="Streak of passes"),
                   texto=Texto(es="Tres jugadas seguidas con regret alto. Aún no es concluyente.",
                               en="Three consecutive plays with high regret. Not conclusive yet."),
                   estimacion=_est(3.4, 3.0, 3.8, 3)),
        ]

    # -- recomendación
    def recomendacion(self, q: SituacionQuery) -> RecomendacionOut:
        mejor = _mejor_zona()
        objetivo = q.zona or mejor
        est = _est_zona(objetivo)
        v, lo, hi, n = _fmt(est)
        es_val = f"Valor esperado {v} yd (IC95% {lo} a {hi}, n={n}). Valor en yardas esperadas, no es EPA oficial."
        en_val = f"Expected value {v} yd (95% CI {lo} to {hi}, n={n}). Value in expected yards, not official EPA."
        if not est.concluyente:
            es_val += " Aún no es concluyente."
            en_val += " Not conclusive yet."
        if objetivo == mejor:
            accion = Texto(es=f"Atacar la zona {_etiqueta(mejor).es}", en=f"Attack the {_etiqueta(mejor).en} zone")
        else:
            d = _VALOR_ZONA[mejor][0] - est.valor
            m, o = _etiqueta(mejor), _etiqueta(objetivo)
            accion = Texto(es=f"La mejor zona es {m.es} (+{d:.1f} yd frente a {o.es})",
                           en=f"The best zone is {m.en} (+{d:.1f} yd vs {o.en})")
        cob = q.cobertura or "Man"
        otro = q.yardsToGo + 1 if q.yardsToGo < 99 else q.yardsToGo - 1
        comparables = [
            Comparable(gameId=2021090900, playId=1234, equipo="TB", semana=1, down=q.down,
                       yardsToGo=q.yardsToGo, zona=objetivo, cobertura=cob, playResult=9,
                       sep_elegido=2.8, sep_mas_abierto=4.1),
            Comparable(gameId=2021091200, playId=2210, equipo="ATL", semana=1, down=q.down,
                       yardsToGo=otro, zona=objetivo, cobertura=cob, playResult=14,
                       sep_elegido=3.5, sep_mas_abierto=3.5),
            Comparable(gameId=2021091201, playId=875, equipo="BUF", semana=1, down=q.down,
                       yardsToGo=otro, zona=objetivo, cobertura=cob, playResult=-2,
                       sep_elegido=1.2, sep_mas_abierto=3.9),
        ]
        return RecomendacionOut(accion=accion, porque=Texto(es=es_val, en=en_val),
                                estimacion=est, comparables=comparables)

    def regret_equipos(self, zona: str | None) -> list[EquipoEstimacion]:
        base = [("TB", 2.1, 1.4, 2.8, 64), ("DAL", 1.8, 1.3, 2.3, 58),
                ("BUF", 1.6, 1.3, 1.9, 120), ("PIT", 1.1, 0.4, 1.8, 12)]
        desp = 0.05 * ZONAS.index(zona) if zona else 0.0
        if zona and zona.startswith("profunda"):
            base = [b for b in base if b[0] != "PIT"]   # sin jugadas en esa zona
        filas = [(e, _est(v + desp, lo + desp, hi + desp, n)) for e, v, lo, hi, n in base]
        filas.sort(key=lambda t: (-t[1].valor, t[0]))
        return [EquipoEstimacion(equipo=e, estimacion=est) for e, est in filas]

    def evidencia(self, down: int, yards_to_go: int, zona: str | None) -> Evidencia:
        pesos = [1, 2, 5, 10, 16, 14, 10, 7, 5, 3, 2]       # 10 bins de 5 yd (-10 a 40) y "40+"
        distribucion = []
        for z in ZONAS:
            n = _VALOR_ZONA[z][3]
            conteos = [n * p // sum(pesos) for p in pesos]
            conteos[4] += n - sum(conteos)
            bins = [BinDistribucion(desde=-10 + 5 * i, hasta=-5 + 5 * i, n=conteos[i]) for i in range(10)]
            bins.append(BinDistribucion(desde=40, hasta=None, n=conteos[10]))
            distribucion.append(DistribucionZona(zona=z, bins=bins))
        base = _VALOR_ZONA[zona] if zona else (6.0, 5.5, 6.5, 1000)
        v, lo, hi, n = base
        cobertura = [
            ValorCobertura(cobertura="Man", estimacion=_est(v + 0.3, lo + 0.3, hi + 0.3, n * 4 // 10)),
            ValorCobertura(cobertura="Zone", estimacion=_est(v - 0.2, lo - 0.2, hi - 0.2, n * 5 // 10)),
            ValorCobertura(cobertura="Otra", estimacion=_est(v, lo, hi, max(1, n // 10))),
        ]
        return Evidencia(
            distribucion=distribucion,
            valor_por_zona=[ValorZona(zona=z, estimacion=_est_zona(z)) for z in ZONAS],
            valor_por_cobertura=cobertura,
            regret_por_zona=[RegretZona(zona=z, estimacion=_est(
                1.0 + 0.15 * i, 0.8 + 0.15 * i, 1.2 + 0.15 * i + (0.0 if i % 3 == 0 else 0.6), _VALOR_ZONA[z][3]))
                for i, z in enumerate(ZONAS)],
        )

    # -- IA (en mock siempre plantilla)
    def explicacion(self, q: SituacionQuery) -> ExplicacionOut:
        rec = self.recomendacion(q)
        return ExplicacionOut(texto=Texto(es=f"{rec.accion.es}. {rec.porque.es}",
                                          en=f"{rec.accion.en}. {rec.porque.en}"),
                              fuente="plantilla")

    def chat(self, game_id: int, hasta: int, mensaje: str) -> ChatOut:
        _partido(game_id)
        _validar_n(hasta)
        acc = self.acumulado(game_id, hasta)
        return ChatOut(
            respuesta=(f"Hasta la jugada {hasta}: regret acumulado {acc.total_yd:.1f} yd "
                       f"en {acc.n_con_regret} jugadas. Aún no es concluyente."),
            fuente="plantilla")
