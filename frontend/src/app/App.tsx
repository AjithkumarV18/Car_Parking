import { CssBaseline, ThemeProvider } from '@mui/material';
import { BrowserRouter } from 'react-router-dom';

import { AppRouter } from '@/app/router';
import { createAppTheme } from '@/app/theme';
import { AuthProvider } from '@/features/auth/AuthContext';
import { useAuth } from '@/features/auth/useAuth';
import { NotificationProvider } from '@/features/notifications/NotificationProvider';
import { PreferencesProvider } from '@/features/preferences/PreferencesProvider';
import { TranslationLayer } from '@/features/preferences/TranslationLayer';
import { usePreferences } from '@/features/preferences/usePreferences';
import { PublicCompanyProvider } from '@/features/setup/PublicCompanyProvider';
import { usePublicCompany } from '@/features/setup/usePublicCompany';
import { ErrorBoundary } from '@/shared/components/ErrorBoundary';

export function App() {
  return <PreferencesProvider><PublicCompanyProvider><AuthProvider><ThemedApp /></AuthProvider></PublicCompanyProvider></PreferencesProvider>;
}

function ThemedApp() {
  const { mode } = usePreferences();
  const { user } = useAuth();
  const { company } = usePublicCompany();
  const companyTheme = user?.companyTheme ?? (company ? { primaryColor: company.theme.primary_color, secondaryColor: company.theme.secondary_color } : null);
  return (
    <ThemeProvider theme={createAppTheme(mode, companyTheme)}>
      <CssBaseline />
      <TranslationLayer />
      <ErrorBoundary>
        <NotificationProvider>
          <BrowserRouter>
            <AppRouter />
          </BrowserRouter>
        </NotificationProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}
