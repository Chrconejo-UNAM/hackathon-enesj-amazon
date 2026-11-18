/** Estado de error: muestra detail y botón Reintentar. */
export default function ErrorEstado({
  detail,
  onReintentar,
  textoReintentar = 'Reintentar',
}: {
  detail: string
  onReintentar: () => void
  textoReintentar?: string
}) {
  return (
    <div role="alert" className="rounded border border-red-300 bg-red-50 p-4">
      <p className="text-red-900">{detail}</p>
      <button
        type="button"
        onClick={onReintentar}
        className="mt-2 rounded bg-red-700 px-3 py-1 text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-red-900 focus-visible:ring-offset-2"
      >
        {textoReintentar}
      </button>
    </div>
  )
}
