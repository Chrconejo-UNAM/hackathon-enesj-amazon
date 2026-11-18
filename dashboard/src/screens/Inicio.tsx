import GraficaPases from '../components/GraficaPases'
import Cargando from '../components/Cargando'
import ErrorEstado from '../components/ErrorEstado'
import Vacio from '../components/Vacio'
import EstimacionBadge from '../components/EstimacionBadge'
import TarjetaResumen from '../components/TarjetaResumen'
import { api } from '../api'
import { useApi } from '../useApi'
import { useAppState } from '../state'
import { t, tx } from '../i18n'

export default function Inicio() {
  const { lang } = useAppState()
  const { estado, datos, error, reintentar } = useApi(() => api.resumen(), [])

  return (
    <section className="space-y-4">
      {estado === 'cargando' && <Cargando texto={t(lang, 'estado.cargando')} className="h-32" />}
      {estado === 'error' && (
        <ErrorEstado
          detail={error ?? t(lang, 'estado.error')}
          onReintentar={reintentar}
          textoReintentar={t(lang, 'btn.reintentar')}
        />
      )}
      {estado === 'vacio' && <Vacio texto={t(lang, 'estado.vacio')} />}
      {estado === 'ok' && datos && (
        <>
          <h2 className="text-xl font-semibold text-gray-900 sm:text-2xl">{tx(datos.titulo, lang)}</h2>
          <TarjetaResumen
            etiqueta={tx(datos.linea, lang)}
            nota={`${t(lang, 'base')} · ${datos.calidad_datos.pct_objetivo_inferido.toFixed(1)} %`}
          >
            <EstimacionBadge estimacion={datos.regret_liga} unidad="yds" lang={lang} />
          </TarjetaResumen>
        </>
      )}
      <GraficaPases />
    </section>
  )
}
