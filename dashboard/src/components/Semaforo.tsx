import type { Confianza } from '../types'

export type Lang = 'es' | 'en'

const TEXTOS: Record<Confianza, Record<Lang, string>> = {
  verde: { es: 'Confiable', en: 'Reliable' },
  amarillo: { es: 'Con reservas', en: 'Use with caution' },
  rojo: { es: 'No concluyente', en: 'Inconclusive' },
}
const ICONOS: Record<Confianza, string> = { verde: '✔', amarillo: '▲', rojo: '✖' }
const CLASES: Record<Confianza, string> = {
  verde: 'bg-green-100 text-green-900 border-green-700',
  amarillo: 'bg-yellow-100 text-yellow-900 border-yellow-700',
  rojo: 'bg-red-100 text-red-900 border-red-700',
}

/** Semáforo de confianza: ícono + texto, nunca solo color. */
export default function Semaforo({ confianza, lang = 'es' }: { confianza: Confianza; lang?: Lang }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm font-medium ${CLASES[confianza]}`}
    >
      <span aria-hidden="true">{ICONOS[confianza]}</span>
      {TEXTOS[confianza][lang]}
    </span>
  )
}
