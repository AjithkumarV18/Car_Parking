import { useState, type FormEvent } from 'react';
import { Alert, Avatar, Box, Button, Checkbox, FormControlLabel, Paper, Stack, TextField, Typography } from '@mui/material';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { authApi, toAuthenticatedUser } from '@/features/auth/authApi';
import { useAuth } from '@/features/auth/useAuth';
import { usePublicCompany } from '@/features/setup/usePublicCompany';
import { getApiErrorMessage } from '@/shared/utils/apiError';

export function RegisterPage() {
  const navigate = useNavigate();
  const { setSession } = useAuth();
  const { company, status, loading: companyLoading, error: companyError } = usePublicCompany();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  if (!companyLoading && status?.step === 'company') return <Navigate to="/setup/company" replace />;
  if (!companyLoading && status?.step === 'employee') return <Navigate to="/setup/employee" replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!company) {
      setError('No active company is available. Complete company setup first.');
      return;
    }
    setError(undefined);
    setSubmitting(true);
    try {
      const response = await authApi.register(company.id, { display_name: displayName, email, password, remember_me: rememberMe });
      if (!response.data) throw new Error(response.message);
      setSession(response.data.access_token, response.data.refresh_token, rememberMe, toAuthenticatedUser(response.data.user));
      navigate('/app', { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to create the account.'));
    } finally {
      setSubmitting(false);
    }
  }

  return <Paper component="form" onSubmit={submit} sx={{ maxWidth: 460, mx: 'auto', p: { xs: 2.5, sm: 4 }, borderTop: 4, borderColor: 'secondary.main' }}>
    <Stack spacing={2}>
      <Stack direction="row" spacing={1.5} alignItems="center"><Avatar variant="rounded" src={company?.logo_url ?? undefined} sx={{ width: 52, height: 52, bgcolor: 'primary.main', fontWeight: 900, fontSize: 22 }}>{company?.company_name.slice(0, 1) ?? 'P'}</Avatar><Box minWidth={0}><Typography variant="h5" fontWeight={900}>Create account</Typography><Typography variant="body2" color="text.secondary">{companyLoading ? 'Loading company details...' : company ? `Create an account for ${company.company_name}.` : 'Create an account after company setup is complete.'}</Typography></Box></Stack>
      {(error || companyError) && <Alert severity="error">{error ?? 'Unable to load the active company details. Please retry.'}</Alert>}
      {!companyLoading && !company && !companyError && <Alert severity="warning">No active company is available. Complete company setup first.</Alert>}
      <TextField label="Display name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} required disabled={companyLoading || !company} />
      <TextField label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" disabled={companyLoading || !company} />
      <TextField label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="new-password" helperText="At least 12 characters, with upper, lower, number, and special character." disabled={companyLoading || !company} />
      <FormControlLabel control={<Checkbox checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} disabled={companyLoading || !company} />} label="Remember me on this device" />
      <Button type="submit" variant="contained" disabled={submitting || companyLoading || !company}>{submitting ? 'Creating...' : 'Create account'}</Button>
      <Button component={Link} to="/login">Already have an account? Sign in</Button>
    </Stack>
  </Paper>;
}
