import { Chip, Paper, Stack, Typography } from '@mui/material';

import type { VehicleMembership } from '@/features/parking/parkingApi';
import { useTranslation } from '@/features/preferences/useTranslation';

export function VehicleMembershipCard({ membership }: { membership?: VehicleMembership }) {
  const { locale, t } = useTranslation();
  if (!membership) return null;
  if (!membership.has_active_pass) return <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'action.hover' }}><Typography variant="body2" color="text.secondary">{t('No active monthly pass for this vehicle.')}</Typography></Paper>;

  const amount = new Intl.NumberFormat(locale, { style: 'currency', currency: 'INR', minimumFractionDigits: 2 }).format(Number(membership.amount));
  return <Paper variant="outlined" sx={{ p: 1.5, borderColor: 'success.main', bgcolor: 'success.50' }}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1} alignItems={{ sm: 'center' }}><Stack spacing={0.25}><Typography fontWeight={800}>{t('Active monthly pass')}</Typography><Typography variant="body2" color="text.secondary">{membership.pass_number} · {membership.holder_name}</Typography></Stack><Stack direction="row" gap={1} flexWrap="wrap"><Chip color="success" size="small" label={`${membership.remaining_days} ${t('days remaining')}`} /><Chip color="primary" size="small" label={`${t('Pass amount')}: ${amount}`} /></Stack></Stack></Paper>;
}
