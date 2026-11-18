/** Estado vacío. */
export default function Vacio({ texto = 'Sin jugadas con esos filtros' }: { texto?: string }) {
  return <p className="rounded border border-gray-300 p-4 text-gray-800">{texto}</p>
}
