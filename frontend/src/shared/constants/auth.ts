export const STORAGE_KEYS = {
  accessToken: 'parking.access_token',
  refreshToken: 'parking.refresh_token',
} as const;

export const AUTH_EVENTS = {
  sessionExpired: 'parking:session-expired',
} as const;
