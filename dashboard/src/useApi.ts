import { DependencyList, useCallback, useEffect, useRef, useState } from 'react'

export type Estado = 'cargando' | 'vacio' | 'error' | 'ok'

export type ResultadoApi<T> = {
  estado: Estado
  datos: T | null
  error: string | null
  reintentar: () => void
}

const REINTENTO_CARGANDO_MS = 2000

const estaVacio = (d: unknown) => d == null || (Array.isArray(d) && d.length === 0)

/** Ejecuta `fn` al montar y cuando cambian `deps`. VacÃ­o = null o arreglo sin elementos. */
export function useApi<T>(fn: () => Promise<T>, deps: DependencyList = [], vacio: (d: T) => boolean = estaVacio): ResultadoApi<T> {
  const [estado, setEstado] = useState<Estado>('cargando')
  const [datos, setDatos] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [intento, setIntento] = useState(0)
  const fnRef = useRef(fn)
  fnRef.current = fn
  const vacioRef = useRef(vacio)
  vacioRef.current = vacio

  useEffect(() => {
    let activo = true
    let timer: ReturnType<typeof setTimeout> | undefined
    setEstado('cargando')
    setError(null)
    const ejecutar = () => {
      fnRef.current().then(
        (d) => {
          if (!activo) return
          setDatos(d)
          setEstado(vacioRef.current(d) ? 'vacio' : 'ok')
        },
        (e: unknown) => {
          if (!activo) return
          // 503 "cargando": el backend aún está arrancando; reintenta sin mostrar error.
          if ((e as { codigo?: string } | null)?.codigo === 'cargando') {
            timer = setTimeout(ejecutar, REINTENTO_CARGANDO_MS)
            return
          }
          setDatos(null)
          setError(e instanceof Error ? e.message : String(e))
          setEstado('error')
        },
      )
    }
    ejecutar()
    return () => { activo = false; if (timer) clearTimeout(timer) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, intento])
  const reintentar = useCallback(() => setIntento((i) => i + 1), [])
  return { estado, datos, error, reintentar }
}

