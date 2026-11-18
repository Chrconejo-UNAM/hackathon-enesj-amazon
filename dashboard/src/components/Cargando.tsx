/** Esqueleto de carga accesible. */
export default function Cargando({ texto = 'Cargando…', className = 'h-64' }: { texto?: string; className?: string }) {
  return (
    <div aria-busy="true" role="status" className={`${className} animate-pulse rounded bg-gray-200`}>
      <span className="sr-only">{texto}</span>
    </div>
  )
}
