import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  applyAutonomyTransition,
  getAutonomyDomains,
  getAutonomyRecommendations,
  getAutonomyStates,
  getAutonomySummary,
  rollbackAutonomyTransition,
  runAutonomyReview,
} from '../../services/autonomy';
import type { AutonomyDomainStatus, AutonomyRecommendationCode, AutonomyStage, AutonomyTransitionStatus } from '../../types/autonomy';

function stageTone(stage: AutonomyStage): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (stage === 'SUPERVISED_AUTOPILOT') return 'ready';
  if (stage === 'ASSISTED') return 'pending';
  if (stage === 'FROZEN' || stage === 'ROLLBACK_RECOMMENDED') return 'offline';
  return 'neutral';
}

function statusTone(status: AutonomyDomainStatus): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (status === 'ACTIVE') return 'ready';
  if (status === 'OBSERVING') return 'pending';
  if (status === 'DEGRADED' || status === 'BLOCKED') return 'offline';
  return 'neutral';
}

function recommendationTone(code: AutonomyRecommendationCode): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (code === 'PROMOTE_TO_ASSISTED' || code === 'PROMOTE_TO_SUPERVISED_AUTOPILOT') return 'ready';
  if (code === 'REQUIRE_MORE_DATA' || code === 'KEEP_CURRENT_STAGE') return 'pending';
  if (code === 'DOWNGRADE_TO_MANUAL' || code === 'FREEZE_DOMAIN' || code === 'ROLLBACK_STAGE') return 'offline';
  return 'neutral';
}

function transitionTone(status: AutonomyTransitionStatus): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (status === 'APPLIED') return 'ready';
  if (status === 'PENDING_APPROVAL' || status === 'READY_TO_APPLY' || status === 'DRAFT') return 'pending';
  if (status === 'ROLLED_BACK') return 'offline';
  return 'neutral';
}

export function AutonomyPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [domains, setDomains] = useState<Awaited<ReturnType<typeof getAutonomyDomains>>>([]);
  const [states, setStates] = useState<Awaited<ReturnType<typeof getAutonomyStates>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomySummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [domainsPayload, statesPayload, recommendationsPayload, summaryPayload] = await Promise.all([
        getAutonomyDomains(),
        getAutonomyStates(),
        getAutonomyRecommendations(),
        getAutonomySummary(),
      ]);
      setDomains(domainsPayload);
      setStates(statesPayload);
      setRecommendations(recommendationsPayload);
      setSummary(summaryPayload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load autonomy stage manager.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const statesBySlug = useMemo(() => new Map(states.map((state) => [state.domain_slug, state])), [states]);
  const recommendationsToShow = useMemo(() => recommendations.slice(0, 24), [recommendations]);

  const runReview = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runAutonomyReview({ requested_by: 'operator-ui' });
      setMessage(`Autonomy review completed. Generated ${result.recommendations_generated} recommendations and ${result.transitions_generated} transitions.`);
      await load();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'Autonomy review failed.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const applyTransition = useCallback(async (transitionId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await applyAutonomyTransition(transitionId, { applied_by: 'operator-ui' });
      setMessage(`Applied transition #${transitionId}.`);
      await load();
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : 'Could not apply transition.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const rollbackTransition = useCallback(async (transitionId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await rollbackAutonomyTransition(transitionId, { rolled_back_by: 'operator-ui' });
      setMessage(`Rolled back transition #${transitionId}.`);
      await load();
    } catch (rollbackError) {
      setError(rollbackError instanceof Error ? rollbackError.message : 'Could not rollback transition.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Domain-level staged autonomy"
        title="/autonomy"
        description="Autonomy stage manager for manual-first domain envelopes. It groups action-level policy controls into operational domains, emits evidence-backed recommendations, and keeps apply/rollback explicit and auditable."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run autonomy review</button><button className="secondary-button" type="button" onClick={() => navigate('/automation-policy')}>Automation policy</button><button className="secondary-button" type="button" onClick={() => navigate('/trust-calibration')}>Trust calibration</button><button className="secondary-button" type="button" onClick={() => navigate('/policy-rollout')}>Policy rollout</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace evidence</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Posture summary" title="Progressive enablement board" description="Manual-first and paper/sandbox only. Stage changes are recommendation-driven and manually applied.">
          <div className="cockpit-metric-grid">
            <div><strong>Manual domains</strong><div>{summary?.manual_domains ?? 0}</div></div>
            <div><strong>Assisted domains</strong><div>{summary?.assisted_domains ?? 0}</div></div>
            <div><strong>Supervised autopilot</strong><div>{summary?.supervised_autopilot_domains ?? 0}</div></div>
            <div><strong>Frozen domains</strong><div>{summary?.frozen_domains ?? 0}</div></div>
            <div><strong>Degraded/blocked</strong><div>{(summary?.degraded_domains ?? 0) + (summary?.blocked_domains ?? 0)}</div></div>
            <div><strong>Pending stage changes</strong><div>{summary?.pending_stage_changes ?? 0}</div></div>
          </div>
        </SectionCard>

        {recommendations.length === 0 ? (
          <EmptyState
            eyebrow="Autonomy review"
            title="No domain recommendations yet"
            description="Run an autonomy review to evaluate domain-level stages. REQUIRE_MORE_DATA is treated as healthy stabilization, not an error."
          />
        ) : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Domain states" title="Current/effective autonomy posture" description="Domain grouping over automation policy action types; action-level policy remains authoritative.">
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Domain</th><th>Current</th><th>Effective</th><th>Status</th><th>Profiles</th><th>Actions</th></tr></thead>
                <tbody>
                  {domains.map((domain) => {
                    const state = statesBySlug.get(domain.slug);
                    return (
                      <tr key={domain.id}>
                        <td><strong>{domain.slug}</strong><div className="muted-text">{domain.owner_app}</div></td>
                        <td><StatusBadge tone={stageTone(state?.current_stage ?? 'MANUAL')}>{state?.current_stage ?? 'MANUAL'}</StatusBadge></td>
                        <td><StatusBadge tone={stageTone(state?.effective_stage ?? 'MANUAL')}>{state?.effective_stage ?? 'MANUAL'}</StatusBadge></td>
                        <td><StatusBadge tone={statusTone(state?.status ?? 'ACTIVE')}>{state?.status ?? 'ACTIVE'}</StatusBadge></td>
                        <td>{(state?.linked_policy_profiles ?? []).join(', ') || 'n/a'}</td>
                        <td>{domain.action_types.join(', ')}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Promote / keep / downgrade / freeze" description="Each recommendation includes rationale, confidence and evidence references from trust calibration, rollout, incidents and certification posture.">
            {recommendationsToShow.length === 0 ? <p className="muted-text">Run a review to generate recommendations.</p> : (
              <div className="page-stack">
                {recommendationsToShow.map((recommendation) => (
                  <article key={recommendation.id} className="status-card">
                    <p className="status-card__label">{recommendation.domain_slug}</p>
                    <h3>{recommendation.current_stage} → {recommendation.proposed_stage}</h3>
                    <p><StatusBadge tone={recommendationTone(recommendation.recommendation_code)}>{recommendation.recommendation_code}</StatusBadge> <span className="muted-text">Confidence {recommendation.confidence}</span></p>
                    <p>{recommendation.rationale || 'No rationale provided.'}</p>
                    <p className="muted-text">Reason codes: {recommendation.reason_codes.join(', ') || 'n/a'}.</p>
                    <p className="muted-text">Evidence: {recommendation.evidence_refs.map((ref) => String(ref.type ?? 'unknown')).join(', ') || 'n/a'}.</p>
                    <div className="button-row">
                      {recommendation.transition ? (
                        <>
                          <StatusBadge tone={transitionTone(recommendation.transition.status)}>{recommendation.transition.status}</StatusBadge>
                          <button className="secondary-button" type="button" disabled={busy || !['READY_TO_APPLY', 'DRAFT', 'PENDING_APPROVAL'].includes(recommendation.transition.status)} onClick={() => void applyTransition(recommendation.transition!.id)}>Apply transition</button>
                          <button className="ghost-button" type="button" disabled={busy || recommendation.transition.status !== 'APPLIED'} onClick={() => void rollbackTransition(recommendation.transition!.id)}>Rollback</button>
                          <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_transition&root_id=${encodeURIComponent(String(recommendation.transition!.id))}`)}>Trace</button>
                          {recommendation.transition.approval_request ? <button className="link-button" type="button" onClick={() => navigate(`/approvals?request_id=${encodeURIComponent(String(recommendation.transition!.approval_request))}`)}>Approval #{recommendation.transition.approval_request}</button> : null}
                        </>
                      ) : (
                        <p className="muted-text">No transition needed (keep or require more data).</p>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
