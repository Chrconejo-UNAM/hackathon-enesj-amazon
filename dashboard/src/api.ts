// Cliente único de API. Rutas relativas SIN diagonal inicial: fetch('api/...').
import type {
  Acumulado, Alerta, ChatReq, ChatResp, Cobertura, ErrorApi, EquipoRegret, Evidencia,
  Explicacion, Jugada, Partido, Recomendacion, Resumen, Zona,
} from './types'
import {
  acumuladoMock, alertas, chatMock, equiposMock, escenario, evidencia, evidenciaVacia, explicacionMock, jugadaMock,
  partidos, recomendacionMock, resumen, resumenAmarillo,
} from './mocks'

/** Error con la forma del contrato {detail, codigo}. */
export class ApiError extends Error {
  codigo: string
  constructor(e: ErrorApi) {
    super(e.detail)
    this.codigo = e.codigo
  }
}

export type Endpoint =
  | 'resumen' | 'partidos' | 'jugada' | 'acumulado' | 'alertas'
  | 'recomendacion' | 'regretEquipos' | 'evidencia' | 'explicacion' | 'chat'

// VITE_USE_MOCKS=false apaga todos los mocks. Por defecto (true) rige MOCK_ENDPOINTS.
// Para pasar un endpoint a API real: ponerlo en false aquí (tarea 10).
const GLOBAL = import.meta.env.VITE_USE_MOCKS !== 'false'
export const MOCK_ENDPOINTS: Record<Endpoint, boolean> = {
  resumen: true, partidos: true, jugada: true, acumulado: true, alertas: true,
  recomendacion: true, regretEquipos: true, evidencia: true, explicacion: true, chat: true,
}
const usaMock = (e: Endpoint) => GLOBAL && MOCK_ENDPOINTS[e]

const espera = <T,>(v: T, ms = 250): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms))
const fallo = (detail: string, codigo: string): Promise<never> =>
  new Promise((_, rej) => setTimeout(() => rej(new ApiError({ detail, codigo })), 250))

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const r = await fetch(ruta, init)
  const cuerpo = await r.json().catch(() => null)
  if (!r.ok) {
    throw new ApiError(
      cuerpo && typeof cuerpo.detail === 'string' && cuerpo.codigo
        ? cuerpo
        : { detail: `Error HTTP ${r.status}`, codigo: 'ERROR_INTERNO' },
    )
  }
  return cuerpo as T
}

const qs = (p: Record<string, string | number | undefined>) => {
  const u = new URLSearchParams()
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== '') u.set(k, String(v))
  const s = u.toString()
  return s ? `?${s}` : ''
}

export const api = {
  resumen: (): Promise<Resumen> =>
    usaMock('resumen')
      ? escenario() === 'error' ? fallo('Error simulado del servidor', 'ERROR_INTERNO') : espera(escenario() === 'amarillo' ? resumenAmarillo : resumen)
      : pedir('api/resumen'),

  partidos: (): Promise<Partido[]> =>
    usaMock('partidos') ? espera(escenario() === 'vacio' ? [] : partidos) : pedir('api/partidos'),

  jugada: (gameId: number, n: number): Promise<Jugada> => {
    if (!usaMock('jugada')) return pedir(`api/partido/${gameId}/jugada/${n}`)
    const j = jugadaMock(gameId, n)
    return j ? espera(j) : fallo('Jugada no encontrada', 'NO_ENCONTRADO')
  },

  acumulado: (gameId: number, hasta: number): Promise<Acumulado> =>
    usaMock('acumulado') ? espera(acumuladoMock(gameId, hasta)) : pedir(`api/partido/${gameId}/acumulado${qs({ hasta })}`),

  alertas: (gameId: number, hasta: number): Promise<Alerta[]> =>
    usaMock('alertas')
      ? espera(hasta <= 0 ? [] : alertas.slice(0, Math.min(3, Math.ceil(hasta / 4))))
      : pedir(`api/partido/${gameId}/alertas${qs({ hasta })}`),

  recomendacion: (f: { down: number; yardsToGo: number; zona: Zona; cobertura: Cobertura }): Promise<Recomendacion> =>
    usaMock('recomendacion')
      ? escenario() === 'error' ? fallo('Error simulado del servidor', 'ERROR_INTERNO') : espera(recomendacionMock(f))
      : pedir(`api/recomendacion${qs(f)}`),

  regretEquipos: (zona?: Zona): Promise<EquipoRegret[]> => {
    if (!usaMock('regretEquipos')) return pedir(`api/regret/equipos${qs({ zona })}`)
    if (escenario() === 'error') return fallo('Error simulado del servidor', 'ERROR_INTERNO')
    return espera(equiposMock(zona))
  },

  evidencia: (f: { down: number; yardsToGo: number; zona: Zona }): Promise<Evidencia> =>
    usaMock('evidencia') ? espera(escenario() === 'vacio' ? evidenciaVacia : evidencia) : pedir(`api/evidencia${qs(f)}`),

  explicacion: (f: { down: number; yardsToGo: number; zona: Zona; cobertura: Cobertura }): Promise<Explicacion> =>
    usaMock('explicacion') ? espera(explicacionMock(f.down % 2 === 0)) : pedir(`api/explicacion${qs(f)}`),

  chat: (body: ChatReq): Promise<ChatResp> =>
    usaMock('chat')
      ? espera(chatMock(body.mensaje, body.hasta))
      : pedir('api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
}
