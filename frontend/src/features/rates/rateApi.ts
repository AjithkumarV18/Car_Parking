import { apiService } from '@/services/apiService';
import type { Page, PaginationParams } from '@/shared/types/api';
import type { ParkingRateStatus, VehicleType } from '@/shared/constants/parking';

export interface DurationSlab {
  from_minutes: number;
  to_minutes: number | null;
  amount: string;
  gst_percent: string;
}

export interface ParkingRate {
  id: string;
  vehicle_type: VehicleType;
  duration_slabs: DurationSlab[];
  effective_date: string;
  status: ParkingRateStatus;
}

export interface ParkingRatePayload {
  vehicle_type: VehicleType;
  duration_slabs: DurationSlab[];
  effective_date: string;
  status: ParkingRateStatus;
}

export interface ParkingRateFilters extends PaginationParams {
  search?: string;
  status?: ParkingRateStatus;
  vehicle_type?: VehicleType;
  effective_from?: string;
  effective_to?: string;
  sort_by?: 'vehicle_type' | 'effective_date' | 'status' | 'created_at';
  sort_order?: 'asc' | 'desc';
}

export const parkingRateApi = {
  list: (filters: ParkingRateFilters) => apiService.get<Page<ParkingRate>>('/parking-rates', { params: filters }),
  get: (id: string) => apiService.get<ParkingRate>(`/parking-rates/${id}`),
  create: (payload: ParkingRatePayload) => apiService.post<ParkingRate, ParkingRatePayload>('/parking-rates', payload),
  update: (id: string, payload: Partial<ParkingRatePayload>) => apiService.patch<ParkingRate, Partial<ParkingRatePayload>>(`/parking-rates/${id}`, payload),
  remove: (id: string) => apiService.delete<null>(`/parking-rates/${id}`),
};
