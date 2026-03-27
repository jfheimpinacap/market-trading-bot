import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { navigate } from '../../lib/router';
import { applyPromotionDecision, getCurrentPromotionRecommendation, getPromotionRuns, getPromotionSummary, runPromotionReview } from '../../services/promotion';
import type { PromotionReviewRun, PromotionSummary } from '../../types/promotion';

const recommendationClass = (code: string) => {
  if (code === 'PROMOTE_CHALLENGER') return 'signal-badge signal-badge--actionable';
  if (code === 'KEEP_CURRENT_CHAMPION') return 'signal-badge signal-badge--monitor';
  if (code === 'EXTEND_SHADOW_TEST') return 'signal-badge signal-badge--neutral';
  if (code === 'REVERT_TO_CONSERVATIVE_STACK') return 'signal-badge signal-badge--bearish';
  return 'signal-badge signal-badge--neutral';
};

const asNumber = (v: unknown) => {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return Number(v);
  return 0;
};

export function PromotionPage() {
  const [summary, setSummary] = useState<PromotionSummary | null>(null);
  const [current, setCurrent] = useState<PromotionReviewRun | null>(null);
  const [runs, setRuns] = useState<PromotionReviewRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [applying, setApplying] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [decisionMode, setDecisionMode] = useState<'RECOMMENDATION_ONLY' | 'MANUAL_APPLY'>('RECOMMENDATION_ONLY');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, runsRes, currentRes] = await Promise.all([getPromotionSummary(), getPromotionRuns(), getCurrentPromotionRecommendation()]);
      setSummary(summaryRes);
      setRuns(runsRes);
      setCurrent(currentRes.current_recommendation);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load promotion committee state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onRun = useCallback(async () => {
    setRunning(true);
    setMessage(null);
    try {
      const run = await runPromotionReview({ decision_mode: decisionMode, metadata: { initiated_from: 'promotion_ui' } });
      setMessage(`Promotion review #${run.id} completed with ${run.recommendation_code}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run promotion review.');
    } finally {
      setRunning(false);
    }
  }, [decisionMode, load]);

  const onApply = useCallback(async () => {
    if (!current) return;
    setApplying(true);
    setMessage(null);
    try {
      await applyPromotionDecision(current.id, { actor: 'frontend_operator' });
      setMessage(`Manual apply executed for review #${current.id}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Manual apply failed.');
    } finally {
      setApplying(false);
    }
  }, [current, load]);

  const evidenceCards = useMemo(() => {
    const metrics = current?.evidence_snapshot.execution_aware_metrics ?? {};
    return [
      { label: 'Execution-aware PnL Δ', value: asNumber(metrics.pnl_delta_execution_adjusted ?? 0).toFixed(2) },
      { label: 'Fill rate Δ', value: asNumber(metrics.fill_rate_delta ?? 0).toFixed(4) },
      { label: 'No-fill rate Δ', value: asNumber(metrics.no_fill_rate_delta ?? 0).toFixed(4) },
      { label: 'Execution drag Δ', value: asNumber(metrics.execution_drag_delta ?? 0).toFixed(4) },
      { label: 'Queue pressure Δ', value: asNumber(metrics.queue_pressure_delta ?? 0).toFixed(4) },
      { label: 'Readiness', value: String(current?.evidence_snapshot.readiness_summary?.status ?? 'UNKNOWN'), badge: true },
    ];
  }, [current]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Stack promotion committee"
        title="/promotion"
        description="Formal, auditable stack governance for paper/demo mode. Consolidates champion-challenger, readiness, execution realism, profile governance and precedents before any manual promotion decision."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/champion-challenger')}>Open Champion Challenger</button><button className="secondary-button" type="button" onClick={() => navigate('/profile-manager')}>Open Profile Manager</button><button className="secondary-button" type="button" onClick={() => navigate('/prediction')}>Open Prediction</button><button className="secondary-button" type="button" onClick={() => navigate('/readiness')}>Open Readiness</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Current recommendation" title="Committee recommendation" description="Manual-first governance output. Recommendation only by default; no silent auto-switching.">
          {!current ? <p className="muted-text">Run a promotion review to evaluate the current stack.</p> : (
            <div className="system-metadata-grid">
              <div><strong>Recommendation:</strong> <span className={recommendationClass(current.recommendation_code)}>{current.recommendation_code}</span></div>
              <div><strong>Confidence:</strong> {current.confidence}</div>
              <div><strong>Rationale:</strong> {current.rationale}</div>
              <div><strong>Blocking constraints:</strong> {current.blocking_constraints.join(', ') || 'None'}</div>
              <div><strong>Reason codes:</strong> {current.reason_codes.join(', ') || 'None'}</div>
              <div><strong>Stack candidate:</strong> {current.evidence_snapshot.challenger_binding?.name ?? 'Not specified'}</div>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Evidence summary" title="Consolidated stack evidence" description="Execution-aware deltas, readiness, profile context, portfolio stress and precedent signals.">
          <div className="dashboard-stat-grid">
            {evidenceCards.map((card) => (
              <article key={card.label} className="dashboard-stat-card">
                <span>{card.label}</span>
                <strong>{card.badge ? <span className={recommendationClass(String(card.value))}>{card.value}</span> : card.value}</strong>
              </article>
            ))}
          </div>
          {current?.evidence_snapshot.precedent_warnings?.length ? <p><strong>Precedent warnings:</strong> {current.evidence_snapshot.precedent_warnings.length} relevant memory warnings detected.</p> : <p className="muted-text">No high-similarity caution precedents were surfaced in the latest review.</p>}
        </SectionCard>

        <SectionCard eyebrow="Run review" title="Review + optional manual apply" description="Default mode is recommendation-only; use manual apply explicitly for safe and auditable promotions.">
          <div className="button-row">
            <label className="field-group"><span>Decision mode</span><select className="select-input" value={decisionMode} onChange={(e) => setDecisionMode(e.target.value as 'RECOMMENDATION_ONLY' | 'MANUAL_APPLY')}><option value="RECOMMENDATION_ONLY">RECOMMENDATION_ONLY</option><option value="MANUAL_APPLY">MANUAL_APPLY</option></select></label>
            <button className="primary-button" type="button" disabled={running} onClick={() => void onRun()}>{running ? 'Running review…' : 'Run promotion review'}</button>
            <button className="secondary-button" type="button" disabled={applying || !current || current.decision_mode !== 'MANUAL_APPLY' || current.recommendation_code !== 'PROMOTE_CHALLENGER'} onClick={() => void onApply()}>{applying ? 'Applying…' : 'Manual apply review'}</button>
            {message ? <span className="muted-text">{message}</span> : null}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Promotion review audit trail" description="Status, recommendation and evidence summary for each committee run.">
          {runs.length === 0 ? (
            <EmptyState
              eyebrow="Promotion committee"
              title="No promotion reviews yet"
              description="Run a promotion review to evaluate the current stack. Inconclusive evidence is handled as EXTEND_SHADOW_TEST or MANUAL_REVIEW_REQUIRED, not as an error."
            />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Status</th><th>Recommendation</th><th>Decision mode</th><th>Created</th><th>Summary</th></tr></thead>
                <tbody>
                  {runs.slice(0, 15).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td>{run.status}</td>
                      <td><span className={recommendationClass(run.recommendation_code)}>{run.recommendation_code}</span></td>
                      <td>{run.decision_mode}</td>
                      <td>{new Date(run.created_at).toLocaleString()}</td>
                      <td>{run.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        {summary?.is_recommendation_stale ? <p className="muted-text">Current recommendation is stale; mission control should trigger a fresh promotion review.</p> : null}
      </DataStateWrapper>
    </div>
  );
}
