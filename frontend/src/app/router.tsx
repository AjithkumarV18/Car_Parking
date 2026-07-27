import { Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/shared/components/AppLayout';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';
import { SuperAdminRoute } from '@/features/auth/SuperAdminRoute';
import { CompanyManagementPage } from '@/pages/CompanyManagementPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage';
import { InitialCompanySetupPage, InitialEmployeeSetupPage, StartupRedirectPage } from '@/pages/InitialSetupPages';
import { LoginPage } from '@/pages/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { ResetPasswordPage } from '@/pages/ResetPasswordPage';
import { RoleManagementPage } from '@/pages/RoleManagementPage';
import { EmployeeManagementPage } from '@/pages/EmployeeManagementPage';
import { ParkingRateMasterPage } from '@/pages/ParkingRateMasterPage';
import { VehicleEntryPage } from '@/pages/VehicleEntryPage';
import { VehicleExitPage } from '@/pages/VehicleExitPage';
import { ReportsPage } from '@/pages/ReportsPage';
import { AuditLogPage } from '@/pages/AuditLogPage';
import { AdvancedParkingPage } from '@/pages/AdvancedParkingPage';
import { MonthlyPassPage } from '@/pages/MonthlyPassPage';
import { VehicleEntryLogPage, VehicleExitLogPage } from '@/pages/VehicleLogPages';
import { SystemMaintenancePage } from '@/pages/SystemMaintenancePage';
import { SoftwareSettingsPage } from '@/pages/SoftwareSettingsPage';
import { UnauthorizedPage } from '@/pages/UnauthorizedPage';

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<StartupRedirectPage />} />
        <Route path="setup/company" element={<InitialCompanySetupPage />} />
        <Route path="setup/employee" element={<InitialEmployeeSetupPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />
        <Route path="unauthorized" element={<UnauthorizedPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<ProtectedRoute permissions={['dashboard:show']} />}>
            <Route path="app" element={<DashboardPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={['employee:show']} />}>
            <Route path="employees" element={<EmployeeManagementPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={['rate:show']} />}>
            <Route path="parking-rates" element={<ParkingRateMasterPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={['parking_entry:show']} />}>
            <Route path="vehicle-entry" element={<VehicleEntryPage />} />
            <Route path="vehicle-entry-log" element={<VehicleEntryLogPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={['parking_exit:show']} />}>
            <Route path="vehicle-exit" element={<VehicleExitPage />} />
            <Route path="vehicle-exit-log" element={<VehicleExitLogPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={['report:show']} />}>
            <Route path="reports" element={<ReportsPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={['audit:show']} />}>
            <Route path="audit-logs" element={<AuditLogPage />} />
          </Route>
          <Route element={<ProtectedRoute permissions={['advanced:show']} />}>
            <Route path="advanced-parking" element={<AdvancedParkingPage />} />
            <Route path="monthly-passes" element={<MonthlyPassPage />} />
          </Route>
          <Route element={<SuperAdminRoute />}>
            <Route path="companies" element={<CompanyManagementPage />} />
            <Route path="roles" element={<RoleManagementPage />} />
            <Route path="system-maintenance" element={<SystemMaintenancePage />} />
            <Route path="software-settings" element={<SoftwareSettingsPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
