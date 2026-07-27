import { useContext } from 'react';

import { PublicCompanyContext, type PublicCompanyContextValue } from '@/features/setup/publicCompanyContext';

export function usePublicCompany(): PublicCompanyContextValue {
  const context = useContext(PublicCompanyContext);
  if (!context) throw new Error('usePublicCompany must be used inside PublicCompanyProvider.');
  return context;
}
