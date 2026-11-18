"""Pruebas de receptor.py, zonas.py y separacion.py (tarea 3.7).

Casos sintéticos (sin leer data/) y propiedades con numpy.random.default_rng y semilla fija
(100 iteraciones). Los casos con datos reales se omiten si falta data/.
Nota: el `team` del tracking es la abreviatura del equipo (p. ej. "TB"), no home/away.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.analytics.jugadas import clave_nombre
from backend.analytics.receptor import (clave_desde_texto, inferir_receptor,
                                        inferir_receptores, nflid_mas_cercano)
from backend.analytics.separacion import (ids_elegibles, indice_mas_abierto,
                                          regret_jugada, separaciones)
from backend.analytics.zonas import (ZONAS, lado_de, lado_de_zona, profundidad_de,
                                     rango_ytg, signo_direccion, zona_de)

SEMILLA = 2021
ITERACIONES = 100
DATA = Path(__file__).resolve().parent.parent / "data"


def _of(*pares) -> pd.DataFrame:
    """Roster ofensivo sintético: pares (nflId, clave)."""
    return pd.DataFrame({"nflId": [p[0] for p in pares], "clave": [p[1] for p in pares]})


# --------------------------------------------------------------------------- receptor: texto
def test_parseo_prescott_a_cooper():
    desc = "(10:00) D.Prescott pass deep left to A.Cooper to DAL 40 for 15 yards (X.Y)."
    assert clave_desde_texto(desc) == "A.Cooper"
    nid, origen = inferir_receptor(desc, _of((1, "D.Prescott"), (2, "A.Cooper")))
    assert (nid, origen) == (2, "texto")


def test_intended_for():
    desc = "T.Brady pass incomplete deep right intended for M.Evans (J.Doe)."
    assert clave_desde_texto(desc) == "M.Evans"


def test_apellido_con_sufijo_y_inicial_doble():
    assert clave_nombre("Odell Beckham Jr.") == "O.Beckham"
    assert clave_nombre("O.J. Howard") == "O.Howard"
    # El texto real usa "O.Howard" (no "O.J.Howard")
    desc = "T.Brady pass short middle to O.Howard to ATL 15 for 21 yards (E.Harris)."
    nid, origen = inferir_receptor(desc, _of((7, clave_nombre("O.J. Howard")),
                                             (8, clave_nombre("Odell Beckham Jr."))))
    assert (nid, origen) == (7, "texto")
    nid, origen = inferir_receptor("pass deep to O.Beckham for 5 yards",
                                   _of((7, "O.Howard"), (8, clave_nombre("Odell Beckham Jr."))))
    assert (nid, origen) == (8, "texto")


def test_nombre_ambiguo_sin_respaldo_da_none():
    desc = "pass short left to J.Smith for 4 yards"
    assert inferir_receptor(desc, _of((1, "J.Smith"), (2, "J.Smith"))) == (None, None)


def test_mismo_nflid_repetido_no_es_ambiguo():
    # Un jugador con varias filas (p. ej. varios frames) sigue siendo único.
    assert inferir_receptor("pass to J.Smith", _of((1, "J.Smith"), (1, "J.Smith"))) == (1, "texto")


def test_sin_objetivo_nombrado():
    assert clave_desde_texto("T.Brady pass incomplete short right.") is None
    assert clave_desde_texto(None) is None
    assert inferir_receptor("pass incomplete short right.", _of((1, "A.Cooper"))) == (None, None)


def test_respaldo_pass_arrived():
    ofensivos = _of((1, "D.Prescott"), (2, "A.Cooper"))
    arrived = pd.DataFrame({"nflId": [2, 3], "x": [30.0, 50.0], "y": [10.0, 10.0]})
    desc = "pass incomplete short right."
    nid, origen = inferir_receptor(desc, ofensivos, (31.0, 10.0), arrived)
    assert (nid, origen) == (2, "pass_arrived")
    # Nombre inexistente en roster también degrada al respaldo
    nid, origen = inferir_receptor("pass to Z.Nadie", ofensivos, (49.0, 10.0), arrived)
    assert (nid, origen) == (3, "pass_arrived")


def test_nflid_mas_cercano_empate_menor_nflid():
    of = pd.DataFrame({"nflId": [9, 4], "x": [1.0, 1.0], "y": [2.0, 2.0]})
    assert nflid_mas_cercano(of, (0.0, 0.0)) == 4
    assert nflid_mas_cercano(of.iloc[0:0], (0.0, 0.0)) is None


def test_inferir_receptores_usa_abreviatura_de_equipo():
    """El `team` del tracking es la abreviatura ("TB"), no home/away."""
    jugadas = pd.DataFrame({
        "gameId": [1, 1, 1], "playId": [10, 20, 30], "equipo": ["TB", "TB", "TB"],
        "playDescription": ["pass short to A.Cooper for 5 yards",
                            "pass incomplete short right.",
                            "pass incomplete short left."]})
    roster = pd.DataFrame({
        "gameId": [1] * 4 + [1] * 3, "playId": [10] * 4 + [20] * 3,
        "nflId": [1, 2, 3, 4, 1, 2, 3],
        "rol": ["pass", "pass route", "pass route", "pass rush", "pass", "pass route", "pass route"],
        "clave": ["T.Brady", "A.Cooper", "M.Evans", "X.Def", "T.Brady", "A.Cooper", "M.Evans"]})
    filas = []

    def f(p, nfl, team, x, y, ev):
        filas.append(dict(gameId=1, playId=p, nflId=nfl, frameId=1, team=team, x=x, y=y, event=ev))

    for p in (10, 20, 30):
        f(p, 1, "TB", 20, 25, "pass_forward")
        f(p, 2, "TB", 30, 20, "pass_forward")
        f(p, 3, "TB", 30, 40, "pass_forward")
        f(p, 4, "DAL", 31, 20, "pass_forward")
    f(20, np.nan, "football", 31, 40, "pass_arrived")
    f(20, 1, "TB", 20, 25, "pass_arrived")
    f(20, 2, "TB", 28, 20, "pass_arrived")
    f(20, 3, "TB", 30, 40, "pass_arrived")
    f(20, 4, "DAL", 31, 40, "pass_arrived")   # defensor cerca del balón: no debe elegirse
    out = inferir_receptores(jugadas, roster, pd.DataFrame(filas)).set_index("playId")
    assert out.loc[10, "receptor_id"] == 2 and out.loc[10, "origen"] == "texto"
    assert out.loc[20, "receptor_id"] == 3 and out.loc[20, "origen"] == "pass_arrived"
    assert pd.isna(out.loc[30, "receptor_id"]) and pd.isna(out.loc[30, "origen"])


def test_propiedad_receptor_unico_o_degrada():
    # Feature: la-jugada-correcta, Property 6
    # **Validates: Requirements 5.4, 5.5, 5.6**
    rng = np.random.default_rng(SEMILLA)
    apellidos = ["Cooper", "Evans", "Smith", "Kelce", "Adams", "Hill", "Jones", "Brown"]
    for _ in range(ITERACIONES):
        k = int(rng.integers(2, 8))
        ids = rng.choice(np.arange(1, 100), size=k, replace=False)
        claves = [f"{chr(65 + int(rng.integers(0, 26)))}.{apellidos[int(rng.integers(0, 8))]}"
                  for _ in range(k)]
        ofensivos = _of(*zip(map(int, ids), claves))
        objetivo = claves[int(rng.integers(0, k))]
        desc = f"Q.Back pass short left to {objetivo} to X 20 for 7 yards (D.Fense)."
        dueños = ofensivos[ofensivos["clave"] == objetivo]["nflId"]
        nid, origen = inferir_receptor(desc, ofensivos)
        if len(dueños) == 1:
            assert (nid, origen) == (int(dueños.iloc[0]), "texto")
        else:
            assert (nid, origen) == (None, None)
        # Con pass_arrived, el ambiguo o inexistente degrada al más cercano
        arr = pd.DataFrame({"nflId": ids, "x": rng.uniform(0, 100, k), "y": rng.uniform(0, 53, k)})
        bal = (float(rng.uniform(0, 100)), float(rng.uniform(0, 53)))
        nid2, origen2 = inferir_receptor(desc, ofensivos, bal, arr)
        if len(dueños) == 1:
            assert origen2 == "texto"
        else:
            assert origen2 == "pass_arrived"
            d = np.hypot(arr["x"] - bal[0], arr["y"] - bal[1])
            assert nid2 == int(arr["nflId"].iloc[int(np.argmin(d.to_numpy()))])
        nid3, origen3 = inferir_receptor("pass to Z.Nadie", ofensivos, bal, arr)
        assert origen3 == "pass_arrived"


# --------------------------------------------------------------------------- zonas
def test_nueve_zonas():
    assert len(ZONAS) == 9 and len(set(ZONAS)) == 9


def test_profundidad_bordes_5_y_15():
    assert profundidad_de(4.999) == "corta"
    assert profundidad_de(5.0) == "media"
    assert profundidad_de(14.999) == "media"
    assert profundidad_de(15.0) == "profunda"
    assert profundidad_de(-3.0) == "corta"   # detrás de la línea


def test_lado_bordes_5_yd():
    assert lado_de(5.0) == "centro"
    assert lado_de(5.001) == "izquierda"
    assert lado_de(-5.0) == "centro"
    assert lado_de(-5.001) == "derecha"
    assert lado_de(0.0) == "centro"


def test_zona_depende_de_direccion():
    # Hacia +x: receptor 20 yd adelante y +10 en y -> profunda_izquierda
    assert zona_de(70, 36, 50, 26, "right") == "profunda_izquierda"
    # Hacia -x, mismo desplazamiento espejado -> misma zona (perspectiva ofensiva)
    assert zona_de(30, 16, 50, 26, "left") == "profunda_izquierda"
    assert signo_direccion("right") == 1 and signo_direccion("left") == -1
    assert lado_de_zona("media_derecha") == "derecha"


def test_rango_ytg_bordes():
    assert [rango_ytg(v) for v in (1, 3, 4, 6, 7, 10, 11, 40)] == \
        ["1-3", "1-3", "4-6", "4-6", "7-10", "7-10", "11+", "11+"]
    assert rango_ytg(0) is None


def test_propiedad_zona_en_catalogo_y_simetrica():
    # Feature: la-jugada-correcta, Property 5 (soporte: zona siempre en el catálogo)
    # **Validates: Requirements 5.1**
    rng = np.random.default_rng(SEMILLA)
    for _ in range(ITERACIONES):
        bx, by = rng.uniform(10, 110), rng.uniform(5, 48)
        dx, dy = rng.uniform(-10, 40), rng.uniform(-20, 20)
        z_r = zona_de(bx + dx, by + dy, bx, by, "right")
        z_l = zona_de(bx - dx, by - dy, bx, by, "left")
        assert z_r in ZONAS and z_r == z_l


# --------------------------------------------------------------------------- separación y regret
def test_separaciones_basico():
    of = np.array([[0.0, 0.0], [10.0, 0.0]])
    de = np.array([[3.0, 4.0], [10.0, 1.0]])
    np.testing.assert_allclose(separaciones(of, de), [5.0, 1.0])
    assert separaciones(np.empty((0, 2)), de).shape == (0,)
    assert np.isnan(separaciones(of, np.empty((0, 2)))).all()


def test_regret_basico_y_empates():
    seps = np.array([2.0, 5.0, 3.0])
    assert regret_jugada(seps, 2) == (1, 2.0)
    assert regret_jugada(seps, 1) == (1, 0.0)           # elegido es el más abierto
    # Empate en el máximo: menor nflId (aquí ids ordenados ascendente)
    empate = np.array([4.0, 4.0, 1.0])
    assert indice_mas_abierto(empate, [10, 20, 30]) == 0
    assert indice_mas_abierto(empate, [20, 10, 30]) == 1   # desempate por nflId, no por índice
    assert regret_jugada(empate, 1)[1] == 0.0          # empate con el elegido => regret 0
    with pytest.raises(ValueError):
        indice_mas_abierto(np.empty(0), [])


def test_ids_elegibles():
    roles = {5: "Pass Route", 3: "pass route", 9: "Pass Block", 1: "Pass"}
    assert ids_elegibles(roles, None) == [3, 5]
    assert ids_elegibles(roles, 9) == [3, 5, 9]      # elegido fuera de la lista se agrega
    assert ids_elegibles(roles, 5) == [3, 5]


def test_propiedad_regret_no_negativo_y_consistente():
    # Feature: la-jugada-correcta, Property 5
    # **Validates: Requirements 5.1, 5.2, 5.3, 9.4**
    rng = np.random.default_rng(SEMILLA)
    for _ in range(ITERACIONES):
        r = int(rng.integers(1, 6))
        d = int(rng.integers(1, 12))
        of = rng.uniform(0, 50, size=(r, 2))
        de = rng.uniform(0, 50, size=(d, 2))
        seps = separaciones(of, de)
        assert seps.shape == (r,) and (seps >= 0).all()
        ids = np.sort(rng.choice(np.arange(1, 200), size=r, replace=False))
        elegido = int(rng.integers(0, r))
        idx, regret = regret_jugada(seps, elegido, ids)
        assert regret >= 0
        assert regret == pytest.approx(seps.max() - seps[elegido])
        assert seps[idx] == seps.max()
        if seps[elegido] == seps.max():
            assert regret == 0.0


# --------------------------------------------------------------------------- datos reales
@pytest.fixture(scope="module")
def almacen_real():
    if not (DATA / "games.csv").exists():
        pytest.skip("falta data/")
    from backend.analytics.carga import cargar_almacen
    return cargar_almacen(DATA)


def _regrets_reales(almacen) -> pd.DataFrame:
    """Regret por jugada con receptor resuelto, usando equipo (abreviatura) del tracking."""
    jug, roster, fr = almacen.jugadas, almacen.roster, almacen.frames_eventos
    rec = inferir_receptores(jug, roster, fr)
    rec = rec.dropna(subset=["receptor_id"])
    llave = ["gameId", "playId"]
    pf = fr[(fr["event"] == "pass_forward") & fr["nflId"].notna()]
    pf = pf.merge(jug[llave + ["equipo", "defensa"]], on=llave)
    roles = roster.drop_duplicates(llave + ["nflId"]).set_index(llave + ["nflId"])["rol"]
    elegido = {(g, p): int(n) for g, p, n in zip(rec["gameId"], rec["playId"], rec["receptor_id"])}
    salida = []
    for (g, p), grp in pf.groupby(llave):
        if (g, p) not in elegido:
            continue
        eq, de = grp["equipo"].iloc[0], grp["defensa"].iloc[0]
        ofe, dfe = grp[grp["team"] == eq], grp[grp["team"] == de]
        rol = {int(n): roles.get((g, p, int(n)), "") for n in ofe["nflId"]}
        ids = ids_elegibles(rol, elegido[(g, p)])
        pos = ofe.drop_duplicates("nflId").set_index("nflId")[["x", "y"]]
        ids = [i for i in ids if i in pos.index]
        if elegido[(g, p)] not in ids or dfe.empty:
            continue
        seps = separaciones(pos.loc[ids].to_numpy(float), dfe[["x", "y"]].to_numpy(float))
        _, reg = regret_jugada(seps, ids.index(elegido[(g, p)]), ids)
        salida.append((g, p, reg))
    return pd.DataFrame(salida, columns=["gameId", "playId", "regret"])


def test_real_receptor_por_texto_y_regret_no_negativo(almacen_real):
    # **Validates: Requirements 5.3, 5.4, 5.6**
    jug = almacen_real.jugadas
    rec = inferir_receptores(jug, almacen_real.roster, almacen_real.frames_eventos)
    assert len(rec) == len(jug)
    assert (rec["origen"] == "texto").mean() > 0.90        # diseño: ~94.7 %
    assert set(rec["origen"].dropna()) <= {"texto", "pass_arrived"}
    reg = _regrets_reales(almacen_real)
    assert len(reg) > 5000
    assert (reg["regret"] >= 0).all()
    assert reg["regret"].notna().all()
