import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import { authEvents } from '@/services/authEvents';
import { companyStorage } from '@/services/companyStorage';
import { tokenStorage } from '@/services/tokenStorage';
import { authApi, toAuthenticatedUser } from '@/features/auth/authApi';
import type { AuthenticatedUser } from '@/shared/types/auth';
import { parseAccessToken } from '@/shared/utils/jwt';
import { AuthContext, type AuthContextValue } from '@/features/auth/context';

function getUserFromToken(token: string | null): AuthenticatedUser | null {
  if (!token) return null;
  const claims = parseAccessToken(token);
  return claims
    ? { id: claims.sub, companyId: claims.company_id, roles: claims.roles ?? [], permissions: claims.permissions ?? [], isSuperAdmin: claims.is_super_admin ?? false }
    : null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(() => getUserFromToken(tokenStorage.getAccessToken()));
  const userId = user?.id;
  const companyId = user?.companyId;

  const signOut = useCallback(() => {
    tokenStorage.clear();
    companyStorage.clear();
    setUser(null);
  }, []);

  const setSession = useCallback((accessToken: string, refreshToken?: string, rememberMe = false, profile?: AuthenticatedUser) => {
    const nextUser = profile ?? getUserFromToken(accessToken);
    if (!nextUser) {
      signOut();
      return;
    }
    tokenStorage.setTokens(accessToken, refreshToken, rememberMe);
    companyStorage.set(nextUser.companyId, rememberMe);
    setUser(nextUser);
  }, [signOut]);

  const refreshProfile = useCallback(async () => {
    const response = await authApi.me();
    if (!response.data) return;
    const profile = toAuthenticatedUser(response.data);
    setUser((current) => current?.id === profile.id ? { ...current, ...profile } : current);
  }, []);

  useEffect(() => authEvents.onSessionExpired(signOut), [signOut]);

  useEffect(() => {
    if (!userId) return;
    void refreshProfile().catch(() => undefined);
  }, [companyId, refreshProfile, userId]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isAuthenticated: user !== null, setSession, refreshProfile, signOut }),
    [user, setSession, refreshProfile, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
