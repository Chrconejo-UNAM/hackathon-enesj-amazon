"""Separación, receptor más abierto (proxy) y regret por jugada (tarea 3.4).

Proxy documentado: el receptor más abierto es el receptor elegible con la mayor separación al
defensor más cercano en el frame `pass_forward` (distancia euclidiana mínima en x, y). No
modela trayectorias futuras ni si el pase era posible (ver Limitaciones 1 y 6).

Receptores elegibles: ofensivos con rol "pass route" (comparación insensible a mayúsculas)
más el receptor elegido si no figura en esa lista, para que el elegido siempre pertenezca al
conjunto y el regret sea >= 0.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np

ROL_RECEPTOR = "pass route"


def separaciones(of_xy: np.ndarray, de_xy: np.ndarray) -> np.ndarray:
    """of_xy (R,2) receptores, de_xy (D,2) defensores -> (R,) distancia mínima a un defensor.

    Sin receptores devuelve un arreglo vacío; sin defensores devuelve NaN por receptor.
    """
    of_xy = np.asarray(of_xy, dtype=float).reshape(-1, 2)
    de_xy = np.asarray(de_xy, dtype=float).reshape(-1, 2)
    if of_xy.shape[0] == 0:
        return np.empty(0)
    if de_xy.shape[0] == 0:
        return np.full(of_xy.shape[0], np.nan)
    d = np.linalg.norm(of_xy[:, None, :] - de_xy[None, :, :], axis=2)
    return d.min(axis=1)


def es_rol_receptor(rol) -> bool:
    """True si el rol PFF es 'Pass Route' (insensible a mayúsculas y espacios)."""
    return isinstance(rol, str) and rol.strip().lower() == ROL_RECEPTOR


def ids_elegibles(roles: dict[int, str], receptor_elegido: int | None) -> list[int]:
    """nflId elegibles ordenados ascendente: roles 'pass route' + el receptor elegido."""
    ids = {int(i) for i, r in roles.items() if es_rol_receptor(r)}
    if receptor_elegido is not None:
        ids.add(int(receptor_elegido))
    return sorted(ids)


def indice_mas_abierto(seps: np.ndarray, nfl_ids: Iterable[int]) -> int:
    """Índice del receptor con mayor separación; empate -> menor nflId (determinista)."""
    seps = np.asarray(seps, dtype=float)
    ids = np.asarray(list(nfl_ids), dtype=np.int64)
    if seps.shape[0] == 0:
        raise ValueError("No hay receptores elegibles")
    maximo = np.nanmax(seps)
    candidatos = np.flatnonzero(seps == maximo)
    return int(candidatos[np.argmin(ids[candidatos])])


def regret_jugada(seps: np.ndarray, idx_elegido: int,
                  nfl_ids: Iterable[int] | None = None) -> tuple[int, float]:
    """(índice del más abierto, regret = sep(más abierto) - sep(elegido)) con regret >= 0.

    Sin `nfl_ids` el desempate usa el menor índice (equivale a nflId ascendente si los
    arreglos vienen ordenados por nflId, como entrega `ids_elegibles`).
    """
    seps = np.asarray(seps, dtype=float)
    ids = list(range(len(seps))) if nfl_ids is None else nfl_ids
    idx_abierto = indice_mas_abierto(seps, ids)
    return idx_abierto, float(seps[idx_abierto] - seps[idx_elegido])


def enriquecer_jugadas(jugadas, roster, frames):
    """Agrega a la tabla `jugadas` el receptor inferido, la zona y el regret (todo en memoria).

    Columnas nuevas: receptor_id (Int64), origen_receptor, receptor_mas_abierto_id (Int64),
    zona, sep_elegido, sep_mas_abierto y regret (nulos si la jugada no tiene receptor o no se
    puede medir). Ofensiva y defensa se separan por `team` == `equipo` / `defensa`
    (abreviaturas; en el tracking `team` NO es home/away).
    """
    import pandas as pd

    from .receptor import inferir_receptores
    from .zonas import zona_de

    llave = ["gameId", "playId"]
    rec = inferir_receptores(jugadas, roster, frames).rename(
        columns={"origen": "origen_receptor"})
    out = jugadas.merge(rec, on=llave, how="left")
    cols_nuevas = ["receptor_mas_abierto_id", "zona", "sep_elegido", "sep_mas_abierto", "regret"]
    if jugadas.empty or frames.empty:
        for c in cols_nuevas:
            out[c] = pd.Series(dtype="object" if c == "zona" else "float64")
        out["receptor_mas_abierto_id"] = pd.array([], dtype="Int64")
        return out

    info = jugadas[llave + ["equipo", "defensa", "frame_pass_forward",
                            "balon_x", "balon_y", "playDirection"]]
    pf = frames[(frames["event"] == "pass_forward") & frames["nflId"].notna()]
    pf = pf.drop(columns=["playDirection"]).merge(info, on=llave)
    pf = pf[pf["frameId"] == pf["frame_pass_forward"]].copy()
    pf["nflId"] = pf["nflId"].astype("int64")
    roles = roster[llave + ["nflId", "rol"]].drop_duplicates(llave + ["nflId"])
    pf = pf.merge(roles, on=llave + ["nflId"], how="left")
    elegido = {(g, p): int(r) for g, p, r in zip(rec["gameId"], rec["playId"], rec["receptor_id"])
               if pd.notna(r)}

    filas = []
    for (g, p), grupo in pf.groupby(llave):
        rid = elegido.get((g, p))
        if rid is None:
            continue
        equipo, defensa = grupo["equipo"].iat[0], grupo["defensa"].iat[0]
        of = grupo[grupo["team"] == equipo].drop_duplicates("nflId")
        de = grupo[grupo["team"] == defensa]
        roles_of = dict(zip(of["nflId"], of["rol"]))
        if rid not in roles_of:
            continue
        ids = ids_elegibles(roles_of, rid)
        pos = of.set_index("nflId").loc[ids, ["x", "y"]].to_numpy(float)
        seps = separaciones(pos, de[["x", "y"]].to_numpy(float))
        if seps.size == 0 or np.isnan(seps).any():
            continue
        i_el = ids.index(rid)
        i_ab, regret = regret_jugada(seps, i_el, ids)
        bx, by = grupo["balon_x"].iat[0], grupo["balon_y"].iat[0]
        zona = None
        if pd.notna(bx) and pd.notna(by):
            zona = zona_de(pos[i_el, 0], pos[i_el, 1], float(bx), float(by),
                           grupo["playDirection"].iat[0])
        filas.append((g, p, ids[i_ab], zona, float(seps[i_el]), float(seps[i_ab]), regret))
    medidas = pd.DataFrame(filas, columns=llave + cols_nuevas[:1] + ["zona", "sep_elegido",
                                                                      "sep_mas_abierto", "regret"])
    medidas["receptor_mas_abierto_id"] = medidas["receptor_mas_abierto_id"].astype("Int64")
    return out.merge(medidas, on=llave, how="left")
