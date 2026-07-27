import { createContext } from 'react';

export type NotificationSeverity = 'success' | 'error' | 'warning';

export interface NotificationContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
}

export const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);
