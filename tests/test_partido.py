"""Pruebas de partido.py con Almacen sintético (tarea 7.1)."""
import pandas as pd
import pytest

from backend.analytics.carga import Almacen, ServicioReal
from backend.analytics.partido import jugada_respuesta, jugadas_hasta, jugadas_ordenadas
from backend.analytics.schemas import ErrorApi, PartidoItem


def _almacen(filas=None):
    # (playId, quarter, gameClock, segundos)
    filas = filas or [(30, 2, "10:00", 600.0), (10, 1, "05:00", 300.0),
                      (20, 1, "12:00", 720.0), (40, 1, "05:00", 300.0)]
    j = pd.DataFrame([{
        "gameId": 1, "playId": p, "quarter": q, "gameClock": c, "segundos": s,
        "down": 1, "yardsToGo": 10, "zona": None, "marcador_local": 0, "marcador_visitante": 3,
        "passResult": "C", "playResult": 5, "playDescription": "x", "regret": None,
    } for p, q, c, s in filas])
    return Almacen([PartidoItem(gameId=1, semana=1, local="A", visitante="B", n_pases=99)], None, j)


def test_orden_cronologico_y_estable():
    d = jugadas_ordenadas(_almacen().jugadas, 1)
    assert list(d["playId"]) == [20, 10, 40, 30]
    assert list(d["n"]) == [1, 2, 3, 4]
    assert list(jugadas_ordenadas(_almacen().jugadas, 1)["playId"]) == list(d["playId"])


def test_jugadas_hasta_corta_y_no_depende_de_posteriores():
    a = _almacen()
    assert list(jugadas_hasta(a.jugadas, 1, 2)["playId"]) == [20, 10]
    recortado = a.jugadas[a.jugadas["playId"].isin([20, 10])]
    assert (jugada_respuesta(a, 1, 2).jugada.model_dump()
            == jugada_respuesta(_almacen([(10, 1, "05:00", 300.0), (20, 1, "12:00", 720.0)]),
                                1, 2).jugada.model_dump())
    assert len(jugadas_hasta(recortado, 1, 2)) == 2


def test_servicio_n_pases_real_y_respuesta():
    a = _almacen()
    assert ServicioReal(a).partidos()[0].n_pases == 4
    r = jugada_respuesta(a, 1, 4)
    assert r.estado.n_pases == 4 and not r.estado.hay_siguiente
    assert r.jugada.reloj == {"quarter": 2, "tiempo": "10:00"}
    assert r.jugada.marcador == {"local": 0, "visitante": 3}


@pytest.mark.parametrize("gid,n,codigo", [(9, 1, "partido_no_encontrado"),
                                          (1, 0, "jugada_no_encontrada"),
                                          (1, 5, "jugada_no_encontrada")])
def test_errores_404(gid, n, codigo):
    with pytest.raises(ErrorApi) as e:
        jugada_respuesta(_almacen(), gid, n)
    assert e.value.codigo == codigo
