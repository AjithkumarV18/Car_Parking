import { useCallback, useEffect, useState } from 'react';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import { Alert, Button, Paper, Stack, Typography } from '@mui/material';

import { useAuth } from '@/features/auth/useAuth';
import { BranchManager } from '@/features/companies/BranchManager';
import { CompanyFormDialog } from '@/features/companies/CompanyFormDialog';
import { companyApi, type Company } from '@/features/companies/companyApi';
import { LoadingState } from '@/shared/components/LoadingState';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

export function CompanyManagementPage() {
  const { user, refreshProfile } = useAuth();
  const [company, setCompany] = useState<Company>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [editing, setEditing] = useState<Company>();

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      if (!user?.companyId) throw new Error('No active company is selected. Please sign in again.');
      const response = await companyApi.get(user.companyId);
      if (!response.data) throw new Error(response.message);
      setCompany(response.data);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to load the company.'));
    } finally {
      setLoading(false);
    }
  }, [user?.companyId]);

  useEffect(() => { void load(); }, [load]);

  return <>
    <PageHeader title="Company management" description="Update the company profile and manage its branches and parking locations." />
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {loading ? <LoadingState label="Loading company…" /> : company ? <>
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1}>
          <Stack spacing={0.25}><Typography variant="h6">{company.company_name}</Typography><Typography color="text.secondary">{company.address.line1}, {company.address.city} · {company.phone}</Typography></Stack>
          <Button variant="outlined" startIcon={<EditOutlinedIcon />} onClick={() => setEditing(company)}>Edit company</Button>
        </Stack>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap mt={2}><Typography variant="body2">GST: {company.gstin || 'Not set'}</Typography><Typography variant="body2">Date: {company.date_format}</Typography><Typography variant="body2">Time: {company.time_format}</Typography></Stack>
      </Paper>
      <BranchManager company={company} />
    </> : <Paper variant="outlined" sx={{ p: 4 }}><Typography color="text.secondary">No active company is available.</Typography></Paper>}
    {editing && <CompanyFormDialog open company={editing} onClose={() => setEditing(undefined)} onSaved={(saved) => { setCompany(saved); setEditing(undefined); void refreshProfile(); }} />}
  </>;
}
