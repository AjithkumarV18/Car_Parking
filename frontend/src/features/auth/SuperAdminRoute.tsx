import { Navigate, Outlet } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';

export function SuperAdminRoute() {
  const { user } = useAuth();
  return user?.isSuperAdmin ? <Outlet /> : <Navigate to="/unauthorized" replace />;
}
