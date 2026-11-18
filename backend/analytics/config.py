"""Constantes y umbrales de La Jugada Correcta (ver design.md, config.py)."""

SEMILLA = 2021            # semilla fija del bootstrap
N_REMUESTREOS = 1000
N_ROJO = 30               # n < 30 => rojo
N_VERDE = 100             # n >= 100 y ancho < ANCHO_VERDE => verde
ANCHO_VERDE = 1.0         # yardas
RANGOS_YTG = [(1, 3, "1-3"), (4, 6, "4-6"), (7, 10, "7-10"), (11, 99, "11+")]
UMBRAL_CORTA, UMBRAL_MEDIA = 5.0, 15.0   # yardas más allá de la línea de golpeo
UMBRAL_CENTRO = 5.0                      # |lateral| <= 5 yd => centro
MAX_COMPARABLES = 50
# Alertas (7.4)
ALERTA_MIN_JUGADAS = 10      # menos jugadas con regret => datos_insuficientes
ALERTA_REGRET_AVISO = 2.0    # yd, regret_alto (aviso)
ALERTA_REGRET_CRITICO = 3.0  # yd, regret_alto (critico)
ALERTA_ZONA_MIN_N = 5        # jugadas mínimas en una zona
ALERTA_ZONA_REGRET = 2.5     # yd, zona_ciega
ALERTA_RACHA_N = 3           # jugadas consecutivas
ALERTA_RACHA_REGRET = 3.0    # yd por jugada
EVENTOS = {
    "ball_snap",
    "pass_forward",
    "pass_arrived",
    "autoevent_ballsnap",
    "autoevent_passforward",
}
COLS_TRACKING = [
    "gameId", "playId", "nflId", "frameId", "team",
    "playDirection", "x", "y", "event",
]
