import axios from 'axios';
import { apiClient } from '@/services/apiClient';
import { apiService } from '@/services/apiService';
import type { PaymentMethod } from '@/features/parking/parkingApi';
import type { VehicleType } from '@/shared/constants/parking';
import type { ApiResponse, Page, PaginationParams } from '@/shared/types/api';

export type ReportName = 'daily-collection' | 'monthly-collection' | 'vehicle' | 'employee-collection' | 'gst' | 'audit' | 'payment' | 'cancelled-receipts';
export type ExportFormat = 'excel' | 'pdf';

export interface ReportFilters {
  date_from?: string;
  date_to?: string;
  search?: string;
  location_id?: string;
  vehicle_type?: VehicleType;
  payment_method?: PaymentMethod;
}

export interface RevenuePoint {
  period: string;
  label: string;
  amount: string;
}

export interface PaymentMethodPoint {
  method: PaymentMethod;
  amount: string;
  count: number;
}

export interface ReportSummary {
  currency: string;
  date_from: string;
  date_to: string;
  total_collection: string;
  advance_collection: string;
  settlement_collection: string;
  completed_exits: number;
  gst_collected: string;
  revenue: RevenuePoint[];
  payment_methods: PaymentMethodPoint[];
}

export type ReportRow = Record<string, unknown>;
export type ReportDataset = ReportRow[] | Page<ReportRow>;

const collectionReports = new Set<ReportName>(['daily-collection', 'monthly-collection', 'employee-collection', 'gst']);

function endpoint(report: ReportName): string {
  const paths: Record<ReportName, string> = {
    'daily-collection': '/reports/daily-collection',
    'monthly-collection': '/reports/monthly-collection',
    vehicle: '/reports/vehicles',
    'employee-collection': '/reports/employee-collection',
    gst: '/reports/gst',
    audit: '/reports/audit',
    payment: '/reports/payments',
    'cancelled-receipts': '/reports/cancelled-receipts',
  };
  return paths[report];
}

export function isPaginatedReport(report: ReportName): boolean {
  return !collectionReports.has(report);
}

async function exportErrorMessage(error: unknown): Promise<string> {
  if (!axios.isAxiosError(error)) return error instanceof Error ? error.message : 'Unable to download the report.';
  const body = error.response?.data;
  if (body instanceof Blob) {
    const text = await body.text();
    try {
      const payload = JSON.parse(text) as { error?: { message?: string }; message?: string };
      return payload.error?.message ?? payload.message ?? 'Unable to download the report.';
    } catch {
      return text || 'Unable to download the report.';
    }
  }
  return error.response?.data?.error?.message ?? error.response?.data?.message ?? 'Unable to download the report.';
}

function downloadFilename(contentDisposition: string | undefined, fallback: string): string {
  const match = contentDisposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] ? decodeURIComponent(match[1]) : fallback;
}

export const reportApi = {
  overview: (filters: ReportFilters) => apiService.get<ReportSummary>('/reports/overview', { params: filters }),
  list: (report: ReportName, filters: ReportFilters, pagination?: PaginationParams): Promise<ApiResponse<ReportDataset>> => apiService.get<ReportDataset>(endpoint(report), { params: { ...filters, ...pagination } }),
  download: async (report: ReportName, format: ExportFormat, filters: ReportFilters): Promise<void> => {
    try {
      const response = await apiClient.get<Blob>(`/reports/export/${report}/${format}`, { params: filters, responseType: 'blob' });
      const blob = response.data;
      if (!blob.size) throw new Error('The report export did not contain any data.');
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = downloadFilename(response.headers['content-disposition'] as string | undefined, `${report}-report.${format === 'excel' ? 'csv' : 'pdf'}`);
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } catch (error) {
      throw new Error(await exportErrorMessage(error));
    }
  },
};
