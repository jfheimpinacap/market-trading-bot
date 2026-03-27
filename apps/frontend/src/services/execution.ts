import { requestJson } from './api/client';
import type { ExecutionSummary, PaperFill, PaperOrder } from '../types/execution';

export function createPaperOrder(payload: {
  market_id: number;
  side: string;
  requested_quantity: string;
  order_type?: string;
  requested_price?: string | null;
  created_from?: string;
  metadata?: Record<string, unknown>;
  policy_profile?: string;
}) {
  return requestJson<{ order: PaperOrder }>('/api/execution/create-order/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function runExecutionLifecycle(payload?: { open_only?: boolean; metadata?: Record<string, unknown> }) {
  return requestJson<{ lifecycle_run: { id: number; summary: string } }>('/api/execution/run-lifecycle/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getPaperOrders() {
  return requestJson<PaperOrder[]>('/api/execution/orders/');
}

export function getPaperOrder(id: number | string) {
  return requestJson<PaperOrder>(`/api/execution/orders/${id}/`);
}

export function getPaperFills() {
  return requestJson<PaperFill[]>('/api/execution/fills/');
}

export function getExecutionSummary() {
  return requestJson<ExecutionSummary>('/api/execution/summary/');
}
