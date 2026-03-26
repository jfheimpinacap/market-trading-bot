import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getTradeReviews } from '../services/reviews';
import {
  getPostmortemBoardConclusions,
  getPostmortemBoardReviews,
  getPostmortemBoardRuns,
  getPostmortemBoardSummary,
  runPostmortemBoard,
} from '../services/postmortemBoard';
import type { PostmortemAgentReview, PostmortemBoardConclusion, PostmortemBoardRun, PostmortemBoardSummary } from '../types/postmortemBoard';
import type { TradeReview } from '../types/reviews';

function fmtDate(value?: string | null) {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(d);
}

function statusTone(status: string) {
  if (status === 'SUCCESS') return 'ready';
  if (status === 'PARTIAL' || status === 'RUNNING') return 'pending';
  if (status === 'FAILED') return 'offline';
  return 'neutral';
}

function confidenceTone(value: string) {
  return Number(value) >= 0.65 ? 'ready' : 'pending';
}

export function PostmortemBoardPage() {
  const [summary, setSummary] = useState<PostmortemBoardSummary | null>(null);
  const [runs, setRuns] = useState<PostmortemBoardRun[]>([]);
  const [reviews, setReviews] = useState<PostmortemAgentReview[]>([]);
  const [conclusions, setConclusions] = useState<PostmortemBoardConclusion[]>([]);
  const [tradeReviews, setTradeReviews] = useState<TradeReview[]>([]);
  const [selectedReviewId, setSelectedReviewId] = useState<number | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, runsRes, tradeReviewsRes] = await Promise.all([
        getPostmortemBoardSummary(),
        getPostmortemBoardRuns(),
        getTradeReviews({ ordering: '-reviewed_at' }),
      ]);
      setSummary(summaryRes);
      setRuns(runsRes);
      setTradeReviews(tradeReviewsRes.slice(0, 30));
      const runId = selectedRunId ?? runsRes[0]?.id ?? null;
      setSelectedRunId(runId);
      if (runId) {
        const [reviewsRes, conclusionsRes] = await Promise.all([
          getPostmortemBoardReviews(runId),
          getPostmortemBoardConclusions(runId),
        ]);
        setReviews(reviewsRes);
        setConclusions(conclusionsRes);
      } else {
        setReviews([]);
        setConclusions([]);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load postmortem board data.');
    } finally {
      setLoading(false);
    }
  }, [selectedRunId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRunBoard = async () => {
    if (!selectedReviewId) {
      setError('Select a trade review first. Generate trade reviews first if needed.');
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const run = await runPostmortemBoard({ related_trade_review_id: selectedReviewId, force_learning_rebuild: true });
      setSelectedRunId(run.id);
      await load();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'Board run failed.');
    } finally {
      setRunning(false);
    }
  };

  const latestConclusion = conclusions[0] ?? null;
  const perspectiveOrder = useMemo(() => ['narrative', 'prediction', 'risk', 'runtime', 'learning'], []);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Multi-agent review committee"
        title="Postmortem Board"
        description="Structured and auditable board review for problematic/loss trades across narrative, prediction, risk, runtime/safety, and learning synthesis. Paper/demo only, local-first."
        actions={<StatusBadge tone={error ? 'offline' : loading ? 'loading' : 'ready'}>{error ? 'Board unavailable' : loading ? 'Loading board' : 'Board ready'}</StatusBadge>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Board telemetry" description="High-level board run metrics and status breakdown.">
          <div className="system-metadata-grid">
            <div><strong>Total runs:</strong> {summary?.total_runs ?? 0}</div>
            <div><strong>Total perspective reviews:</strong> {summary?.total_reviews ?? 0}</div>
            <div><strong>Total conclusions:</strong> {summary?.total_conclusions ?? 0}</div>
            <div><strong>Avg perspectives per run:</strong> {summary?.average_perspectives ?? '—'}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Run board" title="Execute postmortem board cycle" description="Pick a trade review and run the board. This does not execute real trades or real money operations.">
          {tradeReviews.length === 0 ? (
            <EmptyState eyebrow="No trade reviews" title="Generate trade reviews first" description="Use postmortem review generation before running the board committee." />
          ) : (
            <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <select value={selectedReviewId ?? ''} onChange={(event) => setSelectedReviewId(Number(event.target.value))}>
                <option value="">Select trade review</option>
                {tradeReviews.map((review) => (
                  <option key={review.id} value={review.id}>Review #{review.id} · Trade #{review.trade_id} · {review.outcome}</option>
                ))}
              </select>
              <button type="button" className="secondary-button" disabled={running} onClick={() => void handleRunBoard()}>
                {running ? 'Running board...' : 'Run board review'}
              </button>
              <button type="button" className="secondary-button" onClick={() => navigate('/postmortem')}>Open Postmortem</button>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Postmortem board runs" description="Each run is a traceable board cycle linked to one trade review.">
          {runs.length === 0 ? (
            <EmptyState eyebrow="No runs" title="No board runs yet" description="Run the committee to generate perspective reviews and conclusion records." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Status</th><th>Review</th><th>Perspectives</th><th>Summary</th><th>Created</th></tr></thead>
                <tbody>
                  {runs.slice(0, 20).map((run) => (
                    <tr key={run.id} onClick={() => setSelectedRunId(run.id)} style={{ cursor: 'pointer' }}>
                      <td>{run.id}</td>
                      <td><StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge></td>
                      <td>{run.related_trade_review}</td>
                      <td>{run.perspectives_run_count}</td>
                      <td>{run.summary || '—'}</td>
                      <td>{fmtDate(run.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Perspective reviews" title="Committee outputs" description="Narrative/prediction/risk/runtime/learning reviewer conclusions and action items.">
          {reviews.length === 0 ? (
            <EmptyState eyebrow="No reviews" title="No perspective reviews" description="Select or run a board cycle to inspect per-perspective findings." />
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {perspectiveOrder.map((perspective) => {
                const item = reviews.find((review) => review.perspective_type === perspective);
                if (!item) return null;
                return (
                  <div key={item.id} className="panel" style={{ padding: '1rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <StatusBadge tone="neutral">{item.perspective_type.toUpperCase()}</StatusBadge>
                      <StatusBadge tone={statusTone(item.status)}>{item.status}</StatusBadge>
                      <StatusBadge tone={confidenceTone(item.confidence)}>{Number(item.confidence) >= 0.65 ? 'HIGH_CONFIDENCE' : 'LOW_CONFIDENCE'}</StatusBadge>
                    </div>
                    <p>{item.conclusion}</p>
                    <ul>
                      {item.recommended_actions.map((action) => <li key={action}>{action}</li>)}
                    </ul>
                  </div>
                );
              })}
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Final conclusion" title="Board conclusion" description="Structured failure mode, lesson, adjustments, and learning-memory impact.">
          {!latestConclusion ? (
            <EmptyState eyebrow="No conclusion" title="No board conclusion available" description="Run a board cycle to generate a final structured conclusion." />
          ) : (
            <div className="system-metadata-grid">
              <div><strong>Primary failure mode:</strong> {latestConclusion.primary_failure_mode}</div>
              <div><strong>Severity:</strong> {latestConclusion.severity}</div>
              <div><strong>Learning memory update:</strong> {latestConclusion.should_update_learning_memory ? 'Yes' : 'No'}</div>
              <div><strong>Secondary modes:</strong> {latestConclusion.secondary_failure_modes.join(', ') || '—'}</div>
              <div style={{ gridColumn: '1 / -1' }}><strong>Lesson learned:</strong> {latestConclusion.lesson_learned}</div>
              <div style={{ gridColumn: '1 / -1' }}><strong>Recommended adjustments:</strong> {latestConclusion.recommended_adjustments.join(' | ') || '—'}</div>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
