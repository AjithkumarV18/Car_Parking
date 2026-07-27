import { apiService } from '@/services/apiService';
import type { Page, PaginationParams } from '@/shared/types/api';

export type AuditLevel = 'success' | 'warning' | 'error';

export interface AuditActor { id: string | null; name: string; email: string | null; }
export interface AuditLog {
  id: string;
  actor: AuditActor;
  ip_address: string | null;
  module: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  old_value: Record<string, unknown> | unknown[] | string | null;
  new_value: Record<string, unknown> | unknown[] | string | null;
  level: AuditLevel;
  outcome: 'success' | 'failure';
  message: string;
  request_id: string | null;
  occurred_at: string;
  date: string;
  time: string;
}

export type AuditTimelineItem = Omit<AuditLog, 'old_value' | 'new_value' | 'outcome' | 'request_id'>;

export interface AuditFilters extends PaginationParams {
  date_from?: string;
  date_to?: string;
  module?: string;
  action?: string;
  level?: AuditLevel;
  user_id?: string;
  search?: string;
}

export const auditApi = {
  list: (filters: AuditFilters) => apiService.get<Page<AuditTimelineItem>>('/audit-logs', { params: filters }),
  timeline: (filters: Omit<AuditFilters, 'page' | 'limit'>, limit = 20) => apiService.get<AuditTimelineItem[]>('/audit-logs/timeline', { params: { ...filters, limit } }),
  get: (id: string) => apiService.get<AuditLog>(`/audit-logs/${id}`),
};
