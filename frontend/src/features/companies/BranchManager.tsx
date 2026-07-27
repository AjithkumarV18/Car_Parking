import { useCallback, useEffect, useState, type FormEvent } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Grid2, IconButton, Paper, Stack, TextField, Typography } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

import { companyApi, type Address, type Branch, type BranchPayload, type Company, type ParkingLocation, type ParkingLocationPayload } from '@/features/companies/companyApi';
import { LoadingState } from '@/shared/components/LoadingState';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const emptyAddress = (): Address => ({ line1: '', line2: '', city: '', state: '', postal_code: '', country_code: 'IN' });
const emptyBranch = (): BranchPayload => ({ name: '', code: '', address: emptyAddress(), phone: '', email: '', timezone: 'Asia/Kolkata' });
const emptyLocation = (): ParkingLocationPayload => ({ name: '', code: '', address: emptyAddress(), capacity: 0, phone: '', geo: null });

interface BranchManagerProps { company: Company; }

export function BranchManager({ company }: BranchManagerProps) {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [editing, setEditing] = useState<Branch>();
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(undefined);
    try { const response = await companyApi.listBranches(company.id); setBranches(response.data?.items ?? []); }
    catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to load branches.')); }
    finally { setLoading(false); }
  }, [company.id]);
  useEffect(() => { void load(); }, [load]);

  async function remove(branch: Branch) {
    if (!window.confirm(`Deactivate ${branch.name}? Its locations will also be deactivated.`)) return;
    try { await companyApi.removeBranch(company.id, branch.id); await load(); }
    catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to deactivate branch.')); }
  }

  return <Paper variant="outlined" sx={{ p: 2, mt: 3 }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} spacing={1} mb={2}>
      <Box><Typography variant="h6">Branches and parking locations</Typography><Typography variant="body2" color="text.secondary">Manage facilities for {company.company_name}.</Typography></Box>
      <Button startIcon={<AddIcon />} variant="outlined" onClick={() => setCreating(true)}>Add branch</Button>
    </Stack>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {loading ? <LoadingState /> : branches.length === 0 ? <Typography color="text.secondary">No branches yet.</Typography> : branches.map((branch) => <Accordion key={branch.id} disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}><Box flexGrow={1}><Typography fontWeight={600}>{branch.name}</Typography><Typography variant="body2" color="text.secondary">{branch.code} · {branch.address.city}</Typography></Box><IconButton aria-label="Edit branch" onClick={(event) => { event.stopPropagation(); setEditing(branch); }}><EditOutlinedIcon /></IconButton><IconButton aria-label="Delete branch" color="error" onClick={(event) => { event.stopPropagation(); void remove(branch); }}><DeleteOutlineIcon /></IconButton></AccordionSummary>
      <AccordionDetails><LocationManager company={company} branch={branch} /></AccordionDetails>
    </Accordion>)}
    <BranchDialog open={creating || Boolean(editing)} branch={editing} onClose={() => { setCreating(false); setEditing(undefined); }} onSaved={() => { void load(); }} companyId={company.id} />
  </Paper>;
}

interface BranchDialogProps { open: boolean; branch?: Branch; companyId: string; onClose: () => void; onSaved: () => void; }
function BranchDialog({ open, branch, companyId, onClose, onSaved }: BranchDialogProps) {
  const [form, setForm] = useState<BranchPayload>(emptyBranch()); const [error, setError] = useState<string>(); const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) { setForm(branch ? { name: branch.name, code: branch.code, address: branch.address, phone: branch.phone, email: branch.email, timezone: branch.timezone } : emptyBranch()); setError(undefined); } }, [open, branch]);
  const address = (key: keyof Address, value: string) => setForm((current) => ({ ...current, address: { ...current.address, [key]: value } }));
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setSaving(true); setError(undefined); try { const payload = { ...form, code: form.code?.trim() || undefined, phone: form.phone?.trim() || null, email: form.email?.trim() || null, address: { ...form.address, line2: form.address.line2?.trim() || null } }; const response = branch ? await companyApi.updateBranch(companyId, branch.id, payload) : await companyApi.createBranch(companyId, payload); if (!response.data) throw new Error(response.message); onSaved(); onClose(); } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to save branch.')); } finally { setSaving(false); } }
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" PaperProps={{ component: 'form', onSubmit: submit }}><DialogTitle>{branch ? 'Edit branch' : 'Add branch'}</DialogTitle><DialogContent dividers><Grid2 container spacing={2} sx={{ pt: 0.5 }}>
    {error && <Grid2 size={12}><Alert severity="error">{error}</Alert></Grid2>}
    <Grid2 size={{ xs: 12, sm: 8 }}><TextField label="Branch name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Code" value={form.code ?? ''} onChange={(e) => setForm({ ...form, code: e.target.value })} fullWidth /></Grid2>
    <Grid2 size={12}><TextField label="Address line 1" value={form.address.line1} onChange={(e) => address('line1', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="City" value={form.address.city} onChange={(e) => address('city', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="State" value={form.address.state} onChange={(e) => address('state', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 8, sm: 6 }}><TextField label="Postal code" value={form.address.postal_code} onChange={(e) => address('postal_code', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 4, sm: 6 }}><TextField label="Country" value={form.address.country_code} onChange={(e) => address('country_code', e.target.value)} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Email" type="email" value={form.email ?? ''} onChange={(e) => setForm({ ...form, email: e.target.value })} fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Phone" value={form.phone ?? ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} fullWidth /></Grid2>
  </Grid2></DialogContent><DialogActions><Button onClick={onClose}>Cancel</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Saving…' : 'Save branch'}</Button></DialogActions></Dialog>;
}

function LocationManager({ company, branch }: { company: Company; branch: Branch }) {
  const [locations, setLocations] = useState<ParkingLocation[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState<string>(); const [creating, setCreating] = useState(false); const [editing, setEditing] = useState<ParkingLocation>();
  const load = useCallback(async () => { setLoading(true); try { const response = await companyApi.listLocations(company.id, branch.id); setLocations(response.data?.items ?? []); } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to load parking locations.')); } finally { setLoading(false); } }, [company.id, branch.id]);
  useEffect(() => { void load(); }, [load]);
  async function remove(location: ParkingLocation) { if (!window.confirm(`Deactivate ${location.name}?`)) return; try { await companyApi.removeLocation(company.id, branch.id, location.id); await load(); } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to deactivate location.')); } }
  return <Box><Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}><Typography fontWeight={600}>Parking locations</Typography><Button size="small" startIcon={<AddIcon />} onClick={() => setCreating(true)}>Add location</Button></Stack>{error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}{loading ? <LoadingState label="Loading locations…" /> : locations.length === 0 ? <Typography variant="body2" color="text.secondary">No locations yet.</Typography> : locations.map((location) => <Stack key={location.id} direction="row" alignItems="center" justifyContent="space-between" py={0.5}><Typography>{location.name} <Typography component="span" variant="body2" color="text.secondary">({location.code}; {location.capacity} spaces)</Typography></Typography><Box><IconButton size="small" onClick={() => setEditing(location)}><EditOutlinedIcon fontSize="small" /></IconButton><IconButton size="small" color="error" onClick={() => { void remove(location); }}><DeleteOutlineIcon fontSize="small" /></IconButton></Box></Stack>)}<Divider sx={{ mt: 1 }} /><LocationDialog open={creating || Boolean(editing)} location={editing} companyId={company.id} branchId={branch.id} onClose={() => { setCreating(false); setEditing(undefined); }} onSaved={() => { void load(); }} /></Box>;
}

interface LocationDialogProps { open: boolean; location?: ParkingLocation; companyId: string; branchId: string; onClose: () => void; onSaved: () => void; }
function LocationDialog({ open, location, companyId, branchId, onClose, onSaved }: LocationDialogProps) {
  const [form, setForm] = useState<ParkingLocationPayload>(emptyLocation()); const [error, setError] = useState<string>(); const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) { setForm(location ? { name: location.name, code: location.code, address: location.address, geo: location.geo, capacity: location.capacity, phone: location.phone } : emptyLocation()); setError(undefined); } }, [open, location]);
  const address = (key: keyof Address, value: string) => setForm((current) => ({ ...current, address: { ...current.address, [key]: value } }));
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setSaving(true); setError(undefined); try { const payload = { ...form, code: form.code?.trim() || undefined, phone: form.phone?.trim() || null, address: { ...form.address, line2: form.address.line2?.trim() || null } }; const response = location ? await companyApi.updateLocation(companyId, branchId, location.id, payload) : await companyApi.createLocation(companyId, branchId, payload); if (!response.data) throw new Error(response.message); onSaved(); onClose(); } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to save parking location.')); } finally { setSaving(false); } }
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" PaperProps={{ component: 'form', onSubmit: submit }}><DialogTitle>{location ? 'Edit parking location' : 'Add parking location'}</DialogTitle><DialogContent dividers><Grid2 container spacing={2} sx={{ pt: 0.5 }}>
    {error && <Grid2 size={12}><Alert severity="error">{error}</Alert></Grid2>}
    <Grid2 size={{ xs: 12, sm: 8 }}><TextField label="Location name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Code" value={form.code ?? ''} onChange={(e) => setForm({ ...form, code: e.target.value })} fullWidth /></Grid2>
    <Grid2 size={12}><TextField label="Address line 1" value={form.address.line1} onChange={(e) => address('line1', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="City" value={form.address.city} onChange={(e) => address('city', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="State" value={form.address.state} onChange={(e) => address('state', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 8, sm: 6 }}><TextField label="Postal code" value={form.address.postal_code} onChange={(e) => address('postal_code', e.target.value)} required fullWidth /></Grid2><Grid2 size={{ xs: 4, sm: 6 }}><TextField label="Country" value={form.address.country_code} onChange={(e) => address('country_code', e.target.value)} required fullWidth /></Grid2>
    <Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Capacity" type="number" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })} inputProps={{ min: 0 }} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Phone" value={form.phone ?? ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} fullWidth /></Grid2>
  </Grid2></DialogContent><DialogActions><Button onClick={onClose}>Cancel</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Saving…' : 'Save location'}</Button></DialogActions></Dialog>;
}
