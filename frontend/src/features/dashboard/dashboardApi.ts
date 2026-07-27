import { apiService } from '@/services/apiService';
import type { VehicleType } from '@/shared/constants/parking';

export interface RevenuePoint {
  date: string;
  label: string;
  amount: string;
}

export interface VehicleTypePoint {
  vehicle_type: VehicleType;
  count: number;
}

export interface OccupancyStatus {
  location_id: string | null;
  location_name: string;
  capacity: number;
  occupied: number;
  available: number;
}

export interface RecentActivity {
  id: string;
  kind: 'entry' | 'exit';
  vehicle_number: string;
  token_number: string;
  occurred_at: string;
  location_name: string | null;
  amount: string | null;
}

export interface DashboardOverview {
  currency: string;
  today_collection: string;
  today_entries: number;
  today_exits: number;
  monthly_revenue: string;
  weekly_revenue: string;
  occupied_slots: number;
  available_slots: number;
  revenue: RevenuePoint[];
  vehicle_types: VehicleTypePoint[];
  occupancy: OccupancyStatus[];
  recent_activities: RecentActivity[];
}

export const dashboardApi = {
  overview: () => apiService.get<DashboardOverview>('/dashboard/overview'),
};
