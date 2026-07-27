import { apiClient } from '@/services/apiClient';
import { apiService } from '@/services/apiService';

export const systemApi = {
  backup: () => apiClient.get<Blob>('/system/backup', { responseType: 'blob' }),
  restore: (backupJson: string) => apiService.post<Record<string, number>, { backup_json: string }>('/system/restore', { backup_json: backupJson }),
};
