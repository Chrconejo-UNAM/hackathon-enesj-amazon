"""Pruebas de estimacion.py: semáforo en límites y bootstrap reproducible (tarea 3.6).

Los umbrales se escriben como literales (30, 100, 1.0) para que las pruebas
fallen si se cambian en config.py.
"""
import numpy as np
import pytest

from backend.analytics.estimacion import bootstrap_ic, construir_estimacion, semaforo


# --- semáforo en los límites (Req. 3.2, 3.3) ---
@pytest.mark.parametrize(
    "n, ancho, esperado",
    [
        (29, 0.0, "rojo"),
        (30, 0.0, "amarillo"),
        (99, 0.0, "amarillo"),
        (100, 0.99, "verde"),
        (100, 1.0, "amarillo"),
        (99, 0.99, "amarillo"),
        (0, 0.0, "rojo"),
        (1000, 5.0, "amarillo"),
    ],
)
def test_semaforo_limites(n, ancho, esperado):
    assert semaforo(n, ancho) == esperado


def test_semaforo_propiedad_100_iteraciones():
    rng = np.random.default_rng(2021)
    for _ in range(100):
        n = int(rng.integers(0, 300))
        ancho = float(rng.uniform(0, 3))
        esperado = "rojo" if n < 30 else ("verde" if n >= 100 and ancho < 1.0 else "amarillo")
        assert semaforo(n, ancho) == esperado


# --- bootstrap reproducible (Req. 3.4, 3.7) ---
def test_bootstrap_mismo_arreglo_mismo_ic():
    valores = np.random.default_rng(1).normal(2.0, 1.5, size=50)
    assert bootstrap_ic(valores) == bootstrap_ic(valores.copy())


def test_bootstrap_propiedad_reproducible_y_contiene_media():
    rng = np.random.default_rng(2021)
    for _ in range(100):
        n = int(rng.integers(2, 60))
        v = rng.normal(rng.uniform(-5, 5), rng.uniform(0.1, 3), size=n)
        lo1, hi1 = bootstrap_ic(v)
        lo2, hi2 = bootstrap_ic(v)
        assert (lo1, hi1) == (lo2, hi2)
        assert lo1 <= hi1
        assert lo1 <= v.mean() <= hi1


def test_bootstrap_n0_y_n1():
    assert bootstrap_ic(np.array([])) == (0.0, 0.0)
    assert bootstrap_ic(np.array([3.5])) == (3.5, 3.5)


# --- construir_estimacion ---
def test_estimacion_n0_es_rojo_no_concluyente():
    e = construir_estimacion(np.array([]))
    assert e.n == 0
    assert e.confianza == "rojo"
    assert e.concluyente is False
    assert tuple(e.ic95) == (0.0, 0.0)


def test_estimacion_n1_ic_degenerado_rojo():
    e = construir_estimacion(np.array([2.0]))
    assert e.n == 1
    assert e.valor == 2.0
    assert tuple(e.ic95) == (2.0, 2.0)
    assert e.confianza == "rojo"
    assert e.concluyente is False


@pytest.mark.parametrize("n, confianza, concluyente", [
    (29, "rojo", False),
    (30, "amarillo", True),
    (99, "amarillo", True),
])
def test_estimacion_limites_n(n, confianza, concluyente):
    v = np.random.default_rng(7).normal(1.0, 1.0, size=n)
    e = construir_estimacion(v)
    assert e.n == n
    assert e.confianza == confianza
    assert e.concluyente is concluyente


def test_estimacion_verde_con_n100_y_ancho_pequeno():
    v = np.full(100, 2.0)  # ancho 0 < 1.0
    e = construir_estimacion(v)
    assert e.confianza == "verde"
    assert e.concluyente is True


def test_estimacion_n100_ancho_grande_amarillo():
    v = np.random.default_rng(3).normal(0.0, 20.0, size=100)  # IC ancho > 1
    e = construir_estimacion(v)
    assert (e.ic95[1] - e.ic95[0]) >= 1.0
    assert e.confianza == "amarillo"


def test_estimacion_mismas_observaciones_mismo_resultado():
    v = np.random.default_rng(5).normal(1.0, 2.0, size=40)
    assert construir_estimacion(v) == construir_estimacion(v.copy())
