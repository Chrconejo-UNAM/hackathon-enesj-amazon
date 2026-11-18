// Tipos del contrato de API (espejo de backend/analytics/schemas.py). No modificar sin acordar con backend.

export type Textos = { es: string; en: string }
export type Confianza = 'verde' | 'amarillo' | 'rojo'
export type Profundidad = 'corta' | 'media' | 'profunda'
export type Zona = `${Profundidad}_${Lado}`
export type Lado = 'izquierda' | 'centro' | 'derecha'
export type Cobertura = 'todas' | 'Man' | 'Zone'

export type Estimacion = {
  valor: number // yardas (Regret) o proporciÃ³n 0-1 (tasas)
  ic95: [number, number]
  n: number
  concluyente: boolean // false si n < 30
  confianza: Confianza
}

export type ErrorApi = { detail: string; codigo: string }

export type Resumen = {
  titulo: Textos
  linea: Textos
  regret_liga: Estimacion
  calidad_datos: { pct_objetivo_inferido: number } // 0-100
}

export type Partido = {
  gameId: number
  semana: number
  local: string
  visitante: string
  n_pases: number
}

export type Receptor = { nflId: number; nombre: string; posicion: string | null }

export type SeparacionJugador = {
  nflId: number
  nombre: string
  separacion: number
  es_elegido: boolean
  es_mas_abierto: boolean
}

export type EstadoPartido = {
  gameId: number
  n: number
  n_pases: number
  hay_siguiente: boolean
  semana: number
  local: string
  visitante: string
}

export type Jugada = {
  n: number
  down: number
  yardsToGo: number
  zona: Zona | null
  marcador: { local: number; visitante: number }
  reloj: { quarter: number; tiempo: string }
  receptor_elegido: Receptor | null // null = sin receptor identificado
  receptor_mas_abierto: Receptor | null
  separaciones: SeparacionJugador[]
  regret: number | null
  resultado: { pase: string; yardas: number; texto: string }
}

export type JugadaRespuesta = { estado: EstadoPartido; jugada: Jugada }

export type Acumulado = {
  hasta: number
  n_con_regret: number
  total_yd: number
  estimacion: Estimacion
  por_zona: { zona: Zona; total_yd: number; estimacion: Estimacion }[]
  por_lado: { lado: Lado; total_yd: number; estimacion: Estimacion }[]
}

export type Alerta = {
  id: string
  nivel: 'info' | 'aviso' | 'critico'
  titulo: Textos
  texto: Textos
  estimacion: Estimacion
}

/** Pase comparable de la base histórica (yardas reales). */
export type Comparable = {
  gameId: number
  playId: number
  equipo: string
  semana: number
  down: number
  yardsToGo: number
  zona: Zona
  cobertura: string | null
  playResult: number
  sep_elegido: number | null
  sep_mas_abierto: number | null
}

export type Recomendacion = {
  accion: Textos
  porque: Textos
  estimacion: Estimacion // yardas esperadas
  comparables: Comparable[]
}
export type EquipoRegret = { equipo: string; estimacion: Estimacion }

export type Evidencia = {
  distribucion: { zona: Zona; bins: { desde: number; hasta: number | null; n: number }[] }[]
  valor_por_zona: { zona: Zona; estimacion: Estimacion }[] // yardas esperadas
  valor_por_cobertura: { cobertura: 'Man' | 'Zone' | 'Otra'; estimacion: Estimacion }[]
  regret_por_zona: { zona: Zona; estimacion: Estimacion }[]
}
export type Fuente = 'ia' | 'plantilla'
export type Explicacion = { texto: Textos; fuente: Fuente }
export type ChatReq = { gameId: number; hasta: number; mensaje: string }
export type ChatResp = { respuesta: string; fuente: Fuente }

export type FiltrosSala = { down: number; yardsToGo: number; zona: Zona | 'todas'; cobertura: Cobertura }


