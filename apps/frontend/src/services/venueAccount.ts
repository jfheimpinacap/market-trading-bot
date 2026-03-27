import { requestJson } from './api/client';
import type {
  VenueAccountSnapshot,
  VenueAccountSummary,
  VenueBalanceSnapshot,
  VenueOrderSnapshot,
  VenuePositionSnapshot,
  VenueReconciliationRun,
} from '../types/venueAccount';

export function getVenueAccountCurrent() {
  return requestJson<VenueAccountSnapshot>('/api/venue-account/current/');
}

export function getVenueAccountOrders() {
  return requestJson<VenueOrderSnapshot[]>('/api/venue-account/orders/');
}

export function getVenueAccountPositions() {
  return requestJson<VenuePositionSnapshot[]>('/api/venue-account/positions/');
}

export function getVenueAccountBalances() {
  return requestJson<VenueBalanceSnapshot[]>('/api/venue-account/balances/');
}

export function runVenueReconciliation(payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<VenueReconciliationRun>('/api/venue-account/run-reconciliation/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getVenueReconciliationRuns() {
  return requestJson<VenueReconciliationRun[]>('/api/venue-account/reconciliation-runs/');
}

export function getVenueReconciliationRun(id: number | string) {
  return requestJson<VenueReconciliationRun>(`/api/venue-account/reconciliation-runs/${id}/`);
}

export function getVenueAccountSummary() {
  return requestJson<VenueAccountSummary>('/api/venue-account/summary/');
}
