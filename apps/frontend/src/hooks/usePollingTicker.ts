import { useEffect } from 'react';

const DEBUG_PREFIX = '[polling]';
const activePollers = new Map<string, number>();

export type PollingTickResult = {
  changed?: boolean;
  idle?: boolean;
  stop?: boolean;
};

type PollingTickerOptions = {
  pauseWhenHidden?: boolean;
  triggerOnFocus?: boolean;
  backoffMultiplier?: number;
  maxBackoffMs?: number;
};

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
  callback: () => Promise<PollingTickResult | void> | PollingTickResult | void,
  intervalMs: number,
  enabled: boolean,
  options?: PollingTickerOptions,
) {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    let cancelled = false;
    let inFlight = false;
    let idleStreak = 0;
    let timer: number | null = null;
    const pauseWhenHidden = options?.pauseWhenHidden ?? true;
    const triggerOnFocus = options?.triggerOnFocus ?? true;
    const backoffMultiplier = Math.max(1, options?.backoffMultiplier ?? 1.7);
    const maxBackoffMs = Math.max(intervalMs, options?.maxBackoffMs ?? 30000);
    updateCount(owner, 1);

    function getNextDelay() {
      if (idleStreak <= 0) return intervalMs;
      return Math.min(maxBackoffMs, Math.round(intervalMs * (backoffMultiplier ** idleStreak)));
    }

    function clearTimer() {
      if (timer === null) return;
      window.clearTimeout(timer);
      timer = null;
    }

    function schedule(delayMs: number) {
      clearTimer();
      timer = window.setTimeout(() => {
        void tick();
      }, Math.max(250, delayMs));
    }

    async function tick(force = false) {
      if (cancelled || inFlight) return;
      if (!force && pauseWhenHidden && document.visibilityState !== 'visible') {
        schedule(intervalMs);
        return;
      }
      inFlight = true;
      try {
        const result = await Promise.resolve(callback());
        if (result?.stop) return;
        if (result?.idle || result?.changed === false) idleStreak += 1;
        else idleStreak = 0;
      } finally {
        inFlight = false;
      }
      schedule(getNextDelay());
    }

    function handleVisibilityChange() {
      if (!triggerOnFocus) return;
      if (document.visibilityState === 'visible') {
        idleStreak = 0;
        void tick(true);
      }
    }

    function handleFocus() {
      if (!triggerOnFocus) return;
      idleStreak = 0;
      void tick(true);
    }

    schedule(intervalMs);
    if (triggerOnFocus) {
      window.addEventListener('focus', handleFocus);
      document.addEventListener('visibilitychange', handleVisibilityChange);
    }

    return () => {
      cancelled = true;
      clearTimer();
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      updateCount(owner, -1);
    };
  }, [callback, enabled, intervalMs, options?.backoffMultiplier, options?.maxBackoffMs, options?.pauseWhenHidden, options?.triggerOnFocus, owner]);
}
