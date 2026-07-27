import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import { PublicCompanyContext, type PublicCompanyContextValue } from '@/features/setup/publicCompanyContext';
import { setupApi, type SetupStatus } from '@/features/setup/setupApi';

export function PublicCompanyProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const response = await setupApi.status();
      if (!response.data) throw new Error(response.message || 'Unable to load company details.');
      setStatus(response.data);
    } catch (requestError) {
      setStatus(null);
      setError(requestError instanceof Error ? requestError.message : 'Unable to load company details.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const value = useMemo<PublicCompanyContextValue>(() => ({
    company: status?.company ?? null,
    status,
    loading,
    error,
    refresh,
  }), [error, loading, refresh, status]);

  return <PublicCompanyContext.Provider value={value}>{children}</PublicCompanyContext.Provider>;
}
