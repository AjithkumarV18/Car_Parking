import { apiService } from '@/services/apiService';

export interface SoftwareSettings {
  rfid_entry_enabled: boolean;
  rfid_exit_enabled: boolean;
  qr_entry_enabled: boolean;
  qr_exit_enabled: boolean;
  webcam_capture_enabled: boolean;
  vehicle_image_capture_enabled: boolean;
  advance_payment_enabled: boolean;
  monthly_pass_lookup_enabled: boolean;
  auto_open_receipt_enabled: boolean;
}

export const defaultSoftwareSettings: SoftwareSettings = {
  rfid_entry_enabled: true,
  rfid_exit_enabled: true,
  qr_entry_enabled: true,
  qr_exit_enabled: true,
  webcam_capture_enabled: true,
  vehicle_image_capture_enabled: true,
  advance_payment_enabled: true,
  monthly_pass_lookup_enabled: true,
  auto_open_receipt_enabled: true,
};

export const softwareSettingsApi = {
  get: () => apiService.get<SoftwareSettings>('/settings/software'),
  update: (payload: SoftwareSettings) => apiService.patch<SoftwareSettings, SoftwareSettings>('/settings/software', payload),
};
