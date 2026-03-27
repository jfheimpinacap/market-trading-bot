export type ChaosExperiment = {
  id: number;
  name: string;
  slug: string;
  experiment_type: string;
  is_enabled: boolean;
  severity: 'low' | 'warning' | 'high' | 'critical';
  target_module: string;
  description: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ChaosObservation = {
  id: number;
  run: number;
  code: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
  observed_at: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ResilienceBenchmark = {
  id: number;
  run: number;
  experiment: ChaosExperiment;
  detection_time_seconds: string | null;
  mitigation_time_seconds: string | null;
  recovery_time_seconds: string | null;
  incidents_created: number;
  degraded_mode_triggered: boolean;
  rollback_triggered: boolean;
  alerts_sent: number;
  queue_items_created: number;
  recovery_success_rate: string;
  resilience_score: string;
  metrics: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ChaosRun = {
  id: number;
  experiment: ChaosExperiment;
  status: 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'ABORTED';
  started_at: string;
  finished_at: string | null;
  trigger_mode: 'manual' | 'scheduled' | 'benchmark_suite';
  summary: string;
  details: Record<string, unknown>;
  observations: ChaosObservation[];
  benchmark?: ResilienceBenchmark | null;
  created_at: string;
  updated_at: string;
};

export type RunChaosExperimentPayload = {
  experiment_id: number;
  trigger_mode?: 'manual' | 'scheduled' | 'benchmark_suite';
};

export type ChaosSummary = {
  latest_run: ChaosRun | null;
  recent_runs: ChaosRun[];
  recent_benchmarks: ResilienceBenchmark[];
  total_runs: number;
  success_runs: number;
  partial_runs: number;
  average_resilience_score: number;
};
