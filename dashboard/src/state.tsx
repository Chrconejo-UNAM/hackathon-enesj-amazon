import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Lang } from './i18n'

export type AppState = {
  lang: Lang
  setLang: (l: Lang) => void
  bandaLateral: boolean
  setBandaLateral: (b: boolean) => void
  gameId: number | null
  setGameId: (g: number | null) => void
  hasta: number
  setHasta: (n: number) => void
  panelAbierto: boolean
  setPanelAbierto: (b: boolean) => void
}

const Ctx = createContext<AppState | null>(null)

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>('es')
  const [bandaLateral, setBandaLateral] = useState(false)
  const [gameId, setGameId] = useState<number | null>(null)
  const [hasta, setHasta] = useState(0)
  const [panelAbierto, setPanelAbierto] = useState(false)
  const value = useMemo(
    () => ({ lang, setLang, bandaLateral, setBandaLateral, gameId, setGameId, hasta, setHasta, panelAbierto, setPanelAbierto }),
    [lang, bandaLateral, gameId, hasta, panelAbierto],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAppState(): AppState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAppState fuera de AppStateProvider')
  return v
}
