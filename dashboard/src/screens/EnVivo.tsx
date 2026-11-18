import { useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api'
import Cargando from '../components/Cargando'
import ErrorEstado from '../components/ErrorEstado'
import EstimacionBadge from '../components/EstimacionBadge'
import Vacio from '../components/Vacio'
import { t } from '../i18n'
import { useAppState } from '../state'
import type { Acumulado, Jugada } from '../types'
import { useApi } from '../useApi'

const btnCls =
  'rounded bg-blue-800 px-4 py-2 text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-900 focus-visible:ring-offset-2 disabled:bg-gray-500'

/** Pide la jugada n; si no existe (404) devuelve 'fin'. Nunca se pide n > hasta. */
async function cargarJugada(gameId: number, n: number): Promise<Jugada | 'fin'> {
  try {
    return await api.jugada(gameId, n)
  } catch (e) {
    if (e instanceof ApiError && e.codigo === 'NO_ENCONTRADO') return 'fin'
    throw e
  }
}

export default function EnVivo() {
  const { gameId, setGameId, hasta, setHasta, lang, bandaLateral } = useAppState()
  const [auto, setAuto] = useState(false)
  const [fin, setFin] = useState(false)
  const hastaRef = useRef(hasta)
  hastaRef.current = hasta

  const partidos = useApi(() => api.partidos(), [])

  // Selecciona el primer partido por defecto.
  useEffect(() => {
    if (gameId == null && partidos.datos && partidos.datos.length > 0) setGameId(partidos.datos[0].gameId)
  }, [gameId, partidos.datos, setGameId])

  const jug = useApi<Jugada | 'fin' | null>(
    () => (gameId != null && hasta >= 1 ? cargarJugada(gameId, hasta) : Promise.resolve(null)),
    [gameId, hasta],
  )
  const acu = useApi<Acumulado | null>(
    () => (gameId != null && hasta >= 1 ? api.acumulado(gameId, hasta) : Promise.resolve(null)),
    [gameId, hasta],
  )

  // Detecta el final: 404 o última jugada.
  useEffect(() => {
    if (jug.estado !== 'ok' || !jug.datos) return
    if (jug.datos === 'fin') {
      setFin(true)
      setAuto(false)
      if (hasta > 1) setHasta(hasta - 1)
    } else if (jug.datos.n >= jug.datos.total) {
      setFin(true)
      setAuto(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jug.estado, jug.datos])

  // Avance automático cada 3 s; se limpia al pausar, al terminar y al desmontar.
  useEffect(() => {
    if (!auto || fin || gameId == null) return
    const id = setInterval(() => setHasta(hastaRef.current + 1), 3000)
    return () => clearInterval(id)
  }, [auto, fin, gameId, setHasta])

  const elegirPartido = (id: number) => {
    setAuto(false)
    setFin(false)
    setHasta(0)
    setGameId(id)
  }
  const siguiente = () => {
    if (!fin) setHasta(hasta + 1)
  }

  const big = bandaLateral ? 'text-2xl' : ''
  const j = jug.datos && jug.datos !== 'fin' ? jug.datos : null

  return (
    <section aria-labelledby="vivo-titulo" className={`space-y-3 rounded border border-gray-300 p-4 ${big}`}>
      <h2 id="vivo-titulo" className="text-xl font-bold">{t(lang, 'vivo.titulo')}</h2>

      {partidos.estado === 'cargando' && <Cargando texto={t(lang, 'estado.cargando')} className="h-12" />}
      {partidos.estado === 'error' && (
        <ErrorEstado detail={partidos.error ?? ''} onReintentar={partidos.reintentar} textoReintentar={t(lang, 'btn.reintentar')} />
      )}
      {partidos.estado === 'vacio' && <Vacio texto={t(lang, 'estado.vacio')} />}
      {partidos.estado === 'ok' && partidos.datos && (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col text-sm">
              {t(lang, 'vivo.partido')}
              <select
                className="rounded border border-gray-400 bg-white px-2 py-1"
                value={gameId ?? ''}
                onChange={(e) => elegirPartido(Number(e.target.value))}
              >
                {partidos.datos.map((p) => (
                  <option key={p.gameId} value={p.gameId}>
                    {`S${p.semana} ${p.visitante} @ ${p.local}`}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className={btnCls} onClick={siguiente} disabled={fin || gameId == null} aria-label={t(lang, 'vivo.siguiente')}>
              {t(lang, 'vivo.siguiente')}
            </button>
            <button
              type="button"
              className={btnCls}
              aria-pressed={auto}
              aria-label={auto ? t(lang, 'vivo.pausa') : t(lang, 'vivo.auto')}
              disabled={fin || gameId == null}
              onClick={() => setAuto(!auto)}
            >
              {auto ? t(lang, 'vivo.pausa') : t(lang, 'vivo.auto')}
            </button>
          </div>

          {fin && <p role="status" className="font-semibold text-blue-900">{t(lang, 'vivo.fin')}</p>}

          {hasta === 0 && <Vacio texto={t(lang, 'estado.vacio')} />}
          {hasta >= 1 && jug.estado === 'cargando' && !j && <Cargando texto={t(lang, 'estado.cargando')} className="h-32" />}
          {jug.estado === 'error' && (
            <ErrorEstado detail={jug.error ?? ''} onReintentar={jug.reintentar} textoReintentar={t(lang, 'btn.reintentar')} />
          )}
          {j && (
            <dl className="grid grid-cols-2 gap-x-3 gap-y-1">
              <dt className="text-gray-700">#</dt>
              <dd>{j.n} / {j.total}</dd>
              <dt className="text-gray-700">{t(lang, 'ctl.down')}</dt>
              <dd>{j.down} &amp; {j.yardsToGo}</dd>
              <dt className="text-gray-700">{t(lang, 'vivo.marcador')}</dt>
              <dd>{j.marcador.local} - {j.marcador.visitante}</dd>
              <dt className="text-gray-700">{t(lang, 'vivo.reloj')}</dt>
              <dd>Q{j.cuarto} {j.reloj}</dd>
              <dt className="text-gray-700">{t(lang, 'ctl.zona')}</dt>
              <dd>{t(lang, `zona.${j.zona}`)}</dd>
              <dt className="text-gray-700">{t(lang, 'vivo.elegido')}</dt>
              <dd>{j.receptor_elegido.nombre} ({j.receptor_elegido.posicion}){j.receptor_elegido.inferido ? ' *' : ''}</dd>
              <dt className="text-gray-700">{t(lang, 'vivo.abierto')}</dt>
              <dd>{j.receptor_mas_abierto.nombre} ({j.receptor_mas_abierto.posicion})</dd>
              <dt className="text-gray-700">{t(lang, 'vivo.regret')}</dt>
              <dd className="font-semibold">{j.regret.toFixed(1)} yd</dd>
              <dt className="text-gray-700">{t(lang, 'vivo.resultado')}</dt>
              <dd>{j.resultado.pase} · {j.resultado.yardas} yd</dd>
            </dl>
          )}

          {hasta >= 1 && (
            <div className="space-y-2 border-t border-gray-300 pt-3">
              <h3 className="font-semibold">{t(lang, 'vivo.acumulado')}</h3>
              {acu.estado === 'cargando' && !acu.datos && <Cargando texto={t(lang, 'estado.cargando')} className="h-24" />}
              {acu.estado === 'error' && (
                <ErrorEstado detail={acu.error ?? ''} onReintentar={acu.reintentar} textoReintentar={t(lang, 'btn.reintentar')} />
              )}
              {acu.estado === 'vacio' && <Vacio texto={t(lang, 'estado.vacio')} />}
              {acu.datos && (
                <div className="space-y-2">
                  <p>
                    {t(lang, 'vivo.total')}: <strong>{acu.datos.regret_total.toFixed(1)} yd</strong>
                  </p>
                  <EstimacionBadge estimacion={acu.datos.regret_medio} unidad="yds" lang={lang} />
                  <h4 className="text-sm font-medium">{t(lang, 'ctl.zona')}</h4>
                  <ul className="space-y-1">
                    {acu.datos.por_zona.map((z) => (
                      <li key={z.zona} className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{t(lang, `zona.${z.zona}`)}</span>
                        <EstimacionBadge estimacion={z.estimacion} unidad="yds" lang={lang} />
                      </li>
                    ))}
                  </ul>
                  <h4 className="text-sm font-medium">{t(lang, 'vivo.lado')}</h4>
                  <ul className="space-y-1">
                    {acu.datos.por_lado.map((l) => (
                      <li key={l.lado} className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{t(lang, `lado.${l.lado}`)}</span>
                        <EstimacionBadge estimacion={l.estimacion} unidad="yds" lang={lang} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  )
}
