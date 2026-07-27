import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

import { env } from '@/config/env';
import { authEvents } from '@/services/authEvents';
import { companyStorage } from '@/services/companyStorage';
import { tokenStorage } from '@/services/tokenStorage';
import type { ApiResponse } from '@/shared/types/api';
import type { TokenPair } from '@/features/auth/authApi';

export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: env.requestTimeoutMs,
  headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
});

const refreshClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: env.requestTimeoutMs,
  headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
});

let refreshPromise: Promise<TokenPair> | null = null;

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const companyId = companyStorage.get();
  if (companyId && !config.headers['X-Company-ID']) config.headers['X-Company-ID'] = companyId;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse<never>>) => {
    const originalRequest = error.config;
    const errorMessage = error.response?.data.error?.message?.toLowerCase() ?? '';
    if (error.response?.status === 404 && errorMessage.includes('company was not found or is inactive')) {
      tokenStorage.clear();
      companyStorage.clear();
      authEvents.emitSessionExpired();
    }
    const refreshToken = tokenStorage.getRefreshToken();
    const isRefreshCall = originalRequest?.url?.includes('/auth/refresh');
    if (error.response?.status === 401 && originalRequest && !isRefreshCall && refreshToken) {
      try {
        refreshPromise ??= refreshClient
          .post<ApiResponse<TokenPair>>('/auth/refresh', { refresh_token: refreshToken }, { headers: { 'X-Company-ID': companyStorage.get() ?? '' } })
          .then((response) => {
            if (!response.data.data) throw new Error('Refresh response did not include tokens.');
            return response.data.data;
          })
          .finally(() => { refreshPromise = null; });
        const tokens = await refreshPromise;
        tokenStorage.setTokens(tokens.access_token, tokens.refresh_token, Boolean(localStorage.getItem('parking.access_token')));
        originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
        return apiClient(originalRequest);
      } catch {
        tokenStorage.clear();
        companyStorage.clear();
        authEvents.emitSessionExpired();
      }
    }
    if (error.response?.status === 401) {
      tokenStorage.clear();
      companyStorage.clear();
      authEvents.emitSessionExpired();
    }
    return Promise.reject(error);
  },
);
