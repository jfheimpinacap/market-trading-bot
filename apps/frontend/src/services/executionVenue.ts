import { requestJson } from './api/client';
import type { VenueCapabilityProfile, VenueOrderPayload, VenueOrderResponse, VenueParityRun, VenueSummary } from '../types/executionVenue';

export function getVenueCapabilities() {
  return requestJson<VenueCapabilityProfile>('/api/execution-venue/capabilities/');
}

export function buildVenuePayload(intentId: number | string, payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<{ payload: VenueOrderPayload; validation: { is_valid: boolean; reason_codes: string[]; warnings: string[]; missing_fields: string[] } }>(
    `/api/execution-venue/build-payload/${intentId}/`,
    {
      method: 'POST',
      body: JSON.stringify(payload ?? {}),
    },
  );
}

export function dryRunVenueIntent(intentId: number | string, payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<{ payload: VenueOrderPayload; response: VenueOrderResponse }>(`/api/execution-venue/dry-run/${intentId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function runVenueParity(intentId: number | string, payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<VenueParityRun>(`/api/execution-venue/run-parity/${intentId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getVenueParityRuns() {
  return requestJson<VenueParityRun[]>('/api/execution-venue/parity-runs/');
}

export function getVenueSummary() {
  return requestJson<VenueSummary>('/api/execution-venue/summary/');
}
