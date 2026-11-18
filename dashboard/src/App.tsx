import GraficaPases from './components/GraficaPases'

export default function App() {
  return (
    <main className="mx-auto max-w-3xl p-4">
      <h1 className="text-2xl font-bold">La Jugada Correcta</h1>
      <h2 className="mb-2 text-gray-600">Pases por partido</h2>
      <GraficaPases />
    </main>
  )
}
