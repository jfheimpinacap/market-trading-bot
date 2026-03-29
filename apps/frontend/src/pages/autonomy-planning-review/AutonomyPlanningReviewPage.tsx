import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acceptAutonomyPlanningProposal,
  acknowledgeAutonomyPlanningProposal,
  deferAutonomyPlanningProposal,
  getAutonomyPlanningReviewCandidates,
  getAutonomyPlanningReviewRecommendations,
  getAutonomyPlanningReviewResolutions,
  getAutonomyPlanningReviewSummary,
  rejectAutonomyPlanningProposal,
  runAutonomyPlanningReview,
} from '../../services/autonomyPlanningReview';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['ACKNOWLEDGED', 'ACCEPTED', 'CLOSED', 'ACKNOWLEDGE_PROPOSAL', 'MARK_ACCEPTED'].includes(v)) return 'ready';
  if (['PENDING', 'UNKNOWN', 'KEEP_PENDING', 'REORDER_PLANNING_REVIEW_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'REJECTED', 'DEFERRED', 'REQUIRE_MANUAL_REVIEW', 'MARK_REJECTED', 'MARK_DEFERRED'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyPlanningReviewPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyPlanningReviewCandidates>>>([]);
  const [resolutions, setResolutions] = useState<Awaited<ReturnType<typeof getAutonomyPlanningReviewResolutions>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyPlanningReviewRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyPlanningReviewSummary>> | null>(null);

  const resolutionByProposal = useMemo(() => {
    const map = new Map<number, (typeof resolutions)[number]>();
    resolutions.forEach((row) => map.set(row.planning_proposal, row));
    return map;
  }, [resolutions]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, resolutionData, recommendationData, summaryData] = await Promise.all([
        getAutonomyPlanningReviewCandidates(),
        getAutonomyPlanningReviewResolutions(),
        getAutonomyPlanningReviewRecommendations(),
        getAutonomyPlanningReviewSummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setResolutions(resolutionData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy planning review board.');
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
      const result = await runAutonomyPlanningReview({ actor: 'operator-ui' });
      setMessage(`Planning review run #${result.run} processed ${result.candidate_count} proposals and produced ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run planning review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const applyAction = useCallback(async (action: 'ack' | 'accept' | 'defer' | 'reject', proposalId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      if (action === 'ack') await acknowledgeAutonomyPlanningProposal(proposalId, { actor: 'operator-ui' });
      if (action === 'accept') await acceptAutonomyPlanningProposal(proposalId, { actor: 'operator-ui' });
      if (action === 'defer') await deferAutonomyPlanningProposal(proposalId, { actor: 'operator-ui' });
      if (action === 'reject') await rejectAutonomyPlanningProposal(proposalId, { actor: 'operator-ui' });
      setMessage(`Proposal #${proposalId} updated via manual ${action} action.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} planning proposal #${proposalId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy planning review board"
        title="/autonomy-planning-review"
        description="Manual-first proposal resolution tracker for planning proposals already emitted by autonomy intake. Recommendation-first, auditable, and explicitly no opaque auto-apply into roadmap/scenario/program/manager."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run planning review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-intake')}>Autonomy intake</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-backlog')}>Autonomy backlog</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-decision')}>Autonomy decision</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Planning proposal resolution posture" description="Tracks emitted planning proposals and their manual review outcomes so the planning handoff loop remains explicit and auditable.">
          <div className="cockpit-metric-grid">
            <div><strong>Proposals emitted</strong><div>{summary?.planning_proposals_emitted_count ?? 0}</div></div>
            <div><strong>Pending</strong><div>{summary?.pending_count ?? 0}</div></div>
            <div><strong>Acknowledged</strong><div>{summary?.acknowledged_count ?? 0}</div></div>
            <div><strong>Accepted</strong><div>{summary?.accepted_count ?? 0}</div></div>
            <div><strong>Deferred</strong><div>{summary?.deferred_count ?? 0}</div></div>
            <div><strong>Rejected</strong><div>{summary?.rejected_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No planning candidates" title="No emitted planning proposals currently require resolution tracking." description="Run autonomy intake to emit planning proposals, then run planning review." /> : null}

        <SectionCard eyebrow="Candidates" title="Planning proposals and downstream status" description="Candidate list connects proposal, backlog, advisory, insight, and campaign context for manual resolution without mutating roadmap/scenario/program/manager.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Proposal</th><th>Backlog</th><th>Insight</th><th>Campaign</th><th>Target</th><th>Status</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => {
                  const status = resolutionByProposal.get(item.planning_proposal)?.resolution_status ?? item.downstream_status;
                  return (
                    <tr key={item.planning_proposal}>
                      <td>#{item.planning_proposal} <StatusBadge tone={tone(item.proposal_status)}>{item.proposal_status}</StatusBadge></td>
                      <td>{item.backlog_item ? `#${item.backlog_item}` : 'n/a'}</td>
                      <td>{item.insight ? `#${item.insight}` : 'n/a'}</td>
                      <td>{item.campaign_title ?? (item.campaign ? `Campaign #${item.campaign}` : 'Cross-campaign')}</td>
                      <td>{item.target_scope}</td>
                      <td><StatusBadge tone={tone(status)}>{status}</StatusBadge></td>
                      <td>{item.blockers.join(', ') || 'None'}</td>
                      <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=planning_proposal&root_id=${encodeURIComponent(String(item.planning_proposal))}`)}>Proposal</button>{item.backlog_item ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_backlog_item&root_id=${encodeURIComponent(String(item.backlog_item))}`)}>Backlog</button> : null}{item.advisory_artifact ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=advisory_artifact&root_id=${encodeURIComponent(String(item.advisory_artifact))}`)}>Advisory</button> : null}{item.insight ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=campaign_insight&root_id=${encodeURIComponent(String(item.insight))}`)}>Insight</button> : null}{item.campaign ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Campaign</button> : null}</td>
                      <td><div className="button-row"><button className="secondary-button" type="button" disabled={busy} onClick={() => void applyAction('ack', item.planning_proposal)}>Acknowledge</button><button className="secondary-button" type="button" disabled={busy} onClick={() => void applyAction('accept', item.planning_proposal)}>Accept</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void applyAction('defer', item.planning_proposal)}>Defer</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void applyAction('reject', item.planning_proposal)}>Reject</button></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Resolutions" title="Planning proposal resolution history" description="Auditable downstream resolution states for accepted/deferred/rejected/acknowledged planning proposals.">
            {!resolutions.length ? <p className="muted-text">No planning resolutions recorded yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Proposal</th><th>Status</th><th>Type</th><th>Resolved by</th><th>Resolved at</th><th>Rationale</th></tr></thead><tbody>{resolutions.map((item) => (<tr key={item.id}><td>#{item.planning_proposal}</td><td><StatusBadge tone={tone(item.resolution_status)}>{item.resolution_status}</StatusBadge></td><td>{item.resolution_type}</td><td>{item.resolved_by || 'n/a'}</td><td>{item.resolved_at ?? 'n/a'}</td><td>{item.rationale}</td></tr>))}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Planning review recommendations" description="Recommendation-first queue highlighting acknowledge/accept/defer/reject/manual-review actions.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.planning_proposal ? `Proposal #${item.planning_proposal}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
