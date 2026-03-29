import { requestJson } from './api/client';
import type {
  AutonomyBacklogCandidate,
  AutonomyBacklogSummary,
  BacklogRecommendation,
  GovernanceBacklogItem,
  RunAutonomyBacklogReviewResponse,
} from '../types/autonomyBacklog';

export function getAutonomyBacklogCandidates() {
  return requestJson<AutonomyBacklogCandidate[]>('/api/autonomy-backlog/candidates/');
}

export function runAutonomyBacklogReview(payload?: { actor?: string }) {
  return requestJson<RunAutonomyBacklogReviewResponse>('/api/autonomy-backlog/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyBacklogItems() {
  return requestJson<GovernanceBacklogItem[]>('/api/autonomy-backlog/items/');
}

export function getAutonomyBacklogRecommendations() {
  return requestJson<BacklogRecommendation[]>('/api/autonomy-backlog/recommendations/');
}

export function getAutonomyBacklogSummary() {
  return requestJson<AutonomyBacklogSummary>('/api/autonomy-backlog/summary/');
}

export function createAutonomyBacklogItem(artifactId: number, payload?: { actor?: string }) {
  return requestJson<{ item_id: number; backlog_status: string }>(`/api/autonomy-backlog/create/${artifactId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function prioritizeAutonomyBacklogItem(itemId: number, payload?: { actor?: string }) {
  return requestJson<{ item_id: number; backlog_status: string }>(`/api/autonomy-backlog/prioritize/${itemId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function deferAutonomyBacklogItem(itemId: number, payload?: { actor?: string }) {
  return requestJson<{ item_id: number; backlog_status: string }>(`/api/autonomy-backlog/defer/${itemId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}
