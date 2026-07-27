import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material';

import { roleApi, type Permission, type Role, type RolePayload } from '@/features/roles/roleApi';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const actions = ['show', 'save', 'edit', 'delete', 'details'] as const;

interface RoleFormDialogProps {
  open: boolean;
  role?: Role;
  permissions: Permission[];
  onClose: () => void;
  onSaved: (role: Role) => void;
}

export function RoleFormDialog({ open, role, permissions, onClose, onSaved }: RoleFormDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();
  const modules = useMemo(() => [...new Set(permissions.map((permission) => permission.module))], [permissions]);

  useEffect(() => {
    if (!open) return;
    setName(role?.name ?? ''); setDescription(role?.description ?? ''); setSelected(new Set(role?.permissions.map((permission) => permission.key) ?? [])); setError(undefined);
  }, [open, role]);

  function toggle(key: string) {
    setSelected((current) => { const next = new Set(current); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(undefined);
    try {
      const payload: RolePayload = { name, description: description || null, permission_keys: [...selected] };
      const response = role ? await roleApi.update(role.id, payload) : await roleApi.create(payload);
      if (!response.data) throw new Error(response.message);
      onSaved(response.data); onClose();
    } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to save role.')); } finally { setSaving(false); }
  }

  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" PaperProps={{ component: 'form', onSubmit: submit }}>
    <DialogTitle>{role ? 'Edit role' : 'Create role'}</DialogTitle>
    <DialogContent dividers>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <TextField label="Role name" value={name} onChange={(event) => setName(event.target.value)} required fullWidth sx={{ mb: 2 }} />
      <TextField label="Description" value={description} onChange={(event) => setDescription(event.target.value)} fullWidth multiline minRows={2} sx={{ mb: 2 }} />
      <Typography variant="subtitle2" mb={1}>Permission matrix</Typography>
      <Table size="small" sx={{ minWidth: 650 }}><TableHead><TableRow><TableCell>Module</TableCell>{actions.map((action) => <TableCell align="center" key={action} sx={{ textTransform: 'capitalize' }}>{action}</TableCell>)}</TableRow></TableHead><TableBody>{modules.map((module) => <TableRow key={module}><TableCell sx={{ textTransform: 'capitalize' }}>{module}</TableCell>{actions.map((action) => { const permission = permissions.find((item) => item.module === module && item.action === action); return <TableCell align="center" key={action}>{permission ? <Checkbox checked={selected.has(permission.key)} onChange={() => toggle(permission.key)} inputProps={{ 'aria-label': `${module} ${action}` }} /> : '—'}</TableCell>; })}</TableRow>)}</TableBody></Table>
    </DialogContent>
    <DialogActions><Button onClick={onClose}>Cancel</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Saving…' : 'Save role'}</Button></DialogActions>
  </Dialog>;
}
