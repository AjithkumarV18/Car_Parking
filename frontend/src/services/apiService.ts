import type { AxiosRequestConfig } from 'axios';

import { apiClient } from '@/services/apiClient';
import type { ApiResponse } from '@/shared/types/api';

/** Thin, typed wrapper that keeps Axios out of future feature services. */
export const apiService = {
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await apiClient.get<ApiResponse<T>>(url, config);
    return response.data;
  },
  async post<T, TBody>(url: string, body: TBody, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await apiClient.post<ApiResponse<T>>(url, body, config);
    return response.data;
  },
  async put<T, TBody>(url: string, body: TBody, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await apiClient.put<ApiResponse<T>>(url, body, config);
    return response.data;
  },
  async patch<T, TBody>(url: string, body: TBody, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await apiClient.patch<ApiResponse<T>>(url, body, config);
    return response.data;
  },
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await apiClient.delete<ApiResponse<T>>(url, config);
    return response.data;
  },
};
