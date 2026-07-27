import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { Alert, Snackbar } from '@mui/material';

import { NotificationContext, type NotificationSeverity } from '@/features/notifications/context';

interface Notice { id: number; message: string; severity: NotificationSeverity; }

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notices, setNotices] = useState<Notice[]>([]);
  const push = useCallback((severity: NotificationSeverity, message: string) => {
    setNotices((current) => [...current, { id: Date.now() + current.length, severity, message }]);
  }, []);
  const close = useCallback(() => setNotices((current) => current.slice(1)), []);
  const value = useMemo(() => ({ success: (message: string) => push('success', message), error: (message: string) => push('error', message), warning: (message: string) => push('warning', message) }), [push]);
  const notice = notices[0];
  return <NotificationContext.Provider value={value}>{children}<Snackbar open={Boolean(notice)} autoHideDuration={5000} onClose={close} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}><Alert onClose={close} severity={notice?.severity} variant="filled" sx={{ minWidth: 280 }}>{notice?.message}</Alert></Snackbar></NotificationContext.Provider>;
}
