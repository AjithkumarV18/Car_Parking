import { useCallback, useEffect, useState } from 'react';
import CalculateIcon from '@mui/icons-material/Calculate';
import CreditCardIcon from '@mui/icons-material/CreditCard';
import NfcIcon from '@mui/icons-material/Nfc';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import SearchIcon from '@mui/icons-material/Search';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import { Alert, Box, Button, ButtonGroup, Divider, Grid2, Paper, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import { useSearchParams } from 'react-router-dom';

import { parkingApi, paymentMethodLabels, type EntryLookup, type ExitCalculation, type OpenEntryOption, type ParkingReceipt, type PaymentMethod, type VehicleEntry, type VehicleMembership } from '@/features/parking/parkingApi';
import { ParkingReceiptDialog } from '@/features/parking/ParkingReceiptDialog';
import { VehicleMembershipCard } from '@/features/parking/VehicleMembershipCard';
import { useTranslation } from '@/features/preferences/useTranslation';
import { defaultSoftwareSettings, softwareSettingsApi } from '@/features/settings/softwareSettingsApi';
import { vehicleTypeLabels } from '@/shared/constants/parking';
import { PageHeader } from '@/shared/components/PageHeader';
import { getApiErrorMessage } from '@/shared/utils/apiError';

type SearchMode = 'vehicle_number' | 'card' | 'qr_code' | 'rfid';

const searchLabels: Record<SearchMode, string> = { vehicle_number: 'Vehicle number', card: 'Card / token', qr_code: 'QR code', rfid: 'RFID' };

function formatMoney(value: string): string { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2 }).format(Number(value)); }

export function VehicleExitPage() {
  const { t, locale } = useTranslation();
  const [searchParams] = useSearchParams();
  const entryIdFromLog = searchParams.get('entryId');
  const [mode, setMode] = useState<SearchMode>('vehicle_number');
  const [searchValue, setSearchValue] = useState('');
  const [entry, setEntry] = useState<VehicleEntry>();
  const [membership, setMembership] = useState<VehicleMembership>();
  const [calculation, setCalculation] = useState<ExitCalculation>();
  const [openEntries, setOpenEntries] = useState<OpenEntryOption[]>([]);
  const [paidAmount, setPaidAmount] = useState('0.00');
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>();
  const [paymentReference, setPaymentReference] = useState('');
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [receipt, setReceipt] = useState<ParkingReceipt>();
  const [receiptLoading, setReceiptLoading] = useState(false);
  const [receiptError, setReceiptError] = useState<string>();
  const [receiptExitId, setReceiptExitId] = useState<string>();
  const [softwareSettings, setSoftwareSettings] = useState(defaultSoftwareSettings);

  async function loadOpenEntries(search?: string) {
    try {
      const response = await parkingApi.openEntries(search);
      setOpenEntries(response.data ?? []);
    } catch { setOpenEntries([]); }
  }

  const selectEntry = useCallback(async (entryId: string) => {
    setLoading(true); setError(undefined);
    try {
      const response = await parkingApi.calculateExit(entryId);
      if (!response.data) throw new Error(response.message);
      setEntry(response.data.entry); setCalculation(response.data); setPaidAmount(response.data.balance_amount);
    } catch (requestError) { setError(getApiErrorMessage(requestError, t('Unable to retrieve the selected open entry.'))); } finally { setLoading(false); }
  }, [t]);

  useEffect(() => { void loadOpenEntries(); }, []);
  useEffect(() => {
    void softwareSettingsApi.get().then((response) => {
      if (response.data) setSoftwareSettings(response.data);
    }).catch(() => undefined);
  }, []);
  useEffect(() => {
    if ((mode === 'qr_code' && !softwareSettings.qr_exit_enabled) || (mode === 'rfid' && !softwareSettings.rfid_exit_enabled)) {
      setMode('vehicle_number');
    }
  }, [mode, softwareSettings.qr_exit_enabled, softwareSettings.rfid_exit_enabled]);
  useEffect(() => {
    if (entryIdFromLog) void selectEntry(entryIdFromLog);
  }, [entryIdFromLog, selectEntry]);
  const membershipVehicleNumber = entry?.vehicle_number ?? (mode === 'vehicle_number' ? searchValue.trim() : '');
  useEffect(() => {
    if (!softwareSettings.monthly_pass_lookup_enabled || membershipVehicleNumber.length < 4) { setMembership(undefined); return; }
    let active = true;
    void parkingApi.membership(membershipVehicleNumber).then((response) => {
      if (active) setMembership(response.data ?? undefined);
    }).catch(() => { if (active) setMembership(undefined); });
    return () => { active = false; };
  }, [membershipVehicleNumber, softwareSettings.monthly_pass_lookup_enabled]);

  async function calculate(entryId: string, resetPayment = false) {
    const response = await parkingApi.calculateExit(entryId);
    if (!response.data) throw new Error(response.message);
    setCalculation(response.data);
    if (resetPayment) setPaidAmount(response.data.balance_amount);
  }

  async function loadReceipt(exitId: string) {
    setReceiptExitId(exitId); setReceiptLoading(true); setReceiptError(undefined); setReceipt(undefined);
    try {
      const response = await parkingApi.exitReceipt(exitId);
      if (!response.data) throw new Error(response.message);
      setReceipt(response.data);
    } catch (requestError) { setReceiptError(getApiErrorMessage(requestError, t('Vehicle exit was completed, but its receipt could not be retrieved.'))); } finally { setReceiptLoading(false); }
  }

  function closeReceipt() { setReceipt(undefined); setReceiptError(undefined); setReceiptLoading(false); setReceiptExitId(undefined); }

  async function retrieve() {
    const value = searchValue.trim();
    setLoading(true); setError(undefined); setEntry(undefined); setCalculation(undefined);
    try {
      const query: EntryLookup = { [mode]: value };
      const response = await parkingApi.lookup(query);
      if (!response.data) throw new Error(response.message);
      setEntry(response.data); await calculate(response.data.id, true);
    } catch (requestError) {
      const fallback = t('No open entry could be retrieved.');
      setError(getApiErrorMessage(requestError, fallback));
      await loadOpenEntries(mode === 'vehicle_number' ? value : undefined);
    } finally { setLoading(false); }
  }

  const requiredBalance = Number(calculation?.balance_amount ?? 0);
  const paid = Number(paidAmount || 0);
  const remaining = Math.max(0, requiredBalance - paid);
  const canExit = Boolean(calculation) && Math.abs(remaining) < 0.005 && paid >= 0 && (paid === 0 || paymentMethod);

  async function exitVehicle() {
    if (!entry || !calculation) return;
    setExiting(true); setError(undefined);
    try {
      const response = await parkingApi.createExit({ entry_id: entry.id, paid_amount: paidAmount, payment_method: paymentMethod ?? null, payment_reference: paymentReference || null });
      if (!response.data) throw new Error(response.message);
      setEntry(undefined); setCalculation(undefined); setMembership(undefined); setSearchValue(''); setPaidAmount('0.00'); setPaymentMethod(undefined); setPaymentReference('');
      if (softwareSettings.auto_open_receipt_enabled) void loadReceipt(response.data.id); void loadOpenEntries();
    } catch (requestError) { setError(getApiErrorMessage(requestError, t('Unable to complete vehicle exit. Recalculate before retrying if needed.'))); } finally { setExiting(false); }
  }

  return <Box className="operator-screen"><PageHeader title={t('Vehicle exit')} description={t('Retrieve an open entry, calculate the tariff, collect payment, and complete exit.')} />
    {error && <Alert severity="error" sx={{ mb: 2 }}>{t(error)}</Alert>}
    <Paper variant="outlined" sx={{ p: { xs: 2, md: 4 }, mb: 2 }}><Stack spacing={2}>
      <ToggleButtonGroup exclusive value={mode} onChange={(_, next: SearchMode | null) => next && setMode(next)} fullWidth>{(['vehicle_number', 'card', ...(softwareSettings.qr_exit_enabled ? ['qr_code'] : []), ...(softwareSettings.rfid_exit_enabled ? ['rfid'] : [])] as SearchMode[]).map((item) => <ToggleButton key={item} value={item} sx={{ py: 1.5, fontSize: { xs: '0.9rem', md: '1.05rem' } }}>{item === 'card' ? <CreditCardIcon sx={{ mr: 1 }} /> : item === 'qr_code' ? <QrCodeScannerIcon sx={{ mr: 1 }} /> : item === 'rfid' ? <NfcIcon sx={{ mr: 1 }} /> : <SearchIcon sx={{ mr: 1 }} />}{t(searchLabels[item])}</ToggleButton>)}</ToggleButtonGroup>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}><TextField autoFocus label={t(searchLabels[mode])} value={searchValue} onChange={(event) => setSearchValue(event.target.value.toUpperCase())} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); void retrieve(); } }} placeholder={mode === 'vehicle_number' ? 'TN01AB1818' : t('Scan or enter value')} fullWidth /><Button variant="contained" startIcon={<SearchIcon />} onClick={() => { void retrieve(); }} disabled={!searchValue.trim() || loading} sx={{ minWidth: 190, minHeight: 58, fontSize: '1.1rem' }}>{loading ? t('Retrieving…') : t('Retrieve entry')}</Button></Stack>
    </Stack></Paper>
    {!entry && softwareSettings.monthly_pass_lookup_enabled && <Box mb={2}><VehicleMembershipCard membership={membership} /></Box>}
    {!entry && <OpenEntryRecovery entries={openEntries} loading={loading} locale={locale} onSelect={(entryId) => { void selectEntry(entryId); }} t={t} />}
    {entry && calculation && <Stack spacing={2}><Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}><Grid2 container spacing={2}><Grid2 size={{ xs: 12, md: 5 }}><Typography variant="h5" fontWeight={800}>{entry.vehicle_number}</Typography><Typography variant="h6" color="text.secondary">{t(vehicleTypeLabels[entry.vehicle_type])}</Typography><Typography mt={1}>{t('Token')}: <strong>{entry.token_number}</strong></Typography><Typography>{t('Parking no.')}: <strong>{entry.parking_number}</strong></Typography><Grid2 container spacing={1.5} mt={1}><Grid2 size={{ xs: 12, sm: 6 }}><TextField label={t('In time')} value={new Date(entry.entry_at).toLocaleString(locale)} InputProps={{ readOnly: true }} fullWidth /></Grid2><Grid2 size={{ xs: 12, sm: 6 }}><TextField label={t('Out time')} value={new Date().toLocaleString(locale)} InputProps={{ readOnly: true }} fullWidth /></Grid2></Grid2></Grid2><Grid2 size={{ xs: 12, md: 7 }}><Button fullWidth variant="outlined" startIcon={<CalculateIcon />} onClick={() => { void calculate(entry.id, true); }} sx={{ minHeight: 54 }}>{t('Recalculate current charge')}</Button><Grid2 container spacing={1.5} sx={{ mt: 0.5 }}><Metric label={t('Duration')} value={`${calculation.duration_minutes} ${t('min')}`} /><Metric label={t('Parking charge')} value={formatMoney(calculation.parking_charge)} /><Metric label="GST" value={formatMoney(calculation.gst_amount)} /><Metric label={t('Total')} value={formatMoney(calculation.total_amount)} /><Metric label={t('Advance')} value={`− ${formatMoney(calculation.advance_applied)}`} /><Metric label={t('Balance')} value={formatMoney(calculation.balance_amount)} emphasis /></Grid2></Grid2><Grid2 size={12}><VehicleMembershipCard membership={membership} /></Grid2></Grid2></Paper>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}><Typography variant="h6" fontWeight={800} mb={2}>{t('Payment')}</Typography><Grid2 container spacing={2}><Grid2 size={{ xs: 12, md: 4 }}><TextField label={t('Paid amount')} type="number" value={paidAmount} onChange={(event) => setPaidAmount(event.target.value)} inputProps={{ min: 0, max: calculation.balance_amount, step: '0.01' }} fullWidth /></Grid2><Grid2 size={{ xs: 12, md: 5 }}><ButtonGroup fullWidth>{(['cash', 'upi', 'card'] as PaymentMethod[]).map((method) => <Button key={method} variant={paymentMethod === method ? 'contained' : 'outlined'} onClick={() => setPaymentMethod(method)}>{t(paymentMethodLabels[method])}</Button>)}</ButtonGroup></Grid2><Grid2 size={{ xs: 12, md: 3 }}><TextField label={t('Reference (optional)')} value={paymentReference} onChange={(event) => setPaymentReference(event.target.value)} fullWidth /></Grid2></Grid2><Divider sx={{ my: 2 }} /><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1} alignItems={{ sm: 'center' }}><Typography variant="h6">{t('Balance after payment')}: <strong>{formatMoney(remaining.toFixed(2))}</strong></Typography><Button variant="contained" color="success" startIcon={<TaskAltIcon />} onClick={() => { void exitVehicle(); }} disabled={!canExit || exiting} sx={{ minHeight: 64, minWidth: 230, fontSize: '1.15rem' }}>{exiting ? t('Completing exit…') : t('Complete exit & print')}</Button></Stack></Paper>
    </Stack>}
    <ParkingReceiptDialog receipt={receipt} receiptType="exit" loading={receiptLoading} error={receiptError} onRetry={() => { if (receiptExitId) void loadReceipt(receiptExitId); }} onClose={closeReceipt} />
  </Box>;
}

function OpenEntryRecovery({ entries, loading, locale, onSelect, t }: { entries: OpenEntryOption[]; loading: boolean; locale: string; onSelect: (entryId: string) => void; t: (value: string) => string }) {
  return <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 }, mb: 2 }}><Typography variant="h6" fontWeight={800}>{t('Open vehicle entries')}</Typography><Typography variant="body2" color="text.secondary" mb={2}>{t('Select an active vehicle if the search value was entered incorrectly or scanned from another identifier.')}</Typography>{entries.length ? <Grid2 container spacing={1.5}>{entries.map((item) => <Grid2 key={item.id} size={{ xs: 12, sm: 6, lg: 3 }}><Button variant="outlined" fullWidth onClick={() => onSelect(item.id)} disabled={loading} sx={{ display: 'block', textAlign: 'left', p: 1.5 }}><Typography fontWeight={800}>{item.vehicle_number}</Typography><Typography variant="body2">{t('Token')}: {item.token_number}</Typography><Typography variant="caption" color="text.secondary">{item.parking_number} · {new Date(item.entry_at).toLocaleString(locale)}</Typography></Button></Grid2>)}</Grid2> : <Typography color="text.secondary">{t('No active vehicle entries are available for this company.')}</Typography>}</Paper>;
}

function Metric({ label, value, emphasis = false }: { label: string; value: string; emphasis?: boolean }) {
  return <Grid2 size={{ xs: 6, sm: 4 }}><Paper variant="outlined" sx={{ p: 1.5, height: '100%', bgcolor: emphasis ? 'primary.main' : 'background.paper', color: emphasis ? 'primary.contrastText' : undefined }}><Typography variant="body2" color={emphasis ? 'inherit' : 'text.secondary'}>{label}</Typography><Typography variant="h6" fontWeight={800}>{value}</Typography></Paper></Grid2>;
}
