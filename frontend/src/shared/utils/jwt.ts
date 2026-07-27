import type { DecodedAccessToken } from '@/shared/types/auth';

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
  return atob(padded);
}

export function parseAccessToken(token: string): DecodedAccessToken | null {
  try {
    const [, encodedPayload] = token.split('.');
    if (!encodedPayload) return null;
    const payload = JSON.parse(decodeBase64Url(encodedPayload)) as DecodedAccessToken;
    if (!payload.sub || payload.token_type === 'refresh') return null;
    if (payload.exp && payload.exp * 1000 <= Date.now()) return null;
    return payload;
  } catch {
    return null;
  }
}
