import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getAutonomyInsightCandidates,
  getAutonomyInsightRecommendations,
  getAutonomyInsights,
  getAutonomyInsightSummary,
  markAutonomyInsightReviewed,
  runAutonomyInsightsReview,
} from '../../services/autonomyInsights';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['SUCCESS_PATTERN', 'REGISTER_MEMORY_PRECEDENT', 'PREPARE_ROADMAP_GOVERNANCE_NOTE', 'PREPARE_SCENARIO_CAUTION', 'PREPARE_PROGRAM_POLICY_NOTE', 'COMPLETED', 'CLOSED'].includes(v)) return 'ready';
  if (['PENDING', 'REQUIRE_OPERATOR_REVIEW', 'REORDER_INSIGHT_PRIORITY'].includes(v)) return 'pending';
  if (['FAILURE_PATTERN', 'BLOCKER_PATTERN', 'GOVERNANCE_PATTERN', 'HIGH'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyInsightsPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyInsightCandidates>>>([]);
  const [insights, setInsights] = useState<Awaited<ReturnType<typeof getAutonomyInsights>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyInsightRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyInsightSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, insightData, recommendationData, summaryData] = await Promise.all([
        getAutonomyInsightCandidates(),
        getAutonomyInsights(),
        getAutonomyInsightRecommendations(),
        getAutonomyInsightSummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setInsights(insightData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy insights board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runReview = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runAutonomyInsightsReview({ actor: 'operator-ui' });
      setMessage(`Insight run #${result.run} processed ${result.candidate_count} candidates and produced ${result.insight_count} insights.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run autonomy insights review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const markReviewed = useCallback(async (insightId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await markAutonomyInsightReviewed(insightId, { actor: 'operator-ui' });
      setMessage(`Insight #${insightId} marked as reviewed.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not mark insight reviewed.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const closedCandidates = useMemo(() => candidates.filter((candidate) => candidate.lifecycle_closed), [candidates]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy insights board"
        title="/autonomy-insights"
        description="Cross-campaign lessons registry and governance synthesis. Manual-first recommendation layer only; no opaque auto-learning and no automatic roadmap/scenario/program apply."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run insights review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory')}>Autonomy advisory</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-feedback')}>Autonomy feedback</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Autonomy closeout</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Insights summary" title="Cross-campaign synthesis posture" description="Only campaigns with complete closeout + followup + feedback lifecycle are synthesized.">
          <div className="cockpit-metric-grid">
            <div><strong>Lifecycle closed campaigns</strong><div>{summary?.lifecycle_closed_count ?? closedCandidates.length}</div></div>
            <div><strong>Insights generated</strong><div>{summary?.insight_count ?? insights.length}</div></div>
            <div><strong>Success patterns</strong><div>{summary?.success_pattern_count ?? 0}</div></div>
            <div><strong>Failure patterns</strong><div>{summary?.failure_pattern_count ?? 0}</div></div>
            <div><strong>Governance patterns</strong><div>{summary?.governance_pattern_count ?? 0}</div></div>
            <div><strong>Pending review</strong><div>{summary?.pending_review_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {closedCandidates.length === 0 ? <EmptyState eyebrow="No closed lifecycle campaigns" title="No autonomy campaigns currently have a fully closed lifecycle ready for insight synthesis." description="Complete closeout, emit followups, and resolve followup feedback before running insights review." /> : null}

        <SectionCard eyebrow="Candidates" title="Campaign lifecycle candidates" description="Lifecycle closure and friction profile used as synthesis input.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Lifecycle</th><th>Disposition</th><th>Friction</th><th>Signals</th><th>Links</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={item.campaign}>
                    <td>{item.campaign_title}</td>
                    <td><StatusBadge tone={item.lifecycle_closed ? 'ready' : 'pending'}>{item.lifecycle_closed ? 'CLOSED' : 'OPEN'}</StatusBadge></td>
                    <td>{item.disposition_type}</td>
                    <td><StatusBadge tone={tone(item.approval_friction_level)}>{item.approval_friction_level}</StatusBadge> / <StatusBadge tone={tone(item.incident_pressure_level)}>{item.incident_pressure_level}</StatusBadge> / <StatusBadge tone={tone(item.recovery_complexity_level)}>{item.recovery_complexity_level}</StatusBadge></td>
                    <td>{item.major_success_factors.join(', ') || item.major_failure_modes.join(', ') || 'No findings yet'}</td>
                    <td><button className="link-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button> <button className="link-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Closeout</button> <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Insights" title="Reusable campaign and cross-campaign insights" description="Success/failure/blocker/governance patterns with explicit reason codes and recommendation targets.">
            {!insights.length ? <p className="muted-text">No insights generated yet. Run insights review.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Scope</th><th>Campaign</th><th>Summary</th><th>Target</th><th>Confidence</th><th>Actions</th></tr></thead><tbody>{insights.map((item) => (<tr key={item.id}><td><StatusBadge tone={tone(item.insight_type)}>{item.insight_type}</StatusBadge></td><td>{item.scope}</td><td>{item.campaign_title ?? (item.campaign ? `Campaign #${item.campaign}` : 'Cross-campaign')}</td><td>{item.summary}</td><td>{item.recommendation_target}</td><td>{item.confidence}</td><td><button className="link-button" type="button" onClick={() => navigate(item.campaign ? `/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}` : '/trace')}>Trace</button><button className="secondary-button" type="button" disabled={busy || item.reviewed} onClick={() => void markReviewed(item.id)}>{item.reviewed ? 'Reviewed' : 'Mark reviewed'}</button></td></tr>))}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Governance recommendations (manual apply)" description="Artifacts for memory/roadmap/scenario/program/manager review; never auto-applied.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run insights review.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge> <StatusBadge tone={tone(item.insight_type)}>{item.insight_type}</StatusBadge></p><h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Cross-campaign')}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
