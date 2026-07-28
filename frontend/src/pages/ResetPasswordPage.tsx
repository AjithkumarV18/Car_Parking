import { useState, type FormEvent } from 'react';
import { Alert, Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';

import { authApi } from '@/features/auth/authApi';
import { getApiErrorMessage } from '@/shared/utils/apiError';

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [companyId, setCompanyId] = useState('');
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string>();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    try {
      await authApi.resetPassword(companyId, token, password);
      navigate('/login', { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to reset password.'));
    }
  }

  return <Paper component="form" onSubmit={submit} sx={{ maxWidth: 460, mx: 'auto', p: 4 }}><Stack spacing={2}>
    <Typography variant="h5">Choose a new password</Typography>
    {error && <Alert severity="error">{error}</Alert>}
    <TextField label="Company ID" value={companyId} onChange={(event) => setCompanyId(event.target.value)} required />
    <TextField label="Reset token" value={token} onChange={(event) => setToken(event.target.value)} required multiline minRows={3} />
    <TextField label="New password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required inputProps={{ minLength: 3 }} helperText="At least 3 characters" />
    <Button type="submit" variant="contained">Reset password</Button>
    <Button component={Link} to="/login">Return to sign in</Button>
  </Stack></Paper>;
}
