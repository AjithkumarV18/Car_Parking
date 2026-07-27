import { createContext } from 'react';

import type { PublicCompanyBranding, SetupStatus } from '@/features/setup/setupApi';

export interface PublicCompanyContextValue {
  company: PublicCompanyBranding | null;
  status: SetupStatus | null;
  loading: boolean;
  error?: string;
  refresh: () => Promise<void>;
}

export const PublicCompanyContext = createContext<PublicCompanyContextValue | undefined>(undefined);
