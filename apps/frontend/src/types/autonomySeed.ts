export type SeedCandidate = {
  governance_package: number;
  package_resolution: number;
  linked_decisions: number[];
  target_scope: string;
  priority_level: string;
  ready_for_seed: boolean;
  existing_seed: number | null;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type GovernanceSeed = {
  id: number;
  governance_package: number;
  package_resolution: number;
  seed_type: string;
  seed_status: string;
  target_scope: string;
  priority_level: string;
  title: string;
  summary: string;
  rationale: string;
  linked_packages: number[];
  linked_decisions: number[];
  reason_codes: string[];
  blockers: string[];
  grouping_key: string;
  registered_by: string;
  registered_at: string | null;
  linked_target_artifact: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SeedRecommendation = {
  id: number;
  governance_package: number | null;
  governance_seed: number | null;
  recommendation_type: string;
  seed_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type SeedSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  registered_count: number;
  duplicate_skipped_count: number;
  roadmap_seed_count: number;
  scenario_seed_count: number;
  program_seed_count: number;
  manager_seed_count: number;
  recommendation_summary: Record<string, number>;
};
