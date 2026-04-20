import { useEffect } from 'react';

const DEBUG_PREFIX = '[polling]';
const activePollers = new Map<string, number>();

function updateCount(name: string, delta: number) {
  const next = Math.max(0, (activePollers.get(name) ?? 0) + delta);
  if (next === 0) {
    activePollers.delete(name);
  } else {
    activePollers.set(name, next);
  }
  // eslint-disable-next-line no-console
  console.debug(`${DEBUG_PREFIX} ${delta > 0 ? 'start' : 'stop'}`, {
    owner: name,
    activeForOwner: activePollers.get(name) ?? 0,
    activeTotal: Array.from(activePollers.values()).reduce((acc, value) => acc + value, 0),
  });
}

export function usePollingTicker(
  owner: string,
  callback: () => Promise<unknown> | unknown,
  intervalMs: number,
  enabled: boolean,
) {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    let cancelled = false;
    updateCount(owner, 1);

    const timer = window.setInterval(() => {
      if (cancelled) {
        return;
      }
      void callback();
    }, intervalMs);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      updateCount(owner, -1);
    };
  }, [callback, enabled, intervalMs, owner]);
}
