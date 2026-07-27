import { useCallback, useEffect, useState } from 'react';
import PaletteOutlinedIcon from '@mui/icons-material/PaletteOutlined';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';
import { Alert, Box, Button, FormControlLabel, Grid2, Paper, Stack, Switch, TextField, Typography } from '@mui/material';

import { useAuth } from '@/features/auth/useAuth';
import { companyApi, type Theme } from '@/features/companies/companyApi';
import { usePublicCompany } from '@/features/setup/usePublicCompany';
import { defaultSoftwareSettings, softwareSettingsApi, type SoftwareSettings } from '@/features/settings/softwareSettingsApi';
import { LoadingState } from '@/shared/components/LoadingState';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const defaultTheme: Theme = { primary_color: '#0B4F6C', secondary_color: '#EF8354' };
const hexColor = /^#[0-9A-Fa-f]{6}$/;

interface SettingRowProps {
  setting: keyof SoftwareSettings;
  label: string;
  description: string;
  values: SoftwareSettings;
  onChange: (setting: keyof SoftwareSettings, enabled: boolean) => void;
}

function SettingRow({ setting, label, description, values, onChange }: SettingRowProps) {
  return <FormControlLabel sx={{ alignItems: 'flex-start', m: 0, py: 1.25, borderBottom: 1, borderColor: 'divider', '&:last-child': { borderBottom: 0 } }} control={<Switch checked={values[setting]} onChange={(event) => onChange(setting, event.target.checked)} sx={{ mr: 1 }} />} label={<Stack spacing={0.2}><Typography fontWeight={700}>{label}</Typography><Typography variant="body2" color="text.secondary">{description}</Typography></Stack>} />;
}

function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const pickerValue = hexColor.test(value) ? value : '#000000';
  return <Stack direction="row" spacing={1.25} alignItems="center">
    <Box component="input" type="color" aria-label={`${label} picker`} value={pickerValue} onChange={(event) => onChange(event.target.value.toUpperCase())} sx={{ width: 52, height: 52, p: 0.5, border: 1, borderColor: 'divider', borderRadius: 1.5, bgcolor: 'background.paper', cursor: 'pointer' }} />
    <TextField label={label} value={value} onChange={(event) => onChange(event.target.value.toUpperCase())} error={!hexColor.test(value)} helperText={hexColor.test(value) ? 'Pick a color or enter a #RRGGBB value.' : 'Use #RRGGBB, for example #0B4F6C.'} inputProps={{ maxLength: 7 }} fullWidth />
  </Stack>;
}

export function SoftwareSettingsPage() {
  const { user, refreshProfile } = useAuth();
  const { refresh: refreshPublicCompany } = usePublicCompany();
  const [settings, setSettings] = useState<SoftwareSettings>(defaultSoftwareSettings);
  const [theme, setTheme] = useState<Theme>(defaultTheme);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState<string>();

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      if (!user?.companyId) throw new Error('No active company is selected. Please sign in again.');
      const [settingsResponse, companyResponse] = await Promise.all([softwareSettingsApi.get(), companyApi.get(user.companyId)]);
      if (!settingsResponse.data || !companyResponse.data) throw new Error(settingsResponse.message || companyResponse.message);
      setSettings(settingsResponse.data);
      setTheme(companyResponse.data.theme ?? defaultTheme);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to load software settings.'));
    } finally {
      setLoading(false);
    }
  }, [user?.companyId]);

  useEffect(() => { void load(); }, [load]);

  async function save() {
    if (!user?.companyId) return;
    if (!hexColor.test(theme.primary_color) || !hexColor.test(theme.secondary_color)) {
      setError('Theme colors must be in #RRGGBB format.');
      return;
    }
    setSaving(true);
    setError(undefined);
    setSuccess(undefined);
    try {
      const [settingsResponse, companyResponse] = await Promise.all([
        softwareSettingsApi.update(settings),
        companyApi.update(user.companyId, { theme }),
      ]);
      if (!settingsResponse.data || !companyResponse.data) throw new Error(settingsResponse.message || companyResponse.message);
      setSettings(settingsResponse.data);
      setTheme(companyResponse.data.theme);
      await Promise.all([refreshProfile(), refreshPublicCompany()]);
      setSuccess('Software settings and application colors were saved. The new colors are active now.');
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to save software settings.'));
    } finally {
      setSaving(false);
    }
  }

  const toggle = (setting: keyof SoftwareSettings, enabled: boolean) => setSettings((current) => ({ ...current, [setting]: enabled }));
  const updateColor = (key: 'primary_color' | 'secondary_color', value: string) => setTheme((current) => ({ ...current, [key]: value }));

  return <>
    <PageHeader title="Software settings" description="Control the hardware, operator features, and application appearance for this company." actions={<Button variant="contained" startIcon={<SaveOutlinedIcon />} disabled={saving || loading} onClick={() => { void save(); }}>{saving ? 'Saving…' : 'Save settings'}</Button>} />
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
    {loading ? <LoadingState label="Loading software settings…" /> : <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 } }}>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'center' }} gap={2} mb={2.5}>
          <Stack direction="row" spacing={1.25} alignItems="center"><Box sx={{ display: 'grid', placeItems: 'center', width: 42, height: 42, borderRadius: 2, bgcolor: 'primary.main', color: 'primary.contrastText' }}><PaletteOutlinedIcon /></Box><Box><Typography variant="h6" fontWeight={800}>Application colors</Typography><Typography variant="body2" color="text.secondary">Choose colors for navigation, buttons, charts, and highlighted controls.</Typography></Box></Stack>
          <Box sx={{ minWidth: 220, px: 2, py: 1.25, borderRadius: 2, color: 'primary.contrastText', bgcolor: theme.primary_color, boxShadow: 2 }}><Typography variant="caption" sx={{ opacity: 0.82 }}>Live brand preview</Typography><Typography fontWeight={800}>{user?.companyName || 'Company preview'}</Typography><Box sx={{ width: 72, height: 6, borderRadius: 10, bgcolor: theme.secondary_color, mt: 1 }} /></Box>
        </Stack>
        <Grid2 container spacing={2}><Grid2 size={{ xs: 12, md: 6 }}><ColorField label="Primary color" value={theme.primary_color} onChange={(value) => updateColor('primary_color', value)} /></Grid2><Grid2 size={{ xs: 12, md: 6 }}><ColorField label="Secondary color" value={theme.secondary_color} onChange={(value) => updateColor('secondary_color', value)} /></Grid2></Grid2>
      </Paper>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 } }}><Typography variant="h6" fontWeight={800} mb={1}>Scanning and capture</Typography><SettingRow setting="rfid_entry_enabled" label="RFID entry" description="Show RFID input and scan controls on vehicle entry." values={settings} onChange={toggle} /><SettingRow setting="rfid_exit_enabled" label="RFID exit" description="Allow RFID as a vehicle-exit lookup method." values={settings} onChange={toggle} /><SettingRow setting="qr_entry_enabled" label="QR entry" description="Show QR input and scanning controls on vehicle entry." values={settings} onChange={toggle} /><SettingRow setting="qr_exit_enabled" label="QR exit" description="Allow QR code as a vehicle-exit lookup method." values={settings} onChange={toggle} /><SettingRow setting="webcam_capture_enabled" label="Webcam capture" description="Allow the device camera for QR scanning and vehicle capture." values={settings} onChange={toggle} /><SettingRow setting="vehicle_image_capture_enabled" label="Vehicle image upload" description="Allow vehicle images from camera or file upload." values={settings} onChange={toggle} /></Paper>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 } }}><Typography variant="h6" fontWeight={800} mb={1}>Operations</Typography><SettingRow setting="advance_payment_enabled" label="Advance payment" description="Show and accept advance parking amounts at entry." values={settings} onChange={toggle} /><SettingRow setting="monthly_pass_lookup_enabled" label="Monthly pass lookup" description="Show active pass details on entry and exit screens." values={settings} onChange={toggle} /><SettingRow setting="auto_open_receipt_enabled" label="Auto-open receipts" description="Open the printable receipt automatically after entry or exit." values={settings} onChange={toggle} /></Paper>
    </Stack>}
  </>;
}
