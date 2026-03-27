import { requestJson } from './api/client';
import type { BrokerBridgeSummary, BrokerOrderIntent } from '../types/brokerBridge';

export function createBrokerIntent(payload: { source_type: string; source_id?: string; payload?: Record<string, unknown> }) {
  return requestJson<{ intent: BrokerOrderIntent }>('/api/broker-bridge/create-intent/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function validateBrokerIntent(id: number | string, payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<{ intent: BrokerOrderIntent; validation: number }>(`/api/broker-bridge/validate/${id}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function dryRunBrokerIntent(id: number | string, payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<{ intent: BrokerOrderIntent; dry_run: number }>(`/api/broker-bridge/dry-run/${id}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getBrokerIntents() {
  return requestJson<BrokerOrderIntent[]>('/api/broker-bridge/intents/');
}

export function getBrokerIntent(id: number | string) {
  return requestJson<BrokerOrderIntent>(`/api/broker-bridge/intents/${id}/`);
}

export function getBrokerBridgeSummary() {
  return requestJson<BrokerBridgeSummary>('/api/broker-bridge/summary/');
}
