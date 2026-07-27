export const API_PATHS = {
  health: '/system/health',
  auth: {
    login: '/auth/login',
    refresh: '/auth/refresh',
    logout: '/auth/logout',
  },
} as const;
