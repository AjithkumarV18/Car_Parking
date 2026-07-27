import { apiService } from '@/services/apiService';
import type { Page, PaginationParams } from '@/shared/types/api';

export interface Address {
  line1: string;
  line2?: string | null;
  city: string;
  state: string;
  postal_code: string;
  country_code: string;
}

export interface Theme {
  primary_color: string;
  secondary_color: string;
  logo_url?: string | null;
}

export interface Company {
  id: string;
  company_name: string;
  code?: string | null;
  logo_url?: string | null;
  address: Address;
  gstin?: string | null;
  currency: string;
  theme: Theme;
  receipt_footer?: string | null;
  phone: string;
  email: string;
  date_format: 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD';
  time_format: '12h' | '24h';
  timezone: string;
  status: string;
}

export type CompanyPayload = Omit<Company, 'id' | 'status'>;

export interface Branch {
  id: string;
  company_id: string;
  name: string;
  code?: string | null;
  address: Address;
  phone?: string | null;
  email?: string | null;
  timezone: string;
  status: string;
}

export type BranchPayload = Omit<Branch, 'id' | 'company_id' | 'status'>;

export interface ParkingLocation {
  id: string;
  company_id: string;
  branch_id: string;
  name: string;
  code?: string | null;
  address: Address;
  geo?: { type: 'Point'; coordinates: [number, number] } | null;
  capacity: number;
  phone?: string | null;
  status: string;
}

export type ParkingLocationPayload = Omit<ParkingLocation, 'id' | 'company_id' | 'branch_id' | 'status'>;

const pageConfig = (params: PaginationParams = {}) => ({ params: { page: 1, limit: 100, ...params } });

export const companyApi = {
  get: (id: string) => apiService.get<Company>(`/companies/${id}`),
  update: (id: string, payload: Partial<CompanyPayload>) => apiService.patch<Company, Partial<CompanyPayload>>(`/companies/${id}`, payload),
  listBranches: (companyId: string) => apiService.get<Page<Branch>>(`/companies/${companyId}/branches`, pageConfig()),
  createBranch: (companyId: string, payload: BranchPayload) => apiService.post<Branch, BranchPayload>(`/companies/${companyId}/branches`, payload),
  updateBranch: (companyId: string, branchId: string, payload: Partial<BranchPayload>) => apiService.patch<Branch, Partial<BranchPayload>>(`/companies/${companyId}/branches/${branchId}`, payload),
  removeBranch: (companyId: string, branchId: string) => apiService.delete<null>(`/companies/${companyId}/branches/${branchId}`),
  listLocations: (companyId: string, branchId: string) => apiService.get<Page<ParkingLocation>>(`/companies/${companyId}/branches/${branchId}/locations`, pageConfig()),
  createLocation: (companyId: string, branchId: string, payload: ParkingLocationPayload) => apiService.post<ParkingLocation, ParkingLocationPayload>(`/companies/${companyId}/branches/${branchId}/locations`, payload),
  updateLocation: (companyId: string, branchId: string, locationId: string, payload: Partial<ParkingLocationPayload>) => apiService.patch<ParkingLocation, Partial<ParkingLocationPayload>>(`/companies/${companyId}/branches/${branchId}/locations/${locationId}`, payload),
  removeLocation: (companyId: string, branchId: string, locationId: string) => apiService.delete<null>(`/companies/${companyId}/branches/${branchId}/locations/${locationId}`),
};
