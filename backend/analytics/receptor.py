"""Receptor_Inferido por jugada (tarea 3.3). Todo en memoria; no toca disco.

El dataset no identifica al objetivo del pase, así que se infiere en dos pasos:

1. Texto: regex sobre `playDescription` (`" to "` o `" intended for "` seguido de
   `Inicial.Apellido`), cruzada con la clave `inicial.Apellido` (sin sufijos, ver
   `jugadas.clave_nombre`) de los jugadores ofensivos de la jugada. Solo vale si exactamente
   un jugador ofensivo tiene esa clave. Origen = "texto".
2. Respaldo: si el texto no resuelve y existe el frame `pass_arrived` con el balón, se elige
   al jugador ofensivo más cercano al balón en ese frame, excluyendo al pasador
   (`rol == "pass"`). Origen = "pass_arrived". Empate de distancia: menor `nflId`.
3. Si nada aplica, `receptor_id` es nulo y `origen` nulo (la jugada queda fuera del Regret).

Supuestos:

* "Jugadores ofensivos de la jugada" = jugadores del tracking en el frame `pass_forward`
  cuyo `team` coincide con `jugadas.equipo` (abreviatura, p. ej. "TB"; en los CSV reales `team`\n  del tracking es la abreviatura del equipo o "football", NO "home"/"away", por lo que\n  `jugadas.lado_ofensivo` no sirve para esto). El roster (pff) no trae
  equipo, por eso se usa el tracking. Jugadores sin fila en el roster (sin nombre) no pueden
  resolverse por texto pero sí por el respaldo.
* Pasadores: jugadores ofensivos con rol pff "pass" (ya en minúsculas en el roster). Si el
  roster no los trae, el respaldo podría elegir al pasador; con `pass_arrived` el balón
  suele estar lejos de él, por lo que se acepta.
* Apellidos compuestos con espacio (p. ej. "St. Brown") no los captura la regex
  (`[A-Za-z'\\-]+`) y caen al respaldo o a "sin receptor". Es una limitación conocida.
* Solo se analiza la primera coincidencia del regex.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

RX = re.compile(r"(?: to | intended for )([A-Z]\.[A-Za-z'\-]+)")

_LLAVE = ["gameId", "playId"]


def clave_desde_texto(desc) -> str | None:
    """Primera clave `Inicial.Apellido` mencionada como objetivo en la descripción, o None."""
    if not isinstance(desc, str):
        return None
    m = RX.search(desc)
    return m.group(1) if m else None


def nflid_mas_cercano(ofensivos: pd.DataFrame, balon_xy: tuple[float, float]) -> int | None:
    """nflId del jugador ofensivo (columnas nflId, x, y; sin pasador) más cercano al balón.
    Empate: menor nflId. Sin candidatos: None."""
    if ofensivos.empty:
        return None
    d = np.hypot(ofensivos["x"].to_numpy(float) - balon_xy[0],
                 ofensivos["y"].to_numpy(float) - balon_xy[1])
    orden = np.lexsort((ofensivos["nflId"].to_numpy(), d))
    return int(ofensivos["nflId"].to_numpy()[orden[0]])


def inferir_receptor(desc, ofensivos: pd.DataFrame,
                     balon_arrived: tuple[float, float] | None = None,
                     ofensivos_arrived: pd.DataFrame | None = None
                     ) -> tuple[int | None, str | None]:
    """Receptor de una jugada.

    ofensivos: jugadores ofensivos con columnas `nflId` y `clave`.
    balon_arrived / ofensivos_arrived: posición del balón y jugadores ofensivos (nflId, x, y,
    sin pasador) en el frame pass_arrived; None si no existe ese frame.
    Devuelve (nflId, origen) con origen "texto" | "pass_arrived", o (None, None).
    """
    clave = clave_desde_texto(desc)
    if clave:
        c = ofensivos[ofensivos["clave"] == clave]["nflId"].drop_duplicates()
        if len(c) == 1:
            return int(c.iloc[0]), "texto"
    if balon_arrived is not None and ofensivos_arrived is not None:
        nid = nflid_mas_cercano(ofensivos_arrived, balon_arrived)
        if nid is not None:
            return nid, "pass_arrived"
    return None, None


def inferir_receptores(jugadas: pd.DataFrame, roster: pd.DataFrame,
                       frames: pd.DataFrame) -> pd.DataFrame:
    """Aplica `inferir_receptor` a cada jugada.

    jugadas: tabla de construir_jugadas (usa gameId, playId, playDescription, equipo).
    roster: construir_roster (gameId, playId, nflId, rol, clave).
    frames: frames de eventos (Almacen.frames_eventos).
    Devuelve DataFrame con gameId, playId, receptor_id (Int64, nulo si no hay) y
    origen ("texto", "pass_arrived" o nulo), una fila por jugada de `jugadas`.
    """
    base = jugadas[_LLAVE + ["playDescription", "equipo"]]
    rinfo = roster[_LLAVE + ["nflId", "rol", "clave"]].drop_duplicates(_LLAVE + ["nflId"])
    lado = base[_LLAVE + ["equipo"]]

    def _ofensivos(evento: str) -> pd.DataFrame:
        f = frames[(frames["event"] == evento) & frames["nflId"].notna()]
        f = f.merge(lado, on=_LLAVE)
        f = f[f["team"] == f["equipo"]]
        f = f.merge(rinfo, on=_LLAVE + ["nflId"], how="left")
        f["nflId"] = f["nflId"].astype("int64")
        f["clave"] = f["clave"].fillna("")
        f["rol"] = f["rol"].fillna("")
        return f

    of_pf = {k: g for k, g in _ofensivos("pass_forward").groupby(_LLAVE)}
    of_pa = {k: g[g["rol"] != "pass"] for k, g in _ofensivos("pass_arrived").groupby(_LLAVE)}
    bal = frames[(frames["event"] == "pass_arrived") & (frames["team"] == "football")]
    bal = bal.drop_duplicates(_LLAVE).set_index(_LLAVE)[["x", "y"]]
    bal_d = {k: (float(x), float(y)) for k, x, y in zip(bal.index, bal["x"], bal["y"])}

    vacio = pd.DataFrame({"nflId": [], "clave": []})
    ids: list = []
    origenes: list = []
    for g, p, desc in zip(base["gameId"], base["playId"], base["playDescription"]):
        k = (g, p)
        nid, origen = inferir_receptor(desc, of_pf.get(k, vacio), bal_d.get(k), of_pa.get(k))
        ids.append(nid)
        origenes.append(origen)
    out = base[_LLAVE].copy()
    out["receptor_id"] = pd.array(ids, dtype="Int64")
    out["origen"] = pd.Series(origenes, index=out.index, dtype="object")
    return out.reset_index(drop=True)
