import { useEffect } from 'react';
import { DEMO_FLOW_REFRESH_EVENT } from '../lib/demoFlow';

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

    window.addEventListener(DEMO_FLOW_REFRESH_EVENT, refresh as EventListener);
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener(DEMO_FLOW_REFRESH_EVENT, refresh as EventListener);
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [enabled, onRefresh]);
}
