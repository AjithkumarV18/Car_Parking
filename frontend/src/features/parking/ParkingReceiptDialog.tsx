import { useState } from 'react';
import PrintIcon from '@mui/icons-material/Print';
import { Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Stack, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';

import { ReceiptBarcode, ReceiptQrCode } from '@/features/parking/ReceiptCodes';
import type { ParkingReceipt } from '@/features/parking/parkingApi';
import { vehicleTypeLabels } from '@/shared/constants/parking';

type ReceiptWidth = 58 | 80;

interface ParkingReceiptDialogProps {
  receipt?: ParkingReceipt;
  receiptType?: 'entry' | 'exit';
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  onClose: () => void;
}

function money(value: string, currency: string): string {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency, minimumFractionDigits: 2 }).format(Number(value));
}

function dateTime(value: string): string {
  return new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
}

function duration(minutes: number): string {
  const hours = Math.floor(minutes / 60); const remainingMinutes = minutes % 60;
  return hours ? `${hours}h ${remainingMinutes}m` : `${remainingMinutes} min`;
}

function ReceiptRow({ label, value, strong = false }: { label: string; value: string | number | null | undefined; strong?: boolean }) {
  return <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}><Typography variant="body2" color="text.secondary">{label}</Typography><Typography variant="body2" fontWeight={strong ? 800 : 600} textAlign="right" sx={{ overflowWrap: 'anywhere' }}>{value ?? '—'}</Typography></Stack>;
}

export function ParkingReceiptDialog({ receipt, receiptType, loading = false, error, onRetry, onClose }: ParkingReceiptDialogProps) {
  const [paperWidth, setPaperWidth] = useState<ReceiptWidth>(80);
  const entry = receipt?.entry;
  const exit = receipt?.exit;
  const type = receipt?.receipt_type ?? receiptType ?? 'entry';
  const currency = receipt?.company.currency ?? 'INR';

  function printReceipt() {
    const styleId = 'thermal-receipt-page-size';
    document.getElementById(styleId)?.remove();
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `@media print { @page { size: ${paperWidth}mm auto; margin: 0; } }`;
    document.head.appendChild(style);
    document.body.classList.add('printing-thermal-receipt');
    const cleanUp = () => { style.remove(); document.body.classList.remove('printing-thermal-receipt'); };
    window.addEventListener('afterprint', cleanUp, { once: true });
    window.print();
  }

  return <Dialog open={Boolean(receipt || loading || error)} onClose={loading ? undefined : onClose} fullWidth maxWidth="sm" className="parking-receipt-dialog">
    <DialogTitle className="receipt-dialog-title" textAlign="center">{type === 'exit' ? 'Vehicle Exit Receipt' : 'Vehicle Entry Receipt'}</DialogTitle>
    <DialogContent dividers sx={{ bgcolor: 'action.hover', p: { xs: 1, sm: 2 } }}>{loading ? <Stack alignItems="center" spacing={2} py={3}><CircularProgress /><Typography>Retrieving receipt…</Typography></Stack> : error ? <Alert severity="error" action={onRetry && <Button color="inherit" size="small" onClick={onRetry}>Retry</Button>}>{error}</Alert> : receipt && <Box className={`parking-receipt-content receipt-width-${paperWidth}`} sx={{ width: `${paperWidth}mm`, maxWidth: '100%', mx: 'auto', bgcolor: 'common.white', color: 'common.black', p: paperWidth === 58 ? 1.25 : 2, fontFamily: 'Arial, Helvetica, sans-serif' }}>
      <Stack spacing={1.1}>
        <Box textAlign="center">
          {receipt.company.logo_url && <Box component="img" src={receipt.company.logo_url} alt={`${receipt.company.company_name} logo`} sx={{ display: 'block', maxHeight: 42, maxWidth: 130, mx: 'auto', mb: 0.75, objectFit: 'contain' }} />}
          <Typography fontWeight={900} fontSize={paperWidth === 58 ? '0.95rem' : '1.15rem'} lineHeight={1.2}>{receipt.company.company_name}</Typography>
          {receipt.company.address && <Typography variant="caption" display="block" sx={{ lineHeight: 1.25, mt: 0.5 }}>{receipt.company.address}</Typography>}
          {receipt.company.gstin && <Typography variant="caption" display="block" fontWeight={700} mt={0.25}>GSTIN: {receipt.company.gstin}</Typography>}
        </Box>
        <Divider className="receipt-divider" />
        <Box textAlign="center"><Typography variant="caption" fontWeight={800} letterSpacing={1}>{type === 'exit' ? 'PARKING EXIT RECEIPT' : 'PARKING ENTRY RECEIPT'}</Typography><Typography variant="body2" fontFamily="monospace" fontWeight={800}>{receipt.receipt_number}</Typography></Box>
        <Divider className="receipt-divider" />
        <Stack spacing={0.65}>
          <ReceiptRow label="Vehicle" value={entry && `${entry.vehicle_number} · ${vehicleTypeLabels[entry.vehicle_type]}`} strong />
          <ReceiptRow label="Token" value={entry?.token_number} />
          <ReceiptRow label="Parking no." value={entry?.parking_number} />
          {entry?.location_name && <ReceiptRow label="Location" value={entry.location_name} />}
          {entry?.owner_name && <ReceiptRow label="Owner" value={entry.owner_name} />}
          {entry?.mobile && <ReceiptRow label="Mobile" value={entry.mobile} />}
        </Stack>
        <Divider className="receipt-divider" />
        <Stack spacing={0.65}>
          <ReceiptRow label="Entry" value={entry && dateTime(entry.entry_at)} />
          {exit ? <><ReceiptRow label="Exit" value={dateTime(exit.exit_at)} /><ReceiptRow label="Duration" value={duration(exit.duration_minutes)} /><Divider className="receipt-divider" /><ReceiptRow label="Parking amount" value={money(exit.parking_charge, currency)} /><ReceiptRow label={`GST (${exit.gst_percent}%)`} value={money(exit.gst_amount, currency)} /><ReceiptRow label="Total" value={money(exit.total_amount, currency)} strong /><ReceiptRow label="Advance adjusted" value={money(exit.advance_applied, currency)} /><ReceiptRow label="Paid now" value={money(exit.paid_amount, currency)} /><ReceiptRow label="Payment" value={exit.payment_method?.toUpperCase() ?? 'Advance only'} /><ReceiptRow label="Balance" value={money(exit.balance_amount, currency)} strong /></> : <><ReceiptRow label="Advance collected" value={entry && money(entry.advance_amount, currency)} strong /><ReceiptRow label="Entry time" value={entry && dateTime(entry.entry_at)} /></>}
        </Stack>
        <Divider className="receipt-divider" />
        <ReceiptRow label="Operator" value={`${receipt.operator.name}${receipt.operator.employee_id ? ` (${receipt.operator.employee_id})` : ''}`} />
        <ReceiptRow label="Issued" value={dateTime(receipt.issued_at)} />
        <Box display="flex" justifyContent="center" mt={0.25}><ReceiptQrCode value={receipt.qr_payload} /></Box>
        <ReceiptBarcode value={receipt.barcode_value} />
        <Typography textAlign="center" variant="caption" sx={{ lineHeight: 1.25 }}>{receipt.company.receipt_footer || 'Thank you for parking with us.'}</Typography>
        <Typography textAlign="center" variant="caption" color="text.secondary">Keep this receipt for reference.</Typography>
      </Stack>
    </Box>}</DialogContent>
    <DialogActions className="receipt-dialog-actions" sx={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}><ToggleButtonGroup size="small" exclusive value={paperWidth} onChange={(_, value: ReceiptWidth | null) => { if (value) setPaperWidth(value); }} aria-label="Thermal paper width"><ToggleButton value={58}>58 mm</ToggleButton><ToggleButton value={80}>80 mm</ToggleButton></ToggleButtonGroup><Stack direction="row" spacing={1}><Button onClick={onClose} disabled={loading}>Close</Button>{error && onRetry && <Button variant="contained" onClick={onRetry}>Retry</Button>}{receipt && <Button variant="contained" startIcon={<PrintIcon />} onClick={printReceipt}>Print</Button>}</Stack></DialogActions>
  </Dialog>;
}
