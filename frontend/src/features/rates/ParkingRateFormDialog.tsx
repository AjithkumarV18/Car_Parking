import { useEffect, useState, type FormEvent } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Grid2, IconButton, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';

import { parkingRateApi, type DurationSlab, type ParkingRate, type ParkingRatePayload } from '@/features/rates/rateApi';
import { useTranslation } from '@/features/preferences/useTranslation';
import { parkingRateStatuses, VEHICLE_TYPES, vehicleTypeLabels } from '@/shared/constants/parking';
import { getApiErrorMessage } from '@/shared/utils/apiError';

interface ParkingRateFormDialogProps {
  open: boolean;
  rate?: ParkingRate;
  onClose: () => void;
  onSaved: (rate: ParkingRate) => void;
}

type RateMode = 'hourly' | 'single' | 'custom';

const emptySlab = (): DurationSlab => ({ from_minutes: 0, to_minutes: null, amount: '0.00', gst_percent: '18.00' });

function hourlySlabs(count = 4): DurationSlab[] {
  return Array.from({ length: count }, (_, index) => ({
    from_minutes: index * 60,
    to_minutes: index === count - 1 ? null : (index + 1) * 60,
    amount: '',
    gst_percent: '18.00',
  }));
}

function rebaseSlabs(slabs: DurationSlab[]): DurationSlab[] {
  return slabs.map((slab, index) => ({ ...slab, from_minutes: index === 0 ? 0 : Number(slabs[index - 1].to_minutes ?? 0) }));
}

function isHourlyGrid(slabs: DurationSlab[]): boolean {
  return slabs.length > 1 && slabs.every((slab, index) => slab.from_minutes === index * 60 && (index === slabs.length - 1 ? slab.to_minutes === null : slab.to_minutes === (index + 1) * 60));
}

function modeFor(rate?: ParkingRate): RateMode {
  if (!rate) return 'hourly';
  if (rate.duration_slabs.length === 1 && rate.duration_slabs[0].to_minutes === null) return 'single';
  return isHourlyGrid(rate.duration_slabs) ? 'hourly' : 'custom';
}

function emptyPayload(): ParkingRatePayload {
  return { vehicle_type: 'car', duration_slabs: hourlySlabs(), effective_date: new Date().toISOString().slice(0, 10), status: 'active' };
}

function payloadFromRate(rate?: ParkingRate): ParkingRatePayload {
  return rate ? { vehicle_type: rate.vehicle_type, duration_slabs: rate.duration_slabs, effective_date: rate.effective_date, status: rate.status } : emptyPayload();
}

function durationLabel(slab: DurationSlab, t: (value: string) => string): string {
  const minutes = slab.to_minutes ?? slab.from_minutes;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  const hour = hours === 1 ? t('hr') : t('hrs');
  const value = hours && remainder ? `${hours} ${hour} ${remainder} ${t('min')}` : hours ? `${hours} ${hour}` : `${remainder} ${t('min')}`;
  return slab.to_minutes === null ? `${value} ${t('onwards')}` : value;
}

export function ParkingRateFormDialog({ open, rate, onClose, onSaved }: ParkingRateFormDialogProps) {
  const { t } = useTranslation();
  const [form, setForm] = useState<ParkingRatePayload>(payloadFromRate(rate));
  const [mode, setMode] = useState<RateMode>(modeFor(rate));
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    const payload = payloadFromRate(rate);
    setForm(payload);
    setMode(modeFor(rate));
    setError(undefined);
  }, [open, rate]);

  function updateSlab(index: number, changes: Partial<DurationSlab>) {
    setForm((current) => ({ ...current, duration_slabs: rebaseSlabs(current.duration_slabs.map((slab, currentIndex) => currentIndex === index ? { ...slab, ...changes } : slab)) }));
  }

  function chooseMode(nextMode: RateMode) {
    if (nextMode === mode) return;
    setMode(nextMode);
    setError(undefined);
    setForm((current) => {
      const first = current.duration_slabs[0] ?? emptySlab();
      if (nextMode === 'hourly') return { ...current, duration_slabs: hourlySlabs() };
      if (nextMode === 'single') return { ...current, duration_slabs: [{ ...first, from_minutes: 0, to_minutes: null }] };
      return { ...current, duration_slabs: current.duration_slabs.length > 1 ? rebaseSlabs(current.duration_slabs) : [{ ...first, from_minutes: 0, to_minutes: 60 }, { ...emptySlab(), from_minutes: 60, amount: first.amount, gst_percent: first.gst_percent }] };
    });
  }

  function addHourlyRow() {
    setForm((current) => {
      const last = current.duration_slabs.at(-1);
      if (!last) return current;
      const closeAt = last.from_minutes + 60;
      return { ...current, duration_slabs: [...current.duration_slabs.slice(0, -1), { ...last, to_minutes: closeAt }, { ...last, from_minutes: closeAt, to_minutes: null, amount: '' }] };
    });
  }

  function addCustomSlab() {
    const last = form.duration_slabs.at(-1);
    if (!last || last.to_minutes === null || Number(last.to_minutes) <= last.from_minutes) {
      setError('Set an end duration on the current row before adding the next row.');
      return;
    }
    setError(undefined);
    setForm((current) => ({ ...current, duration_slabs: [...current.duration_slabs, { ...emptySlab(), from_minutes: Number(last.to_minutes), gst_percent: last.gst_percent }] }));
  }

  function removeSlab(index: number) {
    if (form.duration_slabs.length === 1) return;
    setForm((current) => ({ ...current, duration_slabs: rebaseSlabs(current.duration_slabs.filter((_, currentIndex) => currentIndex !== index)) }));
  }

  function applyGstToAll(value: string) {
    setForm((current) => ({ ...current, duration_slabs: current.duration_slabs.map((slab) => ({ ...slab, gst_percent: value })) }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (form.duration_slabs.some((slab) => !slab.amount.trim())) {
      setError('Enter a parking amount in every rate row.');
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      const payload = { ...form, duration_slabs: rebaseSlabs(form.duration_slabs) };
      const response = rate ? await parkingRateApi.update(rate.id, payload) : await parkingRateApi.create(payload);
      if (!response.data) throw new Error(response.message);
      onSaved(response.data);
      onClose();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to save parking rate.'));
    } finally {
      setSaving(false);
    }
  }

  const commonGst = form.duration_slabs[0]?.gst_percent ?? '18.00';

  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" PaperProps={{ component: 'form', onSubmit: submit }}>
    <DialogTitle>{rate ? 'Edit parking rate' : 'Create parking rate'}</DialogTitle>
    <DialogContent dividers>
      <Grid2 container spacing={2} sx={{ pt: 0.5 }}>
        {error && <Grid2 size={12}><Alert severity="error">{error}</Alert></Grid2>}
        <Grid2 size={{ xs: 12, sm: 4 }}><TextField select label="Vehicle type" value={form.vehicle_type} onChange={(event) => setForm({ ...form, vehicle_type: event.target.value as ParkingRatePayload['vehicle_type'] })} fullWidth required>{VEHICLE_TYPES.map((type) => <MenuItem key={type} value={type}>{vehicleTypeLabels[type]}</MenuItem>)}</TextField></Grid2>
        <Grid2 size={{ xs: 12, sm: 4 }}><TextField label="Effective date" type="date" value={form.effective_date} onChange={(event) => setForm({ ...form, effective_date: event.target.value })} InputLabelProps={{ shrink: true }} fullWidth required /></Grid2>
        <Grid2 size={{ xs: 12, sm: 4 }}><TextField select label="Status" value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as ParkingRatePayload['status'] })} fullWidth>{parkingRateStatuses.map((item) => <MenuItem key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</MenuItem>)}</TextField></Grid2>
        <Grid2 size={12}><Divider /><Typography fontWeight={800} mt={2}>Rate entry</Typography><Typography variant="body2" color="text.secondary" mb={1.25}>Use the hourly grid to type rates such as 50, 60, 70, and 80. GST is set once and copied to every row.</Typography><ToggleButtonGroup exclusive value={mode} onChange={(_, value: RateMode | null) => value && chooseMode(value)} size="small"><ToggleButton value="hourly">Hourly grid</ToggleButton><ToggleButton value="single">One amount</ToggleButton><ToggleButton value="custom">Custom durations</ToggleButton></ToggleButtonGroup></Grid2>
        {mode === 'hourly' && <Grid2 size={12}><Paper variant="outlined" sx={{ overflowX: 'auto' }}><Stack direction={{ xs: 'column', sm: 'row' }} gap={1.5} justifyContent="space-between" alignItems={{ sm: 'center' }} sx={{ px: 2, py: 1.5, bgcolor: 'action.hover' }}><Typography fontWeight={700}>Hourly rate grid</Typography><Stack direction="row" gap={1}><TextField label="GST for all rows" type="number" value={commonGst} onChange={(event) => applyGstToAll(event.target.value)} inputProps={{ min: 0, max: 100, step: '0.01' }} size="small" sx={{ width: 160 }} /><Button size="small" startIcon={<AddIcon />} onClick={addHourlyRow}>Add hour</Button></Stack></Stack><Table size="small" sx={{ minWidth: 560 }}><TableHead><TableRow><TableCell>Duration</TableCell><TableCell width="35%">Parking amount</TableCell><TableCell>GST</TableCell></TableRow></TableHead><TableBody>{form.duration_slabs.map((slab, index) => <TableRow key={`${slab.from_minutes}-${index}`}><TableCell><Typography fontWeight={700}>{durationLabel(slab, t)}</Typography></TableCell><TableCell><TextField type="number" value={slab.amount} onChange={(event) => updateSlab(index, { amount: event.target.value })} placeholder="e.g. 50" inputProps={{ min: 0, step: '0.01' }} required fullWidth size="small" /></TableCell><TableCell>{slab.gst_percent}%</TableCell></TableRow>)}</TableBody></Table></Paper></Grid2>}
        {mode === 'single' && <Grid2 size={12}><Paper variant="outlined" sx={{ p: 2 }}><Typography fontWeight={700} mb={0.5}>One price for the entire stay</Typography><Typography variant="body2" color="text.secondary" mb={1.5}>Use this when the client charges the same amount regardless of duration.</Typography><Grid2 container spacing={1.5}><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="Parking amount" type="number" value={form.duration_slabs[0]?.amount ?? ''} onChange={(event) => updateSlab(0, { amount: event.target.value })} inputProps={{ min: 0, step: '0.01' }} required fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label="GST %" type="number" value={form.duration_slabs[0]?.gst_percent ?? '18.00'} onChange={(event) => updateSlab(0, { gst_percent: event.target.value })} inputProps={{ min: 0, max: 100, step: '0.01' }} required fullWidth /></Grid2></Grid2></Paper></Grid2>}
        {mode === 'custom' && <Grid2 size={12}><Stack spacing={1.25}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1}><Box><Typography fontWeight={700}>Custom duration grid</Typography><Typography variant="body2" color="text.secondary">Set the end time for each row. The next row starts automatically.</Typography></Box><Button size="small" startIcon={<AddIcon />} onClick={addCustomSlab}>Add row</Button></Stack>{form.duration_slabs.map((slab, index) => <CustomRateRow key={`${index}-${slab.from_minutes}`} index={index} slab={slab} isLast={index === form.duration_slabs.length - 1} canRemove={form.duration_slabs.length > 1} onChange={updateSlab} onRemove={removeSlab} />)}</Stack></Grid2>}
      </Grid2>
    </DialogContent>
    <DialogActions><Button onClick={onClose}>Cancel</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Saving…' : 'Save rate'}</Button></DialogActions>
  </Dialog>;
}

interface CustomRateRowProps {
  index: number;
  slab: DurationSlab;
  isLast: boolean;
  canRemove: boolean;
  onChange: (index: number, changes: Partial<DurationSlab>) => void;
  onRemove: (index: number) => void;
}

function CustomRateRow({ index, slab, isLast, canRemove, onChange, onRemove }: CustomRateRowProps) {
  return <Paper variant="outlined" sx={{ p: 1.5 }}><Grid2 container spacing={1.5} alignItems="center"><Grid2 size={{ xs: 12, sm: 2 }}><TextField label="From min" value={slab.from_minutes} InputProps={{ readOnly: true }} fullWidth size="small" /></Grid2><Grid2 size={{ xs: 12, sm: 2 }}><TextField label={isLast ? 'To min (blank = open)' : 'To min'} type="number" value={slab.to_minutes ?? ''} onChange={(event) => onChange(index, { to_minutes: event.target.value === '' ? null : Number(event.target.value) })} inputProps={{ min: slab.from_minutes + 1, max: 525600 }} required={!isLast} fullWidth size="small" /></Grid2><Grid2 size={{ xs: 12, sm: 3 }}><TextField label="Amount" type="number" value={slab.amount} onChange={(event) => onChange(index, { amount: event.target.value })} inputProps={{ min: 0, step: '0.01' }} required fullWidth size="small" /></Grid2><Grid2 size={{ xs: 10, sm: 3 }}><TextField label="GST %" type="number" value={slab.gst_percent} onChange={(event) => onChange(index, { gst_percent: event.target.value })} inputProps={{ min: 0, max: 100, step: '0.01' }} required fullWidth size="small" /></Grid2><Grid2 size={{ xs: 2, sm: 2 }} textAlign="right"><IconButton aria-label="Remove rate row" disabled={!canRemove} color="error" onClick={() => onRemove(index)}><DeleteOutlineIcon /></IconButton></Grid2></Grid2></Paper>;
}
