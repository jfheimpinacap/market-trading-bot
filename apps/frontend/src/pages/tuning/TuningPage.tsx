import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { getTuningBundles, getTuningHypotheses, getTuningProposals, getTuningRecommendations, getTuningSummary, runTuningReview } from '../../services/tuningBoard';

const toTone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (['READY_FOR_REVIEW', 'HIGH', 'CRITICAL'].includes(value)) return 'ready';
  if (['PROPOSED', 'WATCH', 'MEDIUM'].includes(value)) return 'pending';
  if (['DEFERRED', 'REJECTED', 'EXPIRED', 'LOW'].includes(value)) return 'offline';
  return 'neutral';
};

export function TuningPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getTuningSummary>> | null>(null);
  const [proposals, setProposals] = useState<Awaited<ReturnType<typeof getTuningProposals>>>([]);
  const [hypotheses, setHypotheses] = useState<Awaited<ReturnType<typeof getTuningHypotheses>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getTuningRecommendations>>>([]);
  const [bundles, setBundles] = useState<Awaited<ReturnType<typeof getTuningBundles>>>([]);
  const [componentFilter, setComponentFilter] = useState('');
  const [scopeFilter, setScopeFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, proposalsPayload, hypothesesPayload, recommendationsPayload, bundlesPayload] = await Promise.all([
        getTuningSummary(),
        getTuningProposals({ target_component: componentFilter || undefined, target_scope: scopeFilter || undefined, priority_level: priorityFilter || undefined, proposal_status: statusFilter || undefined }),
        getTuningHypotheses(),
        getTuningRecommendations(),
        getTuningBundles(),
      ]);
      setSummary(summaryPayload);
      setProposals(proposalsPayload);
      setHypotheses(hypothesesPayload);
      setRecommendations(recommendationsPayload);
      setBundles(bundlesPayload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load governed tuning board.');
    } finally {
      setLoading(false);
    }
  }, [componentFilter, scopeFilter, priorityFilter, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const runReview = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await runTuningReview({ metadata: { triggered_from: '/tuning' } });
      await load();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'Tuning review failed.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const proposalById = useMemo(() => new Map(proposals.map((item) => [item.id, item])), [proposals]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Governed quantitative tuning"
        title="/tuning"
        description="Manual-first board that translates evaluation metrics and drift flags into bounded, reviewable tuning proposals. Local-first paper/sandbox only. No opaque auto-tuning or auto-apply."
        actions={<div className="button-row"><button type="button" className="primary-button" disabled={busy} onClick={() => void runReview()}>{busy ? 'Running…' : 'Run tuning review'}</button><button type="button" className="secondary-button" onClick={() => navigate('/evaluation')}>Evaluation</button><button type="button" className="secondary-button" onClick={() => navigate('/prediction')}>Prediction</button><button type="button" className="secondary-button" onClick={() => navigate('/risk-agent')}>Risk agent</button><button type="button" className="ghost-button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Tuning board snapshot" description="Governed tuning conversion from metrics → proposals → manual review readiness.">
          <div className="cockpit-metric-grid">
            <div><strong>Metrics reviewed</strong><div>{summary?.metrics_reviewed ?? 0}</div></div>
            <div><strong>Proposals generated</strong><div>{summary?.proposals_generated ?? 0}</div></div>
            <div><strong>Ready for review</strong><div>{summary?.ready_for_review ?? 0}</div></div>
            <div><strong>Need more data</strong><div>{summary?.need_more_data ?? 0}</div></div>
            <div><strong>Bundled proposals</strong><div>{summary?.bundled_proposals ?? 0}</div></div>
            <div><strong>Critical priority</strong><div>{summary?.critical_priority ?? 0}</div></div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Filters" title="Proposal filters" description="Filter by component, scope, priority and status. REQUIRE_MORE_DATA is a valid watch state.">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(160px, 1fr))', gap: '0.75rem' }}>
            <select value={componentFilter} onChange={(event) => setComponentFilter(event.target.value)}><option value="">All components</option><option value="research">research</option><option value="prediction">prediction</option><option value="risk">risk</option><option value="opportunity_cycle">opportunity_cycle</option><option value="learning">learning</option><option value="calibration">calibration</option></select>
            <select value={scopeFilter} onChange={(event) => setScopeFilter(event.target.value)}><option value="">All scopes</option><option value="global">global</option><option value="provider">provider</option><option value="category">category</option><option value="horizon_band">horizon_band</option><option value="model_mode">model_mode</option></select>
            <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}><option value="">All priorities</option><option value="LOW">LOW</option><option value="MEDIUM">MEDIUM</option><option value="HIGH">HIGH</option><option value="CRITICAL">CRITICAL</option></select>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option><option value="PROPOSED">PROPOSED</option><option value="WATCH">WATCH</option><option value="READY_FOR_REVIEW">READY_FOR_REVIEW</option><option value="DEFERRED">DEFERRED</option><option value="REJECTED">REJECTED</option><option value="EXPIRED">EXPIRED</option></select>
          </div>
        </SectionCard>

        {proposals.length === 0 ? (
          <EmptyState
            eyebrow="No proposals"
            title="No governed tuning proposals are available yet"
            description="No governed tuning proposals are available yet. Run a tuning review to translate evaluation findings into bounded reviewable changes."
          />
        ) : (
          <SectionCard eyebrow="Proposals" title="Governed tuning proposals" description="Bounded threshold/cap/knob suggestions with evidence and explicit manual-first status.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Component</th><th>Scope</th><th>Current</th><th>Proposed</th><th>Evidence</th><th>Priority</th><th>Status</th><th>Rationale</th><th>Links</th></tr></thead><tbody>{proposals.map((item) => <tr key={item.id}><td>{item.proposal_type}</td><td>{item.target_component}</td><td>{item.target_scope}{item.target_value ? `:${item.target_value}` : ''}</td><td>{item.current_value ?? '—'}</td><td>{item.proposed_value ?? '—'}</td><td>{item.evidence_strength_score}</td><td><StatusBadge tone={toTone(item.priority_level)}>{item.priority_level}</StatusBadge></td><td><StatusBadge tone={toTone(item.proposal_status)}>{item.proposal_status}</StatusBadge></td><td>{item.rationale}</td><td><button type="button" className="link-button" onClick={() => navigate('/evaluation')}>Evaluation</button><button type="button" className="link-button" onClick={() => navigate(item.target_component === 'risk' ? '/risk-agent' : '/prediction')}>{item.target_component === 'risk' ? 'Risk' : 'Prediction'}</button><button type="button" className="link-button" onClick={() => navigate('/trace')}>Trace</button></td></tr>)}</tbody></table></div>
          </SectionCard>
        )}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Impact hypotheses" title="Expected quantitative impact" description="Hypothesis cards document expected direction and conservative effect size before any manual apply.">
            {!hypotheses.length ? <p className="muted-text">No hypotheses available yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Proposal</th><th>Type</th><th>Target metric</th><th>Direction</th><th>Effect size</th><th>Rationale</th></tr></thead><tbody>{hypotheses.map((item) => <tr key={item.id}><td>#{item.proposal}</td><td>{item.hypothesis_type}</td><td>{item.target_metric_type}</td><td>{item.expected_direction}</td><td>{item.expected_effect_size ?? '—'}</td><td>{item.rationale}</td></tr>)}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Manual review guidance" description="Recommendation-first outputs, including REQUIRE_MORE_DATA and DEFER states.">
            {!recommendations.length ? <p className="muted-text">No recommendations available yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Proposal</th><th>Confidence</th><th>Reason codes</th><th>Rationale</th></tr></thead><tbody>{recommendations.map((item) => <tr key={item.id}><td><StatusBadge tone={toTone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></td><td>{item.target_proposal ? `#${item.target_proposal}` : '—'}</td><td>{item.confidence}</td><td>{item.reason_codes.join(', ') || '—'}</td><td>{item.rationale}</td></tr>)}</tbody></table></div>}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Bundles (optional)" title="Grouped proposal clusters" description="Scoped groups for coordinated human review when multiple proposals target the same segment.">
          {!bundles.length ? <p className="muted-text">No bundles generated in the latest review.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Label</th><th>Scope</th><th>Status</th><th>Linked proposals</th><th>Rationale</th></tr></thead><tbody>{bundles.map((item) => <tr key={item.id}><td>{item.bundle_label}</td><td>{item.bundle_scope}</td><td><StatusBadge tone={toTone(item.bundle_status)}>{item.bundle_status}</StatusBadge></td><td>{item.linked_proposals.map((id) => proposalById.get(id)?.proposal_type ?? `#${id}`).join(', ')}</td><td>{item.rationale || '—'}</td></tr>)}</tbody></table></div>}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
