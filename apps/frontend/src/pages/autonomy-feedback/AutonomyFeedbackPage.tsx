import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  completeAutonomyFeedbackResolution,
  getAutonomyFeedbackCandidates,
  getAutonomyFeedbackRecommendations,
  getAutonomyFeedbackResolutions,
  getAutonomyFeedbackSummary,
  runAutonomyFeedbackReview,
} from '../../services/autonomyFeedback';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['COMPLETED', 'CLOSED', 'MARK_FOLLOWUP_COMPLETED'].includes(v)) return 'ready';
  if (['PENDING', 'IN_PROGRESS', 'UNKNOWN', 'KEEP_PENDING', 'REVIEW_MEMORY_RESOLUTION', 'REVIEW_POSTMORTEM_RESOLUTION', 'REVIEW_ROADMAP_FEEDBACK_STATUS'].includes(v)) return 'pending';
  if (['BLOCKED', 'REJECTED', 'REQUIRE_MANUAL_REVIEW'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyFeedbackPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyFeedbackCandidates>>>([]);
  const [resolutions, setResolutions] = useState<Awaited<ReturnType<typeof getAutonomyFeedbackResolutions>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyFeedbackRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyFeedbackSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, resolutionData, recommendationData, summaryData] = await Promise.all([
        getAutonomyFeedbackCandidates(),
        getAutonomyFeedbackResolutions(),
        getAutonomyFeedbackRecommendations(),
        getAutonomyFeedbackSummary(),
      ]);
      setCandidates(candidateData.slice(0, 250));
      setResolutions(resolutionData.slice(0, 250));
      setRecommendations(recommendationData.slice(0, 250));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy feedback board.');
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
      const result = await runAutonomyFeedbackReview({ actor: 'operator-ui' });
      setMessage(`Feedback run #${result.run} processed ${result.candidate_count} candidates and produced ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run autonomy feedback review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const complete = useCallback(async (followupId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await completeAutonomyFeedbackResolution(followupId, { actor: 'operator-ui' });
      setMessage(`Follow-up #${followupId} moved to ${result.resolution_status}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not complete follow-up resolution.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const unresolvedCount = useMemo(
    () => candidates.filter((candidate) => ['PENDING', 'IN_PROGRESS', 'UNKNOWN', 'BLOCKED', 'REJECTED'].includes(candidate.downstream_status)).length,
    [candidates],
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy feedback board"
        title="/autonomy-feedback"
        description="Manual-first follow-up resolution tracker and campaign knowledge-loop governance. No opaque auto-learning and no automatic roadmap/scenario apply."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run feedback review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-followup')}>Autonomy followup</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Autonomy closeout</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Feedback summary" title="Resolution posture" description="Tracks emitted follow-ups after handoff completion signals; completed and closed are valid final outcomes.">
          <div className="cockpit-metric-grid">
            <div><strong>Emitted followups</strong><div>{summary?.candidate_count ?? candidates.length}</div></div>
            <div><strong>Pending</strong><div>{summary?.pending_count ?? 0}</div></div>
            <div><strong>In progress</strong><div>{summary?.in_progress_count ?? 0}</div></div>
            <div><strong>Completed</strong><div>{summary?.completed_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Closed loop count</strong><div>{summary?.closed_loop_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {candidates.length === 0 ? <EmptyState eyebrow="Feedback tracking" title="No emitted autonomy follow-ups currently require resolution tracking." description="Run autonomy followup emission first and then execute feedback review when handoffs exist." /> : null}

        <SectionCard eyebrow="Candidates" title="Follow-up resolution candidates" description={`Unresolved candidates needing attention: ${unresolvedCount}.`}>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Followup</th><th>Emitted status</th><th>Downstream</th><th>Linked artifact</th><th>Blockers</th><th>Links & actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={item.followup}>
                    <td>{item.campaign_title}</td>
                    <td>{item.followup_type}</td>
                    <td><StatusBadge tone={tone(item.followup_status)}>{item.followup_status}</StatusBadge></td>
                    <td><StatusBadge tone={tone(item.downstream_status)}>{item.downstream_status}</StatusBadge></td>
                    <td>{item.linked_artifact ?? 'none'}</td>
                    <td>{item.blockers.join(', ') || 'none'}</td>
                    <td>
                      <div className="button-row">
                        <button className="link-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button>
                        <button className="link-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Closeout</button>
                        <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_followup&root_id=${encodeURIComponent(String(item.followup))}`)}>Trace</button>
                        <button className="secondary-button" type="button" disabled={busy || !item.ready_for_resolution} onClick={() => void complete(item.followup)}>Complete resolution</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Resolutions" title="Auditable follow-up resolution records" description="Includes pending, in-progress, blocked/rejected, completed and manually closed records.">
            {!resolutions.length ? <p className="muted-text">No follow-up resolutions yet. Run feedback review first.</p> : <div className="page-stack">{resolutions.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.resolution_status)}>{item.resolution_status}</StatusBadge> <StatusBadge tone={tone(item.downstream_status)}>{item.downstream_status}</StatusBadge></p><h3>{item.campaign_title ?? `Campaign #${item.campaign}`}</h3><p>{item.rationale}</p><p className="muted-text">Follow-up #{item.followup} · Type: {item.followup_type ?? 'n/a'} · Resolver: {item.resolved_by || 'pending'}</p></article>))}</div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Manual-first resolution recommendations" description="Review/complete/pending guidance without any opaque learning authority.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run feedback review.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Cross-campaign')}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
