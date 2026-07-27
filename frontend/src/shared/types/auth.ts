export interface CompanyThemeColors {
  primaryColor: string;
  secondaryColor: string;
}

export interface AuthenticatedUser {
  id: string;
  companyId: string;
  displayName?: string;
  username?: string | null;
  photoUrl?: string | null;
  companyName?: string | null;
  companyLogoUrl?: string | null;
  companyTheme?: CompanyThemeColors | null;
  roles: string[];
  permissions: string[];
  isSuperAdmin: boolean;
}

export interface DecodedAccessToken {
  sub: string;
  roles?: string[];
  permissions?: string[];
  company_id: string;
  is_super_admin?: boolean;
  exp?: number;
  token_type?: 'access' | 'refresh';
}
