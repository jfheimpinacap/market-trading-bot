export type AutonomyDecisionCandidate = {
  planning_proposal: number;
  planning_resolution: number;
  backlog_item: number | null;
  advisory_artifact: number | null;
  insight: number | null;
  campaign: number | null;
  campaign_title: string | null;
  proposal_type: string;
  target_scope: string;
  priority_level: string;
  ready_for_decision: boolean;
  existing_decision: number | null;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type GovernanceDecision = {
  id: number;
  planning_proposal: number;
  planning_resolution: number;
  backlog_item: number | null;
  advisory_artifact: number | null;
  insight: number | null;
  campaign: number | null;
  decision_type: string;
  decision_status: string;
  target_scope: string;
  priority_level: string;
  summary: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  registered_by: string;
  registered_at: string | null;
  linked_target_artifact: string;
  created_at: string;
  updated_at: string;
};

export type DecisionRecommendation = {
  id: number;
  planning_proposal: number | null;
  governance_decision: number | null;
  decision_type: string;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyDecisionSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  registered_count: number;
  duplicate_skipped_count: number;
  roadmap_decision_count: number;
  scenario_decision_count: number;
  program_decision_count: number;
  manager_decision_count: number;
  recommendation_summary: Record<string, number>;
};
