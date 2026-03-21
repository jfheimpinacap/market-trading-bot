export type HealthResponse = {
  status: string;
  service: string;
  environment: string;
  database_configured: boolean;
  redis_configured: boolean;
};

export type NavRoute = {
  label: string;
  path: string;
  description: string;
};

export type DashboardModule = {
  name: string;
  summary: string;
  status: 'available' | 'planned';
};

export type SystemStatus = 'loading' | 'online' | 'offline' | 'degraded';
export type HealthStatusState = 'loading' | 'success' | 'error';
