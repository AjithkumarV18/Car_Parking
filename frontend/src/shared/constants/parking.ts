export const VEHICLE_TYPES = ['cycle', 'bike', 'car', 'auto', 'mini_bus', 'bus', 'truck'] as const;

export type VehicleType = (typeof VEHICLE_TYPES)[number];

export const vehicleTypeLabels: Record<VehicleType, string> = {
  cycle: 'Cycle',
  bike: 'Bike',
  car: 'Car',
  auto: 'Auto',
  mini_bus: 'Mini Bus',
  bus: 'Bus',
  truck: 'Truck',
};

export const parkingRateStatuses = ['draft', 'active', 'inactive'] as const;
export type ParkingRateStatus = (typeof parkingRateStatuses)[number];
