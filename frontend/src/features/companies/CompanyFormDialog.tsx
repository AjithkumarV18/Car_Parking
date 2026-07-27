import { useEffect, useState, type FormEvent } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid2, MenuItem, TextField } from '@mui/material';

import { companyApi, type Company, type CompanyPayload } from '@/features/companies/companyApi';
import { ImageUploadField } from '@/shared/components/ImageUploadField';
import { getApiErrorMessage } from '@/shared/utils/apiError';

interface CompanyFormDialogProps {
  open: boolean;
  company: Company;
  onClose: () => void;
  onSaved: (company: Company) => void;
}

type CompanyProfilePayload = Omit<CompanyPayload, 'theme'>;

function payloadFromCompany(company: Company): CompanyProfilePayload {
  return {
    company_name: company.company_name, code: company.code, logo_url: company.logo_url, address: company.address,
    gstin: company.gstin, currency: company.currency, receipt_footer: company.receipt_footer,
    phone: company.phone, email: company.email, date_format: company.date_format, time_format: company.time_format,
    timezone: company.timezone,
  };
}

export function CompanyFormDialog({ open, company, onClose, onSaved }: CompanyFormDialogProps) {
  const [form, setForm] = useState<CompanyProfilePayload>(payloadFromCompany(company));
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (open) { setForm(payloadFromCompany(company)); setError(undefined); } }, [open, company]);

  const update = <K extends keyof CompanyProfilePayload>(key: K, value: CompanyProfilePayload[K]) => setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(undefined);
    try {
      const normalized: CompanyProfilePayload = {
        ...form,
        company_name: form.company_name.trim(), code: form.code?.trim() || undefined, logo_url: form.logo_url?.trim() || null, gstin: form.gstin?.trim() || null, receipt_footer: form.receipt_footer?.trim() || null,
        phone: form.phone.trim(), email: form.email.trim(), currency: form.currency.trim(), address: { ...form.address, line2: form.address.line2?.trim() || null },
      };
      const response = await companyApi.update(company.id, normalized);
      if (!response.data) throw new Error(response.message);
      onSaved(response.data); onClose();
    } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to save company.')); } finally { setSaving(false); }
  }

  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" PaperProps={{ component: 'form', onSubmit: submit }}>
    <DialogTitle>Edit company</DialogTitle>
    <DialogContent dividers><Grid2 container spacing={2} sx={{ pt: 0.5 }}>
      {error && <Grid2 size={12}><Alert severity="error">{error}</Alert></Grid2>}
      <Grid2 size={{ xs: 12, sm: 8 }}><TextField label="Company name" value={form.company_name} onChange={(e) => update('company_name', e.target.value)} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Code" value={form.code ?? ''} onChange={(e) => update('code', e.target.value)} fullWidth helperText="Optional; auto-generated when blank" /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Email" type="email" value={form.email} onChange={(e) => update('email', e.target.value)} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Phone" value={form.phone} onChange={(e) => update('phone', e.target.value)} required fullWidth placeholder="+919999999999" /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="GSTIN" value={form.gstin ?? ''} onChange={(e) => update('gstin', e.target.value)} fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 6 }}><ImageUploadField label="Company logo" value={form.logo_url} onChange={(value) => update('logo_url', value)} shape="rounded" fallbackText="Logo" /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Currency" value={form.currency} onChange={(e) => update('currency', e.target.value)} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField select label="Date format" value={form.date_format} onChange={(e) => update('date_format', e.target.value as CompanyPayload['date_format'])} fullWidth><MenuItem value="DD/MM/YYYY">DD/MM/YYYY</MenuItem><MenuItem value="MM/DD/YYYY">MM/DD/YYYY</MenuItem><MenuItem value="YYYY-MM-DD">YYYY-MM-DD</MenuItem></TextField></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField select label="Time format" value={form.time_format} onChange={(e) => update('time_format', e.target.value as CompanyPayload['time_format'])} fullWidth><MenuItem value="24h">24-hour</MenuItem><MenuItem value="12h">12-hour</MenuItem></TextField></Grid2>
      <Grid2 size={12}><TextField label="Receipt footer" value={form.receipt_footer ?? ''} onChange={(e) => update('receipt_footer', e.target.value)} multiline minRows={2} fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 8 }}><TextField label="Address line 1" value={form.address.line1} onChange={(e) => update('address', { ...form.address, line1: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Address line 2" value={form.address.line2 ?? ''} onChange={(e) => update('address', { ...form.address, line2: e.target.value })} fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="City" value={form.address.city} onChange={(e) => update('address', { ...form.address, city: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="State" value={form.address.state} onChange={(e) => update('address', { ...form.address, state: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 8, sm: 2 }}><TextField label="Postal code" value={form.address.postal_code} onChange={(e) => update('address', { ...form.address, postal_code: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={{ xs: 4, sm: 2 }}><TextField label="Country" value={form.address.country_code} onChange={(e) => update('address', { ...form.address, country_code: e.target.value })} required fullWidth /></Grid2>
      <Grid2 size={12}><TextField label="Timezone" value={form.timezone} onChange={(e) => update('timezone', e.target.value)} required fullWidth /></Grid2>
    </Grid2></DialogContent>
    <DialogActions><Button onClick={onClose}>Cancel</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Saving…' : 'Save company'}</Button></DialogActions>
  </Dialog>;
}
