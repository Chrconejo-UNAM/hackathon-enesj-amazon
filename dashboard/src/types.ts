// Tipos del contrato de API (copia de design.md). No modificar sin acordar con backend.

export type Textos = { es: string; en: string }
export type Confianza = 'verde' | 'amarillo' | 'rojo'
export type Zona = 'propia' | 'medio' | 'roja'
export type Lado = 'izquierda' | 'centro' | 'derecha'
export type Cobertura = 'todas' | 'Man' | 'Zone'

export type Estimacion = {
  valor: number // yardas (Regret) o proporción 0-1 (tasas)
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

export type Jugada = {
  n: number
  total: number
  gameId: number
  playId: number
  cuarto: number
  ofensiva: string
  defensiva: string
  down: number
  yardsToGo: number
  zona: Zona
  marcador: { local: number; visitante: number }
  reloj: string
  receptor_elegido: { nombre: string; posicion: string; inferido: boolean }
  receptor_mas_abierto: { nombre: string; posicion: string }
  separaciones: { nombre: string; posicion: string; separacion: number; elegido: boolean }[]
  regret: number
  lado: Lado
  resultado: { pase: 'C' | 'I' | 'IN'; yardas: number; exito: boolean }
}

export type Acumulado = {
  hasta: number
  regret_total: number
  regret_medio: Estimacion
  por_zona: { zona: Zona; estimacion: Estimacion }[]
  por_lado: { lado: Lado; estimacion: Estimacion }[]
  serie: { n: number; acumulado: number }[]
}

export type Alerta = {
  id: string
  nivel: 'info' | 'atencion' | 'critica'
  titulo: Textos
  texto: Textos
  estimacion: Estimacion
}

export type Comparable = { etiqueta: Textos; estimacion: Estimacion }

export type Recomendacion = {
  accion: Textos
  porque: Textos
  estimacion: Estimacion
  comparables: Comparable[]
}

export type EquipoRegret = { equipo: string; estimacion: Estimacion }

export type Evidencia = {
  exito_por_zona: { zona: Zona; estimacion: Estimacion }[]
  exito_por_separacion: { rango: string; estimacion: Estimacion }[]
  exito_por_cobertura: { cobertura: 'Man' | 'Zone'; estimacion: Estimacion }[]
}

export type Fuente = 'ia' | 'plantilla'
export type Explicacion = { texto: Textos; fuente: Fuente }
export type ChatReq = { gameId: number; hasta: number; mensaje: string }
export type ChatResp = { respuesta: string; fuente: Fuente }

export type FiltrosSala = { down: number; yardsToGo: number; zona: Zona; cobertura: Cobertura }
