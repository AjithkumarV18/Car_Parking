import { createContext } from 'react';
import type { PaletteMode } from '@mui/material';

export type AppLanguage = 'en' | 'hi' | 'ta';

export interface PreferencesValue {
  mode: PaletteMode;
  language: AppLanguage;
  locale: string;
  t: (value: string) => string;
  toggleMode: () => void;
  setLanguage: (value: AppLanguage) => void;
}

export const PreferencesContext = createContext<PreferencesValue | null>(null);
