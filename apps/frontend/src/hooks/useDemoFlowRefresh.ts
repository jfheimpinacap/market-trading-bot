import { useEffect } from 'react';
import { DEMO_FLOW_REFRESH_EVENT } from '../lib/demoFlow';

const DEBUG_PREFIX = '[demo-flow-refresh]';
let activeBindings = 0;

export function useDemoFlowRefresh(onRefresh: () => Promise<void> | void, enabled = true) {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    function refresh() {
      void onRefresh();
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        refresh();
      }
    }

    activeBindings += 1;
    // eslint-disable-next-line no-console
    console.debug(`${DEBUG_PREFIX} bind`, { activeBindings });

    window.addEventListener(DEMO_FLOW_REFRESH_EVENT, refresh as EventListener);
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener(DEMO_FLOW_REFRESH_EVENT, refresh as EventListener);
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      activeBindings = Math.max(0, activeBindings - 1);
      // eslint-disable-next-line no-console
      console.debug(`${DEBUG_PREFIX} unbind`, { activeBindings });
    };
  }, [enabled, onRefresh]);
}
