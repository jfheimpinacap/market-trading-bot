export type AdapterQualificationStatus = 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED';
export type AdapterQualificationCaseStatus = 'PASSED' | 'FAILED' | 'UNSUPPORTED' | 'WARNING';
export type AdapterReadinessRecommendationCode =
  | 'SANDBOX_CERTIFIED'
  | 'READ_ONLY_PREPARED'
  | 'INCOMPLETE_MAPPING'
  | 'RECONCILIATION_GAPS'
  | 'MANUAL_REVIEW_REQUIRED'
  | 'NOT_READY';

export interface ConnectorCaseDefinition {
  code: string;
  group: string;
  description: string;
}

export interface ConnectorFixtureProfileOption {
  slug: string;
  display_name: string;
  description: string;
}

export interface ConnectorCasesResponse {
  cases: ConnectorCaseDefinition[];
  fixtures: ConnectorFixtureProfileOption[];
}

export interface AdapterQualificationResult {
  id: number;
  qualification_run: number;
  case_code: string;
  case_group: string;
  result_status: AdapterQualificationCaseStatus;
  issues: string[];
  warnings: string[];
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AdapterReadinessRecommendation {
  id: number;
  qualification_run: number;
  recommendation: AdapterReadinessRecommendationCode;
  rationale: string;
  reason_codes: string[];
  missing_capabilities: string[];
  unsupported_paths: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AdapterQualificationRun {
  id: number;
  adapter_name: string;
  adapter_type: string;
  qualification_status: AdapterQualificationStatus;
  capability_checks_run: number;
  payload_checks_run: number;
  response_checks_run: number;
  account_mirror_checks_run: number;
  reconciliation_checks_run: number;
  summary: string;
  details: Record<string, unknown>;
  results: AdapterQualificationResult[];
  readiness_recommendation?: AdapterReadinessRecommendation;
  fixture_profile?: { slug: string; display_name: string };
  created_at: string;
  updated_at: string;
}

export interface ConnectorSummary {
  sandbox_only: boolean;
  total_runs: number;
  success_runs: number;
  partial_runs: number;
  failed_runs: number;
  latest_run: {
    id: number;
    adapter_name: string;
    qualification_status: AdapterQualificationStatus;
    summary: string;
    fixture_profile: string | null;
    created_at: string;
  } | null;
  current_readiness: {
    id: number;
    run_id: number;
    recommendation: AdapterReadinessRecommendationCode;
    rationale: string;
    reason_codes: string[];
    missing_capabilities: string[];
    unsupported_paths: string[];
    created_at: string;
  } | null;
}
