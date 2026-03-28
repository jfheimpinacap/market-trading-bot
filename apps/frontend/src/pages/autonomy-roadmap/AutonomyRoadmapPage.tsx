import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getAutonomyRoadmapDependencies,
  getAutonomyRoadmapPlans,
  getAutonomyRoadmapRecommendations,
  getAutonomyRoadmapSummary,
  runAutonomyRoadmapPlan,
} from '../../services/autonomyRoadmap';
import { getAutonomySummary } from '../../services/autonomy';
import { getAutonomyRolloutSummary } from '../../services/autonomyRollout';

import type { RoadmapRecommendationAction } from '../../types/autonomyRoadmap';

const toneForAction = (action: RoadmapRecommendationAction): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (action === 'PROMOTE_DOMAIN' || action === 'SEQUENCE_BEFORE') return 'ready';
  if (action === 'HOLD_DOMAIN' || action === 'REQUIRE_STABILIZATION_FIRST') return 'pending';
  if (action === 'FREEZE_DOMAIN' || action === 'ROLLBACK_DOMAIN' || action === 'DO_NOT_PROMOTE_IN_PARALLEL') return 'offline';
  return 'neutral';
};

export function AutonomyRoadmapPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyRoadmapSummary>> | null>(null);
  const [dependencies, setDependencies] = useState<Awaited<ReturnType<typeof getAutonomyRoadmapDependencies>>>([]);
  const [plans, setPlans] = useState<Awaited<ReturnType<typeof getAutonomyRoadmapPlans>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyRoadmapRecommendations>>>([]);
  const [autonomySummary, setAutonomySummary] = useState<Awaited<ReturnType<typeof getAutonomySummary>> | null>(null);
  const [rolloutSummary, setRolloutSummary] = useState<Awaited<ReturnType<typeof getAutonomyRolloutSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, dependenciesPayload, plansPayload, recommendationsPayload, autonomyPayload, rolloutPayload] = await Promise.all([
        getAutonomyRoadmapSummary(),
        getAutonomyRoadmapDependencies(),
        getAutonomyRoadmapPlans(),
        getAutonomyRoadmapRecommendations(),
        getAutonomySummary(),
        getAutonomyRolloutSummary(),
      ]);
      setSummary(summaryPayload);
      setDependencies(dependenciesPayload);
      setPlans(plansPayload);
      setRecommendations(recommendationsPayload);
      setAutonomySummary(autonomyPayload);
      setRolloutSummary(rolloutPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy roadmap.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runPlan = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const plan = await runAutonomyRoadmapPlan({ requested_by: 'operator-ui' });
      setMessage(`Roadmap plan #${plan.id} generated with ${plan.recommendations.length} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run roadmap plan.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const nextBestMove = useMemo(
    () => recommendations.find((item) => item.action === 'PROMOTE_DOMAIN' && !summary?.latest_blocked_domains.includes(item.domain_slug)),
    [recommendations, summary?.latest_blocked_domains],
  );

  const parallelWarnings = useMemo(() => dependencies.filter((item) => item.dependency_type === 'incompatible_parallel'), [dependencies]);
  const requiresStableWarnings = useMemo(() => dependencies.filter((item) => item.dependency_type === 'requires_stable'), [dependencies]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Global staged autonomy portfolio"
        title="/autonomy-roadmap"
        description="Dependency-aware roadmap board for cross-domain sequencing. Recommendation-first and manual-first: this module does not auto-apply multi-domain promotions."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runPlan()}>Run roadmap review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy')}>Autonomy manager</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-rollout')}>Autonomy rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/approvals')}>Approvals</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Campaign board</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scenarios')}>Scenario lab</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace evidence</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Global posture" title="Cross-domain autonomy progression" description="Manual-first and paper/sandbox only. REQUIRE_STABILIZATION_FIRST is a healthy guardrail outcome.">
          <div className="cockpit-metric-grid">
            <div><strong>Manual domains</strong><div>{autonomySummary?.manual_domains ?? 0}</div></div>
            <div><strong>Assisted domains</strong><div>{autonomySummary?.assisted_domains ?? 0}</div></div>
            <div><strong>Supervised domains</strong><div>{autonomySummary?.supervised_autopilot_domains ?? 0}</div></div>
            <div><strong>Frozen/blocked</strong><div>{(summary?.latest_frozen_domains.length ?? 0) + (summary?.latest_blocked_domains.length ?? 0)}</div></div>
            <div><strong>Under observation</strong><div>{rolloutSummary?.observing_runs ?? 0}</div></div>
            <div><strong>Next best move</strong><div>{nextBestMove?.domain_slug ?? 'n/a'}</div></div>
          </div>
        </SectionCard>

        {plans.length === 0 ? (
          <EmptyState
            eyebrow="Roadmap board"
            title="No roadmap plan generated yet"
            description="Run an autonomy roadmap review to coordinate domain progression."
          />
        ) : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Roadmap recommendations" title="Next domain actions" description="Prioritized sequence, blocked domains and confidence-backed rationale.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run a roadmap review first.</p> : (
              <div className="page-stack">
                {recommendations.slice(0, 20).map((item) => (
                  <article key={item.id} className="status-card">
                    <p className="status-card__label">{item.domain_slug}</p>
                    <h3>{item.current_stage} → {item.proposed_stage || item.current_stage}</h3>
                    <p><StatusBadge tone={toneForAction(item.action)}>{item.action}</StatusBadge> <span className="muted-text">Confidence {item.confidence}</span></p>
                    <p>{item.rationale}</p>
                    <p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'n/a'}.</p>
                    <div className="button-row"><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_roadmap_recommendation&root_id=${encodeURIComponent(String(item.id))}`)}>Open trace</button></div>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Dependencies" title="Cross-domain dependency map" description="Formal rules for requires stable first and incompatible parallel warnings.">
            {!dependencies.length ? <p className="muted-text">No dependency rules found.</p> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Source</th><th>Target</th><th>Type</th><th>Criticality</th><th>Rationale</th></tr></thead>
                  <tbody>
                    {dependencies.map((item) => (
                      <tr key={item.id}>
                        <td>{item.source_domain_slug}</td>
                        <td>{item.target_domain_slug}</td>
                        <td><StatusBadge tone={item.dependency_type === 'incompatible_parallel' ? 'offline' : item.dependency_type === 'requires_stable' ? 'pending' : 'neutral'}>{item.dependency_type}</StatusBadge></td>
                        <td>{item.source_criticality} / {item.target_criticality}</td>
                        <td>{item.rationale}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="muted-text">DO_NOT_PROMOTE_IN_PARALLEL warnings: {parallelWarnings.length}. Requires stable first rules: {requiresStableWarnings.length}.</p>
          </SectionCard>
        </div>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Bundles" title="Recommended sequence bundles" description="Optional bundle suggestions; still explicit approval/manual apply.">
            {!(summary?.latest_plan?.bundles.length ?? 0) ? <p className="muted-text">No bundles suggested in latest plan.</p> : (
              <div className="page-stack">
                {summary?.latest_plan?.bundles.map((bundle) => (
                  <article key={bundle.id} className="status-card">
                    <p className="status-card__label">{bundle.name}</p>
                    <h3>{bundle.sequence_order.join(' → ')}</h3>
                    <p><StatusBadge tone={bundle.risk_level === 'HIGH' ? 'offline' : bundle.risk_level === 'MEDIUM' ? 'pending' : 'ready'}>{bundle.risk_level}</StatusBadge> {bundle.requires_approval ? <StatusBadge tone="pending">REQUIRES_APPROVAL</StatusBadge> : null}</p>
                    <p>{bundle.rationale}</p>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Recent plans" title="Roadmap snapshots" description="Auditable list of roadmap planning runs.">
            {!plans.length ? <p className="muted-text">No plans created yet.</p> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>ID</th><th>Created</th><th>Summary</th><th>Blocked</th><th>Recommendations</th></tr></thead>
                  <tbody>
                    {plans.slice(0, 10).map((plan) => (
                      <tr key={plan.id}>
                        <td>{plan.id}</td>
                        <td>{new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(plan.created_at))}</td>
                        <td>{plan.summary}</td>
                        <td>{plan.blocked_domains.length}</td>
                        <td>{plan.recommendations.length}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
