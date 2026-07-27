import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';

interface ProtectedRouteProps {
  roles?: string[];
  permissions?: string[];
}

export function ProtectedRoute({ roles = [], permissions = [] }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated || !user) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }
  if (user.isSuperAdmin) return <Outlet />;
  if (roles.length > 0 && !roles.some((role) => user.roles.includes(role))) {
    return <Navigate to="/unauthorized" replace />;
  }
  if (permissions.length > 0 && !permissions.every((permission) => user.permissions.includes(permission))) {
    return <Navigate to="/unauthorized" replace />;
  }
  return <Outlet />;
}
