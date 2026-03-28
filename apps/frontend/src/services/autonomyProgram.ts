import { requestJson } from './api/client';
import type {
  AutonomyProgramStateResponse,
  CampaignConcurrencyRule,
  CampaignHealthSnapshot,
  ProgramRecommendation,
  AutonomyProgramSummary,
  AutonomyProgramRunReviewResponse,
} from '../types/autonomyProgram';

export function getAutonomyProgramState() {
  return requestJson<AutonomyProgramStateResponse>('/api/autonomy-program/state/');
}

export function getAutonomyProgramRules() {
  return requestJson<CampaignConcurrencyRule[]>('/api/autonomy-program/rules/');
}

export function runAutonomyProgramReview(payload?: { actor?: string; apply_pause_gating?: boolean }) {
  return requestJson<AutonomyProgramRunReviewResponse>('/api/autonomy-program/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyProgramRecommendations() {
  return requestJson<ProgramRecommendation[]>('/api/autonomy-program/recommendations/');
}

export function getAutonomyProgramHealth() {
  return requestJson<CampaignHealthSnapshot[]>('/api/autonomy-program/health/');
}

export function getAutonomyProgramSummary() {
  return requestJson<AutonomyProgramSummary>('/api/autonomy-program/summary/');
}
