export type DemoAutomationActionType =
  | 'simulate_tick'
  | 'generate_signals'
  | 'revalue_portfolio'
  | 'generate_trade_reviews'
  | 'sync_demo_state'
  | 'run_demo_cycle'
  | 'rebuild_learning_memory'
  | 'run_full_learning_cycle'
  | 'sync_real_data';

export type DemoAutomationStatus = 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED';
export type DemoAutomationStepStatus = 'SUCCESS' | 'FAILED' | 'SKIPPED';
export type DemoAutomationTriggeredFrom = 'automation_page' | 'dashboard' | 'system' | 'api';

export type DemoAutomationStepResult = {
  step_name: string;
  status: DemoAutomationStepStatus;
  summary: string;
  metadata: Record<string, unknown>;
};

export type DemoAutomationRun = {
  id: number;
  action_type: DemoAutomationActionType;
  status: DemoAutomationStatus;
  summary: string;
  details: Record<string, unknown>;
  step_results: DemoAutomationStepResult[];
  triggered_from: DemoAutomationTriggeredFrom;
  started_at: string;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DemoAutomationActionDescriptor = {
  action_type: DemoAutomationActionType;
  label: string;
  description: string;
};

export type DemoAutomationSummary = {
  recent_runs_count: number;
  available_actions: DemoAutomationActionDescriptor[];
  latest_run: DemoAutomationRun | null;
  last_by_action: Partial<Record<DemoAutomationActionType, DemoAutomationRun | null>>;
};
