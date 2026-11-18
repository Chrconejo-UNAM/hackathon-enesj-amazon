"""Tareas 7.2: acumulado con corte temporal (Almacen sintético)."""
import pandas as pd
import pytest

from backend.analytics.acumulado import acumulado_hasta
from backend.analytics.carga import Almacen
from backend.analytics.schemas import ErrorApi, PartidoItem

ZONAS = ["corta_izquierda", "media_centro", "profunda_derecha"]


def _almacen(n=40):
    filas = []
    for i in range(n):
        # playId desordenado respecto al reloj: el orden lo da (quarter, -segundos, playId)
        filas.append(dict(gameId=1, playId=1000 - i, quarter=1 + i // 20,
                          segundos=900 - (i % 20) * 40, zona=ZONAS[i % 3],
                          regret=None if i % 7 == 0 else float(i % 5)))
    filas.append(dict(gameId=2, playId=1, quarter=1, segundos=800, zona="media_centro", regret=9.0))
    partidos = [PartidoItem(gameId=1, semana=1, local="A", visitante="B", n_pases=n),
                PartidoItem(gameId=2, semana=1, local="C", visitante="D", n_pases=1)]
    return Almacen(partidos, jugadas=pd.DataFrame(filas))


def test_n1_rojo_y_defecto_es_completo():
    a = _almacen()
    r = acumulado_hasta(a, 1, 1)
    assert r.hasta == 1 and r.estimacion.confianza == "rojo"
    assert acumulado_hasta(a, 1, None).hasta == 40


def test_corte_igual_a_partido_truncado():
    a = _almacen()
    full = acumulado_hasta(a, 1, 25)
    d = a.jugadas
    # elimina las 15 jugadas posteriores (las 15 últimas en orden cronológico)
    ordenado = d[d.gameId == 1].sort_values(["quarter", "segundos", "playId"],
                                            ascending=[True, False, True])
    trunc = pd.concat([ordenado.head(25), d[d.gameId == 2]])
    a2 = Almacen(a.partidos[:1] + a.partidos[1:], jugadas=trunc)
    a2.partidos[0] = PartidoItem(gameId=1, semana=1, local="A", visitante="B", n_pases=25)
    assert acumulado_hasta(a2, 1, 25).model_dump() == full.model_dump()


def test_totales_coherentes_por_zona_y_lado():
    r = acumulado_hasta(_almacen(), 1, 40)
    assert sum(z.estimacion.n for z in r.por_zona) == r.n_con_regret
    assert sum(l.estimacion.n for l in r.por_lado) == r.n_con_regret
    assert sum(z.total_yd for z in r.por_zona) == pytest.approx(r.total_yd, abs=0.05)


def test_404():
    a = _almacen()
    with pytest.raises(ErrorApi) as e:
        acumulado_hasta(a, 99, 1)
    assert e.value.codigo == "partido_no_encontrado"
    for h in (0, 41):
        with pytest.raises(ErrorApi) as e:
            acumulado_hasta(a, 1, h)
        assert e.value.codigo == "jugada_no_encontrada"
