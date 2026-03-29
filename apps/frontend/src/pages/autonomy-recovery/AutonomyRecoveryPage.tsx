import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getAutonomyRecoveryCandidates,
  getAutonomyRecoveryRecommendations,
  getAutonomyRecoverySnapshots,
  getAutonomyRecoverySummary,
  requestCloseApproval,
  requestResumeApproval,
  runAutonomyRecoveryReview,
} from '../../services/autonomyRecovery';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY_TO_RESUME', 'READY', 'RESUME_CAMPAIGN'].includes(v)) return 'ready';
  if (['RECOVERY_IN_PROGRESS', 'KEEP_PAUSED', 'CAUTION', 'REQUIRE_MORE_RECOVERY', 'ESCALATE_TO_APPROVAL', 'REORDER_RECOVERY_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'REVIEW_ABORT', 'CLOSE_CANDIDATE', 'NOT_READY', 'REVIEW_FOR_ABORT', 'CLOSE_CAMPAIGN'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyRecoveryPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyRecoveryCandidates>>>([]);
  const [snapshots, setSnapshots] = useState<Awaited<ReturnType<typeof getAutonomyRecoverySnapshots>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyRecoveryRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyRecoverySummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, snapshotData, recommendationData, summaryData] = await Promise.all([
        getAutonomyRecoveryCandidates(),
        getAutonomyRecoverySnapshots(),
        getAutonomyRecoveryRecommendations(),
        getAutonomyRecoverySummary(),
      ]);
      setCandidates(candidateData.slice(0, 80));
      setSnapshots(snapshotData.slice(0, 80));
      setRecommendations(recommendationData.slice(0, 80));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy recovery board.');
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
      const result = await runAutonomyRecoveryReview({ actor: 'operator-ui' });
      setMessage(`Recovery run #${result.run} created ${result.snapshot_count} snapshots and ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run recovery review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const onRequestApproval = useCallback(async (campaignId: number, kind: 'resume' | 'close') => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = kind === 'resume'
        ? await requestResumeApproval(campaignId, { actor: 'operator-ui' })
        : await requestCloseApproval(campaignId, { actor: 'operator-ui' });
      setMessage(`${kind === 'resume' ? 'Resume' : 'Close'} approval requested: #${result.approval_request_id}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not request approval.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy recovery board"
        title="/autonomy-recovery"
        description="Paused/blocked campaign resolution governance with explicit blockers and safe-resume recommendations. Manual-first only: no opaque auto-resume/auto-abort and no real-money execution."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run recovery review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-interventions')}>Interventions</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-operations')}>Operations</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Program</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button></div>}
      />
      {message ? <p className="success-text">{message}</p> : null}
      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Recovery summary" title="Paused campaign resolution posture" description="READY_TO_RESUME and KEEP_PAUSED are valid outcomes. Recommendations remain advisory and auditable.">
          <div className="cockpit-metric-grid">
            <div><strong>Recovery candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready to resume</strong><div>{summary?.ready_to_resume_count ?? 0}</div></div>
            <div><strong>Keep paused</strong><div>{summary?.keep_paused_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Review abort</strong><div>{summary?.review_abort_count ?? 0}</div></div>
            <div><strong>Close candidate</strong><div>{summary?.close_candidate_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {candidates.length === 0 ? <EmptyState eyebrow="Recovery candidates" title="No paused or blocked autonomy campaigns currently require recovery review." description="Run recovery review after interventions or operations pressure changes to refresh recovery posture." /> : null}

        <SectionCard eyebrow="Recovery snapshots" title="Campaign recovery readiness" description="Candidate state, blockers, pressure, and direct links to campaign/approvals/trace.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Paused since</th><th>Blockers</th><th>Pending gates</th><th>Pressure</th><th>Readiness / status</th><th>Links</th></tr></thead>
              <tbody>
                {snapshots.map((item) => (
                  <tr key={item.id}>
                    <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                    <td>{item.created_at ? new Date(item.created_at).toLocaleString() : 'n/a'}<div className="muted-text">paused: {item.paused_duration_seconds ?? 0}s</div></td>
                    <td>{item.blocker_count} · {Object.entries(item.blocker_types ?? {}).map(([k, v]) => `${k}:${v}`).join(', ') || 'none'}</td>
                    <td>approvals: {item.approvals_pending ? 'yes' : 'no'} · checkpoints: {item.checkpoints_pending ? 'yes' : 'no'}</td>
                    <td>incident level: {item.incident_pressure_level} · score: {item.recovery_score} · priority: {item.recovery_priority}</td>
                    <td><StatusBadge tone={tone(item.resume_readiness)}>{item.resume_readiness}</StatusBadge> <StatusBadge tone={tone(item.recovery_status)}>{item.recovery_status}</StatusBadge><div className="muted-text">{item.rationale}</div></td>
                    <td><button type="button" className="link-button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button><button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button><button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Recommendations" title="Recovery disposition recommendations" description="Explicit RESUME/KEEP_PAUSED/REQUIRE_MORE_RECOVERY/REVIEW_FOR_ABORT/CLOSE recommendations with rationale.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run recovery review.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Cross-campaign ordering')}</h3><p>{item.rationale}</p><p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'none'} · Blockers: {item.blockers.join(', ') || 'none'} · Domains: {item.impacted_domains.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>

          <SectionCard eyebrow="Manual actions" title="Approval requests" description="Optional manual-first actions to gate sensitive resume/close dispositions through approval center.">
            {!candidates.length ? <p className="muted-text">No recovery candidates.</p> : <div className="page-stack">{candidates.slice(0, 10).map((item) => (<article key={item.campaign} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recovery_status)}>{item.recovery_status}</StatusBadge></p><h3>{item.campaign_title ?? `Campaign #${item.campaign}`}</h3><p className="muted-text">Open blockers: {item.open_blockers.join(', ') || 'none'} · approvals: {item.pending_approvals_count} · checkpoints: {item.pending_checkpoints_count}</p><div className="button-row"><button className="secondary-button" type="button" disabled={busy} onClick={() => void onRequestApproval(item.campaign, 'resume')}>Request resume approval</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void onRequestApproval(item.campaign, 'close')}>Request close approval</button></div></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
