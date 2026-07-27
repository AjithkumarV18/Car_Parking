import axios from 'axios';

import type { ApiResponse } from '@/shared/types/api';

function validationMessage(details: unknown): string | undefined {
  if (!Array.isArray(details)) return undefined;
  const messages = details.map((detail) => {
    if (!detail || typeof detail !== 'object') return undefined;
    const record = detail as { loc?: unknown; msg?: unknown };
    const location = Array.isArray(record.loc)
      ? record.loc.filter((part) => part !== 'body').map(String).join('.')
      : undefined;
    const message = typeof record.msg === 'string' ? record.msg : undefined;
    return message ? `${location ? `${location}: ` : ''}${message}` : undefined;
  }).filter((message): message is string => Boolean(message));
  return messages.length ? messages.join(' ') : undefined;
}

export function getApiErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  if (axios.isAxiosError<ApiResponse<never>>(error)) {
    const apiError = error.response?.data.error;
    return validationMessage(apiError?.details) ?? apiError?.message ?? error.response?.data.message ?? fallback;
  }
  return error instanceof Error ? error.message : fallback;
}
