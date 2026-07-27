import { Fragment, useCallback, useEffect, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import {
  Alert,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';

import { PermissionGate } from '@/features/auth/PermissionGate';
import { useTranslation } from '@/features/preferences/useTranslation';
import { ParkingRateFormDialog } from '@/features/rates/ParkingRateFormDialog';
import { parkingRateApi, type ParkingRate, type ParkingRateFilters } from '@/features/rates/rateApi';
import { parkingRateStatuses, VEHICLE_TYPES, vehicleTypeLabels } from '@/shared/constants/parking';
import { LoadingState } from '@/shared/components/LoadingState';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const initialFilters: ParkingRateFilters = { page: 1, limit: 10, sort_by: 'effective_date', sort_order: 'desc' };

function formatDuration(minutes: number, language: string): string {
  const min = language === 'hi' ? 'मिनट' : 'min';
  if (minutes === 0) return `0 ${min}`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  const hour = language === 'hi' ? (hours === 1 ? 'घंटा' : 'घंटे') : 'hr';
  if (!hours) return `${remainder} ${min}`;
  if (!remainder) return `${hours} ${hour}`;
  return `${hours} ${hour} ${remainder} ${min}`;
}

function durationRange(fromMinutes: number, toMinutes: number | null, language: string): string {
  const onwards = language === 'hi' ? 'से आगे' : 'onwards';
  return toMinutes === null ? `${formatDuration(fromMinutes, language)} ${onwards}` : `${formatDuration(fromMinutes, language)} – ${formatDuration(toMinutes, language)}`;
}

function slabDurationLabel(fromMinutes: number, toMinutes: number | null, language: string): string {
  const onwards = language === 'hi' ? 'से आगे' : 'onwards';
  return toMinutes === null ? `${formatDuration(fromMinutes, language)} ${onwards}` : formatDuration(toMinutes, language);
}

export function ParkingRateMasterPage() {
  const { language, t } = useTranslation();
  const [filters, setFilters] = useState<ParkingRateFilters>(initialFilters);
  const [rates, setRates] = useState<ParkingRate[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<ParkingRate>();
  const [details, setDetails] = useState<ParkingRate>();

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const response = await parkingRateApi.list(filters);
      setRates(response.data?.items ?? []);
      setTotal(response.data?.meta.total ?? 0);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to load parking rates.'));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  function setFilter<K extends keyof ParkingRateFilters>(key: K, value: ParkingRateFilters[K]) {
    setFilters((current) => ({ ...current, [key]: value, page: 1 }));
  }

  function saved(rate: ParkingRate) {
    setRates((current) => current.some((item) => item.id === rate.id)
      ? current.map((item) => item.id === rate.id ? rate : item)
      : [rate, ...current]);
  }

  async function remove(rate: ParkingRate) {
    if (!window.confirm(`Deactivate the ${vehicleTypeLabels[rate.vehicle_type]} rate effective ${rate.effective_date}?`)) return;
    try {
      await parkingRateApi.remove(rate.id);
      await load();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to deactivate parking rate.'));
    }
  }

  return <>
    <PageHeader
      title="Parking rate master"
      description="Effective-dated, GST-aware duration tariffs for each vehicle type."
      actions={<PermissionGate permissions={['rate:save']}><Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreating(true)}>Add rate</Button></PermissionGate>}
    />
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
        <TextField size="small" label="Search vehicle" value={filters.search ?? ''} onChange={(event) => setFilter('search', event.target.value || undefined)} sx={{ minWidth: { md: 180 } }} />
        <TextField select size="small" label="Vehicle type" value={filters.vehicle_type ?? ''} onChange={(event) => setFilter('vehicle_type', (event.target.value || undefined) as ParkingRateFilters['vehicle_type'])} sx={{ minWidth: 150 }}>
          <MenuItem value="">All vehicles</MenuItem>
          {VEHICLE_TYPES.map((type) => <MenuItem key={type} value={type}>{vehicleTypeLabels[type]}</MenuItem>)}
        </TextField>
        <TextField select size="small" label="Status" value={filters.status ?? ''} onChange={(event) => setFilter('status', (event.target.value || undefined) as ParkingRateFilters['status'])} sx={{ minWidth: 130 }}>
          <MenuItem value="">Current</MenuItem>
          {parkingRateStatuses.map((item) => <MenuItem key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</MenuItem>)}
        </TextField>
        <TextField size="small" label="Effective from" type="date" value={filters.effective_from ?? ''} onChange={(event) => setFilter('effective_from', event.target.value || undefined)} InputLabelProps={{ shrink: true }} />
        <TextField size="small" label="Effective to" type="date" value={filters.effective_to ?? ''} onChange={(event) => setFilter('effective_to', event.target.value || undefined)} InputLabelProps={{ shrink: true }} />
        <TextField select size="small" label="Sort" value={filters.sort_by} onChange={(event) => setFilter('sort_by', event.target.value as ParkingRateFilters['sort_by'])} sx={{ minWidth: 150 }}>
          <MenuItem value="effective_date">Effective date</MenuItem>
          <MenuItem value="vehicle_type">Vehicle type</MenuItem>
          <MenuItem value="status">Status</MenuItem>
        </TextField>
        <Button size="small" onClick={() => setFilter('sort_order', filters.sort_order === 'asc' ? 'desc' : 'asc')}>{filters.sort_order === 'asc' ? 'Ascending' : 'Descending'}</Button>
      </Stack>
    </Paper>

    <Paper variant="outlined" sx={{ overflowX: 'auto' }}>
      {loading ? <LoadingState label="Loading parking rates…" /> : <>
        <Table sx={{ minWidth: 960 }}>
          <TableHead>
            <TableRow>
              <TableCell>Vehicle type</TableCell>
              <TableCell>Duration / hours</TableCell>
              <TableCell align="right">Amount (before GST)</TableCell>
              <TableCell align="right">GST</TableCell>
              <TableCell>Effective date</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!rates.length && <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4 }}>No parking rates found.</TableCell></TableRow>}
            {rates.map((rate) => <Fragment key={rate.id}>
              {rate.duration_slabs.map((slab, index) => <TableRow key={`${rate.id}-${slab.from_minutes}-${slab.to_minutes ?? 'onwards'}`} hover>
                {index === 0 && <TableCell rowSpan={rate.duration_slabs.length}><Typography fontWeight={700}>{vehicleTypeLabels[rate.vehicle_type]}</Typography></TableCell>}
                <TableCell><Typography variant="body2" fontWeight={600}>{slabDurationLabel(slab.from_minutes, slab.to_minutes, language)}</Typography></TableCell>
                <TableCell align="right">{Number(slab.amount).toFixed(2)}</TableCell>
                <TableCell align="right">{Number(slab.gst_percent).toFixed(2)}%</TableCell>
                {index === 0 && <TableCell rowSpan={rate.duration_slabs.length}>{rate.effective_date}</TableCell>}
                {index === 0 && <TableCell rowSpan={rate.duration_slabs.length}><Chip label={rate.status} size="small" color={rate.status === 'active' ? 'success' : rate.status === 'draft' ? 'warning' : 'default'} sx={{ textTransform: 'capitalize' }} /></TableCell>}
                {index === 0 && <TableCell rowSpan={rate.duration_slabs.length} align="right">
                  <PermissionGate permissions={['rate:details']}><IconButton aria-label="View parking rate" onClick={() => setDetails(rate)}><VisibilityOutlinedIcon /></IconButton></PermissionGate>
                  <PermissionGate permissions={['rate:edit']}><IconButton aria-label="Edit parking rate" onClick={() => setEditing(rate)}><EditOutlinedIcon /></IconButton></PermissionGate>
                  <PermissionGate permissions={['rate:delete']}><IconButton aria-label="Deactivate parking rate" color="error" onClick={() => { void remove(rate); }}><DeleteOutlineIcon /></IconButton></PermissionGate>
                </TableCell>}
              </TableRow>)}
            </Fragment>)}
          </TableBody>
        </Table>
        <TablePagination component="div" count={total} page={(filters.page ?? 1) - 1} onPageChange={(_, page) => setFilters((current) => ({ ...current, page: page + 1 }))} rowsPerPage={filters.limit ?? 10} onRowsPerPageChange={(event) => setFilters((current) => ({ ...current, limit: Number(event.target.value), page: 1 }))} rowsPerPageOptions={[10, 25, 50, 100]} />
      </>}
    </Paper>

    <ParkingRateFormDialog open={creating || Boolean(editing)} rate={editing} onClose={() => { setCreating(false); setEditing(undefined); }} onSaved={saved} />
    <Dialog open={Boolean(details)} onClose={() => setDetails(undefined)} fullWidth maxWidth="sm">
      <DialogTitle>{details && `${t(vehicleTypeLabels[details.vehicle_type])} ${t('Rate')}`}</DialogTitle>
      <DialogContent>
        <Stack spacing={1.5}>
          <Typography><strong>Effective date:</strong> {details?.effective_date}</Typography>
          <Typography><strong>Status:</strong> {details?.status}</Typography>
          <Typography fontWeight={700}>Duration slabs</Typography>
          {details?.duration_slabs.map((slab) => <Paper key={`${slab.from_minutes}-${slab.to_minutes}`} variant="outlined" sx={{ p: 1.25 }}>
            <Typography>{durationRange(slab.from_minutes, slab.to_minutes, language)}</Typography>
            <Typography variant="body2" color="text.secondary">Amount: {slab.amount} before GST · GST: {slab.gst_percent}%</Typography>
          </Paper>)}
        </Stack>
      </DialogContent>
      <DialogActions><Button onClick={() => setDetails(undefined)}>Close</Button></DialogActions>
    </Dialog>
  </>;
}
