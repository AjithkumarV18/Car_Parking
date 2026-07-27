import { apiService } from '@/services/apiService';
import type { VehicleType } from '@/shared/constants/parking';

export type SlotStatus = 'available' | 'occupied' | 'reserved' | 'maintenance';
export type PassStatus = 'active' | 'expired' | 'suspended';
export type ReservationStatus = 'active' | 'cancelled' | 'completed' | 'expired';

export interface ParkingLocationOption { id: string; name: string; branch_name: string | null; }
export interface MonthlyPass { id: string; pass_number: string; vehicle_number: string; vehicle_type: VehicleType; holder_name: string; mobile: string | null; parking_location_id: string | null; valid_from: string; valid_until: string; amount: string; status: PassStatus; created_at: string; }
export interface ParkingSlot { id: string; parking_location_id: string; slot_number: string; vehicle_type: VehicleType | null; status: SlotStatus; reserved_for: string | null; occupied_by: string | null; }
export interface ReservedSlot { id: string; parking_slot_id: string; slot_number: string | null; vehicle_number: string; holder_name: string; valid_from: string; valid_until: string; status: ReservationStatus; created_at: string; }

export const advancedApi = {
  locations: () => apiService.get<ParkingLocationOption[]>('/advanced/parking-locations'),
  passes: () => apiService.get<MonthlyPass[]>('/advanced/monthly-passes'),
  createPass: (body: Omit<MonthlyPass, 'id' | 'pass_number' | 'created_at'>) => apiService.post<MonthlyPass, typeof body>('/advanced/monthly-passes', body),
  slots: (locationId?: string) => apiService.get<ParkingSlot[]>('/advanced/parking-slots', { params: locationId ? { location_id: locationId } : undefined }),
  createSlot: (body: Pick<ParkingSlot, 'parking_location_id' | 'slot_number' | 'vehicle_type' | 'status'>) => apiService.post<ParkingSlot, typeof body>('/advanced/parking-slots', body),
  reservations: () => apiService.get<ReservedSlot[]>('/advanced/reserved-slots'),
  createReservation: (body: Omit<ReservedSlot, 'id' | 'slot_number' | 'created_at'>) => apiService.post<ReservedSlot, typeof body>('/advanced/reserved-slots', body),
};
