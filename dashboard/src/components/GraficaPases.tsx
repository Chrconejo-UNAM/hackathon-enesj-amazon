import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useApi } from '../useApi'
import Cargando from './Cargando'
import ErrorEstado from './ErrorEstado'
import Vacio from './Vacio'

/** Barras de n_pases por partido (GET api/partidos). Estados: cargando, vacío, error. */
export default function GraficaPases() {
  const { estado, datos, error, reintentar } = useApi(() => api.partidos(), [])

  if (estado === 'cargando') return <Cargando />
  if (estado === 'error') {
    return <ErrorEstado detail={error ?? 'Error al cargar los partidos'} onReintentar={reintentar} />
  }
  if (estado === 'vacio' || !datos) return <Vacio texto="Sin partidos disponibles" />

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
