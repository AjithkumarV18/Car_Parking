const SETUP_COMPANY_ID_KEY = 'parking.initial_setup.company_id';
const SETUP_TOKEN_KEY = 'parking.initial_setup.token';

export const setupStorage = {
  get: (): { companyId: string; token: string } | null => {
    const companyId = localStorage.getItem(SETUP_COMPANY_ID_KEY);
    const token = localStorage.getItem(SETUP_TOKEN_KEY);
    return companyId && token ? { companyId, token } : null;
  },
  set: (companyId: string, token: string): void => {
    localStorage.setItem(SETUP_COMPANY_ID_KEY, companyId);
    localStorage.setItem(SETUP_TOKEN_KEY, token);
  },
  clear: (): void => {
    localStorage.removeItem(SETUP_COMPANY_ID_KEY);
    localStorage.removeItem(SETUP_TOKEN_KEY);
  },
};
