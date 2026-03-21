import { useCallback, useEffect, useState } from 'react';
import { getHealthCheck } from '../services/health';
import type { HealthResponse, HealthStatusState, SystemStatus } from '../types/system';

type HealthCheckState = {
  data: HealthResponse | null;
  error: string | null;
  status: HealthStatusState;
  lastCheckedAt: string | null;
};

const initialState: HealthCheckState = {
  data: null,
  error: null,
  status: 'loading',
  lastCheckedAt: null,
};

export function useHealthCheck() {
  const [state, setState] = useState<HealthCheckState>(initialState);

  const refresh = useCallback(async () => {
    setState((currentState) => ({
      ...currentState,
      status: 'loading',
      error: null,
    }));

    try {
      const data = await getHealthCheck();

      setState({
        data,
        error: null,
        status: 'success',
        lastCheckedAt: new Date().toISOString(),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to reach the backend health endpoint.';

      setState({
        data: null,
        error: message,
        status: 'error',
        lastCheckedAt: new Date().toISOString(),
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const backendStatus: SystemStatus =
    state.status === 'loading'
      ? 'loading'
      : state.data?.status === 'ok'
        ? 'online'
        : 'offline';

  return {
    ...state,
    backendStatus,
    isLoading: state.status === 'loading',
    isSuccess: state.status === 'success',
    isError: state.status === 'error',
    refresh,
  };
}
