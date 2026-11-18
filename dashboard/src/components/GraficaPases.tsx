import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useApi } from '../useApi'

/** Barras de n_pases por partido (GET api/partidos). Estados: cargando, vacío, error. */
export default function GraficaPases() {
  const { estado, datos, error, reintentar } = useApi(() => api.partidos(), [])

  if (estado === 'cargando') {
    return <div aria-busy="true" className="h-64 animate-pulse rounded bg-gray-200">
      <span className="sr-only">Cargando…</span>
    </div>
  }
  if (estado === 'error') {
    return (
      <div role="alert" className="rounded border border-red-300 bg-red-50 p-4">
        <p className="text-red-800">{error ?? 'Error al cargar los partidos'}</p>
        <button type="button" onClick={reintentar}
          className="mt-2 rounded bg-red-700 px-3 py-1 text-white focus:outline-none focus:ring-2 focus:ring-red-400">
          Reintentar
        </button>
      </div>
    )
  }
  if (estado === 'vacio' || !datos) {
    return <p className="rounded border border-gray-300 p-4 text-gray-700">Sin partidos disponibles</p>
  }

  const filas = datos.map((p) => ({
    nombre: `S${p.semana} ${p.visitante}@${p.local}`,
    n_pases: p.n_pases,
  }))

  return (
    <div className="h-64 w-full" role="img" aria-label="Pases por partido">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={filas} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="nombre" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis width={36} />
          <Tooltip />
          <Bar dataKey="n_pases" name="Pases" fill="#2F7D4F" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
