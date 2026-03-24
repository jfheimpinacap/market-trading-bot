export type HealthResponse = {
  status: string;
  service: string;
  environment: string;
  app_mode: string;
  database_configured: boolean;
  redis_configured: boolean;
  redis_required: boolean;
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

export type SystemRuntimeInfo = {
  label: string;
  value: string;
};

export type DeveloperCommandItem = {
  label: string;
  command: string;
  description: string;
};

export type SimulationActivityItem = {
  id: number;
  title: string;
  providerName: string;
  eventTitle: string | null;
  status: string;
  probability: string | null;
  liquidity: string | null;
  volume24h: string | null;
  snapshotCount: number;
  latestSnapshotAt: string | null;
  updatedAt: string;
  activitySource: 'latest_snapshot_at' | 'updated_at';
};

export type SimulationObservation = {
  label: string;
  value: string;
  helperText: string;
  badge: string;
  tone: 'online' | 'offline' | 'loading' | 'ready' | 'pending' | 'neutral';
};
