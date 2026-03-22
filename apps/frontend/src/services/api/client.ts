import { API_BASE_URL } from '../../lib/config';

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let detail = '';

    try {
      detail = await response.text();
    } catch {
      detail = '';
    }

    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}
