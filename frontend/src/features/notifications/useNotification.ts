import { useContext } from 'react';

import { NotificationContext, type NotificationContextValue } from '@/features/notifications/context';

export function useNotification(): NotificationContextValue {
  const value = useContext(NotificationContext);
  if (!value) throw new Error('useNotification must be used inside NotificationProvider.');
  return value;
}
