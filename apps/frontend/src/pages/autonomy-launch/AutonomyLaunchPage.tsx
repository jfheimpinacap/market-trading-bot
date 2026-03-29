import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  authorizeAutonomyLaunch,
  getAutonomyLaunchAuthorizations,
  getAutonomyLaunchCandidates,
  getAutonomyLaunchReadiness,
  getAutonomyLaunchRecommendations,
  getAutonomyLaunchSummary,
  holdAutonomyLaunch,
  runAutonomyLaunchPreflight,
} from '../../services/autonomyLaunch';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY_TO_START', 'AUTHORIZED', 'START_NOW', 'OPEN'].includes(v)) return 'ready';
  if (['CAUTION', 'WAITING', 'PENDING_REVIEW', 'HOLD', 'WAIT_FOR_WINDOW', 'REQUIRE_APPROVAL_TO_START'].includes(v)) return 'pending';
  if (['BLOCKED', 'BLOCK_START', 'EXPIRED', 'FROZEN'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyLaunchPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyLaunchCandidates>>>([]);
  const [readiness, setReadiness] = useState<Awaited<ReturnType<typeof getAutonomyLaunchReadiness>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyLaunchRecommendations>>>([]);
  const [authorizations, setAuthorizations] = useState<Awaited<ReturnType<typeof getAutonomyLaunchAuthorizations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyLaunchSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, readinessData, recommendationData, authorizationData, summaryData] = await Promise.all([
        getAutonomyLaunchCandidates(),
        getAutonomyLaunchReadiness(),
        getAutonomyLaunchRecommendations(),
        getAutonomyLaunchAuthorizations(),
        getAutonomyLaunchSummary(),
      ]);
      setCandidates(candidateData);
      setReadiness(readinessData.slice(0, 30));
      setRecommendations(recommendationData.slice(0, 20));
      setAuthorizations(authorizationData.slice(0, 20));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy launch board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runPreflight = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await runAutonomyLaunchPreflight({ actor: 'operator-ui' });
      setMessage(`Preflight run #${response.run.id} evaluated ${response.candidates.length} launch candidates.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run launch preflight.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const doAuthorize = useCallback(async (campaignId: number) => {
    setBusy(true);
    try {
      await authorizeAutonomyLaunch(campaignId, { actor: 'operator-ui' });
      setMessage(`Campaign #${campaignId} authorized for manual start handoff.`);
      await load();
    } finally {
      setBusy(false);
    }
  }, [load]);

  const doHold = useCallback(async (campaignId: number) => {
    setBusy(true);
    try {
      await holdAutonomyLaunch(campaignId, { actor: 'operator-ui', rationale: 'Manual hold from launch board' });
      setMessage(`Campaign #${campaignId} moved to HOLD.`);
      await load();
    } finally {
      setBusy(false);
    }
  }, [load]);

  const readinessByCampaign = useMemo(() => new Map(readiness.map((item) => [item.campaign, item])), [readiness]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy launch control"
        title="/autonomy-launch"
        description="Formal preflight start gate between campaign admission and campaign start. Manual-first and auditable: explicit readiness, blockers, recommendations, and start authorization without opaque mass auto-start."
        actions={<div className="button-row"><button className="primary-button" type="button" onClick={() => void runPreflight()} disabled={busy}>Run preflight</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scheduler')}>Autonomy scheduler</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Autonomy program</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Autonomy campaigns</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}
      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Posture + readiness" title="Launch start gate summary" description="WAITING and HOLD are valid conservative states, not failures.">
          <div className="cockpit-metric-grid">
            <div><strong>Program posture</strong><div>{summary?.program_posture ? <StatusBadge tone={tone(summary.program_posture)}>{summary.program_posture}</StatusBadge> : 'n/a'}</div></div>
            <div><strong>Candidate campaigns</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Start-ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Approval-required</strong><div>{summary?.approval_required_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Waiting</strong><div>{summary?.waiting_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {candidates.length === 0 ? <EmptyState eyebrow="Launch candidates" title="No admitted autonomy campaigns are awaiting launch authorization right now." description="Admit campaigns from autonomy scheduler first, then run launch preflight." /> : null}

        <SectionCard eyebrow="Candidate readiness" title="Campaign launch readiness panel" description="Preflight blockers are explicit and auditable before manual authorization.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Admission</th><th>Readiness</th><th>Window</th><th>Pending approvals/checkpoints</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => {
                  const snap = readinessByCampaign.get(item.campaign);
                  return (
                    <tr key={item.id}>
                      <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                      <td><StatusBadge tone={tone(item.status)}>{item.status}</StatusBadge></td>
                      <td>{snap ? <StatusBadge tone={tone(snap.readiness_status)}>{snap.readiness_status}</StatusBadge> : 'not evaluated'}</td>
                      <td>{snap?.active_window_status ?? 'n/a'}</td>
                      <td>{snap ? `${snap.unresolved_approvals_count} approvals · ${snap.unresolved_checkpoints_count} checkpoints` : 'n/a'}</td>
                      <td>{snap?.blockers.join(', ') || 'none'}</td>
                      <td><button type="button" className="link-button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button><button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button><button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></td>
                      <td><button type="button" className="link-button" disabled={busy} onClick={() => void doAuthorize(item.campaign)}>Authorize</button><button type="button" className="link-button" disabled={busy} onClick={() => void doHold(item.campaign)}>Hold</button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Recommendations" title="START / HOLD / WAIT / BLOCK guidance" description="Recommendations stay explicit and explainable; campaign start remains manual.">
            {!recommendations.length ? <p className="muted-text">No launch recommendations yet. Run preflight.</p> : (
              <div className="page-stack">
                {recommendations.map((item) => (
                  <article key={item.id} className="status-card">
                    <p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p>
                    <h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Launch board')}</h3>
                    <p>{item.rationale}</p>
                    <p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'none'} · Blockers: {item.blockers.join(', ') || 'none'} · Domains: {item.impacted_domains.join(', ') || 'none'} · Confidence: {item.confidence}</p>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Authorizations" title="Recent start authorization decisions" description="Formal authorization state does not replace autonomy_campaign.start; it gates start decisioning.">
            {!authorizations.length ? <p className="muted-text">No launch authorizations yet.</p> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Campaign</th><th>Status</th><th>Type</th><th>Approval linkage</th><th>Expiry</th><th>Rationale</th></tr></thead>
                  <tbody>
                    {authorizations.map((row) => (
                      <tr key={row.id}>
                        <td>{row.campaign_title ?? `#${row.campaign}`}</td>
                        <td><StatusBadge tone={tone(row.authorization_status)}>{row.authorization_status}</StatusBadge></td>
                        <td>{row.authorization_type}</td>
                        <td>{row.approved_request ?? 'none'}</td>
                        <td>{row.expires_at ? new Date(row.expires_at).toLocaleString() : 'n/a'}</td>
                        <td>{row.rationale}</td>
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
