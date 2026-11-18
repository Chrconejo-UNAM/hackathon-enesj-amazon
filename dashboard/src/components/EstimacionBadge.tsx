import type { Estimacion } from '../types'
import Semaforo, { type Lang } from './Semaforo'

type Props = {
  estimacion: Estimacion
  /** 'pct' para tasas (0-1), 'yds' para yardas */
  unidad?: 'pct' | 'yds'
  lang?: Lang
}

const T = {
  es: { ic: 'IC95 %', noConcl: 'aún no es concluyente', yds: 'yd' },
  en: { ic: '95% CI', noConcl: 'not conclusive yet', yds: 'yd' },
}

/** Valor, IC95 %, n, semáforo y aviso si n<30 o concluyente=false. */
export default function EstimacionBadge({ estimacion, unidad = 'yds', lang = 'es' }: Props) {
  const { valor, ic95, n, concluyente, confianza } = estimacion
  const t = T[lang]
  const fmt = (x: number) => (unidad === 'pct' ? `${(x * 100).toFixed(0)} %` : `${x.toFixed(2)} ${t.yds}`)
  const noConcluyente = n < 30 || !concluyente
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <span className="text-lg font-semibold text-gray-900">{fmt(valor)}</span>
      <span className="text-sm text-gray-700">
        {t.ic} [{fmt(ic95[0])}, {fmt(ic95[1])}] · n={n}
      </span>
      <Semaforo confianza={noConcluyente ? 'rojo' : confianza} lang={lang} />
      {noConcluyente && <span className="text-sm font-medium text-red-800">{t.noConcl}</span>}
    </div>
  )
}
