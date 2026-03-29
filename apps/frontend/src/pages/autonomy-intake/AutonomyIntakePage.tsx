import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acknowledgeAutonomyIntakeProposal,
  emitAutonomyIntakeProposal,
  getAutonomyIntakeCandidates,
  getAutonomyIntakeProposals,
  getAutonomyIntakeRecommendations,
  getAutonomyIntakeSummary,
  runAutonomyIntakeReview,
} from '../../services/autonomyIntake';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'EMITTED', 'ACKNOWLEDGED', 'ROADMAP_PROPOSAL', 'SCENARIO_PROPOSAL', 'PROGRAM_REVIEW_PROPOSAL', 'MANAGER_REVIEW_PROPOSAL', 'EMIT_ROADMAP_PROPOSAL', 'EMIT_SCENARIO_PROPOSAL', 'EMIT_PROGRAM_REVIEW_PROPOSAL', 'EMIT_MANAGER_REVIEW_PROPOSAL'].includes(v)) return 'ready';
  if (['PENDING_REVIEW', 'MEDIUM', 'HIGH', 'REORDER_INTAKE_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'DUPLICATE_SKIPPED', 'SKIP_DUPLICATE_PROPOSAL', 'REQUIRE_MANUAL_INTAKE_REVIEW'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyIntakePage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyIntakeCandidates>>>([]);
  const [proposals, setProposals] = useState<Awaited<ReturnType<typeof getAutonomyIntakeProposals>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyIntakeRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyIntakeSummary>> | null>(null);

  const proposalByBacklog = useMemo(() => {
    const map = new Map<number, (typeof proposals)[number]>();
    proposals.forEach((row) => map.set(row.backlog_item, row));
    return map;
  }, [proposals]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, proposalData, recommendationData, summaryData] = await Promise.all([
        getAutonomyIntakeCandidates(),
        getAutonomyIntakeProposals(),
        getAutonomyIntakeRecommendations(),
        getAutonomyIntakeSummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setProposals(proposalData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy intake board.');
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
      const result = await runAutonomyIntakeReview({ actor: 'operator-ui' });
      setMessage(`Intake run #${result.run} reviewed ${result.candidate_count} candidates and emitted ${result.emitted_count} proposals.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run intake review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const emitProposal = useCallback(async (backlogItemId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await emitAutonomyIntakeProposal(backlogItemId, { actor: 'operator-ui' });
      setMessage(`Planning proposal emitted/confirmed for backlog item #${backlogItemId}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not emit planning proposal for backlog item #${backlogItemId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const acknowledgeProposal = useCallback(async (proposalId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await acknowledgeAutonomyIntakeProposal(proposalId, { actor: 'operator-ui' });
      setMessage(`Planning proposal #${proposalId} acknowledged.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not acknowledge planning proposal #${proposalId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy intake board"
        title="/autonomy-intake"
        description="Manual-first governance intake board that converts prioritized backlog items into formal planning proposals. Recommendation-first, auditable, and explicitly no opaque auto-apply into roadmap/scenario/program/manager."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run intake review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-backlog')}>Backlog</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory-resolution')}>Advisory resolution</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Planning intake posture" description="Candidate readiness, blockers, emitted proposals, duplicate skips, and target-specific proposal distribution for the next governed planning cycle.">
          <div className="cockpit-metric-grid">
            <div><strong>Candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Emitted</strong><div>{summary?.emitted_count ?? 0}</div></div>
            <div><strong>Duplicate skipped</strong><div>{summary?.duplicate_skipped_count ?? 0}</div></div>
            <div><strong>Roadmap</strong><div>{summary?.roadmap_proposal_count ?? 0}</div></div>
            <div><strong>Scenario</strong><div>{summary?.scenario_proposal_count ?? 0}</div></div>
            <div><strong>Program</strong><div>{summary?.program_proposal_count ?? 0}</div></div>
            <div><strong>Manager</strong><div>{summary?.manager_proposal_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No intake candidates" title="No governance backlog items currently require planning intake." description="Prioritize backlog items in /autonomy-backlog, then run intake review." /> : null}

        <SectionCard eyebrow="Candidates" title="Backlog items eligible for planning intake" description="Traceable conversion candidates from backlog into formal planning proposals without mutating roadmap/scenario/program/manager artifacts.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Backlog</th><th>Insight</th><th>Campaign</th><th>Target</th><th>Priority</th><th>Readiness</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={item.backlog_item}>
                    <td>#{item.backlog_item}</td>
                    <td>#{item.insight}</td>
                    <td>{item.campaign_title ?? (item.campaign ? `Campaign #${item.campaign}` : 'Cross-campaign')}</td>
                    <td>{item.target_scope}</td>
                    <td><StatusBadge tone={tone(item.priority_level)}>{item.priority_level}</StatusBadge></td>
                    <td><StatusBadge tone={item.ready_for_intake ? 'ready' : 'offline'}>{item.ready_for_intake ? 'READY' : 'BLOCKED'}</StatusBadge></td>
                    <td>{item.blockers.join(', ') || 'None'}</td>
                    <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_backlog_item&root_id=${encodeURIComponent(String(item.backlog_item))}`)}>Backlog</button><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=campaign_insight&root_id=${encodeURIComponent(String(item.insight))}`)}>Insight</button><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=advisory_artifact&root_id=${encodeURIComponent(String(item.advisory_artifact))}`)}>Advisory</button>{item.campaign ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Campaign</button> : null}</td>
                    <td><button className="secondary-button" type="button" disabled={busy || Boolean(item.existing_proposal) || !item.ready_for_intake} onClick={() => void emitProposal(item.backlog_item)}>{item.existing_proposal ? 'Exists' : 'Emit proposal'}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Proposals" title="Planning proposal history" description="Formal planning proposal artifacts emitted from governance backlog with explicit target scope and manual-first apply expectations.">
            {!proposals.length ? <p className="muted-text">No proposals emitted yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Proposal</th><th>Type</th><th>Status</th><th>Target</th><th>Priority</th><th>Emitted</th><th>Summary</th><th>Actions</th></tr></thead><tbody>{proposals.map((item) => (<tr key={item.id}><td>#{item.id}</td><td>{item.proposal_type}</td><td><StatusBadge tone={tone(item.proposal_status)}>{item.proposal_status}</StatusBadge></td><td>{item.target_scope}</td><td><StatusBadge tone={tone(item.priority_level)}>{item.priority_level}</StatusBadge></td><td>{item.emitted_at ?? 'n/a'}</td><td>{item.summary}</td><td><div className="button-row"><button className="ghost-button" type="button" disabled={busy || item.proposal_status === 'ACKNOWLEDGED'} onClick={() => void acknowledgeProposal(item.id)}>Acknowledge</button>{item.backlog_item ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_backlog_item&root_id=${encodeURIComponent(String(item.backlog_item))}`)}>Trace</button> : null}</div></td></tr>))}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Intake recommendations" description="Recommendation-first intake actions with rationale, blockers, confidence, and duplicate/manual-review guidance.">
            {!recommendations.length ? <p className="muted-text">No intake recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.backlog_item ? `Backlog item #${item.backlog_item}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>

        {candidates.length > 0 && !candidates.some((item) => item.ready_for_intake) ? (
          <EmptyState
            eyebrow="Intake blocked"
            title="No READY backlog candidates for formal planning emission."
            description="Review blockers and backlog statuses; EMITTED and DUPLICATE_SKIPPED are valid states and remain traceable in this board."
          />
        ) : null}
      </DataStateWrapper>
    </div>
  );
}
