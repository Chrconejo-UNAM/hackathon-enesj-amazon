import type {
  Acumulado, Alerta, ChatResp, Comparable, Confianza, EquipoRegret, Estimacion,
  Evidencia, Explicacion, Jugada, Lado, Partido, Recomendacion, Resumen, Zona,
} from '../types'

/** Construye una Estimacion coherente con las reglas de semáforo (Req. 8). */
export function est(valor: number, n: number, mitad = 0.4, confianza?: Confianza): Estimacion {
  const c: Confianza = confianza ?? (n < 30 ? 'rojo' : n < 100 ? 'amarillo' : 'verde')
  return { valor, ic95: [+(valor - mitad).toFixed(2), +(valor + mitad).toFixed(2)], n, concluyente: n >= 30, confianza: c }
}

/** Escenario forzado por URL: ?mock=error | amarillo | vacio (solo mocks, para probar estados). */
export const escenario = (): string =>
  typeof window === 'undefined' ? '' : new URLSearchParams(window.location.search).get('mock') ?? ''

export const resumenAmarillo: Resumen = {
  titulo: { es: 'Los QB dejan 1.3 yardas de separación sobre la mesa (con reservas)', en: 'QBs leave 1.3 yards of separation on the table (with caveats)' },
  linea: { es: 'Muestra reducida de 2021', en: 'Small 2021 sample' },
  regret_liga: est(1.3, 60, 0.9),
  calidad_datos: { pct_objetivo_inferido: 18.5 },
}

export const evidenciaVacia: Evidencia = { exito_por_zona: [], exito_por_separacion: [], exito_por_cobertura: [] }

const FZ: Record<string, number> = { propia: 0.8, medio: 1, roja: 1.3 }
/** Equipos filtrados por zona (omitida = todas), orden descendente por valor. */
export function equiposMock(zona?: Zona): EquipoRegret[] {
  const f = zona ? FZ[zona] : 1
  const div = zona ? 3 : 1
  return equipos
    .map((e) => ({ equipo: e.equipo, estimacion: est(+(e.estimacion.valor * f).toFixed(2), Math.max(5, Math.round(e.estimacion.n / div)), 0.3) }))
    .sort((a, b) => b.estimacion.valor - a.estimacion.valor)
}

export const resumen: Resumen = {
  titulo: {
    es: 'Los QB tiran en promedio 1.3 yardas de separación por debajo del mejor receptor',
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

const ZONAS: Zona[] = ['propia', 'medio', 'roja']
const LADOS: Lado[] = ['izquierda', 'centro', 'derecha']
const NOMBRES = ['C. Godwin', 'M. Evans', 'R. Gronkowski', 'L. Fournette']
const POS = ['WR', 'WR', 'TE', 'RB']

/** 12 jugadas de un partido (n empieza en 1). */
export function jugadaMock(gameId: number, n: number): Jugada | null {
  if (n < 1 || n > 12) return null
  const i = n - 1
  const elegido = i % 4
  const seps = [3.1, 5.4, 2.2, 4.0].map((s, k) => ({
    nombre: NOMBRES[k], posicion: POS[k], separacion: +(s + (i % 3) * 0.2).toFixed(1), elegido: k === elegido,
  }))
  const max = Math.max(...seps.map((s) => s.separacion))
  const mas = seps.find((s) => s.separacion === max)!
  const ch = seps[elegido]
  return {
    n, total: 12, gameId, playId: 100 + n, cuarto: 1 + Math.floor(i / 3),
    ofensiva: 'TB', defensiva: 'DAL', down: 1 + (i % 3), yardsToGo: 10 - (i % 4),
    zona: ZONAS[i % 3], marcador: { local: 0 + Math.floor(i / 4) * 7, visitante: 0 },
    reloj: `${String(14 - i).padStart(2, '0')}:${i % 2 ? '30' : '05'}`,
    receptor_elegido: { nombre: ch.nombre, posicion: ch.posicion, inferido: i % 5 === 0 },
    receptor_mas_abierto: { nombre: mas.nombre, posicion: mas.posicion },
    separaciones: seps, regret: +(max - ch.separacion).toFixed(1), lado: LADOS[i % 3],
    resultado: { pase: i % 5 === 4 ? 'I' : 'C', yardas: i % 5 === 4 ? 0 : 4 + i, exito: i % 3 !== 2 },
  }
}

export function acumuladoMock(gameId: number, hasta: number): Acumulado {
  const h = Math.max(0, Math.min(12, hasta))
  let acc = 0
  const serie: { n: number; acumulado: number }[] = []
  const porZona: Record<string, number[]> = {}
  const porLado: Record<string, number[]> = {}
  for (let n = 1; n <= h; n++) {
    const j = jugadaMock(gameId, n)!
    acc += j.regret
    serie.push({ n, acumulado: +acc.toFixed(1) })
    ;(porZona[j.zona] ??= []).push(j.regret)
    ;(porLado[j.lado] ??= []).push(j.regret)
  }
  const media = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length
  return {
    hasta: h, regret_total: +acc.toFixed(1),
    regret_medio: est(h ? acc / h : 0, h, 0.8),
    por_zona: ZONAS.filter((z) => porZona[z]).map((z) => ({ zona: z, estimacion: est(+media(porZona[z]).toFixed(2), porZona[z].length, 0.9) })),
    por_lado: LADOS.filter((l) => porLado[l]).map((l) => ({ lado: l, estimacion: est(+media(porLado[l]).toFixed(2), porLado[l].length, 0.9) })),
    serie,
  }
}

export const alertas: Alerta[] = [
  { id: 'a1', nivel: 'info', titulo: { es: 'Sin cambios relevantes', en: 'No relevant changes' },
    texto: { es: 'El Regret medio reciente está en rango normal.', en: 'Recent mean Regret is in the normal range.' }, estimacion: est(1.1, 120, 0.2) },
  { id: 'a2', nivel: 'atencion', titulo: { es: 'Lado izquierdo con más Regret', en: 'Left side has most Regret' },
    texto: { es: 'Los pases por la izquierda pierden más separación.', en: 'Passes to the left lose more separation.' }, estimacion: est(2.0, 45, 0.9) },
  { id: 'a3', nivel: 'critica', titulo: { es: 'Regret reciente alto', en: 'High recent Regret' },
    texto: { es: 'Las últimas jugadas superan 3 yardas de Regret.', en: 'The last plays exceed 3 yards of Regret.' }, estimacion: est(3.2, 12, 1.5) },
]

/** Alertas calculadas solo con jugadas 1..hasta; aparecen según n. Con n<30 la estimación es roja. */
export function alertasMock(gameId: number, hasta: number): Alerta[] {
  const h = Math.max(0, Math.min(12, hasta))
  if (h < 1) return []
  const ac = acumuladoMock(gameId, h)
  const peor = [...ac.por_lado].sort((a, b) => b.estimacion.valor - a.estimacion.valor)[0]
  const out: Alerta[] = [
    { id: 'a1', nivel: 'info', titulo: alertas[0].titulo, texto: alertas[0].texto, estimacion: ac.regret_medio },
  ]
  if (h >= 4 && peor) out.push({ id: 'a2', nivel: 'atencion', titulo: { es: `Lado ${peor.lado} con más Regret`, en: `${peor.lado} side has most Regret` },
    texto: alertas[1].texto, estimacion: peor.estimacion })
  if (h >= 8) out.push({ id: 'a3', nivel: 'critica', titulo: alertas[2].titulo, texto: alertas[2].texto, estimacion: est(ac.regret_medio.valor, h, 1.5) })
  return out
}

const comp = (es: string, en: string, e: Estimacion): Comparable => ({ etiqueta: { es, en }, estimacion: e })

export function recomendacionMock(filtros: { down: number; yardsToGo: number; zona: string; cobertura: string }): Recomendacion {
  // Caso vacío: 4ª y más de 20 en zona roja.
  if (filtros.down === 4 && filtros.yardsToGo > 20) {
    return { accion: { es: 'Sin datos', en: 'No data' }, porque: { es: '', en: '' }, estimacion: est(0, 0, 0), comparables: [] }
  }
  // Semáforo según yardsToGo: <=5 rojo (n=12), 6-12 amarillo (n=60), >12 verde (n=240).
  const n = filtros.yardsToGo <= 5 ? 12 : filtros.yardsToGo <= 12 ? 60 : 240
  const base = est(0.52, n, n >= 100 ? 0.08 : 0.25)
  return {
    accion: { es: 'Tira al receptor más abierto por el medio', en: 'Throw to the most open receiver in the middle' },
    porque: { es: 'Con esta situación, más separación sube la tasa de éxito.', en: 'In this situation, more separation raises the success rate.' },
    estimacion: base,
    comparables: [
      comp('Mismo down y distancia', 'Same down and distance', base),
      comp('Misma zona', 'Same zone', est(0.47, 150, 0.1)),
      comp('Misma cobertura', 'Same coverage', est(0.44, 40, 0.2)),
    ],
  }
}

export const equipos: EquipoRegret[] = [
  ['NYJ', 1.9, 160], ['DET', 1.7, 150], ['HOU', 1.6, 140], ['MIA', 1.4, 120],
  ['KC', 1.2, 130], ['BUF', 1.0, 110], ['TB', 0.9, 45], ['LAR', 0.6, 14],
].map(([equipo, v, n]) => ({ equipo: equipo as string, estimacion: est(v as number, n as number, 0.3) }))

export const evidencia: Evidencia = {
  exito_por_zona: [
    { zona: 'propia', estimacion: est(0.5, 400, 0.05) },
    { zona: 'medio', estimacion: est(0.46, 350, 0.05) },
    { zona: 'roja', estimacion: est(0.38, 60, 0.15) },
  ],
  exito_por_separacion: [
    { rango: '0-2', estimacion: est(0.33, 120, 0.1) },
    { rango: '2-4', estimacion: est(0.48, 300, 0.06) },
    { rango: '4+', estimacion: est(0.61, 25, 0.2) },
  ],
  exito_por_cobertura: [
    { cobertura: 'Man', estimacion: est(0.44, 140, 0.08) },
    { cobertura: 'Zone', estimacion: est(0.5, 260, 0.06) },
  ],
}

export function explicacionMock(plantilla = false): Explicacion {
  return {
    texto: { es: 'Con poca distancia, la separación explica gran parte del éxito.', en: 'On short yardage, separation explains much of the success.' },
    fuente: plantilla ? 'plantilla' : 'ia',
  }
}

export function chatMock(mensaje: string, hasta: number): ChatResp {
  const plantilla = hasta % 2 === 0
  return {
    respuesta: plantilla ? `Respuesta automática a: "${mensaje}"` : `Según las jugadas hasta la ${hasta}: prioriza al receptor más abierto.`,
    fuente: plantilla ? 'plantilla' : 'ia',
  }
}
