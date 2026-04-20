import { API_BASE_URL } from '../../lib/config';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

type InFlightEntry = {
  promise: Promise<unknown>;
  startedAt: number;
};

type CachedSuccessEntry = {
  value: unknown;
  resolvedAt: number;
};

const GET_DEDUP_COOLDOWN_MS = 800;
const SUCCESS_CACHE_TTL_MS = 1200;
const DEBUG_PREFIX = '[frontend-fetch]';
const requestCounters = new Map<string, number>();
const inFlightRequests = new Map<string, InFlightEntry>();
const recentSuccessCache = new Map<string, CachedSuccessEntry>();

const isBrowser = typeof window !== 'undefined';

function normalizeMethod(init?: RequestInit) {
  return (init?.method ?? 'GET').toUpperCase();
}

function shouldDeduplicate(method: string) {
  return method === 'GET';
}

function isNoisyResource(path: string) {
  return [
    '/api/paper/account/',
    '/api/paper/summary/',
    '/api/paper/positions/',
    '/api/paper/trades/',
    '/api/paper/snapshots/',
    '/api/reviews/',
    '/api/mission-control/test-console/status/',
  ].some((prefix) => path.startsWith(prefix));
}

function trackRequestStart(path: string) {
  const current = requestCounters.get(path) ?? 0;
  requestCounters.set(path, current + 1);
  if (isBrowser && isNoisyResource(path)) {
    const inFlight = Array.from(inFlightRequests.keys()).filter((entryPath) => entryPath.startsWith(path)).length;
    // Dev-only lightweight instrumentation for fetch storm debugging.
    // eslint-disable-next-line no-console
    console.debug(`${DEBUG_PREFIX} start`, { path, started: current + 1, inFlight });
  }
}

function trackRequestEnd(path: string) {
  const current = requestCounters.get(path) ?? 0;
  if (current <= 1) {
    requestCounters.delete(path);
  } else {
    requestCounters.set(path, current - 1);
  }

  if (isBrowser && isNoisyResource(path)) {
    const remaining = requestCounters.get(path) ?? 0;
    const inFlight = Array.from(inFlightRequests.keys()).filter((entryPath) => entryPath.startsWith(path)).length;
    // eslint-disable-next-line no-console
    console.debug(`${DEBUG_PREFIX} end`, { path, remaining, inFlight });
  }
}

function getCacheKey(path: string, method: string) {
  return `${method}:${path}`;
}

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

async function performRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await getResponseErrorMessage(response));
  }

  return (await response.json()) as T;
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const method = normalizeMethod(init);
  const dedupeEnabled = shouldDeduplicate(method);
  const cacheKey = getCacheKey(path, method);
  const now = Date.now();

  if (dedupeEnabled) {
    const cached = recentSuccessCache.get(cacheKey);
    if (cached && now - cached.resolvedAt < SUCCESS_CACHE_TTL_MS) {
      return cached.value as T;
    }

    const existing = inFlightRequests.get(cacheKey);
    if (existing && now - existing.startedAt < GET_DEDUP_COOLDOWN_MS) {
      return existing.promise as Promise<T>;
    }
  }

  trackRequestStart(path);

  const requestPromise = performRequest<T>(path, init)
    .then((value) => {
      if (dedupeEnabled) {
        recentSuccessCache.set(cacheKey, {
          value,
          resolvedAt: Date.now(),
        });
      }
      return value;
    })
    .finally(() => {
      inFlightRequests.delete(cacheKey);
      trackRequestEnd(path);
    });

  if (dedupeEnabled) {
    inFlightRequests.set(cacheKey, {
      promise: requestPromise,
      startedAt: now,
    });
  }

  return requestPromise;
}

export function isNotFoundApiError(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 404;
}
