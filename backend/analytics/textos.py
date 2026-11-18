"""Plantillas bilingües {es,en} (tarea 5.2). Las cifras llegan ya como números."""
from .schemas import Estimacion, Texto

_PROF = {"corta": ("corta", "short"), "media": ("media", "mid"), "profunda": ("profunda", "deep")}
_LADO = {"izquierda": ("izquierda", "left"), "centro": ("centro", "center"),
         "derecha": ("derecha", "right")}


def etiqueta_zona(zona: str) -> Texto:
    """'media_izquierda' -> es 'media-izquierda', en 'mid-left'."""
    p, l = zona.split("_", 1)
    return Texto(es=f"{_PROF[p][0]}-{_LADO[l][0]}", en=f"{_PROF[p][1]}-{_LADO[l][1]}")


def accion_sin_muestra() -> Texto:
    return Texto(es="No hay muestra para esta situación",
                 en="No sample for this situation")


def accion_atacar(zona: str) -> Texto:
    z = etiqueta_zona(zona)
    return Texto(es=f"Atacar la zona {z.es}", en=f"Attack the {z.en} zone")


def accion_mejor_otra(mejor: str, dif: float, consultada: str) -> Texto:
    m, c = etiqueta_zona(mejor), etiqueta_zona(consultada)
    return Texto(es=f"La mejor zona es {m.es} ({dif:+.1f} yd frente a {c.es})",
                 en=f"The best zone is {m.en} ({dif:+.1f} yd vs {c.en})")


def accion_zona_vacia(mejor: str, consultada: str) -> Texto:
    m, c = etiqueta_zona(mejor), etiqueta_zona(consultada)
    return Texto(es=f"Sin datos en {c.es}; la mejor zona es {m.es}",
                 en=f"No data in {c.en}; the best zone is {m.en}")


def porque(est: Estimacion) -> Texto:
    if est.n == 0:
        return Texto(
            es="No hay jugadas comparables. Aún no es concluyente. "
               "Valor en yardas esperadas, no es EPA oficial.",
            en="No comparable plays. Not conclusive yet. "
               "Value in expected yards, not official EPA.")
    v, lo, hi = f"{est.valor:.1f}", f"{est.ic95[0]:.1f}", f"{est.ic95[1]:.1f}"
    es = (f"Valor esperado {v} yd (IC95% {lo} a {hi}, n={est.n}). "
          "Valor en yardas esperadas, no es EPA oficial.")
    en = (f"Expected value {v} yd (95% CI {lo} to {hi}, n={est.n}). "
          "Value in expected yards, not official EPA.")
    if not est.concluyente:
        es += " Aún no es concluyente."
        en += " Not conclusive yet."
    return Texto(es=es, en=en)
