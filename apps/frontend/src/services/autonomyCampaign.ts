import { requestJson } from './api/client';
import type { AutonomyCampaign, AutonomyCampaignSummary, AutonomyCampaignSourceType } from '../types/autonomyCampaign';

export function createAutonomyCampaign(payload: { source_type: AutonomyCampaignSourceType; source_object_id: string; title?: string; summary?: string; metadata?: Record<string, unknown> }) {
  return requestJson<AutonomyCampaign>('/api/autonomy-campaigns/create/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getAutonomyCampaigns() {
  return requestJson<AutonomyCampaign[]>('/api/autonomy-campaigns/');
}

export function getAutonomyCampaign(id: number) {
  return requestJson<AutonomyCampaign>(`/api/autonomy-campaigns/${id}/`);
}

export function startAutonomyCampaign(id: number, payload?: { actor?: string }) {
  return requestJson<AutonomyCampaign>(`/api/autonomy-campaigns/${id}/start/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function resumeAutonomyCampaign(id: number, payload?: { actor?: string }) {
  return requestJson<AutonomyCampaign>(`/api/autonomy-campaigns/${id}/resume/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function abortAutonomyCampaign(id: number, payload?: { actor?: string; reason?: string }) {
  return requestJson<AutonomyCampaign>(`/api/autonomy-campaigns/${id}/abort/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyCampaignSummary() {
  return requestJson<AutonomyCampaignSummary>('/api/autonomy-campaigns/summary/');
}
