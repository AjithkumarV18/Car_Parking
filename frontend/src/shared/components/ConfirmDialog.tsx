import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from '@mui/material';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  confirmColor?: 'error' | 'primary' | 'warning';
  loading?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDialog({ open, title, description, confirmLabel = 'Confirm', confirmColor = 'primary', loading = false, onCancel, onConfirm }: ConfirmDialogProps) {
  return <Dialog open={open} onClose={loading ? undefined : onCancel} fullWidth maxWidth="xs"><DialogTitle>{title}</DialogTitle><DialogContent><Typography color="text.secondary">{description}</Typography></DialogContent><DialogActions><Button onClick={onCancel} disabled={loading}>Cancel</Button><Button variant="contained" color={confirmColor} onClick={onConfirm} disabled={loading}>{loading ? 'Working…' : confirmLabel}</Button></DialogActions></Dialog>;
}
