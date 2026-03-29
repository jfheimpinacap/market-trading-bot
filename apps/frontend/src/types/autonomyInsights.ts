export type AutonomyInsightCandidate = {
  campaign: number;
  campaign_title: string;
  closeout_status: string;
  feedback_resolution_status: string;
  disposition_type: string;
  lifecycle_closed: boolean;
  major_failure_modes: string[];
  major_success_factors: string[];
  approval_friction_level: 'LOW' | 'MEDIUM' | 'HIGH';
  incident_pressure_level: 'LOW' | 'MEDIUM' | 'HIGH';
  recovery_complexity_level: 'LOW' | 'MEDIUM' | 'HIGH';
  roadmap_feedback_present: boolean;
  memory_followup_resolved: boolean;
  postmortem_followup_resolved: boolean;
  metadata: Record<string, unknown>;
};

export type CampaignInsight = {
  id: number;
  campaign: number | null;
  campaign_title?: string | null;
  insight_type: string;
  scope: string;
  summary: string;
  evidence_summary: Record<string, unknown>;
  reason_codes: string[];
  recommended_followup: string;
  recommendation_target: string;
  confidence: string;
  reviewed: boolean;
  reviewed_by: string;
  reviewed_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type InsightRecommendation = {
  id: number;
  recommendation_type: string;
  target_campaign: number | null;
  target_campaign_title?: string | null;
  campaign_insight: number | null;
  insight_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyInsightSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  lifecycle_closed_count: number;
  insight_count: number;
  success_pattern_count: number;
  failure_pattern_count: number;
  blocker_pattern_count: number;
  governance_pattern_count: number;
  pending_review_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunAutonomyInsightReviewResponse = {
  run: number;
  candidate_count: number;
  insight_count: number;
  recommendation_count: number;
};
