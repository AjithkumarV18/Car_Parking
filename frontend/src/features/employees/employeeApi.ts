import { apiClient } from '@/services/apiClient';
import { apiService } from '@/services/apiService';
import type { Address } from '@/features/companies/companyApi';
import type { Page, PaginationParams } from '@/shared/types/api';

export type EmployeeStatus = 'active' | 'on_leave' | 'inactive';
export type Gender = 'male' | 'female' | 'non_binary' | 'prefer_not_to_say';

export interface Employee {
  id: string;
  employee_id: string;
  photo_url?: string | null;
  name: string;
  gender: Gender;
  email: string;
  phone: string;
  address: Address;
  designation: string;
  username: string;
  role_id: string;
  role_name: string;
  salary: string;
  joining_date: string;
  parking_location_id?: string | null;
  parking_location_name?: string | null;
  status: EmployeeStatus;
}

export interface EmployeePayload {
  employee_id: string;
  photo_url?: string | null;
  name: string;
  gender: Gender;
  email: string;
  phone: string;
  address: Address;
  designation: string;
  username: string;
  password?: string;
  role_id: string;
  salary: string;
  joining_date: string;
  parking_location_id?: string | null;
  status: EmployeeStatus;
}

export interface EmployeeOptions {
  roles: Array<{ id: string; name: string }>;
  parking_locations: Array<{ id: string; name: string }>;
}

export interface EmployeeFilters extends PaginationParams {
  search?: string;
  status?: EmployeeStatus;
  gender?: Gender;
  role_id?: string;
  parking_location_id?: string;
  sort_by?: 'employee_id' | 'name' | 'joining_date' | 'salary' | 'designation' | 'created_at';
  sort_order?: 'asc' | 'desc';
}

export const employeeApi = {
  list: (filters: EmployeeFilters) => apiService.get<Page<Employee>>('/employees', { params: filters }),
  get: (id: string) => apiService.get<Employee>(`/employees/${id}`),
  options: () => apiService.get<EmployeeOptions>('/employees/options'),
  create: (payload: EmployeePayload) => apiService.post<Employee, EmployeePayload>('/employees', payload),
  update: (id: string, payload: Partial<EmployeePayload>) => apiService.patch<Employee, Partial<EmployeePayload>>(`/employees/${id}`, payload),
  remove: (id: string) => apiService.delete<null>(`/employees/${id}`),
  download: async (format: 'excel' | 'pdf', filters: Omit<EmployeeFilters, 'page' | 'limit'>): Promise<void> => {
    const response = await apiClient.get(`/employees/export/${format}`, { params: filters, responseType: 'blob' });
    const url = URL.createObjectURL(response.data as Blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = format === 'excel' ? 'employees.csv' : 'employees.pdf';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  },
};
