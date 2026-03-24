import { requestJson } from './api/client';
import type { SafetyConfig, SafetyEvent, SafetyStatus, SafetySummary } from '../types/safety';

export function getSafetyStatus() {
  return requestJson<SafetyStatus>('/api/safety/status/');
}

export function getSafetyEvents() {
  return requestJson<SafetyEvent[]>('/api/safety/events/');
}

export function getSafetyEvent(id: string | number) {
  return requestJson<SafetyEvent>(`/api/safety/events/${id}/`);
}

export function enableKillSwitch() {
  return requestJson<{ kill_switch_enabled: boolean; status: string }>('/api/safety/kill-switch/enable/', { method: 'POST', body: JSON.stringify({}) });
}

export function disableKillSwitch() {
  return requestJson<{ kill_switch_enabled: boolean; status: string }>('/api/safety/kill-switch/disable/', { method: 'POST', body: JSON.stringify({}) });
}

export function getSafetyConfig() {
  return requestJson<SafetyConfig>('/api/safety/config/');
}

export function updateSafetyConfig(payload: Partial<SafetyConfig>) {
  return requestJson<SafetyConfig>('/api/safety/config/', { method: 'POST', body: JSON.stringify(payload) });
}

export function getSafetySummary() {
  return requestJson<SafetySummary>('/api/safety/summary/');
}

export function resetSafetyCooldown() {
  return requestJson<{ status: string; cooldown_until_cycle: number | null }>('/api/safety/reset-cooldown/', { method: 'POST', body: JSON.stringify({}) });
}
