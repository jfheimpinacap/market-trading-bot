import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { getEvaluationComparison, getEvaluationSummary } from '../../services/evaluation';
import type { EvaluationComparison, EvaluationRun, EvaluationSummary } from '../../types/evaluation';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function formatDate(value: string | null) {
  if (!value) return 'Pending';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function formatPercent(value: string | number | undefined) {
  if (value === undefined) return '0.00%';
  const numericValue = typeof value === 'number' ? value : Number(value);
  return `${(numericValue * 100).toFixed(2)}%`;
}

function formatMoney(value: string | number | undefined) {
  const numericValue = value === undefined ? 0 : typeof value === 'number' ? value : Number(value);
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(numericValue);
}

function statusTone(value: string) {
  if (value === 'READY') return 'ready';
  if (value === 'IN_PROGRESS') return 'pending';
  if (value === 'FAILED') return 'offline';
  return 'neutral';
}

export function EvaluationPage() {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [comparison, setComparison] = useState<EvaluationComparison | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const summaryResponse = await getEvaluationSummary();
      setSummary(summaryResponse);

      if (summaryResponse.recent_runs.length >= 2) {
        const left = summaryResponse.recent_runs[1];
        const right = summaryResponse.recent_runs[0];
        const comparisonResponse = await getEvaluationComparison(left.id, right.id);
        setComparison(comparisonResponse);
      } else {
        setComparison(null);
      }
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load evaluation data.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const latestRun = summary?.latest_run ?? null;
  const latestMetrics = latestRun?.metric_set;

  const guidance = useMemo(() => {
    if (!latestRun?.guidance?.length) return ['Run continuous demo or semi-auto sessions first to build evaluation data.'];
    return latestRun.guidance;
  }, [latestRun]);

  const recentRuns = summary?.recent_runs ?? [];

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Benchmark / evaluation harness"
        title="Evaluation"
        description="Technical benchmark layer for autonomous paper/demo performance. This view is local-first and paper/demo only. No real-money execution."
        actions={<div style={{ display: 'flex', gap: '0.75rem' }}><button type="button" className="secondary-button" onClick={() => navigate('/replay')}>Open Replay</button><button type="button" className="secondary-button" onClick={() => navigate('/experiments')}>Open Experiments</button><button type="button" className="secondary-button" onClick={() => navigate('/continuous-demo')}>Open Continuous Demo</button><button type="button" className="secondary-button" onClick={() => navigate('/learning')}>Open Learning</button></div>}
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!latestRun || !latestMetrics ? (
          <EmptyState
            eyebrow="No evaluation data"
            title="No completed sessions available yet"
            description="Run continuous demo or semi-auto sessions first to build evaluation data."
          />
        ) : (
          <>
            <SectionCard eyebrow="Current performance" title="Snapshot" description="Quick technical snapshot from the latest evaluation run.">
              <div className="system-metadata-grid">
                <div><strong>Status:</strong> <StatusBadge tone={statusTone(latestRun.status)}>{latestRun.status}</StatusBadge></div>
                <div><strong>Auto execution rate:</strong> {formatPercent(latestMetrics.auto_execution_rate)}</div>
                <div><strong>Approval required rate:</strong> {formatPercent(latestMetrics.approval_rate)}</div>
                <div><strong>Block rate:</strong> {formatPercent(latestMetrics.block_rate)}</div>
                <div><strong>Favorable review rate:</strong> {formatPercent(latestMetrics.favorable_review_rate)}</div>
                <div><strong>Ending equity:</strong> {formatMoney(latestMetrics.ending_equity)}</div>
                <div><strong>Equity delta:</strong> {formatMoney(latestMetrics.equity_delta)}</div>
                <div><strong>Total PnL:</strong> {formatMoney(latestMetrics.total_pnl)}</div>
                <div><strong>Safety events:</strong> {latestMetrics.safety_events_count}</div>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Runs" title="Recent evaluation runs" description="Comparable run snapshots for session-level review.">
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Status</th>
                      <th>Scope</th>
                      <th>Market scope</th>
                      <th>Started</th>
                      <th>Finished</th>
                      <th>Proposals</th>
                      <th>Auto</th>
                      <th>Blocked</th>
                      <th>Favorable / Unfavorable</th>
                      <th>Total PnL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentRuns.map((run: EvaluationRun) => (
                      <tr key={run.id}>
                        <td>{run.id}</td>
                        <td><StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge></td>
                        <td>{run.evaluation_scope}</td>
                        <td>{run.market_scope}</td>
                        <td>{formatDate(run.started_at)}</td>
                        <td>{formatDate(run.finished_at)}</td>
                        <td>{run.metric_set?.proposals_generated ?? 0}</td>
                        <td>{run.metric_set?.auto_executed_count ?? 0}</td>
                        <td>{run.metric_set?.blocked_count ?? 0}</td>
                        <td>{run.metric_set?.favorable_reviews_count ?? 0} / {run.metric_set?.unfavorable_reviews_count ?? 0}</td>
                        <td>{formatMoney(run.metric_set?.total_pnl)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>

            {comparison ? (
              <SectionCard eyebrow="Comparison" title="Latest run delta" description="Simple A/B comparison between the two most recent runs.">
                <ul>
                  <li><strong>PnL delta:</strong> {formatMoney(comparison.delta.total_pnl)}</li>
                  <li><strong>Equity delta:</strong> {formatMoney(comparison.delta.equity_delta)}</li>
                  <li><strong>Auto-execution delta:</strong> {formatPercent(comparison.delta.auto_execution_rate)}</li>
                  <li><strong>Block-rate delta:</strong> {formatPercent(comparison.delta.block_rate)}</li>
                  <li><strong>Favorable review delta:</strong> {formatPercent(comparison.delta.favorable_review_rate)}</li>
                  <li><strong>Safety events delta:</strong> {comparison.delta.safety_events_count}</li>
                </ul>
              </SectionCard>
            ) : null}

            <SectionCard eyebrow="Guidance" title="Operational interpretation" description="Rule-based hints to detect conservative/aggressive drift.">
              <ul>
                {guidance.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </SectionCard>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
