import { apiService } from '@/services/apiService';
import type { VehicleType } from '@/shared/constants/parking';
import type { Page, PaginationParams } from '@/shared/types/api';

export type PaymentMethod = 'cash' | 'upi' | 'card';

export interface VehicleEntry {
  id: string;
  vehicle_number: string;
  rfid: string | null;
  qr_code: string | null;
  vehicle_type: VehicleType;
  entry_at: string;
  parking_number: string;
  token_number: string;
  owner_name: string | null;
  mobile: string | null;
  vehicle_image_available: boolean;
  advance_amount: string;
  location_name: string | null;
  operator: ReceiptOperator;
  status: 'open' | 'closed';
}

export interface VehicleEntryPayload {
  vehicle_number: string;
  rfid?: string | null;
  qr_code?: string | null;
  vehicle_type: VehicleType;
  owner_name?: string | null;
  mobile?: string | null;
  vehicle_image_data?: string | null;
  advance_amount: string;
}

export interface ExitCalculation {
  entry: VehicleEntry;
  duration_minutes: number;
  parking_charge: string;
  gst_percent: string;
  gst_amount: string;
  total_amount: string;
  advance_amount: string;
  advance_applied: string;
  paid_amount: string;
  balance_amount: string;
  rate_effective_date: string;
}

export interface VehicleExit extends ExitCalculation {
  id: string;
  exit_at: string;
  payment_method: PaymentMethod | null;
  payment_reference: string | null;
  status: 'completed';
}

export interface ReceiptCompany {
  company_name: string;
  logo_url: string | null;
  gstin: string | null;
  address: string | null;
  currency: string;
  receipt_footer: string | null;
}

export interface ReceiptOperator {
  name: string;
  employee_id: string | null;
  designation: string | null;
}

export interface ParkingReceipt {
  receipt_type: 'entry' | 'exit';
  receipt_number: string;
  qr_payload: string;
  barcode_value: string;
  issued_at: string;
  company: ReceiptCompany;
  operator: ReceiptOperator;
  entry: VehicleEntry;
  exit: VehicleExit | null;
}

export interface EntryLookup {
  vehicle_number?: string;
  card?: string;
  qr_code?: string;
  rfid?: string;
}

export interface OpenEntryOption {
  id: string;
  vehicle_number: string;
  token_number: string;
  parking_number: string;
  vehicle_type: VehicleType;
  entry_at: string;
}

export interface VehicleMembership {
  vehicle_number: string;
  has_active_pass: boolean;
  pass_number: string | null;
  holder_name: string | null;
  valid_until: string | null;
  remaining_days: number;
  amount: string | null;
}

export interface VehicleExitPayload {
  entry_id: string;
  paid_amount: string;
  payment_method?: PaymentMethod | null;
  payment_reference?: string | null;
}

export const parkingApi = {
  createEntry: (payload: VehicleEntryPayload) => apiService.post<VehicleEntry, VehicleEntryPayload>('/vehicle-entries', payload),
  entryLog: (params: PaginationParams & { search?: string }) => apiService.get<Page<VehicleEntry>>('/vehicle-entries', { params }),
  membership: (vehicleNumber: string) => apiService.get<VehicleMembership>('/vehicle-entries/membership', { params: { vehicle_number: vehicleNumber } }),
  entryReceipt: (id: string) => apiService.get<ParkingReceipt>(`/vehicle-entries/${id}/receipt`),
  lookup: (query: EntryLookup) => apiService.get<VehicleEntry>('/vehicle-exits/lookup', { params: query }),
  openEntries: (search?: string) => apiService.get<OpenEntryOption[]>('/vehicle-exits/open-entries', { params: search ? { search } : undefined }),
  calculateExit: (entryId: string) => apiService.get<ExitCalculation>(`/vehicle-exits/${entryId}/calculate`),
  createExit: (payload: VehicleExitPayload) => apiService.post<VehicleExit, VehicleExitPayload>('/vehicle-exits', payload),
  exitLog: (params: PaginationParams & { search?: string }) => apiService.get<Page<VehicleExit>>('/vehicle-exits', { params }),
  exitReceipt: (id: string) => apiService.get<ParkingReceipt>(`/vehicle-exits/${id}/receipt`),
};

export const paymentMethodLabels: Record<PaymentMethod, string> = { cash: 'Cash', upi: 'UPI', card: 'Card' };
