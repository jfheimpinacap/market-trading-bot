import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { EmptyState } from '../components/EmptyState';
import { evaluateAllocation, getAllocationRuns, getAllocationSummary, runAllocation } from '../services/allocation';
import type { AllocationEvaluateResponse, AllocationScopeType, AllocationRun } from '../types/allocation';

function decisionTone(decision: string): 'ready' | 'pending' | 'neutral' | 'offline' {
  if (decision === 'SELECTED') return 'ready';
  if (decision === 'REDUCED') return 'pending';
  if (decision === 'SKIPPED') return 'neutral';
  return 'offline';
}

export function AllocationPage() {
  const [scope, setScope] = useState<AllocationScopeType>('mixed');
  const [evaluation, setEvaluation] = useState<AllocationEvaluateResponse | null>(null);
  const [runs, setRuns] = useState<AllocationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summary, runsList] = await Promise.all([getAllocationSummary(), getAllocationRuns()]);
      setRuns(runsList);
      const latest = summary.latest_run;
      if (latest?.decisions?.length) {
        setEvaluation((current) => current ?? {
          scope_type: latest.scope_type,
          triggered_from: latest.triggered_from,
          proposals_considered: latest.proposals_considered,
          proposals_ranked: latest.proposals_ranked,
          proposals_selected: latest.proposals_selected,
          proposals_rejected: latest.proposals_rejected,
          allocated_total: latest.allocated_total,
          remaining_cash: latest.remaining_cash,
          summary: latest.summary,
          details: latest.decisions.map((item) => ({
            proposal_id: item.proposal,
            market: item.market_title,
            direction: item.direction,
            proposal_score: item.proposal_score,
            confidence: item.confidence,
            suggested_quantity: item.suggested_quantity,
            final_allocated_quantity: item.final_allocated_quantity,
            decision: item.decision,
            rank: item.rank,
            source_type: item.source_type,
            provider: item.provider,
            rationale: item.rationale ? item.rationale.split('; ').filter(Boolean) : [],
          })),
          run_id: latest.id,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load allocation module.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = useMemo(() => {
    const reduced = evaluation?.details.filter((item) => item.decision === 'REDUCED').length ?? 0;
    const rejected = evaluation?.details.filter((item) => item.decision === 'REJECTED').length ?? 0;
    return { reduced, rejected };
  }, [evaluation]);

  async function handleEvaluate() {
    setBusy(true);
    try {
      setEvaluation(await evaluateAllocation({ scope_type: scope, triggered_from: 'ui_allocation' }));
    } finally {
      setBusy(false);
    }
  }

  async function handleRun() {
    setBusy(true);
    try {
      setEvaluation(await runAllocation({ scope_type: scope, triggered_from: 'ui_allocation' }));
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Portfolio-aware execution prioritization"
        title="Allocation"
        description="Heuristic and auditable capital allocation for paper/demo proposals. This module prioritizes candidates, applies conservative caps, and never executes real-money trades."
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Controls" title="Evaluate or run allocation" description="Run allocation on eligible proposals after policy/safety gates.">
          <div className="button-row">
            <label>
              Scope
              <select value={scope} onChange={(event) => setScope(event.target.value as AllocationScopeType)}>
                <option value="mixed">mixed</option>
                <option value="demo_only">demo_only</option>
                <option value="real_only">real_only</option>
              </select>
            </label>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleEvaluate()}>Evaluate allocation</button>
            <button type="button" className="primary-button" disabled={busy} onClick={() => void handleRun()}>Run allocation</button>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Summary" title="Allocation summary" description="Portfolio-aware result for the latest evaluation.">
          <p>Candidates: {evaluation?.proposals_considered ?? 0} · Selected: {evaluation?.proposals_selected ?? 0} · Reduced: {stats.reduced} · Rejected: {stats.rejected}</p>
          <p>Allocated total: {evaluation?.allocated_total ?? '0.00'} · Remaining cash: {evaluation?.remaining_cash ?? '0.00'}</p>
          <p>{evaluation?.summary ?? 'Generate proposals or run real-market evaluation first.'}</p>
        </SectionCard>

        <SectionCard eyebrow="Ranked proposals" title="Allocation decisions" description="Rank and decision rationale for each candidate.">
          {!evaluation || evaluation.details.length === 0 ? (
            <EmptyState title="No eligible proposals available for allocation." description="Generate proposals or run real-market evaluation first." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr><th>Rank</th><th>Market</th><th>Direction</th><th>Score</th><th>Confidence</th><th>Suggested qty</th><th>Final qty</th><th>Decision</th><th>Provider/source</th><th>Rationale</th></tr>
                </thead>
                <tbody>
                  {evaluation.details.map((item) => (
                    <tr key={`${item.proposal_id}-${item.rank}`}>
                      <td>{item.rank}</td>
                      <td>{item.market}</td>
                      <td>{item.direction}</td>
                      <td>{item.proposal_score}</td>
                      <td>{item.confidence}</td>
                      <td>{item.suggested_quantity}</td>
                      <td>{item.final_allocated_quantity}</td>
                      <td><StatusBadge tone={decisionTone(item.decision)}>{item.decision}</StatusBadge></td>
                      <td>{item.provider} / {item.source_type}</td>
                      <td>{item.rationale.join(', ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="History" title="Recent allocation runs" description="Persisted audit trail for allocation runs.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr><th>ID</th><th>Status</th><th>Scope</th><th>Started</th><th>Finished</th><th>Allocated</th><th>Selected</th><th>Rejected</th></tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td>{run.id}</td>
                    <td><StatusBadge tone={run.status === 'SUCCESS' ? 'ready' : run.status === 'FAILED' ? 'offline' : 'pending'}>{run.status}</StatusBadge></td>
                    <td>{run.scope_type}</td>
                    <td>{run.started_at}</td>
                    <td>{run.finished_at ?? '—'}</td>
                    <td>{run.allocated_total}</td>
                    <td>{run.proposals_selected}</td>
                    <td>{run.proposals_rejected}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
