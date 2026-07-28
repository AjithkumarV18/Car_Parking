import { useState, type FormEvent } from 'react';
import { Alert, Avatar, Box, Button, Checkbox, FormControlLabel, Paper, Stack, TextField, Typography } from '@mui/material';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { authApi, toAuthenticatedUser } from '@/features/auth/authApi';
import { useAuth } from '@/features/auth/useAuth';
import { usePublicCompany } from '@/features/setup/usePublicCompany';
import { getApiErrorMessage } from '@/shared/utils/apiError';

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setSession } = useAuth();
  const { company, status, loading: companyLoading, error: companyError } = usePublicCompany();
  const companyId = company?.id ?? searchParams.get('companyId') ?? '';
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  if (!companyLoading && status?.step === 'company') return <Navigate to="/setup/company" replace />;
  if (!companyLoading && status?.step === 'employee') return <Navigate to="/setup/employee" replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!companyId) {
      setError('No active company is available. Complete company setup first.');
      return;
    }
    setError(undefined);
    setSubmitting(true);
    try {
      const response = await authApi.login(companyId, { username, password, remember_me: rememberMe });
      if (!response.data) throw new Error(response.message);
      setSession(response.data.access_token, response.data.refresh_token, rememberMe, toAuthenticatedUser(response.data.user));
      navigate('/app', { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to sign in.'));
    } finally {
      setSubmitting(false);
    }
  }

  return <Paper component="form" onSubmit={submit} sx={{ maxWidth: 460, mx: 'auto', p: { xs: 2.5, sm: 4 }, borderTop: 4, borderColor: 'secondary.main' }}>
    <Stack spacing={2}>
      <CompanyIdentity company={company} loading={companyLoading} title="Sign in" description="Use your account credentials to access this parking workspace." />
      {(error || companyError) && <Alert severity="error">{error ?? 'Unable to load the active company details. Please retry.'}</Alert>}
      {!companyLoading && !company && !companyError && <Alert severity="warning">No active company is available. Complete company setup first.</Alert>}
      <TextField label="Username" value={username} onChange={(event) => setUsername(event.target.value)} required autoComplete="username" inputProps={{ minLength: 3 }} disabled={companyLoading || !companyId} />
      <TextField label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" inputProps={{ minLength: 3 }} disabled={companyLoading || !companyId} />
      <FormControlLabel control={<Checkbox checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} disabled={companyLoading || !companyId} />} label="Remember me on this device" />
      <Button type="submit" variant="contained" disabled={submitting || companyLoading || !companyId}>{submitting ? 'Signing in...' : 'Sign in'}</Button>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between"><Button component={Link} to="/forgot-password">Forgot password?</Button><Button component={Link} to="/register">Create account</Button></Stack>
    </Stack>
  </Paper>;
}

function CompanyIdentity({ company, loading, title, description }: { company: ReturnType<typeof usePublicCompany>['company']; loading: boolean; title: string; description: string }) {
  return <Stack direction="row" spacing={1.5} alignItems="center"><Avatar variant="rounded" src={company?.logo_url ?? undefined} sx={{ width: 52, height: 52, bgcolor: 'primary.main', fontWeight: 900, fontSize: 22 }}>{company?.company_name.slice(0, 1) ?? 'P'}</Avatar><Box minWidth={0}><Typography variant="h5" fontWeight={900}>{title}</Typography><Typography variant="body2" color="text.secondary">{loading ? 'Loading company details...' : company ? `${description} ${company.company_name}.` : description}</Typography></Box></Stack>;
}
