import { createContext, useContext } from 'react';
import type { PropsWithChildren } from 'react';
import { useHealthCheck } from '../hooks/useHealthCheck';

type SystemHealthContextValue = ReturnType<typeof useHealthCheck>;

const SystemHealthContext = createContext<SystemHealthContextValue | null>(null);

export function SystemHealthProvider({ children }: PropsWithChildren) {
  const value = useHealthCheck();

  return <SystemHealthContext.Provider value={value}>{children}</SystemHealthContext.Provider>;
}

export function useSystemHealth() {
  const context = useContext(SystemHealthContext);

  if (!context) {
    throw new Error('useSystemHealth must be used within a SystemHealthProvider');
  }

  return context;
}
