import { createTheme, type PaletteMode } from '@mui/material/styles';

import type { CompanyThemeColors } from '@/shared/types/auth';

const defaultPrimary = '#0B4F6C';
const defaultSecondary = '#EF8354';
const hexColor = /^#[0-9A-Fa-f]{6}$/;

function colorOrFallback(value: string | null | undefined, fallback: string): string {
  return value && hexColor.test(value) ? value.toUpperCase() : fallback;
}

export function createAppTheme(mode: PaletteMode, companyTheme?: CompanyThemeColors | null) {
  const primary = colorOrFallback(companyTheme?.primaryColor, defaultPrimary);
  const secondary = colorOrFallback(companyTheme?.secondaryColor, defaultSecondary);

  return createTheme({
  palette: {
    mode,
    primary: { main: primary },
    secondary: { main: secondary },
    background: mode === 'dark' ? { default: '#111827', paper: '#1f2937' } : { default: '#f7f9fc', paper: '#ffffff' },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: '"Noto Sans Tamil", Inter, Roboto, Helvetica, Arial, sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
  },
  components: {
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { borderRadius: 10, fontWeight: 700, textTransform: 'none' } } },
    MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 10 } } },
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none', borderRadius: 12 } } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 800, backgroundColor: mode === 'dark' ? '#182334' : '#F4F7FB' } } },
  },
  });
}
