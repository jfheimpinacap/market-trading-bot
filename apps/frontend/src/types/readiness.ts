export type ReadinessProfileType = 'conservative' | 'balanced' | 'strict' | 'custom';
export type ReadinessStatus = 'READY' | 'CAUTION' | 'NOT_READY';

export type ReadinessProfile = {
  id: number;
  name: string;
  slug: string;
  description: string;
  is_active: boolean;
  profile_type: ReadinessProfileType;
  config: Record<string, number>;
  created_at: string;
  updated_at: string;
};

export type ReadinessGateResult = {
  gate: string;
  expected: number;
  actual: number;
  comparator: string;
  passed: boolean;
  severity: 'critical' | 'warning';
  reason: string;
};

export type ReadinessAssessmentRun = {
  id: number;
  readiness_profile: ReadinessProfile;
  status: ReadinessStatus;
  overall_score: string | null;
  summary: string;
  rationale: string;
  gates_passed_count: number;
  gates_failed_count: number;
  warnings_count: number;
  details: {
    metrics?: Record<string, number>;
    gates?: ReadinessGateResult[];
    critical_blockers?: ReadinessGateResult[];
    warnings?: ReadinessGateResult[];
    recommendations?: string[];
    execution_impact_summary?: {
      execution_aware_runs: number;
      avg_fill_rate: number;
      avg_no_fill_rate: number;
      avg_execution_drag: number;
      avg_execution_realism_score: number;
      readiness_penalty: number;
      summary: string;
    };
  };
  created_at: string;
  updated_at: string;
};

export type RunReadinessAssessmentPayload = {
  readiness_profile_id: number;
};

export type ReadinessSummary = {
  latest_run: ReadinessAssessmentRun | null;
  recent_runs: ReadinessAssessmentRun[];
  total_runs: number;
  ready_runs: number;
  caution_runs: number;
  not_ready_runs: number;
};
