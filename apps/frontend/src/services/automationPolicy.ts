import { requestJson } from './api/client';
import type { AutomationActionLog, AutomationDecision, AutomationPolicyCurrent, AutomationPolicyProfile, AutomationPolicySummary } from '../types/automationPolicy';

export function getAutomationProfiles() {
  return requestJson<AutomationPolicyProfile[]>('/api/automation-policy/profiles/');
}

export function getCurrentAutomationPolicy() {
  return requestJson<AutomationPolicyCurrent>('/api/automation-policy/current/');
}

export function evaluateAutomationAction(payload: {
  action_type: string;
  source_context_type?: string;
  runbook_instance_id?: number;
  runbook_step_id?: number;
  metadata?: Record<string, unknown>;
  execute?: boolean;
}) {
  return requestJson<{ decision: AutomationDecision; flags: { can_auto_execute: boolean; approval_required: boolean; blocked: boolean }; action_log: AutomationActionLog | null }>('/api/automation-policy/evaluate/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getAutomationDecisions() {
  return requestJson<AutomationDecision[]>('/api/automation-policy/decisions/');
}

export function getAutomationActionLogs() {
  return requestJson<AutomationActionLog[]>('/api/automation-policy/action-logs/');
}

export function getAutomationPolicySummary() {
  return requestJson<AutomationPolicySummary>('/api/automation-policy/summary/');
}

export function applyAutomationProfile(profileSlug: string) {
  return requestJson<AutomationPolicyProfile>('/api/automation-policy/apply-profile/', {
    method: 'POST',
    body: JSON.stringify({ profile_slug: profileSlug }),
  });
}
