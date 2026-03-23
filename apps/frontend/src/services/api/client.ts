import { API_BASE_URL } from '../../lib/config';

function extractErrorMessage(value: unknown): string | null {
  if (typeof value === 'string') {
    return value.trim() || null;
  }

  if (Array.isArray(value)) {
    const messages = value
      .map((entry) => extractErrorMessage(entry))
      .filter((entry): entry is string => Boolean(entry));

    return messages.length > 0 ? messages.join(' ') : null;
  }

  if (value && typeof value === 'object') {
    const detail = Reflect.get(value, 'detail');
    const detailMessage = extractErrorMessage(detail);
    if (detailMessage) {
      return detailMessage;
    }

    const messages = Object.values(value as Record<string, unknown>)
      .map((entry) => extractErrorMessage(entry))
      .filter((entry): entry is string => Boolean(entry));

    return messages.length > 0 ? messages.join(' ') : null;
  }

  return null;
}

async function getResponseErrorMessage(response: Response) {
  const fallback = `Request failed with status ${response.status}`;

  let text = '';
  try {
    text = await response.text();
  } catch {
    return fallback;
  }

  if (!text) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(text) as unknown;
    return extractErrorMessage(parsed) ?? text;
  } catch {
    return text;
  }
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(await getResponseErrorMessage(response));
  }

  return (await response.json()) as T;
}
