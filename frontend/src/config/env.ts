const DEFAULT_API_URL = "/api/v1";

function parsePositiveInteger(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? '', 10);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export const env = Object.freeze({
  appName: import.meta.env.VITE_APP_NAME ?? 'PMS',
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_URL).replace(/\/$/, ''),
  requestTimeoutMs: parsePositiveInteger(import.meta.env.VITE_REQUEST_TIMEOUT_MS, 15_000),
});
