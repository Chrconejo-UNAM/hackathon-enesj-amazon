import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import Cargando from '../components/Cargando'
import ErrorEstado from '../components/ErrorEstado'
import Vacio from '../components/Vacio'
import { api } from '../api'
import { t } from '../i18n'
import type { Lang } from '../i18n'
import { useApi } from '../useApi'
import type { Estimacion, Evidencia as EvidenciaT, FiltrosSala } from '../types'

type Fila = { nombre: string; valor: number; n: number }

function Grafica({ titulo, datos, lang, unidad }: { titulo: string; datos: Fila[]; lang: Lang; unidad: string }) {
  return (
    <figure className="rounded border border-gray-300 p-3">
      <figcaption className="mb-2 font-semibold">{titulo}</figcaption>
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={datos}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="nombre" tick={{ fontSize: 10 }} interval={0} />
            <YAxis unit={unidad} />
            <Tooltip formatter={(v, _n, p) => [`${v}${unidad} (${t(lang, 'n')}=${(p.payload as Fila).n})`, '']} />
            <Bar dataKey="valor" fill="#1d4ed8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

const fila = (nombre: string, e: Estimacion): Fila => ({ nombre, valor: +e.valor.toFixed(2), n: e.n })

/** Suma los bins de todas las zonas en un solo histograma de yardas. */
function histograma(d: EvidenciaT['distribucion']): Fila[] {
  const acc = new Map<number, { hasta: number | null; n: number }>()
  for (const z of d) for (const b of z.bins) {
    const prev = acc.get(b.desde)
    acc.set(b.desde, { hasta: b.hasta, n: (prev?.n ?? 0) + b.n })
  }
  return [...acc.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([desde, v]) => ({ nombre: v.hasta == null ? `${desde}+` : `${desde}`, valor: v.n, n: v.n }))
}

export default function Evidencia({ filtros, lang }: { filtros: FiltrosSala; lang: Lang }) {
  const { down, yardsToGo, zona } = filtros
  const r = useApi(
    () => api.evidencia({ down, yardsToGo, zona }),
    [down, yardsToGo, zona],
    (d) => d.valor_por_zona.length === 0 && d.valor_por_cobertura.length === 0 && d.distribucion.length === 0,
  )
  if (r.estado === 'cargando') return <Cargando texto={t(lang, 'estado.cargando')} />
  if (r.estado === 'error')
    return <ErrorEstado detail={r.error ?? ''} onReintentar={r.reintentar} textoReintentar={t(lang, 'btn.reintentar')} />
  if (r.estado === 'vacio' || !r.datos) return <Vacio texto={t(lang, 'estado.vacio')} />
  const d = r.datos
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Grafica lang={lang} unidad=" yd" titulo={`${t(lang, 'sala.yardas_esperadas')} · ${t(lang, 'ctl.zona')}`}
        datos={d.valor_por_zona.map((x) => fila(t(lang, `zona.${x.zona}`), x.estimacion))} />
      <Grafica lang={lang} unidad=" yd" titulo={`${t(lang, 'sala.yardas_esperadas')} · ${t(lang, 'ctl.cobertura')}`}
        datos={d.valor_por_cobertura.map((x) => fila(t(lang, `cob.${x.cobertura}`), x.estimacion))} />
      <Grafica lang={lang} unidad=" yd" titulo={t(lang, 'sala.regret_zona')}
        datos={d.regret_por_zona.map((x) => fila(t(lang, `zona.${x.zona}`), x.estimacion))} />
      <Grafica lang={lang} unidad="" titulo={t(lang, 'sala.distribucion')} datos={histograma(d.distribucion)} />
    </div>
  )
}
