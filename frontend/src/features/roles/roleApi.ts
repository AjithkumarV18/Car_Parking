import { apiService } from '@/services/apiService';

export interface Permission {
  key: string;
  name: string;
  module: string;
  action: 'show' | 'save' | 'edit' | 'delete' | 'details' | string;
}

export interface Role {
  id: string;
  company_id: string | null;
  scope: 'system' | 'company';
  code: string;
  name: string;
  description?: string | null;
  is_system: boolean;
  status: string;
  permissions: Permission[];
}

export interface RolePayload {
  name: string;
  description?: string | null;
  permission_keys: string[];
}

export const roleApi = {
  list: () => apiService.get<Role[]>('/roles'),
  get: (id: string) => apiService.get<Role>(`/roles/${id}`),
  permissions: () => apiService.get<Permission[]>('/roles/permissions'),
  create: (payload: RolePayload) => apiService.post<Role, RolePayload>('/roles', payload),
  update: (id: string, payload: Partial<RolePayload>) => apiService.patch<Role, Partial<RolePayload>>(`/roles/${id}`, payload),
  remove: (id: string) => apiService.delete<null>(`/roles/${id}`),
};
