import { useState } from 'react'
import Cargando from '../components/Cargando'
import ErrorEstado from '../components/ErrorEstado'
import Semaforo from '../components/Semaforo'
import Vacio from '../components/Vacio'
import { api } from '../api'
import { t } from '../i18n'
import { useAppState } from '../state'
import { useApi } from '../useApi'
import type { Zona } from '../types'

type Filtro = Zona | 'todas'
const FILTROS: Filtro[] = ['todas', 'propia', 'medio', 'roja']

const TXT = {
  es: {
    sinConcluyente: 'Aún no hay un equipo concluyente',
    masArrepiente: 'es el que más se arrepiente',
    yds: 'yds',
    ic: 'IC95 %',
    ranking: 'Ranking de Regret por equipo',
  },
  en: {
    sinConcluyente: 'There is no conclusive team yet',
    masArrepiente: 'regrets the most',
    yds: 'yds',
    ic: '95% CI',
    ranking: 'Regret ranking by team',
  },
}

export default function TableroRegret() {
  const { lang } = useAppState()
  const [zona, setZona] = useState<Filtro>('todas')
  const x = TXT[lang]
  const r = useApi(() => api.regretEquipos(zona === 'todas' ? undefined : zona), [zona])

  const filas = r.datos ? [...r.datos].sort((a, b) => b.estimacion.valor - a.estimacion.valor) : []
  const lider = filas.find((f) => f.estimacion.concluyente)
  const titulo = r.estado === 'ok' ? (lider ? `${lider.equipo} ${x.masArrepiente}` : x.sinConcluyente) : x.ranking

  return (
    <section className="min-w-0">
      <h2 className="mb-3 text-xl font-semibold">{titulo}</h2>

      <div role="group" aria-label={t(lang, 'ctl.zona')} className="mb-3 flex flex-wrap gap-2">
        {FILTROS.map((z) => (
          <button
            key={z}
            type="button"
            aria-pressed={zona === z}
            onClick={() => setZona(z)}
            className={`rounded border px-3 py-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 ${
              zona === z ? 'border-blue-800 bg-blue-800 text-white' : 'border-gray-400 bg-white text-gray-900'
            }`}
          >
            {t(lang, `zona.${z}`)}
          </button>
        ))}
      </div>

      {r.estado === 'cargando' && <Cargando texto={t(lang, 'estado.cargando')} />}
      {r.estado === 'error' && (
        <ErrorEstado detail={r.error ?? ''} onReintentar={r.reintentar} textoReintentar={t(lang, 'btn.reintentar')} />
      )}
      {r.estado === 'vacio' && <Vacio texto={t(lang, 'estado.vacio')} />}
      {r.estado === 'ok' && (
        <ol className="grid gap-2">
          {filas.map((f, i) => {
            const e = f.estimacion
            return (
              <li key={f.equipo} className="min-w-0 rounded border border-gray-300 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">
                    {i + 1}. {f.equipo}
                  </span>
                  <span className="text-lg font-bold">
                    {e.valor.toFixed(2)} {x.yds}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-800">
                  <span>
                    {x.ic}: {e.ic95[0].toFixed(2)} – {e.ic95[1].toFixed(2)}
                  </span>
                  <span>
                    {t(lang, 'n')}={e.n}
                  </span>
                  <Semaforo confianza={e.confianza} lang={lang} />
                  {!e.concluyente && <span className="font-medium text-red-900">{t(lang, 'aviso.no_concluyente')}</span>}
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
