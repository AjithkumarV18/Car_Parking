const COMPANY_KEY = 'parking.company_id';

function getStorage(rememberMe: boolean): Storage {
  return rememberMe ? localStorage : sessionStorage;
}

export const companyStorage = {
  get: (): string | null => localStorage.getItem(COMPANY_KEY) ?? sessionStorage.getItem(COMPANY_KEY),
  set: (companyId: string, rememberMe: boolean): void => {
    localStorage.removeItem(COMPANY_KEY);
    sessionStorage.removeItem(COMPANY_KEY);
    getStorage(rememberMe).setItem(COMPANY_KEY, companyId.trim());
  },
  clear: (): void => {
    localStorage.removeItem(COMPANY_KEY);
    sessionStorage.removeItem(COMPANY_KEY);
  },
};
