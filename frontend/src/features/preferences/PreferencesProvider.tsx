import { useMemo, useState, type ReactNode } from 'react';
import type { PaletteMode } from '@mui/material';
import { PreferencesContext, type AppLanguage } from '@/features/preferences/context';
import { translate } from '@/features/preferences/translations';

function read<T>(key: string, fallback: T): T {
  try { return (localStorage.getItem(key) as T | null) ?? fallback; } catch { return fallback; }
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<PaletteMode>(() => read<PaletteMode>('parking.color-mode', 'light'));
  const [language, setLanguageState] = useState<AppLanguage>(() => read<AppLanguage>('parking.language', 'en'));
  const value = useMemo(() => ({ mode, language, locale: language === 'ta' ? 'ta-IN' : language === 'hi' ? 'hi-IN' : 'en-IN', t: (value: string) => translate(value, language), toggleMode: () => setMode((current) => { const next = current === 'dark' ? 'light' : 'dark'; localStorage.setItem('parking.color-mode', next); return next; }), setLanguage: (next: AppLanguage) => { localStorage.setItem('parking.language', next); setLanguageState(next); } }), [language, mode]);
  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}
