import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import NfcIcon from '@mui/icons-material/Nfc';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import SaveIcon from '@mui/icons-material/Save';
import { Alert, Avatar, Box, Button, Grid2, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';

import { parkingApi, type ParkingReceipt, type VehicleEntryPayload, type VehicleMembership } from '@/features/parking/parkingApi';
import { CameraScannerDialog } from '@/features/parking/CameraScannerDialog';
import { ParkingReceiptDialog } from '@/features/parking/ParkingReceiptDialog';
import { VehicleMembershipCard } from '@/features/parking/VehicleMembershipCard';
import { useTranslation } from '@/features/preferences/useTranslation';
import { defaultSoftwareSettings, softwareSettingsApi } from '@/features/settings/softwareSettingsApi';
import { VEHICLE_TYPES, vehicleTypeLabels } from '@/shared/constants/parking';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

const emptyEntry = (): VehicleEntryPayload => ({ vehicle_number: '', rfid: '', qr_code: '', vehicle_type: 'car', owner_name: '', mobile: '', vehicle_image_data: null, advance_amount: '0.00' });

export function VehicleEntryPage() {
  const { locale, t } = useTranslation();
  const [form, setForm] = useState<VehicleEntryPayload>(emptyEntry());
  const [membership, setMembership] = useState<VehicleMembership>();
  const [imagePreview, setImagePreview] = useState<string>();
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState<string>();
  const [saving, setSaving] = useState(false);
  const [receipt, setReceipt] = useState<ParkingReceipt>();
  const [receiptLoading, setReceiptLoading] = useState(false);
  const [receiptError, setReceiptError] = useState<string>();
  const [receiptEntryId, setReceiptEntryId] = useState<string>();
  const [cameraOpen, setCameraOpen] = useState(false);
  const [softwareSettings, setSoftwareSettings] = useState(defaultSoftwareSettings);
  const rfidInput = useRef<HTMLInputElement>(null);
  const qrInput = useRef<HTMLInputElement>(null);
  const imageInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void softwareSettingsApi.get().then((response) => {
      if (response.data) setSoftwareSettings(response.data);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    const vehicleNumber = form.vehicle_number.trim();
    if (!softwareSettings.monthly_pass_lookup_enabled || vehicleNumber.length < 4) { setMembership(undefined); return; }
    let active = true;
    const timer = window.setTimeout(() => {
      void parkingApi.membership(vehicleNumber).then((response) => {
        if (active) setMembership(response.data ?? undefined);
      }).catch(() => { if (active) setMembership(undefined); });
    }, 350);
    return () => { active = false; window.clearTimeout(timer); };
  }, [form.vehicle_number, softwareSettings.monthly_pass_lookup_enabled]);

  async function captureImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { setError('Vehicle image must be 2 MB or smaller.'); return; }
    const reader = new FileReader();
    reader.onload = () => { const data = String(reader.result); setImagePreview(data); setForm((current) => ({ ...current, vehicle_image_data: data })); };
    reader.onerror = () => setError('Unable to read the selected vehicle image.');
    reader.readAsDataURL(file);
  }

  async function loadReceipt(entryId: string) {
    setReceiptEntryId(entryId); setReceiptLoading(true); setReceiptError(undefined); setReceipt(undefined);
    try {
      const response = await parkingApi.entryReceipt(entryId);
      if (!response.data) throw new Error(response.message);
      setReceipt(response.data);
    } catch (requestError) { setReceiptError(getApiErrorMessage(requestError, 'Entry was saved, but its receipt could not be retrieved.')); } finally { setReceiptLoading(false); }
  }

  function closeReceipt() { setReceipt(undefined); setReceiptError(undefined); setReceiptLoading(false); setReceiptEntryId(undefined); }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(undefined); setSuccess(undefined);
    try {
      const payload = { ...form, rfid: softwareSettings.rfid_entry_enabled ? form.rfid || null : null, qr_code: softwareSettings.qr_entry_enabled ? form.qr_code || null : null, vehicle_image_data: softwareSettings.vehicle_image_capture_enabled ? form.vehicle_image_data : null, owner_name: form.owner_name || null, mobile: form.mobile || null, advance_amount: softwareSettings.advance_payment_enabled ? form.advance_amount : '0.00' };
      const response = await parkingApi.createEntry(payload);
      if (!response.data) throw new Error(response.message);
      setSuccess(`Entry saved. Token ${response.data.token_number} and parking number ${response.data.parking_number} were generated.`);
      setForm(emptyEntry()); setImagePreview(undefined); setMembership(undefined);
      if (softwareSettings.auto_open_receipt_enabled) void loadReceipt(response.data.id);
    } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to save vehicle entry.')); } finally { setSaving(false); }
  }

  return <Box className="operator-screen"><PageHeader title="Vehicle entry" description="Fast check-in screen. Entry time, parking number, and token are generated automatically." />
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}{success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
    <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: { xs: 2, md: 4 } }}><Grid2 container spacing={2.5}>
      <Grid2 size={{ xs: 12, md: 7 }}><TextField autoFocus label="Vehicle number" value={form.vehicle_number} onChange={(event) => setForm({ ...form, vehicle_number: event.target.value.toUpperCase() })} placeholder="KA01AB1234" required fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, md: 5 }}><TextField select label="Vehicle type" value={form.vehicle_type} onChange={(event) => setForm({ ...form, vehicle_type: event.target.value as VehicleEntryPayload['vehicle_type'] })} required fullWidth>{VEHICLE_TYPES.map((type) => <MenuItem key={type} value={type}>{vehicleTypeLabels[type]}</MenuItem>)}</TextField></Grid2>
      <Grid2 size={{ xs: 12, md: 6 }}><TextField label={t('In time')} value={new Date().toLocaleString(locale)} InputProps={{ readOnly: true }} fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, md: 6 }}><TextField label={t('Out time')} value={t('Recorded at vehicle exit')} InputProps={{ readOnly: true }} fullWidth /></Grid2>
      {softwareSettings.monthly_pass_lookup_enabled && <Grid2 size={12}><VehicleMembershipCard membership={membership} /></Grid2>}
      {softwareSettings.rfid_entry_enabled && <Grid2 size={{ xs: 12, md: 6 }}><Stack direction="row" spacing={1}><TextField inputRef={rfidInput} label="RFID" value={form.rfid ?? ''} onChange={(event) => setForm({ ...form, rfid: event.target.value })} fullWidth /><Button type="button" variant="outlined" startIcon={<NfcIcon />} onClick={() => rfidInput.current?.focus()} sx={{ minWidth: 138 }}>Scan RFID</Button></Stack></Grid2>}
      {softwareSettings.qr_entry_enabled && <Grid2 size={{ xs: 12, md: 6 }}><Stack direction="row" spacing={1}><TextField inputRef={qrInput} label="QR scan" value={form.qr_code ?? ''} onChange={(event) => setForm({ ...form, qr_code: event.target.value })} fullWidth />{softwareSettings.webcam_capture_enabled && <Button type="button" variant="outlined" startIcon={<QrCodeScannerIcon />} onClick={() => setCameraOpen(true)} sx={{ minWidth: 128 }}>Scan QR</Button>}</Stack></Grid2>}
      <Grid2 size={{ xs: 12, md: 6 }}><TextField label="Owner (optional)" value={form.owner_name ?? ''} onChange={(event) => setForm({ ...form, owner_name: event.target.value })} fullWidth /></Grid2>
      <Grid2 size={{ xs: 12, md: 6 }}><TextField label="Mobile (optional)" type="tel" value={form.mobile ?? ''} onChange={(event) => setForm({ ...form, mobile: event.target.value })} placeholder="+919999999999" fullWidth /></Grid2>
      {softwareSettings.advance_payment_enabled && <Grid2 size={{ xs: 12, md: 6 }}><TextField label="Advance amount" type="number" value={form.advance_amount} onChange={(event) => setForm({ ...form, advance_amount: event.target.value })} inputProps={{ min: 0, step: '0.01' }} helperText="Collected at entry and automatically adjusted at exit." fullWidth /></Grid2>}
      {softwareSettings.vehicle_image_capture_enabled && <Grid2 size={{ xs: 12, md: 6 }}><Stack direction="row" spacing={2} alignItems="center"><Avatar src={imagePreview} variant="rounded" sx={{ width: 64, height: 64 }}><CameraAltIcon /></Avatar><Box><Stack direction="row" spacing={1}>{softwareSettings.webcam_capture_enabled && <Button type="button" variant="outlined" startIcon={<CameraAltIcon />} onClick={() => setCameraOpen(true)}>Webcam capture</Button>}<Button type="button" variant="text" onClick={() => imageInput.current?.click()}>Upload</Button></Stack><Typography variant="body2" color="text.secondary" mt={0.5}>Optional JPEG, PNG, or WebP up to 2 MB.</Typography><input ref={imageInput} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden onChange={(event) => { void captureImage(event); }} /></Box></Stack></Grid2>}
      <Grid2 size={12}><Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover' }}><Typography fontWeight={700}>Automatic at save</Typography><Typography color="text.secondary">Entry time · Parking number · Token number</Typography></Paper></Grid2>
      <Grid2 size={12}><Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={saving} fullWidth sx={{ minHeight: 68, fontSize: '1.2rem' }}>{saving ? 'Saving entry…' : 'Save entry & print receipt'}</Button></Grid2>
    </Grid2></Paper>
    <ParkingReceiptDialog receipt={receipt} receiptType="entry" loading={receiptLoading} error={receiptError} onRetry={() => { if (receiptEntryId) void loadReceipt(receiptEntryId); }} onClose={closeReceipt} />
    <CameraScannerDialog open={cameraOpen && softwareSettings.webcam_capture_enabled} onClose={() => setCameraOpen(false)} onQrDetected={(qrCode) => { if (softwareSettings.qr_entry_enabled) { setForm((current) => ({ ...current, qr_code: qrCode })); qrInput.current?.focus(); } }} onImageCaptured={(imageData) => { if (softwareSettings.vehicle_image_capture_enabled) { setImagePreview(imageData); setForm((current) => ({ ...current, vehicle_image_data: imageData })); } }} />
  </Box>;
}
