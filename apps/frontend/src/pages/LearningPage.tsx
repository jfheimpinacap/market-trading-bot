import { useCallback, useEffect, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import {
  getLearningAdjustments,
  getLearningIntegrationStatus,
  getLearningMemory,
  getLearningRebuildRuns,
  getLearningSummary,
  rebuildLearningMemory,
} from '../services/learning';
import type { LearningAdjustment, LearningIntegrationStatus, LearningMemoryEntry, LearningRebuildRun, LearningSummary } from '../types/learning';

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function outcomeTone(outcome: string) {
  if (outcome === 'positive') return 'ready';
  if (outcome === 'negative') return 'pending';
  return 'neutral';
}

function activeTone(active: boolean) {
  return active ? 'ready' : 'neutral';
}

export function LearningPage() {
  const [summary, setSummary] = useState<LearningSummary | null>(null);
  const [memoryEntries, setMemoryEntries] = useState<LearningMemoryEntry[]>([]);
  const [adjustments, setAdjustments] = useState<LearningAdjustment[]>([]);
  const [rebuildRuns, setRebuildRuns] = useState<LearningRebuildRun[]>([]);
  const [integrationStatus, setIntegrationStatus] = useState<LearningIntegrationStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRebuilding, setIsRebuilding] = useState(false);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryRes, memoryRes, adjustmentsRes, rebuildRunsRes, integrationStatusRes] = await Promise.all([
        getLearningSummary(),
        getLearningMemory(),
        getLearningAdjustments(),
        getLearningRebuildRuns(),
        getLearningIntegrationStatus(),
      ]);
      setSummary(summaryRes);
      setMemoryEntries(memoryRes);
      setAdjustments(adjustmentsRes);
      setRebuildRuns(rebuildRunsRes);
      setIntegrationStatus(integrationStatusRes);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load learning memory data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleRebuild = async () => {
    setIsRebuilding(true);
    try {
      await rebuildLearningMemory();
      await loadData();
    } finally {
      setIsRebuilding(false);
    }
  };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Heuristic demo learning"
        title="Learning Memory"
        description="Operational memory from reviews/evaluation/safety to apply conservative, auditable heuristic adjustments. This is not ML and not autonomous optimization."
        actions={(
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button type="button" className="secondary-button" onClick={() => navigate('/evaluation')}>Open Evaluation</button>
            <button type="button" className="secondary-button" disabled={isRebuilding} onClick={() => void handleRebuild()}>
              {isRebuilding ? 'Rebuilding learning memory...' : 'Rebuild learning memory'}
            </button>
          </div>
        )}
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!summary ? (
          <EmptyState
            eyebrow="No learning memory"
            title="Learning memory is empty"
            description="Run reviews and evaluation first to build learning memory."
          />
        ) : (
          <>
            <SectionCard eyebrow="Summary" title="Learning summary" description="Conservative learning indicators derived from auditable entries and active adjustments.">
              <div className="system-metadata-grid">
                <div><strong>Total memory entries:</strong> {summary.total_memory_entries}</div>
                <div><strong>Active adjustments:</strong> {summary.active_adjustments}</div>
                <div><strong>Negative patterns detected:</strong> {summary.negative_patterns_detected}</div>
                <div><strong>Conservative bias score:</strong> {summary.conservative_bias_score}</div>
              </div>
            </SectionCard>


            <SectionCard eyebrow="Controlled loop" title="Learning integration status" description="How rebuild is integrated into automation/continuous demo under conservative guardrails.">
              <div className="system-metadata-grid">
                <div><strong>Mode:</strong> {integrationStatus?.learning_rebuild_enabled ? 'Automatic (conservative)' : 'Manual by default'}</div>
                <div><strong>Cadence:</strong> every {integrationStatus?.learning_rebuild_every_n_cycles ?? '—'} cycles</div>
                <div><strong>After reviews:</strong> {integrationStatus?.learning_rebuild_after_reviews ? 'enabled' : 'disabled'}</div>
                <div><strong>Guidance:</strong> {integrationStatus?.message ?? 'Learning rebuild is currently manual.'}</div>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Rebuild audit" title="Recent rebuild runs" description="Every rebuild leaves explicit traceability: trigger, counts, summary, and warnings.">
              {rebuildRuns.length === 0 ? (
                <EmptyState
                  eyebrow="No rebuild runs"
                  title="No learning rebuild runs yet"
                  description="Run reviews and evaluation first to get better learning results."
                />
              ) : (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Status</th>
                        <th>Triggered from</th>
                        <th>Entries</th>
                        <th>Created</th>
                        <th>Updated</th>
                        <th>Deactivated</th>
                        <th>Started</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rebuildRuns.slice(0, 10).map((run) => (
                        <tr key={run.id}>
                          <td>{run.id}</td>
                          <td><StatusBadge tone={run.status === 'SUCCESS' ? 'ready' : run.status === 'PARTIAL' ? 'pending' : 'offline'}>{run.status}</StatusBadge></td>
                          <td>{run.triggered_from}</td>
                          <td>{run.memory_entries_processed}</td>
                          <td>{run.adjustments_created}</td>
                          <td>{run.adjustments_updated}</td>
                          <td>{run.adjustments_deactivated}</td>
                          <td>{formatDate(run.started_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <SectionCard eyebrow="Entries" title="Memory entries" description="Recent memory entries used to derive conservative biases for proposals and risk.">
              {memoryEntries.length === 0 ? (
                <EmptyState eyebrow="No entries" title="No memory entries yet" description="Run reviews and evaluation first to build learning memory." />
              ) : (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Type</th>
                        <th>Scope</th>
                        <th>Outcome</th>
                        <th>Summary</th>
                        <th>Δ Score</th>
                        <th>Δ Confidence</th>
                        <th>Δ Quantity</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {memoryEntries.map((entry) => (
                        <tr key={entry.id}>
                          <td>{entry.id}</td>
                          <td>{entry.memory_type}</td>
                          <td>{entry.provider_slug ?? entry.market_slug ?? entry.source_type}</td>
                          <td><StatusBadge tone={outcomeTone(entry.outcome)}>{entry.outcome}</StatusBadge></td>
                          <td>{entry.summary}</td>
                          <td>{entry.score_delta}</td>
                          <td>{entry.confidence_delta}</td>
                          <td>{entry.quantity_bias_delta}</td>
                          <td>{formatDate(entry.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <SectionCard eyebrow="Active heuristics" title="Adjustments" description="Active conservative adjustments and their scope/magnitude, always auditable and explicit.">
              {adjustments.length === 0 ? (
                <EmptyState eyebrow="No adjustments" title="No active adjustments" description="Rebuild learning memory to calculate current heuristic adjustments." />
              ) : (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Type</th>
                        <th>Scope</th>
                        <th>Magnitude</th>
                        <th>Reason</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {adjustments.map((adjustment) => (
                        <tr key={adjustment.id}>
                          <td>{adjustment.id}</td>
                          <td>{adjustment.adjustment_type}</td>
                          <td>{adjustment.scope_type}:{adjustment.scope_key}</td>
                          <td>{adjustment.magnitude}</td>
                          <td>{adjustment.reason}</td>
                          <td><StatusBadge tone={activeTone(adjustment.is_active)}>{adjustment.is_active ? 'active' : 'inactive'}</StatusBadge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <SectionCard eyebrow="Influence" title="How it impacts the flow" description="Learning memory only nudges proposal confidence/size and adds risk caution. It does not bypass policy or create autonomous control.">
              <ul>
                <li>Proposal engine: confidence and suggested quantity receive bounded, conservative deltas.</li>
                <li>Risk demo: additional caution warning can be injected for sensitive scopes.</li>
                <li>Policy engine: remains authoritative; learning context is secondary and auditable.</li>
              </ul>
            </SectionCard>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
