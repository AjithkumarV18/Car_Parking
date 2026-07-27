import { apiService } from '@/services/apiService';
import type { AuthenticatedUser } from '@/shared/types/auth';

export interface Credentials {
  email: string;
  password: string;
  remember_me: boolean;
}

export interface RegisterPayload extends Credentials {
  display_name: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: ApiUser;
}

export interface ApiUser {
  id: string;
  company_id: string;
  email: string;
  display_name: string;
  username?: string | null;
  photo_url?: string | null;
  company_name?: string | null;
  company_logo_url?: string | null;
  company_theme?: { primary_color: string; secondary_color: string } | null;
  roles: string[];
  permissions: string[];
  is_super_admin: boolean;
}

export interface ForgotPasswordResult {
  message: string;
  debug_reset_token?: string | null;
}

const authHeaders = (companyId: string) => ({ headers: { 'X-Company-ID': companyId } });

export const authApi = {
  login: (companyId: string, payload: Credentials) => apiService.post<TokenPair, Credentials>('/auth/login', payload, authHeaders(companyId)),
  register: (companyId: string, payload: RegisterPayload) => apiService.post<TokenPair, RegisterPayload>('/auth/register', payload, authHeaders(companyId)),
  forgotPassword: (companyId: string, email: string) => apiService.post<ForgotPasswordResult, { email: string }>('/auth/forgot-password', { email }, authHeaders(companyId)),
  resetPassword: (companyId: string, token: string, password: string) => apiService.post<null, { token: string; password: string }>('/auth/reset-password', { token, password }, authHeaders(companyId)),
  me: () => apiService.get<ApiUser>('/auth/me'),
};

export function toAuthenticatedUser(user: ApiUser): AuthenticatedUser {
  return {
    id: user.id,
    companyId: user.company_id,
    displayName: user.display_name,
    username: user.username,
    photoUrl: user.photo_url,
    companyName: user.company_name,
    companyLogoUrl: user.company_logo_url,
    companyTheme: user.company_theme ? { primaryColor: user.company_theme.primary_color, secondaryColor: user.company_theme.secondary_color } : null,
    roles: user.roles,
    permissions: user.permissions,
    isSuperAdmin: user.is_super_admin,
  };
}
