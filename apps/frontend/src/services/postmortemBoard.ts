import { requestJson } from './api/client';
import type {
  PostmortemAgentReview,
  PostmortemBoardConclusion,
  PostmortemBoardRun,
  PostmortemBoardSummary,
  RunPostmortemBoardPayload,
} from '../types/postmortemBoard';

export function runPostmortemBoard(payload: RunPostmortemBoardPayload) {
  return requestJson<PostmortemBoardRun>('/api/postmortem-board/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPostmortemBoardRuns() {
  return requestJson<PostmortemBoardRun[]>('/api/postmortem-board/runs/');
}

export function getPostmortemBoardRun(id: string | number) {
  return requestJson<PostmortemBoardRun>(`/api/postmortem-board/runs/${id}/`);
}

export function getPostmortemBoardReviews(boardRunId?: string | number) {
  const qs = boardRunId ? `?board_run_id=${boardRunId}` : '';
  return requestJson<PostmortemAgentReview[]>(`/api/postmortem-board/reviews/${qs}`);
}

export function getPostmortemBoardConclusions(boardRunId?: string | number) {
  const qs = boardRunId ? `?board_run_id=${boardRunId}` : '';
  return requestJson<PostmortemBoardConclusion[]>(`/api/postmortem-board/conclusions/${qs}`);
}

export function getPostmortemBoardSummary() {
  return requestJson<PostmortemBoardSummary>('/api/postmortem-board/summary/');
}

export function runPostmortemPrecedentCompare(payload: { query_text: string; review_id?: number; limit?: number }) {
  return requestJson<{
    retrieval_run_id: number;
    result_count: number;
    influence_mode: string;
    precedent_confidence: number;
    summary: Record<string, unknown>;
  }>('/api/postmortem-board/precedent-compare/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
