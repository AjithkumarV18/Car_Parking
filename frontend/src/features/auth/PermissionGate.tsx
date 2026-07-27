import type { ReactNode } from 'react';

import { useAuth } from '@/features/auth/useAuth';

interface PermissionGateProps {
  permissions?: string[];
  roles?: string[];
  fallback?: ReactNode;
  children: ReactNode;
}

export function PermissionGate({ permissions = [], roles = [], fallback = null, children }: PermissionGateProps) {
  const { user } = useAuth();
  if (user?.isSuperAdmin) return children;
  const hasRole = roles.length === 0 || roles.some((role) => user?.roles.includes(role));
  const hasPermissions = permissions.length === 0 || permissions.every((permission) => user?.permissions.includes(permission));
  return hasRole && hasPermissions ? children : fallback;
}
