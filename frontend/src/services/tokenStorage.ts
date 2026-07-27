import { STORAGE_KEYS } from '@/shared/constants/auth';

export const tokenStorage = {
  getAccessToken: (): string | null => localStorage.getItem(STORAGE_KEYS.accessToken) ?? sessionStorage.getItem(STORAGE_KEYS.accessToken),
  getRefreshToken: (): string | null => localStorage.getItem(STORAGE_KEYS.refreshToken) ?? sessionStorage.getItem(STORAGE_KEYS.refreshToken),
  setTokens: (accessToken: string, refreshToken?: string, rememberMe = false): void => {
    localStorage.removeItem(STORAGE_KEYS.accessToken);
    localStorage.removeItem(STORAGE_KEYS.refreshToken);
    sessionStorage.removeItem(STORAGE_KEYS.accessToken);
    sessionStorage.removeItem(STORAGE_KEYS.refreshToken);
    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem(STORAGE_KEYS.accessToken, accessToken);
    if (refreshToken) storage.setItem(STORAGE_KEYS.refreshToken, refreshToken);
  },
  clear: (): void => {
    localStorage.removeItem(STORAGE_KEYS.accessToken);
    localStorage.removeItem(STORAGE_KEYS.refreshToken);
    sessionStorage.removeItem(STORAGE_KEYS.accessToken);
    sessionStorage.removeItem(STORAGE_KEYS.refreshToken);
  },
};
