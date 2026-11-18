import type { ReactNode } from 'react'

/** Tarjeta de una línea: etiqueta, contenido y nota opcional. */
export default function TarjetaResumen({
  etiqueta,
  children,
  nota,
}: {
  etiqueta: string
  children: ReactNode
  nota?: string
}) {
  return (
    <section className="rounded-lg border border-gray-300 bg-white p-3 shadow-sm">
      <h3 className="text-sm font-medium text-gray-700">{etiqueta}</h3>
      <div className="mt-1">{children}</div>
      {nota && <p className="mt-1 text-xs text-gray-700">{nota}</p>}
    </section>
  )
}
