import { useState, type FormEvent } from 'react';
import { Alert, Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { Link } from 'react-router-dom';

import { authApi } from '@/features/auth/authApi';
import { getApiErrorMessage } from '@/shared/utils/apiError';

export function ForgotPasswordPage() {
  const [companyId, setCompanyId] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState<string>();
  const [debugToken, setDebugToken] = useState<string>();
  const [error, setError] = useState<string>();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    try {
      const response = await authApi.forgotPassword(companyId, email);
      setMessage(response.data?.message ?? response.message);
      setDebugToken(response.data?.debug_reset_token ?? undefined);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to request a password reset.'));
    }
  }

  return <Paper component="form" onSubmit={submit} sx={{ maxWidth: 460, mx: 'auto', p: 4 }}><Stack spacing={2}>
    <Typography variant="h5">Reset password</Typography>
    {error && <Alert severity="error">{error}</Alert>}{message && <Alert severity="success">{message}</Alert>}
    {debugToken && <Alert severity="warning">Development token: {debugToken}</Alert>}
    <TextField label="Company ID" value={companyId} onChange={(event) => setCompanyId(event.target.value)} required />
    <TextField label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
    <Button type="submit" variant="contained">Send reset instructions</Button>
    <Button component={Link} to="/login">Return to sign in</Button>
  </Stack></Paper>;
}
