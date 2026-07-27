import { createContext } from 'react';

import type { AuthenticatedUser } from '@/shared/types/auth';

export interface AuthContextValue {
  user: AuthenticatedUser | null;
  isAuthenticated: boolean;
  setSession: (accessToken: string, refreshToken?: string, rememberMe?: boolean, profile?: AuthenticatedUser) => void;
  refreshProfile: () => Promise<void>;
  signOut: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
