import { useCallback, useEffect, useState } from 'react';

import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { navigate } from '../../lib/router';
import {
  dispatchAutonomyCampaign,
  getAutonomyActivationCandidates,
  getAutonomyActivationRecommendations,
  getAutonomyActivationSummary,
  getAutonomyActivations,
  runAutonomyActivationDispatchReview,
} from '../../services/autonomyActivation';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY_TO_DISPATCH', 'STARTED', 'DISPATCH_NOW'].includes(v)) return 'ready';
  if (['WAITING', 'REVALIDATE_REQUIRED', 'HOLD_DISPATCH', 'WAIT_FOR_WINDOW', 'DISPATCHING'].includes(v)) return 'pending';
  if (['BLOCKED', 'FAILED', 'EXPIRED', 'BLOCK_DISPATCH', 'EXPIRE_AUTHORIZATION'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyActivationPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyActivationCandidates>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyActivationRecommendations>>>([]);
  const [activations, setActivations] = useState<Awaited<ReturnType<typeof getAutonomyActivations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyActivationSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, recommendationData, activationData, summaryData] = await Promise.all([
        getAutonomyActivationCandidates(),
        getAutonomyActivationRecommendations(),
        getAutonomyActivations(),
        getAutonomyActivationSummary(),
      ]);
      setCandidates(candidateData);
      setRecommendations(recommendationData.slice(0, 20));
      setActivations(activationData.slice(0, 25));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy activation board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runReview = useCallback(async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await runAutonomyActivationDispatchReview({ actor: 'operator-ui' });
      setMessage(`Dispatch review #${result.run.id} evaluated ${result.candidates.length} authorized candidates.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run dispatch review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const dispatchCampaign = useCallback(async (campaignId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await dispatchAutonomyCampaign(campaignId, {
        actor: 'operator-ui',
        trigger_source: 'manual_ui',
        rationale: 'Manual dispatch from /autonomy-activation',
      });
      setMessage(`Dispatch attempt recorded: campaign #${campaignId} -> ${result.activation_status}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not dispatch campaign.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy activation gateway"
        title="/autonomy-activation"
        description="Manual-first authorized start handoff: consumes launch authorization, revalidates posture/window/conflicts at dispatch time, and records explicit started/blocked/failed/expired outcomes. No opaque mass auto-start."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run dispatch review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-launch')}>Autonomy launch</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scheduler')}>Autonomy scheduler</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Autonomy program</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Autonomy campaigns</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}
      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Dispatch posture" title="Activation summary" description="BLOCKED, WAITING and EXPIRED are valid safety outcomes, not UI bugs.">
          <div className="cockpit-metric-grid">
            <div><strong>Current program posture</strong><div>{summary?.current_program_posture ? <StatusBadge tone={tone(summary.current_program_posture)}>{summary.current_program_posture}</StatusBadge> : 'n/a'}</div></div>
            <div><strong>Active window</strong><div>{summary?.active_window_name ?? 'n/a'}</div></div>
            <div><strong>Dispatch-ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Expired authorizations</strong><div>{summary?.expired_count ?? 0}</div></div>
            <div><strong>Recent activations</strong><div>{summary?.recent_activations ?? 0}</div></div>
            <div><strong>Started activations</strong><div>{summary?.dispatch_started_count ?? 0}</div></div>
            <div><strong>Failed activations</strong><div>{summary?.failed_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {candidates.length === 0 ? <EmptyState eyebrow="Authorized dispatch candidates" title="No authorized autonomy campaigns are ready for dispatch right now." description="Run dispatch review after launch authorization, or wait for posture/window constraints to clear." /> : null}

        <SectionCard eyebrow="Candidates" title="Authorized campaign dispatch board" description="Each row revalidates launch auth, posture, windows, incidents, and conflict constraints before dispatch.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Auth</th><th>Readiness</th><th>Posture / window</th><th>Risk signals</th><th>Blockers</th><th>Links</th><th>Action</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={item.campaign}>
                    <td>{item.campaign_title}</td>
                    <td><StatusBadge tone={tone(item.authorization_status)}>{item.authorization_status}</StatusBadge><div className="muted-text">{item.expires_at ? new Date(item.expires_at).toLocaleString() : 'n/a'}</div></td>
                    <td><StatusBadge tone={tone(item.dispatch_readiness_status)}>{item.dispatch_readiness_status}</StatusBadge></td>
                    <td>{item.current_program_posture} · {item.active_window_name ?? 'no active window'}</td>
                    <td>{item.domain_conflict ? 'domain conflict' : 'no domain conflict'} · incidents: {item.incident_impact} · degraded: {item.degraded_impact} · rollout pressure: {item.rollout_pressure}</td>
                    <td>{item.blockers.join(', ') || 'none'}</td>
                    <td><button type="button" className="link-button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button><button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button><button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></td>
                    <td><button type="button" className="link-button" disabled={busy || item.dispatch_readiness_status !== 'READY_TO_DISPATCH'} onClick={() => void dispatchCampaign(item.campaign)}>Dispatch</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Recommendations" title="Dispatch recommendations" description="Recommendation-first guidance; final start remains explicit and manual.">
            {!recommendations.length ? <p className="muted-text">No dispatch recommendations yet. Run dispatch review.</p> : (
              <div className="page-stack">
                {recommendations.map((item) => (
                  <article key={item.id} className="status-card">
                    <p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p>
                    <h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Dispatch board')}</h3>
                    <p>{item.rationale}</p>
                    <p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'none'} · Blockers: {item.blockers.join(', ') || 'none'} · Domains: {item.impacted_domains.join(', ') || 'none'} · Confidence: {item.confidence}</p>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Activation history" title="Recent activation outcomes" description="Auditable activation records: started, blocked, failed, expired.">
            {!activations.length ? <p className="muted-text">No activation attempts recorded yet.</p> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Campaign</th><th>Status</th><th>Actor</th><th>Activated at</th><th>Failure</th></tr></thead>
                  <tbody>
                    {activations.map((item) => (
                      <tr key={item.id}>
                        <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                        <td><StatusBadge tone={tone(item.activation_status)}>{item.activation_status}</StatusBadge></td>
                        <td>{item.activated_by || 'n/a'}</td>
                        <td>{item.activated_at ? new Date(item.activated_at).toLocaleString() : 'n/a'}</td>
                        <td>{item.failure_message || '—'}</td>
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
