import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import Cargando from '../components/Cargando'
import ErrorEstado from '../components/ErrorEstado'
import Vacio from '../components/Vacio'
import { api } from '../api'
import { t } from '../i18n'
import type { Lang } from '../i18n'
import { useApi } from '../useApi'
import type { Estimacion, FiltrosSala } from '../types'

type Fila = { nombre: string; pct: number; n: number; est: Estimacion }

function Grafica({ titulo, datos, lang }: { titulo: string; datos: Fila[]; lang: Lang }) {
  return (
    <figure className="rounded border border-gray-300 p-3">
      <figcaption className="mb-2 font-semibold">{titulo}</figcaption>
      <div style={{ width: '100%', height: 200 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={datos}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="nombre" />
            <YAxis unit=" %" domain={[0, 100]} />
            <Tooltip
              formatter={(v, _n, p) => [`${v} % (${t(lang, 'n')}=${(p.payload as Fila).n})`, '']}
            />
            <Bar dataKey="pct" fill="#1d4ed8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

export default function Evidencia({ filtros, lang }: { filtros: FiltrosSala; lang: Lang }) {
  const { down, yardsToGo, zona, cobertura } = filtros
  void cobertura
  const r = useApi(() => api.evidencia({ down, yardsToGo, zona }), [down, yardsToGo, zona])
  if (r.estado === 'cargando') return <Cargando texto={t(lang, 'estado.cargando')} />
  if (r.estado === 'error')
    return <ErrorEstado detail={r.error ?? ''} onReintentar={r.reintentar} textoReintentar={t(lang, 'btn.reintentar')} />
  if (r.estado === 'vacio' || !r.datos) return <Vacio texto={t(lang, 'estado.vacio')} />
  const f = (nombre: string, est: Estimacion): Fila => ({ nombre, pct: Math.round(est.valor * 100), n: est.n, est })
  const d = r.datos
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <Grafica lang={lang} titulo={t(lang, 'ctl.zona')} datos={d.exito_por_zona.map((x) => f(t(lang, `zona.${x.zona}`), x.estimacion))} />
      <Grafica lang={lang} titulo={`${t(lang, 'ctl.distancia')} / sep.`} datos={d.exito_por_separacion.map((x) => f(x.rango, x.estimacion))} />
      <Grafica lang={lang} titulo={t(lang, 'ctl.cobertura')} datos={d.exito_por_cobertura.map((x) => f(t(lang, `cob.${x.cobertura}`), x.estimacion))} />
    </div>
  )
}
