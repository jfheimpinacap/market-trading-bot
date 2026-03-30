import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { navigate } from '../../lib/router';
import {
  getPromotionCases,
  getPromotionEvidencePacks,
  getPromotionRecommendations,
  getPromotionSummary,
  runPromotionReview,
} from '../../services/promotionReview';
import type {
  GovernedPromotionSummary,
  PromotionCase,
  PromotionCaseStatus,
  PromotionDecisionRecommendation,
  PromotionEvidencePack,
} from '../../types/promotion';

const statusBadgeClass = (status: string) => {
  if (status === 'APPROVED_FOR_MANUAL_ADOPTION' || status === 'READY_FOR_REVIEW' || status === 'STRONG' || status === 'APPROVE_FOR_MANUAL_ADOPTION') {
    return 'signal-badge signal-badge--actionable';
  }
  if (status === 'NEEDS_MORE_DATA' || status === 'INSUFFICIENT' || status === 'DEFER_FOR_MORE_EVIDENCE') {
    return 'signal-badge signal-badge--neutral';
  }
  if (status === 'DEFERRED' || status === 'MIXED' || status === 'SPLIT_SCOPE_AND_RETEST' || status === 'GROUP_WITH_RELATED_CHANGES') {
    return 'signal-badge signal-badge--monitor';
  }
  if (status === 'REJECTED' || status === 'WEAK' || status === 'REJECT_CHANGE') {
    return 'signal-badge signal-badge--bearish';
  }
  return 'signal-badge signal-badge--neutral';
};

export function PromotionPage() {
  const [summary, setSummary] = useState<GovernedPromotionSummary | null>(null);
  const [cases, setCases] = useState<PromotionCase[]>([]);
  const [evidencePacks, setEvidencePacks] = useState<PromotionEvidencePack[]>([]);
  const [recommendations, setRecommendations] = useState<PromotionDecisionRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [componentFilter, setComponentFilter] = useState<string>('ALL');
  const [scopeFilter, setScopeFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query: Record<string, string> = {};
      if (statusFilter !== 'ALL') query.case_status = statusFilter;
      if (componentFilter !== 'ALL') query.target_component = componentFilter;
      if (scopeFilter !== 'ALL') query.target_scope = scopeFilter;
      if (priorityFilter !== 'ALL') query.priority_level = priorityFilter;
      const [summaryRes, casesRes, evidenceRes, recommendationRes] = await Promise.all([
        getPromotionSummary(),
        getPromotionCases(query),
        getPromotionEvidencePacks(),
        getPromotionRecommendations(),
      ]);
      setSummary(summaryRes);
      setCases(casesRes);
      setEvidencePacks(evidenceRes);
      setRecommendations(recommendationRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load promotion governance board state.');
    } finally {
      setLoading(false);
    }
  }, [componentFilter, priorityFilter, scopeFilter, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const onRun = useCallback(async () => {
    setRunning(true);
    setMessage(null);
    setError(null);
    try {
      const run = await runPromotionReview({ actor: 'promotion_ui', metadata: { initiated_from: 'promotion_ui' } });
      setMessage(`Promotion governance review #${run.id} completed.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run governed promotion review.');
    } finally {
      setRunning(false);
    }
  }, [load]);

  const evidenceByCase = useMemo(() => {
    const rows = new Map<number, PromotionEvidencePack>();
    evidencePacks.forEach((item) => {
      if (!rows.has(item.linked_promotion_case)) rows.set(item.linked_promotion_case, item);
    });
    return rows;
  }, [evidencePacks]);

  const statusOptions: PromotionCaseStatus[] = ['READY_FOR_REVIEW', 'NEEDS_MORE_DATA', 'DEFERRED', 'REJECTED', 'APPROVED_FOR_MANUAL_ADOPTION'];

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Promotion governance board"
        title="/promotion"
        description="Manual-first, local-first and paper-only adoption governance. This board prepares auditable promotion cases from validated experiment evidence. It never auto-promotes or auto-applies changes."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/experiments')}>Open Experiments</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Open Cockpit</button><button className="secondary-button" type="button" onClick={() => navigate('/tuning')}>Open Tuning</button><button className="secondary-button" type="button" onClick={() => navigate('/trace')}>Open Trace</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Adoption readiness overview" description="Cases reviewed and governance outcomes from the latest promotion review run.">
          <div className="dashboard-stat-grid">
            <article className="dashboard-stat-card"><span>Cases reviewed</span><strong>{summary?.cases_reviewed ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Ready for review</span><strong>{summary?.ready_for_review ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Needs more data</span><strong>{summary?.needs_more_data ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Deferred</span><strong>{summary?.deferred ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Rejected</span><strong>{summary?.rejected ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>High priority</span><strong>{summary?.high_priority ?? 0}</strong></article>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Actions" title="Run promotion review" description="Manual trigger for auditable promotion governance run. No automatic adoption is performed.">
          <div className="button-row">
            <button className="primary-button" type="button" disabled={running} onClick={() => void onRun()}>{running ? 'Running…' : 'Run promotion review'}</button>
            <label className="field-group"><span>Component</span><input className="text-input" value={componentFilter} onChange={(event) => setComponentFilter(event.target.value)} placeholder="ALL / prediction / risk / calibration" /></label>
            <label className="field-group"><span>Scope</span><input className="text-input" value={scopeFilter} onChange={(event) => setScopeFilter(event.target.value)} placeholder="ALL / global / provider / category" /></label>
            <label className="field-group"><span>Status</span><select className="select-input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="ALL">ALL</option>{statusOptions.map((status) => <option key={status} value={status}>{status}</option>)}</select></label>
            <label className="field-group"><span>Priority</span><select className="select-input" value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}><option value="ALL">ALL</option><option value="LOW">LOW</option><option value="MEDIUM">MEDIUM</option><option value="HIGH">HIGH</option><option value="CRITICAL">CRITICAL</option></select></label>
            {message ? <span className="muted-text">{message}</span> : null}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Cases" title="Promotion cases" description="Formal adoption cases generated from experiment_lab comparisons and promotion recommendations.">
          {!cases.length ? (
            <EmptyState
              eyebrow="Promotion governance"
              title="No governed promotion cases are available yet"
              description="No governed promotion cases are available yet. Run promotion review to prepare manual adoption decisions."
            />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Component</th><th>Scope</th><th>Change type</th><th>Current</th><th>Proposed</th><th>Priority</th><th>Status</th><th>Blockers</th><th>Context</th></tr></thead>
                <tbody>
                  {cases.map((item) => (
                    <tr key={item.id}>
                      <td>{item.target_component}</td>
                      <td>{item.target_scope}</td>
                      <td>{item.change_type}</td>
                      <td>{item.current_value || 'n/a'}</td>
                      <td>{item.proposed_value || 'n/a'}</td>
                      <td>{item.priority_level}</td>
                      <td><span className={statusBadgeClass(item.case_status)}>{item.case_status}</span></td>
                      <td>{item.blockers.join(', ') || 'None'}</td>
                      <td>
                        <div className="stacked-meta">
                          <span>Experiment #{item.metadata.experiment_run_id ? String(item.metadata.experiment_run_id) : 'n/a'}</span>
                          <span><button type="button" className="link-button" onClick={() => navigate('/experiments')}>Experiments</button> · <button type="button" className="link-button" onClick={() => navigate('/tuning')}>Tuning</button> · <button type="button" className="link-button" onClick={() => navigate('/evaluation')}>Evaluation</button> · <button type="button" className="link-button" onClick={() => navigate('/trace')}>Trace</button></span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Evidence" title="Evidence packs" description="Quantitative and rationale-focused pack for each case. NEEDS_MORE_DATA and DEFERRED are valid governance states.">
          {!evidencePacks.length ? <p className="muted-text">No evidence packs generated yet.</p> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Case</th><th>Summary</th><th>Sample</th><th>Confidence</th><th>Risk of adoption</th><th>Expected benefit</th><th>Status</th></tr></thead>
                <tbody>
                  {evidencePacks.map((item) => (
                    <tr key={item.id}>
                      <td>#{item.linked_promotion_case}</td>
                      <td>{item.summary}</td>
                      <td>{item.sample_count}</td>
                      <td>{item.confidence_score}</td>
                      <td>{item.risk_of_adoption_score}</td>
                      <td>{item.expected_benefit_score}</td>
                      <td><span className={statusBadgeClass(item.evidence_status)}>{item.evidence_status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Committee-facing recommendations" description="Explicit human recommendation outputs for manual adoption committee review.">
          {!recommendations.length ? <p className="muted-text">No recommendations yet.</p> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Recommendation</th><th>Case</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead>
                <tbody>
                  {recommendations.map((item) => (
                    <tr key={item.id}>
                      <td><span className={statusBadgeClass(item.recommendation_type)}>{item.recommendation_type}</span></td>
                      <td>{item.target_case ? `#${item.target_case}` : 'Run-level'}</td>
                      <td>{item.rationale}</td>
                      <td>{item.reason_codes.join(', ') || 'None'}</td>
                      <td>{item.confidence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        {!cases.length && !loading ? (
          <p className="muted-text">No governed promotion cases are available yet. Run promotion review to prepare manual adoption decisions.</p>
        ) : null}

        <p className="muted-text">Manual-first safety rule: this board does not auto-promote challengers, does not auto-apply tuning changes and does not touch live money execution.</p>
      </DataStateWrapper>
    </div>
  );
}
