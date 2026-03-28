import { requestJson } from './api/client';
import type {
  AutomationFeedbackSnapshot,
  RunTrustCalibrationResponse,
  TrustCalibrationRecommendation,
  TrustCalibrationRun,
  TrustCalibrationSummary,
} from '../types/trustCalibration';

export function runTrustCalibration(payload: {
  window_days?: number;
  source_type?: string;
  runbook_template_slug?: string;
  profile_slug?: string;
  include_degraded?: boolean;
}) {
  return requestJson<RunTrustCalibrationResponse>('/api/trust-calibration/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getTrustCalibrationRuns() {
  return requestJson<TrustCalibrationRun[]>('/api/trust-calibration/runs/');
}

export function getTrustCalibrationRun(id: number) {
  return requestJson<TrustCalibrationRun>(`/api/trust-calibration/runs/${id}/`);
}

export function getTrustCalibrationRecommendations(runId?: number) {
  const suffix = runId ? `?run_id=${encodeURIComponent(String(runId))}` : '';
  return requestJson<TrustCalibrationRecommendation[]>(`/api/trust-calibration/recommendations/${suffix}`);
}

export function getTrustCalibrationSummary() {
  return requestJson<TrustCalibrationSummary>('/api/trust-calibration/summary/');
}

export function getTrustCalibrationFeedback(runId?: number) {
  const suffix = runId ? `?run_id=${encodeURIComponent(String(runId))}` : '';
  return requestJson<AutomationFeedbackSnapshot[]>(`/api/trust-calibration/feedback/${suffix}`);
}
