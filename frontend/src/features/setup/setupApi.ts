import { apiService } from '@/services/apiService';
import type { Address } from '@/features/companies/companyApi';

export type SetupStep = 'company' | 'employee' | 'login';

export interface PublicCompanyBranding {
  id: string;
  company_name: string;
  logo_url?: string | null;
  theme: {
    primary_color: string;
    secondary_color: string;
  };
}

export interface SetupStatus {
  step: SetupStep;
  company_id: string | null;
  setup_required: boolean;
  company: PublicCompanyBranding | null;
}

export interface InitialCompanyPayload {
  company_name: string;
  code?: string;
  logo_url?: string | null;
  address: Address;
  phone: string;
  email: string;
}

export interface InitialCompanyResult {
  company: { id: string };
  setup_token: string;
}

export interface InitialEmployeePayload {
  employee_id: string;
  photo_url?: string | null;
  name: string;
  gender: 'male' | 'female' | 'non_binary' | 'prefer_not_to_say';
  email: string;
  phone: string;
  address: Address;
  designation: string;
  username: string;
  password: string;
  salary?: string;
  joining_date?: string;
}

export const setupApi = {
  status: () => apiService.get<SetupStatus>('/setup/status'),
  createCompany: (payload: InitialCompanyPayload) => apiService.post<InitialCompanyResult, InitialCompanyPayload>('/setup/company', payload),
  createEmployee: (companyId: string, setupToken: string, payload: InitialEmployeePayload) => apiService.post<null, InitialEmployeePayload>('/setup/employee', payload, {
    headers: { 'X-Setup-Company-ID': companyId, 'X-Setup-Token': setupToken },
  }),
};
