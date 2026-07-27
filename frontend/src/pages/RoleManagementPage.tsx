import { useCallback, useEffect, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import { Alert, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';

import { RoleFormDialog } from '@/features/roles/RoleFormDialog';
import { roleApi, type Permission, type Role } from '@/features/roles/roleApi';
import { useNotification } from '@/features/notifications/useNotification';
import { ConfirmDialog } from '@/shared/components/ConfirmDialog';
import { LoadingState } from '@/shared/components/LoadingState';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

export function RoleManagementPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Role>();
  const [details, setDetails] = useState<Role>();
  const [deleting, setDeleting] = useState<Role>();
  const [removing, setRemoving] = useState(false);
  const notifications = useNotification();

  const load = useCallback(async () => {
    setLoading(true); setError(undefined);
    try {
      const [roleResponse, permissionResponse] = await Promise.all([roleApi.list(), roleApi.permissions()]);
      setRoles(roleResponse.data ?? []); setPermissions(permissionResponse.data ?? []);
    } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to load roles.')); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  function saved(role: Role) { setRoles((current) => current.some((item) => item.id === role.id) ? current.map((item) => item.id === role.id ? role : item) : [...current, role]); }
  async function remove(role?: Role) { if (role) { setDeleting(role); return; } if (!deleting) return; setRemoving(true); try { await roleApi.remove(deleting.id); setDeleting(undefined); notifications.success(`${deleting.name} was deleted.`); await load(); } catch (requestError) { const message = getApiErrorMessage(requestError, 'Unable to delete role.'); setError(message); notifications.error(message); } finally { setRemoving(false); } }

  return <>
    <PageHeader title="Role management" description="System templates and tenant-specific roles with an explicit permission matrix." actions={<Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreating(true)}>Create role</Button>} />
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    <Paper variant="outlined" sx={{ overflowX: 'auto' }}>{loading ? <LoadingState label="Loading roles…" /> : <Table sx={{ minWidth: 760 }}><TableHead><TableRow><TableCell>Role</TableCell><TableCell>Scope</TableCell><TableCell>Permissions</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead><TableBody>{roles.map((role) => <TableRow key={role.id}><TableCell><Typography fontWeight={600}>{role.name}</Typography><Typography variant="body2" color="text.secondary">{role.description || role.code}</Typography></TableCell><TableCell><Chip size="small" label={role.is_system ? 'System template' : 'Company custom'} color={role.is_system ? 'secondary' : 'primary'} /></TableCell><TableCell>{role.permissions.length} selected</TableCell><TableCell align="right"><IconButton aria-label="View role" onClick={() => setDetails(role)}><VisibilityOutlinedIcon /></IconButton><IconButton aria-label="Edit role" onClick={() => setEditing(role)}><EditOutlinedIcon /></IconButton>{!role.is_system && <IconButton aria-label="Delete role" color="error" onClick={() => { void remove(role); }}><DeleteOutlineIcon /></IconButton>}</TableCell></TableRow>)}</TableBody></Table>}</Paper>
    <RoleFormDialog open={creating || Boolean(editing)} role={editing} permissions={permissions} onClose={() => { setCreating(false); setEditing(undefined); }} onSaved={saved} />
    <Dialog open={Boolean(details)} onClose={() => setDetails(undefined)} fullWidth maxWidth="sm"><DialogTitle>{details?.name}</DialogTitle><DialogContent><Typography color="text.secondary" mb={2}>{details?.description || 'No description provided.'}</Typography><Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>{details?.permissions.map((permission) => <Chip key={permission.key} label={permission.key} variant="outlined" />)}</Stack></DialogContent><DialogActions><Button onClick={() => setDetails(undefined)}>Close</Button></DialogActions></Dialog>
    <ConfirmDialog open={Boolean(deleting)} title="Delete role?" description={`Delete ${deleting?.name ?? 'this role'}? Users assigned to it may lose its permissions.`} confirmLabel="Delete role" confirmColor="error" loading={removing} onCancel={() => setDeleting(undefined)} onConfirm={() => { void remove(); }} />
  </>;
}
