import { useRef, useState, type KeyboardEvent } from 'react'
import Inicio from './screens/Inicio'
import SalaDecisiones from './screens/SalaDecisiones'
import TableroRegret from './screens/TableroRegret'
import { useAppState } from './state'
import { t } from './i18n'

const TABS = [
  { id: 'inicio', key: 'tab.inicio', Comp: Inicio },
  { id: 'sala', key: 'tab.sala', Comp: SalaDecisiones },
  { id: 'tablero', key: 'tab.tablero', Comp: TableroRegret },
] as const

export default function App() {
  const { lang, setLang, bandaLateral, setBandaLateral } = useAppState()
  const [tab, setTab] = useState(0)
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  const onKey = (e: KeyboardEvent, i: number) => {
    let j = i
    if (e.key === 'ArrowRight') j = (i + 1) % TABS.length
    else if (e.key === 'ArrowLeft') j = (i - 1 + TABS.length) % TABS.length
    else if (e.key === 'Home') j = 0
    else if (e.key === 'End') j = TABS.length - 1
    else return
    e.preventDefault()
    setTab(j)
    refs.current[j]?.focus()
  }

  const Active = TABS[tab].Comp

  return (
    <div className={`min-h-screen pb-16 lg:pb-0 ${bandaLateral ? 'banda text-lg' : ''}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b p-3">
        <h1 className="text-xl font-bold">La Jugada Correcta</h1>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded border px-3 py-1 focus:outline focus:outline-2"
            onClick={() => setLang(lang === 'es' ? 'en' : 'es')}
            aria-label={t(lang, 'btn.idioma')}
          >
            {lang === 'es' ? 'ES' : 'EN'}
          </button>
          <button
            type="button"
            aria-pressed={bandaLateral}
            className={`rounded border px-3 py-1 focus:outline focus:outline-2 ${bandaLateral ? 'bg-black text-white' : ''}`}
            onClick={() => setBandaLateral(!bandaLateral)}
          >
            {t(lang, 'btn.banda')}
          </button>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl flex-col lg:flex-row">
        <div className="min-w-0 flex-1">
          <div
            role="tablist"
            className="fixed inset-x-0 bottom-0 z-10 flex border-t bg-white lg:static lg:border-b lg:border-t-0"
          >
            {TABS.map((tb, i) => (
              <button
                key={tb.id}
                ref={(el) => { refs.current[i] = el }}
                role="tab"
                id={`tab-${tb.id}`}
                type="button"
                aria-selected={tab === i}
                aria-controls="tabpanel"
                tabIndex={tab === i ? 0 : -1}
                className={`flex-1 px-2 py-3 text-sm focus:outline focus:outline-2 ${tab === i ? 'border-t-2 border-black font-semibold lg:border-b-2 lg:border-t-0' : 'text-gray-600'}`}
                onClick={() => setTab(i)}
                onKeyDown={(e) => onKey(e, i)}
              >
                {t(lang, tb.key)}
              </button>
            ))}
          </div>
          <main id="tabpanel" role="tabpanel" aria-labelledby={`tab-${TABS[tab].id}`} className="p-4">
            <Active />
          </main>
        </div>
        <aside id="panel-ia" className="lg:w-80 lg:shrink-0 lg:border-l" />
      </div>
    </div>
  )
}
