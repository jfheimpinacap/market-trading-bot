import { requestJson } from './api/client';
import type { GoLiveApprovalRequest, GoLiveChecklistRun, GoLiveRehearsalRun, GoLiveState, GoLiveSummary } from '../types/goLive';

export function getGoLiveState() {
  return requestJson<GoLiveState>('/api/go-live/state/');
}

export function runGoLiveChecklist(payload: Record<string, unknown> = {}) {
  return requestJson<GoLiveChecklistRun>('/api/go-live/run-checklist/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getGoLiveChecklists() {
  return requestJson<GoLiveChecklistRun[]>('/api/go-live/checklists/');
}

export function createGoLiveApprovalRequest(payload: Record<string, unknown>) {
  return requestJson<GoLiveApprovalRequest>('/api/go-live/request-approval/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getGoLiveApprovals() {
  return requestJson<GoLiveApprovalRequest[]>('/api/go-live/approvals/');
}

export function runGoLiveRehearsal(payload: Record<string, unknown>) {
  return requestJson<GoLiveRehearsalRun>('/api/go-live/run-rehearsal/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getGoLiveRehearsals() {
  return requestJson<GoLiveRehearsalRun[]>('/api/go-live/rehearsals/');
}

export function getGoLiveSummary() {
  return requestJson<GoLiveSummary>('/api/go-live/summary/');
}
