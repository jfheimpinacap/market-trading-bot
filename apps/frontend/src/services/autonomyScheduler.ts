import { requestJson } from './api/client';
import type {
  AdmissionRecommendation,
  AutonomySchedulerSummary,
  CampaignAdmission,
  ChangeWindow,
  SchedulerRunPlanResponse,
} from '../types/autonomyScheduler';

export function getAutonomySchedulerQueue() {
  return requestJson<CampaignAdmission[]>('/api/autonomy-scheduler/queue/');
}

export function getAutonomySchedulerWindows() {
  return requestJson<ChangeWindow[]>('/api/autonomy-scheduler/windows/');
}

export function runAutonomySchedulerPlan(payload?: { actor?: string }) {
  return requestJson<SchedulerRunPlanResponse>('/api/autonomy-scheduler/run-plan/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomySchedulerRecommendations() {
  return requestJson<AdmissionRecommendation[]>('/api/autonomy-scheduler/recommendations/');
}

export function getAutonomySchedulerSummary() {
  return requestJson<AutonomySchedulerSummary>('/api/autonomy-scheduler/summary/');
}

export function admitAutonomyCampaign(campaignId: number, payload?: { actor?: string }) {
  return requestJson<CampaignAdmission>(`/api/autonomy-scheduler/admit/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function deferAutonomyCampaign(campaignId: number, payload?: { actor?: string; deferred_until?: string; reason?: string }) {
  return requestJson<CampaignAdmission>(`/api/autonomy-scheduler/defer/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}
