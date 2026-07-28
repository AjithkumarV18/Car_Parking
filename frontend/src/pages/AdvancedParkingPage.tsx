import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import { Alert, Box, Button, Chip, Divider, Grid2, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';

import { advancedApi, type ParkingLocationOption, type ParkingSlot, type ReservedSlot, type SlotStatus } from '@/features/advanced/advancedApi';
import { useAuth } from '@/features/auth/useAuth';
import { useNotification } from '@/features/notifications/useNotification';
import { VEHICLE_TYPES, vehicleTypeLabels, type VehicleType } from '@/shared/constants/parking';
import { EmptyState } from '@/shared/components/EmptyState';
import { LoadingState } from '@/shared/components/LoadingState';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const slotColors: Record<SlotStatus, 'success' | 'error' | 'warning' | 'default'> = {
  available: 'success',
  occupied: 'error',
  reserved: 'warning',
  maintenance: 'default',
};

function toDateTimeLocal(value: Date): string {
  const timezoneOffsetMs = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - timezoneOffsetMs).toISOString().slice(0, 16);
}

function defaultReservationStart(): string {
  return toDateTimeLocal(new Date());
}

function defaultReservationEnd(): string {
  return toDateTimeLocal(new Date(Date.now() + 60 * 60 * 1000));
}

export function AdvancedParkingPage() {
  const { user } = useAuth();
  const notification = useNotification();
  const [locations, setLocations] = useState<ParkingLocationOption[]>([]);
  const [slots, setSlots] = useState<ParkingSlot[]>([]);
  const [reservations, setReservations] = useState<ReservedSlot[]>([]);
  const [locationId, setLocationId] = useState('');
  const [reservationSlotId, setReservationSlotId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [actionError, setActionError] = useState<string>();
  const [saving, setSaving] = useState(false);
  const canManage = Boolean(user?.isSuperAdmin || user?.permissions.includes('advanced:manage'));

  const load = useCallback(async (selectedLocation = locationId) => {
    setLoading(true);
    setError(undefined);
    try {
      const [locationResponse, slotResponse, reservationResponse] = await Promise.all([
        advancedApi.locations(),
        advancedApi.slots(selectedLocation || undefined),
        advancedApi.reservations(),
      ]);
      if (!locationResponse.data || !slotResponse.data || !reservationResponse.data) {
        throw new Error('Parking slot data was unavailable.');
      }
      setLocations(locationResponse.data);
      setSlots(slotResponse.data);
      setReservations(reservationResponse.data);
      if (!selectedLocation && locationResponse.data[0]) setLocationId(locationResponse.data[0].id);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Unable to load parking slot data.'));
    } finally {
      setLoading(false);
    }
  }, [locationId]);

  useEffect(() => { void load(); }, [load]);

  const slotOptions = useMemo(() => slots.filter((slot) => slot.status === 'available'), [slots]);

  useEffect(() => {
    setReservationSlotId((current) =>
      slotOptions.some((slot) => slot.id === current) ? current : (slotOptions[0]?.id ?? ''),
    );
  }, [slotOptions]);

  async function createSlot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const currentLocation = String(values.get('parking_location_id') || locationId);
    if (!currentLocation) {
      notification.warning('Create a parking location before adding slots.');
      return;
    }
    setSaving(true);
    setActionError(undefined);
    try {
      const response = await advancedApi.createSlot({
        parking_location_id: currentLocation,
        slot_number: String(values.get('slot_number')),
        vehicle_type: (String(values.get('vehicle_type')) || null) as VehicleType | null,
        status: 'available',
      });
      if (!response.data) throw new Error(response.message);
      notification.success('Parking slot created.');
      form.reset();
      await load(currentLocation);
    } catch (requestError) {
      const message = getApiErrorMessage(requestError, 'Unable to create parking slot.');
      setActionError(message);
      notification.error(message);
    } finally {
      setSaving(false);
    }
  }

  async function createReservation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!reservationSlotId) {
      const message = 'Select an available parking slot first.';
      setActionError(message);
      notification.error(message);
      return;
    }
    const values = new FormData(form);
    const validFrom = new Date(String(values.get('valid_from')));
    const validUntil = new Date(String(values.get('valid_until')));
    if (Number.isNaN(validFrom.valueOf()) || Number.isNaN(validUntil.valueOf()) || validUntil <= validFrom) {
      const message = 'Reservation end must be after its start.';
      setActionError(message);
      notification.error(message);
      return;
    }
    setSaving(true);
    setActionError(undefined);
    try {
      const response = await advancedApi.createReservation({
        parking_slot_id: reservationSlotId,
        vehicle_number: String(values.get('vehicle_number')),
        holder_name: String(values.get('holder_name')),
        valid_from: validFrom.toISOString(),
        valid_until: validUntil.toISOString(),
        status: 'active',
      });
      if (!response.data) throw new Error(response.message);
      const createdReservation = response.data;
      notification.success('Slot reserved. It will be occupied automatically when this vehicle enters during the reservation.');
      setSlots((current) => current.map((slot) => slot.id === reservationSlotId ? { ...slot, status: 'reserved', reserved_for: createdReservation.holder_name } : slot));
      setReservations((current) => [createdReservation, ...current.filter((reservation) => reservation.id !== createdReservation.id)]);
      form.reset();
      setReservationSlotId('');
      await load(locationId);
    } catch (requestError) {
      const message = getApiErrorMessage(requestError, 'Unable to reserve the selected slot.');
      setActionError(message);
      notification.error(message);
    } finally {
      setSaving(false);
    }
  }

  return <>
    <PageHeader
      title="Advanced parking"
      description="Manage parking slots, vehicle reservations, and the live slot map. Monthly passes are managed separately."
      actions={<Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => { void load(); }} disabled={loading}>Refresh</Button>}
    />
    {(error || actionError) && <Alert severity="error" action={error ? <Button color="inherit" size="small" onClick={() => { void load(); }}>Retry</Button> : undefined} sx={{ mb: 2 }}>{error ?? actionError}</Alert>}
    {loading ? <LoadingState label="Loading parking slots…" /> : <Stack spacing={3}>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2} alignItems={{ sm: 'center' }}>
          <Box>
            <Typography variant="h6" fontWeight={800}>Parking slot visualization</Typography>
            <Typography variant="body2" color="text.secondary">A reserved slot becomes occupied when its vehicle enters and available again after exit.</Typography>
          </Box>
          <TextField select label="Parking location" value={locationId} onChange={(event) => { setLocationId(event.target.value); void load(event.target.value); }} sx={{ minWidth: 260 }}>
            <MenuItem value="">All locations</MenuItem>
            {locations.map((location) => <MenuItem key={location.id} value={location.id}>{location.name}{location.branch_name ? ` · ${location.branch_name}` : ''}</MenuItem>)}
          </TextField>
        </Stack>
        <Divider sx={{ my: 2 }} />
        {slots.length ? <Grid2 container spacing={1.5}>{slots.map((slot) => <Grid2 key={slot.id} size={{ xs: 4, sm: 3, md: 2 }}><Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center', borderColor: `${slotColors[slot.status]}.main`, bgcolor: 'action.hover' }}><Typography fontWeight={800}>{slot.slot_number}</Typography><Chip size="small" color={slotColors[slot.status]} label={slot.status} sx={{ mt: 0.75, textTransform: 'capitalize' }} />{slot.reserved_for && <Typography variant="caption" display="block" noWrap mt={0.5}>{slot.reserved_for}</Typography>}{slot.occupied_by && <Typography variant="caption" display="block" noWrap mt={0.5}>{slot.occupied_by}</Typography>}</Paper></Grid2>)}</Grid2> : <EmptyState title="No parking slots" description="Create slots for a configured parking location to render the live map." />}
      </Paper>
      {canManage && <Grid2 container spacing={3}>
        <Grid2 size={{ xs: 12, lg: 6 }}><CreateCard title="Add parking slot" onSubmit={createSlot} saving={saving} disabled={!locations.length}><TextField select name="parking_location_id" label="Parking location" required value={locationId} onChange={(event) => { setLocationId(event.target.value); void load(event.target.value); }} fullWidth>{locations.map((location) => <MenuItem key={location.id} value={location.id}>{location.name}</MenuItem>)}</TextField>{!locations.length && <Typography variant="body2" color="warning.main">Create a branch and parking location first.</Typography>}<TextField name="slot_number" label="Slot number" placeholder="A-01" required fullWidth /><TextField select name="vehicle_type" label="Vehicle type (optional)" defaultValue="" fullWidth><MenuItem value="">Any vehicle</MenuItem>{VEHICLE_TYPES.map((type) => <MenuItem key={type} value={type}>{vehicleTypeLabels[type]}</MenuItem>)}</TextField></CreateCard></Grid2>
        <Grid2 size={{ xs: 12, lg: 6 }}><CreateCard title="Reserve a slot" onSubmit={createReservation} saving={saving} disabled={!slotOptions.length}><TextField select name="parking_slot_id" label="Available slot" required value={reservationSlotId} onChange={(event) => setReservationSlotId(event.target.value)} fullWidth>{slotOptions.map((slot) => <MenuItem key={slot.id} value={slot.id}>{slot.slot_number} · {slot.status}</MenuItem>)}</TextField>{!slotOptions.length && <Typography variant="body2" color="warning.main">Create an available parking slot before reserving it.</Typography>}<TextField name="vehicle_number" label="Vehicle number" required fullWidth /><TextField name="holder_name" label="Reserved for" required fullWidth /><TextField name="valid_from" label="Starts" type="datetime-local" required defaultValue={defaultReservationStart()} InputLabelProps={{ shrink: true }} fullWidth /><TextField name="valid_until" label="Ends" type="datetime-local" required defaultValue={defaultReservationEnd()} InputLabelProps={{ shrink: true }} fullWidth /></CreateCard></Grid2>
      </Grid2>}
      <SummaryList title="Slot reservations" empty="No slot reservations yet." items={reservations.map((reservation) => <Stack key={reservation.id} direction="row" justifyContent="space-between" gap={1}><Box><Typography fontWeight={700}>{reservation.slot_number ?? 'Slot'} · {reservation.holder_name}</Typography><Typography variant="body2" color="text.secondary">{reservation.vehicle_number} · until {new Date(reservation.valid_until).toLocaleString()}</Typography></Box><Chip size="small" label={reservation.status} color={reservation.status === 'active' ? 'warning' : 'default'} /></Stack>)} />
    </Stack>}
  </>;
}

function CreateCard({ title, onSubmit, saving, disabled = false, children }: { title: string; onSubmit: (event: FormEvent<HTMLFormElement>) => void; saving: boolean; disabled?: boolean; children: React.ReactNode }) {
  return <Paper component="form" onSubmit={onSubmit} variant="outlined" sx={{ p: 2.5, height: '100%' }}><Typography variant="h6" fontWeight={800} mb={2}>{title}</Typography><Stack spacing={1.5}>{children}<Button type="submit" variant="contained" startIcon={<AddIcon />} disabled={saving || disabled}>{saving ? 'Saving…' : title}</Button></Stack></Paper>;
}

function SummaryList({ title, empty, items }: { title: string; empty: string; items: React.ReactNode[] }) {
  return <Paper variant="outlined" sx={{ p: 2.5 }}><Typography variant="h6" fontWeight={800}>{title}</Typography><Stack spacing={1.5} mt={2}>{items.length ? items : <Typography color="text.secondary">{empty}</Typography>}</Stack></Paper>;
}
