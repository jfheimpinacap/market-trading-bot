import { requestJson } from './api/client';
import type {
  NotificationAutomationState,
  NotificationChannel,
  NotificationDelivery,
  NotificationEscalationEvent,
  NotificationRule,
  NotificationSummary,
} from '../types/notifications';

export function getNotificationChannels() {
  return requestJson<NotificationChannel[]>('/api/notifications/channels/');
}

export function createOrUpdateNotificationChannel(payload: Partial<NotificationChannel>) {
  return requestJson<NotificationChannel>('/api/notifications/channels/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getNotificationRules() {
  return requestJson<NotificationRule[]>('/api/notifications/rules/');
}

export function createOrUpdateNotificationRule(payload: Partial<NotificationRule>) {
  return requestJson<NotificationRule>('/api/notifications/rules/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getNotificationDeliveries() {
  return requestJson<NotificationDelivery[]>('/api/notifications/deliveries/');
}

export function getNotificationDelivery(id: string | number) {
  return requestJson<NotificationDelivery>(`/api/notifications/deliveries/${id}/`);
}

export function sendAlertNotification(id: string | number, force = false) {
  return requestJson<NotificationDelivery[]>(`/api/notifications/send-alert/${id}/`, {
    method: 'POST',
    body: JSON.stringify({ force }),
  });
}

export function sendDigestNotification(id: string | number, force = false) {
  return requestJson<NotificationDelivery[]>(`/api/notifications/send-digest/${id}/`, {
    method: 'POST',
    body: JSON.stringify({ force }),
  });
}

export function getNotificationSummary() {
  return requestJson<NotificationSummary>('/api/notifications/summary/');
}

export function getNotificationAutomationStatus() {
  return requestJson<NotificationAutomationState>('/api/notifications/automation-status/');
}

export function enableNotificationAutomation() {
  return requestJson<NotificationAutomationState>('/api/notifications/automation-enable/', { method: 'POST' });
}

export function disableNotificationAutomation() {
  return requestJson<NotificationAutomationState>('/api/notifications/automation-disable/', { method: 'POST' });
}

export function runAutomaticDispatch() {
  return requestJson<{ dispatch: Record<string, unknown>; escalation: Record<string, unknown> }>('/api/notifications/run-automatic-dispatch/', {
    method: 'POST',
  });
}

export function runDigestCycle(force = false) {
  return requestJson<Record<string, unknown>>('/api/notifications/run-digest-cycle/', {
    method: 'POST',
    body: JSON.stringify({ force }),
  });
}

export function getNotificationEscalations() {
  return requestJson<NotificationEscalationEvent[]>('/api/notifications/escalations/');
}
