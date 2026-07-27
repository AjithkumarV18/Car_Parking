import { AUTH_EVENTS } from '@/shared/constants/auth';

export const authEvents = {
  emitSessionExpired: (): void => {
    window.dispatchEvent(new Event(AUTH_EVENTS.sessionExpired));
  },
  onSessionExpired: (listener: () => void): (() => void) => {
    window.addEventListener(AUTH_EVENTS.sessionExpired, listener);
    return () => window.removeEventListener(AUTH_EVENTS.sessionExpired, listener);
  },
};
