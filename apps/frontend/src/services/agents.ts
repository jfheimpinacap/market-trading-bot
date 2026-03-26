import { requestJson } from './api/client';
import type { AgentDefinition, AgentHandoff, AgentPipelineRun, AgentRun, AgentSummary } from '../types/agents';

export function getAgents() {
  return requestJson<AgentDefinition[]>('/api/agents/');
}

export function getAgentRuns() {
  return requestJson<AgentRun[]>('/api/agents/runs/');
}

export function getAgentRun(id: number | string) {
  return requestJson<AgentRun>(`/api/agents/runs/${id}/`);
}

export function runAgentPipeline(payload: {
  pipeline_type:
    | 'research_to_prediction'
    | 'postmortem_to_learning'
    | 'real_market_agent_cycle'
    | 'postmortem_board_cycle'
    | 'opportunity_cycle_pipeline'
    | 'signal_to_proposal_execution_cycle';
  triggered_from?: 'manual' | 'automation' | 'continuous_demo' | 'real_ops' | 'replay' | 'experiment';
  payload?: Record<string, unknown>;
}) {
  return requestJson<AgentPipelineRun>('/api/agents/run-pipeline/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getAgentPipelines() {
  return requestJson<AgentPipelineRun[]>('/api/agents/pipelines/');
}

export function getAgentPipeline(id: number | string) {
  return requestJson<AgentPipelineRun>(`/api/agents/pipelines/${id}/`);
}

export function getAgentHandoffs() {
  return requestJson<AgentHandoff[]>('/api/agents/handoffs/');
}

export function getAgentSummary() {
  return requestJson<AgentSummary>('/api/agents/summary/');
}
