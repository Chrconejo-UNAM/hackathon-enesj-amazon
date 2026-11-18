import { useState } from 'react'
import { api } from '../api'
import Cargando from '../components/Cargando'
import ErrorEstado from '../components/ErrorEstado'
import EstimacionBadge from '../components/EstimacionBadge'
import Semaforo from '../components/Semaforo'
import Vacio from '../components/Vacio'
import { t, tx } from '../i18n'
import { useAppState } from '../state'
import type { Cobertura, FiltrosSala, Zona } from '../types'
import { useApi } from '../useApi'
import Evidencia from './Evidencia'

const ZONAS = ['todas', 'propia', 'medio', 'roja']
const COBS = ['todas', 'Man', 'Zone']
const selCls = 'rounded border border-gray-400 bg-white px-2 py-1'

export default function SalaDecisiones() {
  const { lang, bandaLateral } = useAppState()
  const [f, setF] = useState<FiltrosSala>({ down: 3, yardsToGo: 5, zona: 'todas' as Zona, cobertura: 'todas' })
  const { down, yardsToGo, zona, cobertura } = f

  const rec = useApi(() => api.recomendacion(f), [down, yardsToGo, zona, cobertura])
  const exp = useApi(() => api.explicacion(f), [down, yardsToGo, zona, cobertura])

  const sinConcl = (n: number, c: boolean) => n < 30 || !c

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col text-sm">
          {t(lang, 'ctl.down')}
          <select className={selCls} value={down} onChange={(e) => setF({ ...f, down: Number(e.target.value) })}>
            {[1, 2, 3, 4].map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label className="flex flex-col text-sm">
          {t(lang, 'ctl.distancia')}
          <input
            type="number" min={1} max={20} className={`${selCls} w-24`} value={yardsToGo}
            onChange={(e) => {
              const v = Math.min(20, Math.max(1, Math.round(Number(e.target.value)) || 1))
              setF({ ...f, yardsToGo: v })
            }}
          />
        </label>
        <label className="flex flex-col text-sm">
          {t(lang, 'ctl.zona')}
          <select className={selCls} value={zona} onChange={(e) => setF({ ...f, zona: e.target.value as Zona })}>
            {ZONAS.map((z) => <option key={z} value={z}>{t(lang, `zona.${z}`)}</option>)}
          </select>
        </label>
        <label className="flex flex-col text-sm">
          {t(lang, 'ctl.cobertura')}
          <select className={selCls} value={cobertura} onChange={(e) => setF({ ...f, cobertura: e.target.value as Cobertura })}>
            {COBS.map((c) => <option key={c} value={c}>{t(lang, `cob.${c}`)}</option>)}
          </select>
        </label>
      </div>

      {rec.estado === 'cargando' && <Cargando texto={t(lang, 'estado.cargando')} />}
      {rec.estado === 'error' && (
        <ErrorEstado detail={rec.error ?? ''} onReintentar={rec.reintentar} textoReintentar={t(lang, 'btn.reintentar')} />
      )}
      {rec.estado === 'vacio' && <Vacio texto={t(lang, 'estado.vacio')} />}
      {rec.estado === 'ok' && rec.datos && (() => {
        const d = rec.datos
        const e = d.estimacion
        const conf = sinConcl(e.n, e.concluyente) ? 'rojo' : e.confianza
        return (
          <>
            <div className="space-y-2 rounded border border-gray-300 p-4">
              <h2 className={bandaLateral ? 'text-4xl font-bold' : 'text-2xl font-bold'}>{tx(d.accion, lang)}</h2>
              <p className={bandaLateral ? 'text-2xl' : ''}>{tx(d.porque, lang)}</p>
              {bandaLateral ? (
                <div className="text-2xl"><Semaforo confianza={conf} lang={lang} /></div>
              ) : (
                <EstimacionBadge estimacion={e} unidad="pct" lang={lang} />
              )}
            </div>

            {!bandaLateral && (
              <>
                {exp.estado === 'ok' && exp.datos && (
                  <p className="rounded bg-gray-50 p-3">
                    {tx(exp.datos.texto, lang)}
                    {exp.datos.fuente === 'plantilla' && (
                      <span className="ml-2 text-xs text-gray-600">({t(lang, 'ia.automatica')})</span>
                    )}
                  </p>
                )}

                {d.comparables.length > 0 && (
                  <ul className="space-y-1">
                    {d.comparables.map((c, i) => (
                      <li key={i} className="flex flex-wrap items-center gap-2 rounded border border-gray-200 p-2">
                        <span className="font-medium">{tx(c.etiqueta, lang)}</span>
                        <EstimacionBadge estimacion={c.estimacion} unidad="pct" lang={lang} />
                      </li>
                    ))}
                  </ul>
                )}

                <Evidencia filtros={f} lang={lang} />
              </>
            )}
          </>
        )
      })()}

      {/* <div id="en-vivo-slot" /> */}
    </section>
  )
}
