import { usePreferences } from '@/features/preferences/usePreferences';

export function useTranslation() {
  const { language, locale, t } = usePreferences();
  return { language, locale, t };
}
