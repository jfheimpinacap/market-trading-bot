export type AgentStatus = 'READY' | 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'SKIPPED';

export type AgentDefinition = {
  id: number;
  name: string;
  slug: string;
  agent_type: string;
  is_enabled: boolean;
  description: string;
  input_schema_version: string;
  output_schema_version: string;
  created_at: string;
  updated_at: string;
};

export type AgentRun = {
  id: number;
  agent_definition: number;
  agent_name: string;
  agent_slug: string;
  pipeline_run: number | null;
  status: AgentStatus;
  triggered_from: string;
  started_at: string;
  finished_at: string | null;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AgentPipelineRun = {
  id: number;
  pipeline_type: 'research_to_prediction' | 'postmortem_to_learning' | 'real_market_agent_cycle' | 'postmortem_board_cycle';
  status: AgentStatus;
  triggered_from: string;
  started_at: string;
  finished_at: string | null;
  agents_run_count: number;
  handoffs_count: number;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AgentHandoff = {
  id: number;
  from_agent_run: number;
  from_agent_slug: string;
  to_agent_definition: number;
  to_agent_slug: string;
  pipeline_run: number | null;
  handoff_type: string;
  payload_summary: string;
  payload_ref: Record<string, unknown>;
  created_at: string;
};

export type AgentSummary = {
  total_agents: number;
  enabled_agents: number;
  total_runs: number;
  total_handoffs: number;
  total_pipeline_runs: number;
  latest_pipeline_run: AgentPipelineRun | null;
  latest_agent_run: AgentRun | null;
  runs_by_status: Record<string, number>;
  pipelines_by_type: Record<string, number>;
};
