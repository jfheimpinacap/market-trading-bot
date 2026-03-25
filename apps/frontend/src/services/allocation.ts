import { requestJson } from './api/client';
import type { AllocationEvaluatePayload, AllocationEvaluateResponse, AllocationRun, AllocationSummary } from '../types/allocation';

export async function evaluateAllocation(payload: AllocationEvaluatePayload): Promise<AllocationEvaluateResponse> {
  return requestJson<AllocationEvaluateResponse>('/api/allocation/evaluate/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function runAllocation(payload: AllocationEvaluatePayload): Promise<AllocationEvaluateResponse> {
  return requestJson<AllocationEvaluateResponse>('/api/allocation/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getAllocationRuns(): Promise<AllocationRun[]> {
  return requestJson<AllocationRun[]>('/api/allocation/runs/');
}

export async function getAllocationRun(id: number): Promise<AllocationRun> {
  return requestJson<AllocationRun>(`/api/allocation/runs/${id}/`);
}

export async function getAllocationSummary(): Promise<AllocationSummary> {
  return requestJson<AllocationSummary>('/api/allocation/summary/');
}
