export type OpportunityExecutionPath = 'WATCH' | 'PROPOSAL_ONLY' | 'QUEUE' | 'AUTO_EXECUTE_PAPER' | 'BLOCKED' | string;

export type OpportunityCycleRun = {
  id: number;
  status: string;
  profile_slug: string;
  started_at: string;
  finished_at: string | null;
  markets_scanned: number;
  opportunities_built: number;
  proposals_generated: number;
  allocation_ready_count: number;
  queued_count: number;
  auto_executed_count: number;
  blocked_count: number;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type OpportunityExecutionPlan = {
  id: number;
  allocation_quantity: string | null;
  runtime_mode: string;
  policy_decision: string;
  safety_status: string;
  queue_required: boolean;
  auto_execute_allowed: boolean;
  final_recommended_action: OpportunityExecutionPath;
  explanation: string;
};

export type OpportunityCycleItem = {
  id: number;
  run: number;
  market: number;
  market_title: string;
  market_slug: string;
  source_provider: string;
  research_context: Record<string, unknown>;
  prediction_context: Record<string, unknown>;
  risk_context: Record<string, unknown>;
  signal_context: Record<string, unknown>;
  proposal: number | null;
  proposal_status: string;
  allocation_status: string;
  allocation_quantity: string | null;
  execution_path: OpportunityExecutionPath;
  rationale: string;
  execution_plan: OpportunityExecutionPlan | null;
  created_at: string;
  updated_at: string;
};

export type OpportunitySummary = {
  total_cycles: number;
  latest_cycle: number | null;
  opportunities_built: number;
  proposal_ready: number;
  queued: number;
  auto_executable: number;
  blocked: number;
  watch: number;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
  portfolio_throttle_state: string;
  portfolio_new_entries_blocked: boolean;
  profiles: Array<{ slug: string; label: string }>;
};
