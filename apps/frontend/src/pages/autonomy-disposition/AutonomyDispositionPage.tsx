import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  applyAutonomyDisposition,
  getAutonomyDispositionCandidates,
  getAutonomyDispositionRecommendations,
  getAutonomyDispositions,
  getAutonomyDispositionSummary,
  requestAutonomyDispositionApproval,
  runAutonomyDispositionReview,
} from '../../services/autonomyDisposition';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY_TO_CLOSE', 'READY_TO_RETIRE', 'CLOSED', 'COMPLETED_RECORDED', 'READY', 'RECORD_COMPLETION'].includes(v)) return 'ready';
  if (['REQUIRE_MORE_REVIEW', 'KEEP_OPEN', 'PENDING_REVIEW', 'APPROVAL_REQUIRED', 'KEEP_CAMPAIGN_OPEN', 'KEPT_OPEN'].includes(v)) return 'pending';
  if (['READY_TO_ABORT', 'ABORTED', 'RETIRED', 'BLOCKED', 'REJECTED', 'EXPIRED', 'ABORT_CAMPAIGN', 'RETIRE_CAMPAIGN'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyDispositionPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyDispositionCandidates>>>([]);
  const [dispositions, setDispositions] = useState<Awaited<ReturnType<typeof getAutonomyDispositions>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyDispositionRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyDispositionSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, dispositionData, recommendationData, summaryData] = await Promise.all([
        getAutonomyDispositionCandidates(),
        getAutonomyDispositions(),
        getAutonomyDispositionRecommendations(),
        getAutonomyDispositionSummary(),
      ]);
      setCandidates(candidateData.slice(0, 100));
      setDispositions(dispositionData.slice(0, 100));
      setRecommendations(recommendationData.slice(0, 100));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy disposition board.');
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
      const result = await runAutonomyDispositionReview({ actor: 'operator-ui' });
      setMessage(`Disposition run #${result.run} created ${result.disposition_count} dispositions and ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run disposition review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const requestApproval = useCallback(async (campaignId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await requestAutonomyDispositionApproval(campaignId, { actor: 'operator-ui' });
      setMessage(`Disposition approval requested: #${response.approval_request_id}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not request disposition approval.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const apply = useCallback(async (campaignId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await applyAutonomyDisposition(campaignId, { actor: 'operator-ui' });
      setMessage(`Disposition #${response.disposition_id} applied. Campaign status: ${response.campaign_status}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not apply disposition.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy disposition board"
        title="/autonomy-disposition"
        description="Campaign closure committee for final lifecycle disposition. Manual-first governance only: explicit rationale, blockers, approval gating, and auditable apply with no opaque auto-close/auto-abort."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run disposition review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-recovery')}>Recovery</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-interventions')}>Interventions</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Campaigns</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Disposition summary" title="Final campaign lifecycle posture" description="KEEP_OPEN and APPLIED are expected, valid states in a manual-first governance loop.">
          <div className="cockpit-metric-grid">
            <div><strong>Disposition candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready to close</strong><div>{summary?.ready_to_close_count ?? 0}</div></div>
            <div><strong>Ready to abort</strong><div>{summary?.ready_to_abort_count ?? 0}</div></div>
            <div><strong>Ready to retire</strong><div>{summary?.ready_to_retire_count ?? 0}</div></div>
            <div><strong>Require more review</strong><div>{summary?.require_more_review_count ?? 0}</div></div>
            <div><strong>Approval required</strong><div>{summary?.approval_required_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {candidates.length === 0 ? <EmptyState eyebrow="Disposition candidates" title="No autonomy campaigns currently require final disposition review." description="Run disposition review after recovery/intervention updates or campaign completion events." /> : null}

        <SectionCard eyebrow="Candidates" title="Campaign disposition candidates" description="Readiness, blockers, approvals/checkpoints pressure, and recommended disposition outcome.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Readiness</th><th>Blockers</th><th>Gates / pressure</th><th>Recommended</th><th>Links & actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={item.campaign}>
                    <td>{item.campaign_title}<div className="muted-text">status: {item.campaign_status} · recovery: {item.recovery_status ?? 'n/a'} · runtime: {item.last_runtime_status ?? 'n/a'}</div></td>
                    <td><StatusBadge tone={tone(item.disposition_readiness)}>{item.disposition_readiness}</StatusBadge><div className="muted-text">risk: {item.closure_risk_level}</div></td>
                    <td>{item.open_blockers.join(', ') || 'none'}</td>
                    <td>approvals: {item.pending_approvals_count} · checkpoints: {item.unresolved_checkpoints_count} · incidents: {item.unresolved_incident_pressure}</td>
                    <td><StatusBadge tone={tone(item.recommended_disposition)}>{item.recommended_disposition}</StatusBadge></td>
                    <td>
                      <div className="button-row">
                        <button type="button" className="link-button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button>
                        <button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button>
                        <button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button>
                        <button type="button" className="secondary-button" disabled={busy} onClick={() => void requestApproval(item.campaign)}>Request approval</button>
                        <button type="button" className="ghost-button" disabled={busy} onClick={() => void apply(item.campaign)}>Apply disposition</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Recommendations" title="Disposition recommendations" description="Explicit recommendation list with rationale, blockers, confidence, and impacted domains.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run disposition review.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Cross-campaign ordering')}</h3><p>{item.rationale}</p><p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'none'} · Blockers: {item.blockers.join(', ') || 'none'} · Domains: {item.impacted_domains.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>

          <SectionCard eyebrow="History" title="Disposition history" description="Auditable final disposition records with before/after campaign state and apply metadata.">
            {!dispositions.length ? <p className="muted-text">No dispositions recorded yet.</p> : <div className="page-stack">{dispositions.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.disposition_status)}>{item.disposition_status}</StatusBadge> <StatusBadge tone={tone(item.disposition_type)}>{item.disposition_type}</StatusBadge></p><h3>{item.campaign_title ?? `Campaign #${item.campaign}`}</h3><p>{item.rationale}</p><p className="muted-text">Before: {item.campaign_state_before || 'n/a'} · After: {item.campaign_state_after || 'n/a'} · Applied by: {item.applied_by || 'pending'} · Applied at: {item.applied_at ? new Date(item.applied_at).toLocaleString() : 'pending'}.</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
