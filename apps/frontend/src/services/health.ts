import { requestJson } from './api/client';
import type { HealthResponse } from '../types/system';

export function getHealthCheck() {
  return requestJson<HealthResponse>('/api/health/');
}
