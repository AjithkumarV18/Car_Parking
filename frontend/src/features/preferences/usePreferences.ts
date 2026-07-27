import { useContext } from 'react';

import { PreferencesContext, type PreferencesValue } from '@/features/preferences/context';

export function usePreferences(): PreferencesValue {
  const context = useContext(PreferencesContext);
  if (!context) throw new Error('usePreferences must be used within PreferencesProvider.');
  return context;
}
