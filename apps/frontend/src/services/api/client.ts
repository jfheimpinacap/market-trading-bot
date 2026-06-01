import { API_BASE_URL } from '../../lib/config';

export class ApiError extends Error {
  status: number;
  responseBody: string | null;

  constructor(status: number, message: string, responseBody: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.responseBody = responseBody;
  }
}

type InFlightEntry = {
  promise: Promise<unknown>;
  startedAt: number;
  method: string;
  path: string;
  controller: AbortController | null;
  critical: boolean;
};

type CachedSuccessEntry = {
  value: unknown;
  resolvedAt: number;
};

export type CriticalMutationOptions = {
  timeoutMs?: number;
  starvationWarningMs?: number;
  starvationPendingGetThreshold?: number;
  allowGetPathsDuringMutation?: string[];
  onCreated?: (details: CriticalMutationDetails) => void;
  onDispatched?: (details: CriticalMutationDetails) => void;
  onAborted?: (details: CriticalMutationDetails) => void;
  onTimeout?: (details: CriticalMutationDetails) => void;
  onStarved?: (details: CriticalMutationDetails) => void;
};

export type CriticalMutationDetails = {
  path: string;
  method: string;
  pendingGetCount: number;
  abortedGetCount: number;
  timeoutMs?: number;
  elapsedMs?: number;
};

const GET_DEDUP_COOLDOWN_MS = 800;
const SUCCESS_CACHE_TTL_MS = 1200;
const DEFAULT_CRITICAL_MUTATION_TIMEOUT_MS = 90_000;
const DEFAULT_CRITICAL_MUTATION_STARVATION_MS = 8_000;
const DEFAULT_CRITICAL_MUTATION_PENDING_GET_THRESHOLD = 4;
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
    '/api/mission-control/status/',
    '/api/mission-control/live-paper-validation/',
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

function getPendingGetEntries(allowPaths: string[] = []) {
  return Array.from(inFlightRequests.values()).filter((entry) => (
    entry.method === 'GET'
    && !entry.critical
    && !allowPaths.some((allowedPath) => entry.path.startsWith(allowedPath))
  ));
}

export function countPendingGetRequests(allowPaths: string[] = []) {
  return getPendingGetEntries(allowPaths).length;
}

export function abortSecondaryGetRequests(allowPaths: string[] = []) {
  const entries = getPendingGetEntries(allowPaths);
  entries.forEach((entry) => {
    entry.controller?.abort();
  });
  return entries.length;
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

async function getResponseErrorDetails(response: Response) {
  const fallback = `Request failed with status ${response.status}`;

  let text = '';
  try {
    text = await response.text();
  } catch {
    return { message: fallback, responseBody: null };
  }

  if (!text) {
    return { message: fallback, responseBody: null };
  }

  try {
    const parsed = JSON.parse(text) as unknown;
    return { message: extractErrorMessage(parsed) ?? text, responseBody: text };
  } catch {
    return { message: text, responseBody: text };
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
    const errorDetails = await getResponseErrorDetails(response);
    throw new ApiError(response.status, errorDetails.message, errorDetails.responseBody);
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

  if (!dedupeEnabled) {
    recentSuccessCache.clear();
  }

  const controller = dedupeEnabled && !init?.signal ? new AbortController() : null;
  const requestInit = controller ? { ...init, signal: controller.signal } : init;
  trackRequestStart(path);

  const requestPromise = performRequest<T>(path, requestInit)
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
      method,
      path,
      controller,
      critical: false,
    });
  }

  return requestPromise;
}

export async function requestCriticalJson<T>(path: string, init: RequestInit, options: CriticalMutationOptions = {}): Promise<T> {
  const method = normalizeMethod(init);
  const externalSignal = init.signal;
  const cacheKey = getCacheKey(path, method);
  const allowGetPaths = options.allowGetPathsDuringMutation ?? [];
  const pendingGetCount = countPendingGetRequests(allowGetPaths);
  const abortedGetCount = abortSecondaryGetRequests(allowGetPaths);
  const createdDetails: CriticalMutationDetails = { path, method, pendingGetCount, abortedGetCount };
  options.onCreated?.(createdDetails);

  trackRequestStart(path);
  const startedAt = Date.now();
  let timedOut = false;
  const timeoutController = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_CRITICAL_MUTATION_TIMEOUT_MS;
  const requestInit = { ...init, signal: timeoutController.signal };

  let timeoutId: number | null = null;
  let starvationId: number | null = null;

  const requestPromise = performRequest<T>(path, requestInit)
    .finally(() => {
      inFlightRequests.delete(cacheKey);
      trackRequestEnd(path);
      recentSuccessCache.clear();
    });

  inFlightRequests.set(cacheKey, {
    promise: requestPromise,
    startedAt,
    method,
    path,
    controller: timeoutController,
    critical: true,
  });

  const dispatchedDetails = { ...createdDetails, timeoutMs };
  options.onDispatched?.(dispatchedDetails);

  let handleExternalAbort: (() => void) | null = null;
  if (externalSignal) {
    if (externalSignal.aborted) {
      timeoutController.abort();
    } else {
      handleExternalAbort = () => timeoutController.abort();
      externalSignal.addEventListener('abort', handleExternalAbort, { once: true });
    }
  }

  if (isBrowser) {
    timeoutId = window.setTimeout(() => {
      timedOut = true;
      const elapsedMs = Date.now() - startedAt;
      options.onTimeout?.({ ...dispatchedDetails, elapsedMs });
      timeoutController.abort();
    }, timeoutMs);
  }

  if (isBrowser) {
    const starvationWarningMs = options.starvationWarningMs ?? DEFAULT_CRITICAL_MUTATION_STARVATION_MS;
    starvationId = window.setTimeout(() => {
      const activeGetCount = countPendingGetRequests(allowGetPaths);
      const threshold = options.starvationPendingGetThreshold ?? DEFAULT_CRITICAL_MUTATION_PENDING_GET_THRESHOLD;
      if (pendingGetCount >= threshold || activeGetCount >= threshold) {
        options.onStarved?.({
          ...dispatchedDetails,
          pendingGetCount: activeGetCount,
          elapsedMs: Date.now() - startedAt,
        });
      }
    }, starvationWarningMs);
  }

  try {
    return await requestPromise;
  } catch (error) {
    if (timedOut || (error instanceof DOMException && error.name === 'AbortError')) {
      options.onAborted?.({ ...dispatchedDetails, elapsedMs: Date.now() - startedAt });
    }
    throw error;
  } finally {
    if (timeoutId !== null) window.clearTimeout(timeoutId);
    if (starvationId !== null) window.clearTimeout(starvationId);
    if (externalSignal && handleExternalAbort) {
      externalSignal.removeEventListener('abort', handleExternalAbort);
    }
  }
}

export function isNotFoundApiError(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 404;
}
