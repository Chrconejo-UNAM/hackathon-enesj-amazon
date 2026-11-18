"""Pruebas de alertas.py con Almacen sintético (tarea 7.4)."""
import pandas as pd
import pytest

from backend.analytics.carga import Almacen, ServicioReal
from backend.analytics.schemas import ErrorApi, PartidoItem


def _almacen(regrets, zonas=None):
    """Una jugada por regret; playId crece con el tiempo (mismo quarter, reloj descendente)."""
    zonas = zonas or ["media_izquierda"] * len(regrets)
    j = pd.DataFrame([{
        "gameId": 1, "playId": i + 1, "quarter": 1, "segundos": 900.0 - i,
        "zona": z, "regret": r,
    } for i, (r, z) in enumerate(zip(regrets, zonas))])
    return Almacen([PartidoItem(gameId=1, semana=1, local="A", visitante="B",
                                n_pases=len(regrets))], None, j)


def _ids(al):
    return [a.id for a in al]


def test_pocos_datos_es_info_no_concluyente():
    al = ServicioReal(_almacen([1.0] * 6)).alertas(1, 6)
    assert _ids(al) == ["datos_insuficientes"]
    a = al[0]
    assert a.nivel == "info" and not a.estimacion.concluyente and a.estimacion.n == 6
    assert "n=6" in a.texto.es and "Aún no es concluyente" in a.texto.es
    assert "Not conclusive yet" in a.texto.en


def test_regret_alto_critico_con_n_concluyente():
    al = ServicioReal(_almacen([3.5] * 40)).alertas(1, 40)
    ra = next(a for a in al if a.id == "regret_alto")
    assert ra.nivel == "critico" and ra.estimacion.concluyente
    assert "Aún no es concluyente" not in ra.texto.es
    assert _ids(al) == sorted(_ids(al), key=lambda i: (
        {"critico": 0, "aviso": 1, "info": 2}[next(a.nivel for a in al if a.id == i)], i))


def test_regret_alto_aviso_y_zona_ciega():
    al = ServicioReal(_almacen([2.2] * 12 + [2.8] * 30,
                               ["a"] * 12 + ["media_centro"] * 30)).alertas(1, 42)
    niveles = {a.id: a.nivel for a in al}
    assert niveles["regret_alto"] == "aviso"
    assert niveles["zona_ciega:media_centro"] == "aviso"
    assert "zona_ciega:a" not in niveles


def test_concluyencia_baja_nivel_a_info():
    # zona ciega con n=5 (<30): no concluyente => info
    al = ServicioReal(_almacen([0.0] * 10 + [3.0] * 5, ["x"] * 10 + ["z"] * 5)).alertas(1, 15)
    zc = next(a for a in al if a.id == "zona_ciega:z")
    assert zc.nivel == "info" and not zc.estimacion.concluyente
    assert "Aún no es concluyente" in zc.texto.es and "Not conclusive yet" in zc.texto.en


def test_racha():
    al = ServicioReal(_almacen([0.0] * 10 + [3.0] * 3)).alertas(1, 13)
    assert "racha" in _ids(al)
    assert "racha" not in _ids(ServicioReal(_almacen([0.0] * 10 + [3.0, 3.0, 1.0])).alertas(1, 13))


def test_determinista():
    s = ServicioReal(_almacen([3.5] * 40))
    assert ([a.model_dump() for a in s.alertas(1, 40)]
            == [a.model_dump() for a in s.alertas(1, 40)])


def test_hasta_k_no_depende_de_jugadas_posteriores():
    k = 20
    base = [2.0, 3.5, 1.0, 4.0] * 5
    a = ServicioReal(_almacen(base + [9.0] * 10)).alertas(1, k)
    b = ServicioReal(_almacen(base + [0.0] * 3)).alertas(1, k)
    c = ServicioReal(_almacen(base)).alertas(1, k)
    dump = lambda x: [i.model_dump() for i in x]  # noqa: E731
    assert dump(a) == dump(b) == dump(c)


def test_hasta_omitido_usa_partido_completo():
    s = ServicioReal(_almacen([3.5] * 40))
    assert s.alertas(1, None) == s.alertas(1, 40)


@pytest.mark.parametrize("gid,hasta,codigo", [(9, 1, "partido_no_encontrado"),
                                              (1, 0, "jugada_no_encontrada"),
                                              (1, 7, "jugada_no_encontrada")])
def test_errores_404(gid, hasta, codigo):
    with pytest.raises(ErrorApi) as e:
        ServicioReal(_almacen([1.0] * 6)).alertas(gid, hasta)
    assert e.value.status == 404 and e.value.codigo == codigo
