import type {
  Acumulado, Alerta, ChatResp, Confianza, EquipoRegret, Estimacion,
  Evidencia, Explicacion, JugadaRespuesta, Lado, Partido, Recomendacion, Resumen, Zona,
} from '../types'

/** Construye una Estimacion coherente con las reglas de semÃ¡foro (Req. 8). */
export function est(valor: number, n: number, mitad = 0.4, confianza?: Confianza): Estimacion {
  const c: Confianza = confianza ?? (n < 30 ? 'rojo' : n < 100 ? 'amarillo' : 'verde')
  return { valor, ic95: [+(valor - mitad).toFixed(2), +(valor + mitad).toFixed(2)], n, concluyente: n >= 30, confianza: c }
}

/** Escenario forzado por URL: ?mock=error | amarillo | vacio (solo mocks, para probar estados). */
export const escenario = (): string =>
  typeof window === 'undefined' ? '' : new URLSearchParams(window.location.search).get('mock') ?? ''

export const resumenAmarillo: Resumen = {
  titulo: { es: 'Los QB dejan 1.3 yardas de separaciÃ³n sobre la mesa (con reservas)', en: 'QBs leave 1.3 yards of separation on the table (with caveats)' },
  linea: { es: 'Muestra reducida de 2021', en: 'Small 2021 sample' },
  regret_liga: est(1.3, 60, 0.9),
  calidad_datos: { pct_objetivo_inferido: 18.5 },
}

export const evidenciaVacia: Evidencia = { distribucion: [], valor_por_zona: [], valor_por_cobertura: [], regret_por_zona: [] }

const FZ = (z: string): number => (z.startsWith('corta') ? 0.8 : z.startsWith('media') ? 1 : 1.3)
/** Equipos filtrados por zona (omitida = todas), orden descendente por valor. */
export function equiposMock(zona?: Zona): EquipoRegret[] {
  const f = zona ? FZ(zona) : 1
  const div = zona ? 3 : 1
  return equipos
    .map((e) => ({ equipo: e.equipo, estimacion: est(+(e.estimacion.valor * f).toFixed(2), Math.max(5, Math.round(e.estimacion.n / div)), 0.3) }))
    .sort((a, b) => b.estimacion.valor - a.estimacion.valor)
}

export const resumen: Resumen = {
  titulo: {
    es: 'Los QB tiran en promedio 1.3 yardas de separaciÃ³n por debajo del mejor receptor',
    en: 'QBs throw to a receiver 1.3 yards less open than the best option on average',
  },
  linea: { es: 'Regret medio de la liga en pases de 2021', en: 'League mean Regret on 2021 passes' },
  regret_liga: est(1.3, 4200, 0.1),
  calidad_datos: { pct_objetivo_inferido: 18.5 },
}

export const partidos: Partido[] = [
  { gameId: 2021090900, semana: 1, local: 'TB', visitante: 'DAL', n_pases: 80 },
  { gameId: 2021091200, semana: 1, local: 'BUF', visitante: 'PIT', n_pases: 62 },
  { gameId: 2021091201, semana: 1, local: 'KC', visitante: 'CLE', n_pases: 70 },
]

const LADOS: Lado[] = ['izquierda', 'centro', 'derecha']
const PROFS = ['corta', 'media', 'profunda'] as const
const ZONAS: Zona[] = PROFS.flatMap((p) => LADOS.map((l) => `${p}_${l}` as Zona))
const NOMBRES = ['C. Godwin', 'M. Evans', 'R. Gronkowski', 'L. Fournette']
const POS = ['WR', 'WR', 'TE', 'RB']
const ladoDe = (z: Zona): Lado => z.split('_')[1] as Lado

/** 12 jugadas de un partido (n empieza en 1). Cada 5ª jugada no tiene receptor identificado. */
export function jugadaMock(gameId: number, n: number): JugadaRespuesta | null {
  if (n < 1 || n > 12) return null
  const i = n - 1
  const sinReceptor = i % 5 === 4
  const elegido = i % 4
  const seps = [3.1, 5.4, 2.2, 4.0].map((s, k) => ({
    nflId: 1000 + k, nombre: NOMBRES[k], posicion: POS[k], separacion: +(s + (i % 3) * 0.2).toFixed(1), es_elegido: !sinReceptor && k === elegido, es_mas_abierto: false,
  }))
  const max = Math.max(...seps.map((s) => s.separacion))
  const mas = seps.find((s) => s.separacion === max)!
  mas.es_mas_abierto = true
  const ch = seps[elegido]
  const rec = (s: typeof ch) => ({ nflId: s.nflId, nombre: s.nombre, posicion: s.posicion })
  return {
    estado: { gameId, n, n_pases: 12, hay_siguiente: n < 12, semana: 1, local: 'TB', visitante: 'DAL' },
    jugada: {
      n, down: 1 + (i % 3), yardsToGo: 10 - (i % 4),
      zona: ZONAS[i % 9], marcador: { local: Math.floor(i / 4) * 7, visitante: 0 },
      reloj: { quarter: 1 + Math.floor(i / 3), tiempo: `${String(14 - i).padStart(2, '0')}:${i % 2 ? '30' : '05'}` },
      receptor_elegido: sinReceptor ? null : rec(ch),
      receptor_mas_abierto: rec(mas),
      separaciones: seps,
      regret: sinReceptor ? null : +(max - ch.separacion).toFixed(1),
      resultado: { pase: i % 5 === 3 ? 'I' : 'C', yardas: i % 5 === 3 ? 0 : 4 + i, texto: i % 5 === 3 ? 'Pase incompleto' : `Pase completo de ${4 + i} yardas` },
    },
  }
}

export function acumuladoMock(gameId: number, hasta: number): Acumulado {
  const h = Math.max(0, Math.min(12, hasta))
  const todos: number[] = []
  const porZona: Record<string, number[]> = {}
  const porLado: Record<string, number[]> = {}
  for (let n = 1; n <= h; n++) {
    const j = jugadaMock(gameId, n)!.jugada
    if (j.regret == null || j.zona == null) continue
    todos.push(j.regret)
    ;(porZona[j.zona] ??= []).push(j.regret)
    ;(porLado[ladoDe(j.zona)] ??= []).push(j.regret)
  }
  const suma = (a: number[]) => +a.reduce((x, y) => x + y, 0).toFixed(1)
  const media = (a: number[]) => (a.length ? suma(a) / a.length : 0)
  return {
    hasta: h, n_con_regret: todos.length, total_yd: suma(todos),
    estimacion: est(+media(todos).toFixed(2), todos.length, 0.8),
    por_zona: ZONAS.filter((z) => porZona[z]).map((z) => ({ zona: z, total_yd: suma(porZona[z]), estimacion: est(+media(porZona[z]).toFixed(2), porZona[z].length, 0.9) })),
    por_lado: LADOS.filter((l) => porLado[l]).map((l) => ({ lado: l, total_yd: suma(porLado[l]), estimacion: est(+media(porLado[l]).toFixed(2), porLado[l].length, 0.9) })),
  }
}

export const alertas: Alerta[] = [
  { id: 'a1', nivel: 'info', titulo: { es: 'Sin cambios relevantes', en: 'No relevant changes' },
    texto: { es: 'El Regret medio reciente está en rango normal.', en: 'Recent mean Regret is in the normal range.' }, estimacion: est(1.1, 120, 0.2) },
  { id: 'a2', nivel: 'aviso', titulo: { es: 'Lado izquierdo con más Regret', en: 'Left side has most Regret' },
    texto: { es: 'Los pases por la izquierda pierden más separación.', en: 'Passes to the left lose more separation.' }, estimacion: est(2.0, 45, 0.9) },
  { id: 'a3', nivel: 'critico', titulo: { es: 'Regret reciente alto', en: 'High recent Regret' },
    texto: { es: 'Las últimas jugadas superan 3 yardas de Regret.', en: 'The last plays exceed 3 yards of Regret.' }, estimacion: est(3.2, 12, 1.5) },
]

/** Alertas calculadas solo con jugadas 1..hasta; aparecen según n. Con n<30 la estimación es roja. */
export function alertasMock(gameId: number, hasta: number): Alerta[] {
  const h = Math.max(0, Math.min(12, hasta))
  if (h < 1) return []
  const ac = acumuladoMock(gameId, h)
  const peor = [...ac.por_lado].sort((a, b) => b.estimacion.valor - a.estimacion.valor)[0]
  const out: Alerta[] = [
    { id: 'a1', nivel: 'info', titulo: alertas[0].titulo, texto: alertas[0].texto, estimacion: ac.estimacion },
  ]
  if (h >= 4 && peor) out.push({ id: 'a2', nivel: 'aviso', titulo: { es: `Lado ${peor.lado} con más Regret`, en: `${peor.lado} side has most Regret` },
    texto: alertas[1].texto, estimacion: peor.estimacion })
  if (h >= 8) out.push({ id: 'a3', nivel: 'critico', titulo: alertas[2].titulo, texto: alertas[2].texto, estimacion: est(ac.estimacion.valor, h, 1.5) })
  return out
}

export function recomendacionMock(filtros: { down: number; yardsToGo: number; zona: string; cobertura: string }): Recomendacion {
  // Caso vacío: 4ª y más de 20.
  if (filtros.down === 4 && filtros.yardsToGo > 20) {
    return { accion: { es: 'Sin datos', en: 'No data' }, porque: { es: '', en: '' }, estimacion: est(0, 0, 0), comparables: [] }
  }
  // Semáforo según yardsToGo: <=5 rojo (n=12), 6-12 amarillo (n=60), >12 verde (n=240).
  const n = filtros.yardsToGo <= 5 ? 12 : filtros.yardsToGo <= 12 ? 60 : 240
  const zona = (filtros.zona === 'todas' ? 'media_centro' : filtros.zona) as Zona
  return {
    accion: { es: 'Tira al receptor más abierto por el medio', en: 'Throw to the most open receiver in the middle' },
    porque: { es: 'Con esta situación, se esperan unas 7 yardas en pases comparables.', en: 'In this situation, about 7 yards are expected on comparable passes.' },
    estimacion: est(7.2, n, n >= 100 ? 0.8 : 2.5),
    comparables: [
      { gameId: 2021090900, playId: 1234, equipo: 'TB', semana: 1, down: filtros.down, yardsToGo: filtros.yardsToGo, zona,
        cobertura: filtros.cobertura === 'todas' ? 'Man' : filtros.cobertura, playResult: 9, sep_elegido: 2.1, sep_mas_abierto: 4.3 },
      { gameId: 2021091200, playId: 876, equipo: 'BUF', semana: 1, down: filtros.down, yardsToGo: filtros.yardsToGo, zona,
        cobertura: null, playResult: 4, sep_elegido: null, sep_mas_abierto: null },
    ],
  }
}
export const equipos: EquipoRegret[] = [
  ['NYJ', 1.9, 160], ['DET', 1.7, 150], ['HOU', 1.6, 140], ['MIA', 1.4, 120],
  ['KC', 1.2, 130], ['BUF', 1.0, 110], ['TB', 0.9, 45], ['LAR', 0.6, 14],
].map(([equipo, v, n]) => ({ equipo: equipo as string, estimacion: est(v as number, n as number, 0.3) }))

const dist = (zona: Zona) => ({
  zona,
  bins: [-10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40].map((desde, k) => ({ desde, hasta: desde === 40 ? null : desde + 5, n: [1, 2, 5, 10, 16, 14, 10, 7, 5, 3, 2][k] })),
})

export const evidencia: Evidencia = {
  distribucion: ZONAS.map(dist),
  valor_por_zona: ZONAS.map((z, i) => ({ zona: z, estimacion: est(+(4 + (i % 5) * 1.1).toFixed(1), i % 4 === 0 ? 20 : 150, 0.6) })),
  valor_por_cobertura: [
    { cobertura: 'Man', estimacion: est(6.1, 140, 0.8) },
    { cobertura: 'Zone', estimacion: est(7.0, 260, 0.6) },
    { cobertura: 'Otra', estimacion: est(5.2, 18, 1.5) },
  ],
  regret_por_zona: ZONAS.map((z, i) => ({ zona: z, estimacion: est(+(0.8 + (i % 4) * 0.3).toFixed(1), 60, 0.4) })),
}
export function explicacionMock(plantilla = false): Explicacion {
  return {
    texto: { es: 'Con poca distancia, la separaciÃ³n explica gran parte del Ã©xito.', en: 'On short yardage, separation explains much of the success.' },
    fuente: plantilla ? 'plantilla' : 'ia',
  }
}

export function chatMock(mensaje: string, hasta: number): ChatResp {
  const plantilla = hasta % 2 === 0
  return {
    respuesta: plantilla ? `Respuesta automÃ¡tica a: "${mensaje}"` : `SegÃºn las jugadas hasta la ${hasta}: prioriza al receptor mÃ¡s abierto.`,
    fuente: plantilla ? 'plantilla' : 'ia',
  }
}


