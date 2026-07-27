export const ROLES = {
  superAdmin: 'super_admin',
  admin: 'admin',
  operator: 'operator',
  attendant: 'attendant',
  viewer: 'viewer',
} as const;

export const PERMISSIONS = {
  systemRead: 'system:read',
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];
export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];
