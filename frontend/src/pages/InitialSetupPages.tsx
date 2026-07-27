import { useState, type FormEvent } from 'react';
import { Alert, Box, Button, Grid2, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';
import { Navigate, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';
import { setupApi, type InitialCompanyPayload, type InitialEmployeePayload } from '@/features/setup/setupApi';
import { usePublicCompany } from '@/features/setup/usePublicCompany';
import { setupStorage } from '@/features/setup/setupStorage';
import { LoadingState } from '@/shared/components/LoadingState';
import { ImageUploadField } from '@/shared/components/ImageUploadField';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const emptyAddress = () => ({ line1: '', line2: null, city: '', state: '', postal_code: '', country_code: 'IN' });
const emptyCompany = (): InitialCompanyPayload => ({ company_name: '', code: '', logo_url: null, email: '', phone: '', address: emptyAddress() });
const emptyEmployee = (): InitialEmployeePayload => ({
  employee_id: '', photo_url: null, name: '', gender: 'prefer_not_to_say', email: '', phone: '', designation: 'Administrator', username: '', password: '', address: emptyAddress(), salary: '0.00', joining_date: new Date().toISOString().slice(0, 10),
});

function normalizeIndianPhone(value: string): string {
  const normalized = value.replace(/[\s()-]/g, '');
  if (/^[6-9]\d{9}$/.test(normalized)) return `+91${normalized}`;
  if (/^0[6-9]\d{9}$/.test(normalized)) return `+91${normalized.slice(1)}`;
  if (/^91[6-9]\d{9}$/.test(normalized)) return `+${normalized}`;
  return normalized;
}

function SetupPaper({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <Paper sx={{ maxWidth: 820, mx: 'auto', p: { xs: 2, sm: 4 } }}><Stack spacing={3}><Box><Typography variant="h4" component="h1">{title}</Typography><Typography color="text.secondary" mt={0.5}>{description}</Typography></Box>{children}</Stack></Paper>;
}

export function StartupRedirectPage() {
  const { isAuthenticated } = useAuth();
  const { status: setup, loading, error, refresh } = usePublicCompany();

  if (isAuthenticated) return <Navigate to="/app" replace />;
  if (error) return <SetupPaper title="Unable to start" description="The application could not determine its setup status."><Alert severity="error">{error}</Alert><Button variant="outlined" onClick={() => { void refresh(); }}>Retry</Button></SetupPaper>;
  if (loading) return <LoadingState label="Checking application setup..." />;
  if (!setup) return <LoadingState label="Checking application setup…" />;
  const destination = setup.step === 'company' ? '/setup/company' : setup.step === 'employee' ? '/setup/employee' : `/login${setup.company_id ? `?companyId=${encodeURIComponent(setup.company_id)}` : ''}`;
  return <Navigate to={destination} replace />;
}

export function InitialCompanySetupPage() {
  const navigate = useNavigate();
  const { refresh: refreshCompany } = usePublicCompany();
  const [form, setForm] = useState(emptyCompany);
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const address = (key: keyof InitialCompanyPayload['address'], value: string) => setForm((current) => ({ ...current, address: { ...current.address, [key]: value } }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setSaving(true);
    try {
      const payload = { ...form, company_name: form.company_name.trim(), code: form.code?.trim() || undefined, email: form.email.trim(), phone: normalizeIndianPhone(form.phone), address: { ...form.address, line1: form.address.line1.trim(), city: form.address.city.trim(), state: form.address.state.trim(), postal_code: form.address.postal_code.trim() } };
      const response = await setupApi.createCompany(payload);
      if (!response.data) throw new Error(response.message);
      setupStorage.set(response.data.company.id, response.data.setup_token);
      await refreshCompany();
      navigate('/setup/employee', { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to create the initial company.'));
    } finally { setSaving(false); }
  }

  return <SetupPaper title="Create your company" description="This one-time step configures the first company in the parking system."><Box component="form" onSubmit={submit}><Grid2 container spacing={2}>
    {error && <Grid2 size={12}><Alert severity="error">{error}</Alert></Grid2>}
    <Grid2 size={{ xs: 12, sm: 8 }}><TextField label="Company name" value={form.company_name} onChange={(event) => setForm({ ...form, company_name: event.target.value })} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Code (optional)" value={form.code ?? ''} onChange={(event) => setForm({ ...form, code: event.target.value })} helperText="Generated automatically when blank" fullWidth /></Grid2>
    <Grid2 size={12}><ImageUploadField label="Company logo" value={form.logo_url} onChange={(value) => setForm({ ...form, logo_url: value })} shape="rounded" fallbackText="Logo" /></Grid2>
    <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Email" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Phone" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="9876543210" helperText="A 10-digit Indian mobile number is accepted" required fullWidth /></Grid2>
    <Grid2 size={12}><TextField label="Address line 1" value={form.address.line1} onChange={(event) => address('line1', event.target.value)} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="City" value={form.address.city} onChange={(event) => address('city', event.target.value)} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="State" value={form.address.state} onChange={(event) => address('state', event.target.value)} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Postal code" value={form.address.postal_code} onChange={(event) => address('postal_code', event.target.value)} required fullWidth /></Grid2>
    <Grid2 size={12}><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Creating company…' : 'Continue to employee setup'}</Button></Grid2>
  </Grid2></Box></SetupPaper>;
}

export function InitialEmployeeSetupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyEmployee);
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const setup = setupStorage.get();
  const address = (key: keyof InitialEmployeePayload['address'], value: string) => setForm((current) => ({ ...current, address: { ...current.address, [key]: value } }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!setup) return;
    setError(undefined);
    setSaving(true);
    try {
      const employeeId = form.employee_id.trim().toUpperCase();
      if (!/^[A-Z0-9_-]{3,40}$/.test(employeeId)) throw new Error('Employee ID must contain at least 3 letters, numbers, hyphens, or underscores.');
      const payload = { ...form, employee_id: employeeId, name: form.name.trim(), email: form.email.trim(), phone: normalizeIndianPhone(form.phone), designation: form.designation.trim(), username: form.username.trim(), address: { ...form.address, line1: form.address.line1.trim(), city: form.address.city.trim(), state: form.address.state.trim(), postal_code: form.address.postal_code.trim() } };
      const response = await setupApi.createEmployee(setup.companyId, setup.token, payload);
      if (!response.success) throw new Error(response.message);
      setupStorage.clear();
      navigate(`/login?companyId=${encodeURIComponent(setup.companyId)}`, { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to create the initial employee account.'));
    } finally { setSaving(false); }
  }

  if (!setup) return <SetupPaper title="Continue setup" description="The initial company was created, but this browser no longer has the setup session."><Alert severity="warning">Return to the original browser tab to create the initial employee account.</Alert></SetupPaper>;
  return <SetupPaper title="Create the first employee" description="This employee becomes the Super Admin and can sign in after setup."><Box component="form" onSubmit={submit}><Grid2 container spacing={2}>
    {error && <Grid2 size={12}><Alert severity="error">{error}</Alert></Grid2>}
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Employee ID" value={form.employee_id} onChange={(event) => setForm({ ...form, employee_id: event.target.value })} helperText="At least 3 characters" inputProps={{ minLength: 3 }} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 8 }}><TextField label="Full name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField select label="Gender" value={form.gender} onChange={(event) => setForm({ ...form, gender: event.target.value as InitialEmployeePayload['gender'] })} fullWidth><MenuItem value="male">Male</MenuItem><MenuItem value="female">Female</MenuItem><MenuItem value="non_binary">Non-binary</MenuItem><MenuItem value="prefer_not_to_say">Prefer not to say</MenuItem></TextField></Grid2>
    <Grid2 size={{ xs: 12, sm: 8 }}><ImageUploadField label="Employee photo" value={form.photo_url} onChange={(value) => setForm({ ...form, photo_url: value })} fallbackText={form.name || 'Employee'} /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Email" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Phone" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="9876543210" helperText="10-digit Indian mobile accepted" required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Designation" value={form.designation} onChange={(event) => setForm({ ...form, designation: event.target.value })} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Username" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} required fullWidth /></Grid2>
    <Grid2 size={12}><TextField label="Password" type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} helperText="At least 12 characters with upper, lower, number, and special character" required fullWidth /></Grid2>
    <Grid2 size={12}><TextField label="Address line 1" value={form.address.line1} onChange={(event) => address('line1', event.target.value)} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="City" value={form.address.city} onChange={(event) => address('city', event.target.value)} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="State" value={form.address.state} onChange={(event) => address('state', event.target.value)} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Postal code" value={form.address.postal_code} onChange={(event) => address('postal_code', event.target.value)} required fullWidth /></Grid2>
    <Grid2 size={12}><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Creating employee…' : 'Create employee and continue to sign in'}</Button></Grid2>
  </Grid2></Box></SetupPaper>;
}
