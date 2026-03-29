export type AutonomyPackageCandidate = {
  governance_decision: number;
  planning_proposal: number | null;
  backlog_item: number | null;
  insight: number | null;
  campaign: number | null;
  decision_type: string;
  target_scope: string;
  priority_level: string;
  ready_for_packaging: boolean;
  grouping_key: string;
  existing_package: number | null;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type GovernancePackage = {
  id: number;
  package_type: string;
  package_status: string;
  target_scope: string;
  priority_level: string;
  title: string;
  summary: string;
  rationale: string;
  decision_count: number;
  linked_decision_ids: number[];
  reason_codes: string[];
  blockers: string[];
  grouping_key: string;
  registered_by: string;
  registered_at: string | null;
  linked_target_artifact: string;
  created_at: string;
  updated_at: string;
};

export type PackageRecommendation = {
  id: number;
  governance_decision: number | null;
  governance_package: number | null;
  package_type: string;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyPackageSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  registered_count: number;
  duplicate_skipped_count: number;
  roadmap_package_count: number;
  scenario_package_count: number;
  program_package_count: number;
  manager_package_count: number;
  recommendation_summary: Record<string, number>;
};
