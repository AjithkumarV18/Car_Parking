import { useRef, useState, type ChangeEvent } from 'react';
import BackupIcon from '@mui/icons-material/Backup';
import RestoreIcon from '@mui/icons-material/Restore';
import { Alert, Box, Button, Paper, Stack, Typography } from '@mui/material';

import { useNotification } from '@/features/notifications/useNotification';
import { systemApi } from '@/features/system/systemApi';
import { ConfirmDialog } from '@/shared/components/ConfirmDialog';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

export function SystemMaintenancePage() {
  const notification = useNotification();
  const fileInput = useRef<HTMLInputElement>(null);
  const [backupJson, setBackupJson] = useState<string>();
  const [fileName, setFileName] = useState<string>();
  const [working, setWorking] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  async function downloadBackup() {
    setWorking(true);
    try { const response = await systemApi.backup(); const url = URL.createObjectURL(response.data); const link = document.createElement('a'); link.href = url; link.download = 'parking-tenant-backup.json'; link.click(); URL.revokeObjectURL(url); notification.success('Tenant backup downloaded.'); } catch (requestError) { notification.error(getApiErrorMessage(requestError, 'Unable to create the backup.')); } finally { setWorking(false); }
  }
  async function chooseRestoreFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 25_000_000) { notification.warning('Backup files must be 25 MB or smaller.'); return; }
    try { setBackupJson(await file.text()); setFileName(file.name); } catch { notification.error('Unable to read the selected backup file.'); }
  }
  async function restore() {
    if (!backupJson) return;
    setWorking(true);
    try { const response = await systemApi.restore(backupJson); if (!response.data) throw new Error(response.message); notification.success(`Restore completed: ${Object.values(response.data).reduce((sum, count) => sum + count, 0)} records merged.`); setConfirmOpen(false); setBackupJson(undefined); setFileName(undefined); if (fileInput.current) fileInput.current.value = ''; } catch (requestError) { notification.error(getApiErrorMessage(requestError, 'Unable to restore this backup.')); } finally { setWorking(false); }
  }

  return <><PageHeader title="Backup & restore" description="Super-admin tenant maintenance. Backups exclude user passwords, refresh sessions, and platform role definitions." />
    <Stack spacing={3}><Alert severity="warning">Restore is merge-only: records from this company are inserted or updated by their original identifier. It does not delete records, and it cannot restore data into another company.</Alert>
      <Paper variant="outlined" sx={{ p: { xs: 2.5, md: 4 } }}><Typography variant="h6" fontWeight={800}>Create tenant backup</Typography><Typography color="text.secondary" mt={0.5} mb={2}>Download operational configuration, parking activity, payments, audit history, passes, slots, and reservations.</Typography><Button variant="contained" startIcon={<BackupIcon />} onClick={() => { void downloadBackup(); }} disabled={working}>Download backup</Button></Paper>
      <Paper variant="outlined" sx={{ p: { xs: 2.5, md: 4 } }}><Typography variant="h6" fontWeight={800}>Restore tenant backup</Typography><Typography color="text.secondary" mt={0.5} mb={2}>Only JSON exports created by this system for the currently selected company are accepted.</Typography><Box><Button variant="outlined" component="label" startIcon={<RestoreIcon />} disabled={working}>Choose backup JSON<input ref={fileInput} type="file" accept="application/json,.json" hidden onChange={(event) => { void chooseRestoreFile(event); }} /></Button>{fileName && <Typography component="span" variant="body2" ml={1.5}>{fileName}</Typography>}</Box>{backupJson && <Button color="warning" variant="contained" sx={{ mt: 2 }} onClick={() => setConfirmOpen(true)} disabled={working}>Review & restore</Button>}</Paper>
    </Stack>
    <ConfirmDialog open={confirmOpen} title="Restore this tenant backup?" description="The backup will be validated against the selected company, then its records will be merged into the database. Existing data is not deleted." confirmLabel="Restore backup" confirmColor="warning" loading={working} onCancel={() => setConfirmOpen(false)} onConfirm={() => { void restore(); }} />
  </>;
}
