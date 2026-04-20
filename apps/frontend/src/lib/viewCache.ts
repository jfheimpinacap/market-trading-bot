const viewCache = new Map<string, unknown>();

export function getViewCache<T>(key: string): T | null {
  if (!viewCache.has(key)) {
    return null;
  }

  return viewCache.get(key) as T;
}

export function setViewCache<T>(key: string, value: T) {
  viewCache.set(key, value);
}
