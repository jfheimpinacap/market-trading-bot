import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getAgentHandoffs, getAgentPipelines, getAgents, getAgentRuns, getAgentSummary, runAgentPipeline } from '../services/agents';
import type { AgentHandoff, AgentPipelineRun, AgentRun, AgentStatus, AgentSummary, AgentDefinition } from '../types/agents';

function fmtDate(value?: string | null) {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(d);
}

function statusTone(status: AgentStatus) {
  if (status === 'SUCCESS') return 'ready';
  if (status === 'RUNNING') return 'pending';
  if (status === 'PARTIAL') return 'pending';
  if (status === 'FAILED') return 'offline';
  return 'neutral';
}

function enabledTone(enabled: boolean) {
  return enabled ? 'ready' : 'neutral';
}

const PIPELINE_OPTIONS: Array<{ key: AgentPipelineRun['pipeline_type']; label: string; description: string; payload?: Record<string, unknown> }> = [
  {
    key: 'research_to_prediction',
    label: 'Run Research → Prediction',
    description: 'Uses narrative candidates and scores markets with explicit research→prediction handoffs.',
    payload: { candidate_limit: 10 },
  },
  {
    key: 'postmortem_to_learning',
    label: 'Run Postmortem → Learning',
    description: 'Generates/refreshed reviews then rebuilds learning memory adjustments.',
    payload: { review_limit: 25 },
  },
  {
    key: 'postmortem_board_cycle',
    label: 'Run Postmortem Board Cycle',
    description: 'Runs postmortem board committee (narrative/prediction/risk/runtime/learning) with explicit handoffs.',
    payload: { review_limit: 25, force_learning_rebuild: true },
  },
  {
    key: 'real_market_agent_cycle',
    label: 'Run Real-Market Agent Cycle',
    description: 'Read-only real-market scope through research→prediction→risk in paper/demo mode.',
    payload: { market_limit: 5, quantity: '1.0000' },
  },
  {
    key: 'opportunity_cycle_pipeline',
    label: 'Run Opportunity Cycle Pipeline',
    description: 'research→prediction→risk handoffs plus opportunity supervisor cycle (signal→proposal→allocation→path).',
    payload: { profile_slug: 'balanced_supervisor' },
  },
  {
    key: 'signal_to_proposal_execution_cycle',
    label: 'Run Signal→Proposal→Execution Cycle',
    description: 'Shortcut pipeline for end-to-end signal-to-execution-path supervision in paper/demo mode.',
    payload: { profile_slug: 'balanced_supervisor' },
  },
];

export function AgentsPage() {
  const [summary, setSummary] = useState<AgentSummary | null>(null);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [handoffs, setHandoffs] = useState<AgentHandoff[]>([]);
  const [pipelines, setPipelines] = useState<AgentPipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningPipeline, setRunningPipeline] = useState<AgentPipelineRun['pipeline_type'] | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, agentsRes, runsRes, handoffsRes, pipelinesRes] = await Promise.all([
        getAgentSummary(),
        getAgents(),
        getAgentRuns(),
        getAgentHandoffs(),
        getAgentPipelines(),
      ]);
      setSummary(summaryRes);
      setAgents(agentsRes);
      setRuns(runsRes.slice(0, 20));
      setHandoffs(handoffsRes.slice(0, 20));
      setPipelines(pipelinesRes.slice(0, 20));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load agent orchestration data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runPipeline = async (pipelineType: AgentPipelineRun['pipeline_type'], payload?: Record<string, unknown>) => {
    setRunningPipeline(pipelineType);
    setError(null);
    try {
      await runAgentPipeline({ pipeline_type: pipelineType, triggered_from: 'manual', payload });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline run failed.');
    } finally {
      setRunningPipeline(null);
    }
  };

  const disabledAgentCount = useMemo(() => agents.filter((agent) => !agent.is_enabled).length, [agents]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Agent orchestration"
        title="Agents"
        description="Explicit, auditable orchestration layer for scan/research/prediction/risk/postmortem agents. Local-first and paper/demo only (no real-money execution)."
        actions={(
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button type="button" className="secondary-button" onClick={() => navigate('/research')}>Open Research</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/prediction')}>Open Prediction</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/runtime')}>Open Runtime</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/risk-agent')}>Open Risk Agent</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/postmortem-board')}>Open Postmortem Board</button>
          </div>
        )}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Overview" title="Agent orchestration summary" description="Run traceability, handoff visibility, and pipeline-level execution status.">
          <div className="system-metadata-grid">
            <div><strong>Registered agents:</strong> {summary?.total_agents ?? 0}</div>
            <div><strong>Enabled agents:</strong> {summary?.enabled_agents ?? 0}</div>
            <div><strong>Pipeline runs:</strong> {summary?.total_pipeline_runs ?? 0}</div>
            <div><strong>Agent runs:</strong> {summary?.total_runs ?? 0}</div>
            <div><strong>Handoffs:</strong> {summary?.total_handoffs ?? 0}</div>
            <div><strong>Disabled agents:</strong> {disabledAgentCount}</div>
          </div>
          <p style={{ marginTop: '0.75rem' }}>
            <strong>Latest pipeline:</strong> {summary?.latest_pipeline_run ? `${summary.latest_pipeline_run.pipeline_type} (${summary.latest_pipeline_run.status})` : 'No pipeline run yet.'}
          </p>
        </SectionCard>

        <SectionCard eyebrow="Registry" title="Registered agents" description="Explicit agent registry with schema versions and operational status.">
          {agents.length === 0 ? (
            <EmptyState eyebrow="No agents" title="No agent definitions available" description="Refresh the page to trigger default registry bootstrap." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Agent</th><th>Slug</th><th>Type</th><th>Status</th><th>Schema in/out</th><th>Description</th></tr></thead>
                <tbody>
                  {agents.map((agent) => (
                    <tr key={agent.id}>
                      <td>{agent.name}</td>
                      <td>{agent.slug}</td>
                      <td>{agent.agent_type}</td>
                      <td><StatusBadge tone={enabledTone(agent.is_enabled)}>{agent.is_enabled ? 'enabled' : 'disabled'}</StatusBadge></td>
                      <td>{agent.input_schema_version} → {agent.output_schema_version}</td>
                      <td>{agent.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Controls" title="Pipeline controls" description="Manual trigger controls for explicit pipeline runs with auditable handoffs.">
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {PIPELINE_OPTIONS.map((option) => (
              <div key={option.key} className="panel" style={{ padding: '0.9rem 1rem', boxShadow: 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                  <div>
                    <strong>{option.label}</strong>
                    <p style={{ margin: '0.35rem 0 0' }}>{option.description}</p>
                  </div>
                  <button type="button" className="secondary-button" disabled={Boolean(runningPipeline)} onClick={() => void runPipeline(option.key, option.payload)}>
                    {runningPipeline === option.key ? 'Running...' : 'Run'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Runs" title="Recent agent runs" description="Per-agent execution records with status, trigger origin, timing, and summary.">
          {runs.length === 0 ? (
            <EmptyState eyebrow="No runs" title="No agent runs yet" description="Run a pipeline to see agent handoffs." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Agent</th><th>Status</th><th>Triggered from</th><th>Started</th><th>Finished</th><th>Summary</th></tr></thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>{run.agent_name}</td>
                      <td><StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge></td>
                      <td>{run.triggered_from}</td>
                      <td>{fmtDate(run.started_at)}</td>
                      <td>{fmtDate(run.finished_at)}</td>
                      <td>{run.summary || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Handoffs" title="Recent handoffs" description="Structured handoff payload trace between registered agents.">
          {handoffs.length === 0 ? (
            <EmptyState eyebrow="No handoffs" title="No handoffs yet" description="Run a pipeline to see agent handoffs." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>From</th><th>To</th><th>Type</th><th>Payload summary</th><th>Created</th></tr></thead>
                <tbody>
                  {handoffs.map((handoff) => (
                    <tr key={handoff.id}>
                      <td>{handoff.from_agent_slug}</td>
                      <td>{handoff.to_agent_slug}</td>
                      <td>{handoff.handoff_type}</td>
                      <td>{handoff.payload_summary || '—'}</td>
                      <td>{fmtDate(handoff.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Pipelines" title="Recent pipeline runs" description="End-to-end pipeline execution runs for continuous demo and real-ops integration readiness.">
          {pipelines.length === 0 ? (
            <EmptyState eyebrow="No pipelines" title="No pipeline runs yet" description="Run a pipeline to register end-to-end orchestration traces." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Type</th><th>Status</th><th>Agents</th><th>Handoffs</th><th>Started</th><th>Finished</th><th>Summary</th></tr></thead>
                <tbody>
                  {pipelines.map((pipeline) => (
                    <tr key={pipeline.id}>
                      <td>{pipeline.pipeline_type}</td>
                      <td><StatusBadge tone={statusTone(pipeline.status)}>{pipeline.status}</StatusBadge></td>
                      <td>{pipeline.agents_run_count}</td>
                      <td>{pipeline.handoffs_count}</td>
                      <td>{fmtDate(pipeline.started_at)}</td>
                      <td>{fmtDate(pipeline.finished_at)}</td>
                      <td>{pipeline.summary || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
