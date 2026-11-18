import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api'
import { useAppState } from '../state'
import { t, tx, type Lang } from '../i18n'
import { useApi } from '../useApi'
import type { Alerta, Fuente } from '../types'
import Cargando from '../components/Cargando'
import ErrorEstado from '../components/ErrorEstado'
import EstimacionBadge from '../components/EstimacionBadge'
import Vacio from '../components/Vacio'

type Mensaje = { id: number; rol: 'user' | 'bot'; texto: string; fuente?: Fuente; error?: boolean }

const NIVEL: Record<Alerta['nivel'], { icono: string; clase: string }> = {
  info: { icono: 'ℹ', clase: 'border-blue-400 bg-blue-50 text-blue-950' },
  atencion: { icono: '▲', clase: 'border-yellow-500 bg-yellow-50 text-yellow-950' },
  critica: { icono: '✖', clase: 'border-red-500 bg-red-50 text-red-950' },
}

const PREGUNTAS = ['q.tiro', 'q.lado', 'q.medio', 'q.vestidor'] as const

function SeccionAlertas({ lang, gameId, estado, datos, error, reintentar }: {
  lang: Lang
  gameId: number | null
  estado: string
  datos: Alerta[] | null
  error: string | null
  reintentar: () => void
}) {
  if (gameId === null) return <Vacio texto={t(lang, 'ia.elige')} />
  if (estado === 'cargando') return <Cargando className="h-24" texto={t(lang, 'estado.cargando')} />
  if (estado === 'error') {
    return <ErrorEstado detail={error ?? t(lang, 'ia.error')} onReintentar={reintentar} textoReintentar={t(lang, 'btn.reintentar')} />
  }
  if (estado === 'vacio' || !datos) return <Vacio texto={t(lang, 'ia.sin_alertas')} />
  return (
    <ul className="space-y-2">
      {datos.map((a) => (
        <li key={a.id} className={`rounded border-l-4 p-2 ${NIVEL[a.nivel].clase}`}>
          <p className="font-semibold">
            <span aria-hidden="true">{NIVEL[a.nivel].icono} </span>
            <span>{t(lang, `ia.nivel.${a.nivel}`)}: </span>
            {tx(a.titulo, lang)}
          </p>
          <p className="text-sm">{tx(a.texto, lang)}</p>
          <EstimacionBadge estimacion={a.estimacion} unidad="yds" lang={lang} />
        </li>
      ))}
    </ul>
  )
}

export default function PanelIA() {
  const { gameId, hasta, lang, panelAbierto, setPanelAbierto, bandaLateral } = useAppState()
  const alertas = useApi<Alerta[]>(
    () => (gameId === null ? Promise.resolve([]) : api.alertas(gameId, hasta)),
    [gameId, hasta],
  )

  // Alertas vistas: se marcan al abrir el panel (o mientras está abierto).
  const [vistas, setVistas] = useState<string[]>([])
  useEffect(() => { setVistas([]) }, [gameId])
  const ids = alertas.estado === 'ok' && alertas.datos ? alertas.datos.map((a) => a.id) : []
  const idsClave = ids.join('|')
  useEffect(() => {
    if (panelAbierto && idsClave) setVistas((v) => Array.from(new Set([...v, ...idsClave.split('|')])))
  }, [panelAbierto, idsClave])
  const nuevas = ids.filter((id) => !vistas.includes(id)).length

  // Chat
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const contador = useRef(0)
  const activo = useRef(true)
  useEffect(() => { activo.current = true; return () => { activo.current = false } }, [])

  const enviar = async (mensaje: string) => {
    const m = mensaje.trim().slice(0, 500)
    if (!m || gameId === null || enviando) return
    setMensajes((x) => [...x, { id: ++contador.current, rol: 'user', texto: m }])
    setTexto('')
    setEnviando(true)
    try {
      const r = await api.chat({ gameId, hasta, mensaje: m })
      if (activo.current) setMensajes((x) => [...x, { id: ++contador.current, rol: 'bot', texto: r.respuesta, fuente: r.fuente }])
    } catch (e) {
      const d = e instanceof Error ? e.message : ''
      if (activo.current) setMensajes((x) => [...x, { id: ++contador.current, rol: 'bot', texto: d || t(lang, 'ia.error'), error: true }])
    } finally {
      if (activo.current) setEnviando(false)
    }
  }

  // Esc cierra el drawer
  useEffect(() => {
    if (!panelAbierto) return
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') setPanelAbierto(false) }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [panelAbierto, setPanelAbierto])

  const cerrarRef = useRef<HTMLButtonElement>(null)
  const abrirRef = useRef<HTMLButtonElement>(null)
  const eraAbierto = useRef(false)
  useEffect(() => {
    if (panelAbierto) cerrarRef.current?.focus()
    else if (eraAbierto.current) abrirRef.current?.focus()
    eraAbierto.current = panelAbierto
  }, [panelAbierto])

  const contenido = (sufijo: string) => (
    <div className={`space-y-4 p-3 ${bandaLateral ? 'text-xl' : ''}`}>
      <section aria-labelledby={`ia-al-${sufijo}`}>
        <h3 id={`ia-al-${sufijo}`} className="mb-2 font-semibold">{t(lang, 'ia.alertas')}</h3>
        <SeccionAlertas
          lang={lang}
          gameId={gameId}
          estado={alertas.estado}
          datos={alertas.datos}
          error={alertas.error}
          reintentar={alertas.reintentar}
        />
      </section>

      {!bandaLateral && (
        <section aria-labelledby={`ia-ch-${sufijo}`}>
          <h3 id={`ia-ch-${sufijo}`} className="mb-2 font-semibold">{t(lang, 'ia.preguntas')}</h3>
          <div className="flex flex-wrap gap-2">
            {PREGUNTAS.map((q) => (
              <button
                key={q}
                type="button"
                disabled={gameId === null || enviando}
                onClick={() => void enviar(t(lang, q))}
                className="rounded border px-2 py-1 text-left text-sm focus:outline focus:outline-2 disabled:opacity-50"
              >
                {t(lang, q)}
              </button>
            ))}
          </div>

          <ul className="my-3 space-y-2" aria-live="polite">
            {mensajes.map((m) => (
              <li
                key={m.id}
                className={`rounded p-2 text-sm ${m.rol === 'user' ? 'bg-gray-100' : m.error ? 'border border-red-300 bg-red-50 text-red-900' : 'border'}`}
                role={m.error ? 'alert' : undefined}
              >
                <span className="font-semibold">{m.rol === 'user' ? t(lang, 'ia.tu') : t(lang, 'ia.asistente')}: </span>
                {m.texto}
                {m.fuente === 'plantilla' && (
                  <span className="ml-2 text-xs italic text-gray-700">({t(lang, 'ia.automatica')})</span>
                )}
              </li>
            ))}
            {enviando && <li className="text-sm text-gray-700">{t(lang, 'ia.pensando')}</li>}
          </ul>

          <form
            onSubmit={(e: FormEvent) => { e.preventDefault(); void enviar(texto) }}
            className="flex flex-col gap-2"
          >
            <label htmlFor={`ia-in-${sufijo}`} className="text-sm">{t(lang, 'ia.chat_label')}</label>
            <input
              id={`ia-in-${sufijo}`}
              type="text"
              maxLength={500}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder={t(lang, 'ia.chat_placeholder')}
              disabled={gameId === null}
              className="rounded border px-2 py-1 focus:outline focus:outline-2"
            />
            <button
              type="submit"
              disabled={gameId === null || enviando || !texto.trim()}
              className="rounded bg-black px-3 py-1 text-white focus:outline focus:outline-2 disabled:opacity-50"
            >
              {t(lang, 'ia.enviar')}
            </button>
          </form>
        </section>
      )}
    </div>
  )

  return (
    <>
      {/* Escritorio ≥1024 px: columna fija */}
      <div className="hidden lg:block">
        <h2 className="border-b p-3 font-bold">{t(lang, 'ia.titulo')}</h2>
        {contenido('d')}
      </div>

      {/* Móvil <1024 px: botón flotante + drawer */}
      <div className="lg:hidden">
        <button
          ref={abrirRef}
          type="button"
          aria-label={t(lang, 'ia.abrir')}
          onClick={() => setPanelAbierto(true)}
          className="fixed bottom-20 right-4 z-20 rounded-full bg-black px-4 py-3 text-white shadow-lg focus:outline focus:outline-2 focus:outline-offset-2"
        >
          <span aria-hidden="true">🤖</span>
          {nuevas > 0 && (
            <span className="ml-1 rounded-full bg-red-700 px-2 text-sm" aria-label={`${nuevas} ${t(lang, 'ia.nuevas')}`}>
              {nuevas}
            </span>
          )}
        </button>

        {panelAbierto && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label={t(lang, 'ia.titulo')}
            className="fixed inset-0 z-30 flex flex-col overflow-y-auto bg-white"
          >
            <div className="flex items-center justify-between border-b p-3">
              <h2 className="font-bold">{t(lang, 'ia.titulo')}</h2>
              <button
                ref={cerrarRef}
                type="button"
                aria-label={t(lang, 'ia.cerrar')}
                onClick={() => setPanelAbierto(false)}
                className="rounded border px-3 py-1 focus:outline focus:outline-2"
              >
                {t(lang, 'ia.cerrar_corto')}
              </button>
            </div>
            {contenido('m')}
          </div>
        )}
      </div>
    </>
  )
}
