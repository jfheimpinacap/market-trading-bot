import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acknowledgeAutonomyDecision,
  getAutonomyDecisionCandidates,
  getAutonomyDecisionRecommendations,
  getAutonomyDecisions,
  getAutonomyDecisionSummary,
  registerAutonomyDecision,
  runAutonomyDecisionReview,
} from '../../services/autonomyDecision';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'REGISTERED', 'ACKNOWLEDGED', 'REGISTER_ROADMAP_DECISION', 'REGISTER_SCENARIO_DECISION', 'REGISTER_PROGRAM_DECISION', 'REGISTER_MANAGER_DECISION'].includes(v)) return 'ready';
  if (['PENDING_REVIEW', 'REORDER_DECISION_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'DUPLICATE_SKIPPED', 'REQUIRE_MANUAL_DECISION_REVIEW', 'SKIP_DUPLICATE_DECISION'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyDecisionPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyDecisionCandidates>>>([]);
  const [decisions, setDecisions] = useState<Awaited<ReturnType<typeof getAutonomyDecisions>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyDecisionRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyDecisionSummary>> | null>(null);

  const decisionByProposal = useMemo(() => {
    const map = new Map<number, (typeof decisions)[number]>();
    decisions.forEach((item) => map.set(item.planning_proposal, item));
    return map;
  }, [decisions]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, decisionData, recommendationData, summaryData] = await Promise.all([
        getAutonomyDecisionCandidates(),
        getAutonomyDecisions(),
        getAutonomyDecisionRecommendations(),
        getAutonomyDecisionSummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setDecisions(decisionData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy decision board.');
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
      const result = await runAutonomyDecisionReview({ actor: 'operator-ui' });
      setMessage(`Decision review run #${result.run} processed ${result.candidate_count} candidates and generated ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run decision review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const registerDecision = useCallback(async (proposalId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await registerAutonomyDecision(proposalId, { actor: 'operator-ui' });
      setMessage(`Decision ${result.decision_status} for proposal #${proposalId}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not register decision for proposal #${proposalId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const acknowledgeDecision = useCallback(async (decisionId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await acknowledgeAutonomyDecision(decisionId);
      setMessage(`Decision #${decisionId} acknowledged.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not acknowledge decision #${decisionId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy decision board"
        title="/autonomy-decision"
        description="Accepted proposal registry and future-cycle decision package board. Manual-first, recommendation-first, auditable, and explicitly no opaque auto-apply into roadmap/scenario/program/manager."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run decision review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-planning-review')}>Planning review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-intake')}>Intake</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Decision registration posture" description="Converts ACCEPTED planning proposals into explicit governance decision packages for future cycles without mutating target modules.">
          <div className="cockpit-metric-grid">
            <div><strong>Candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Registered</strong><div>{summary?.registered_count ?? 0}</div></div>
            <div><strong>Duplicate skipped</strong><div>{summary?.duplicate_skipped_count ?? 0}</div></div>
            <div><strong>Roadmap/Scenario/Program/Manager</strong><div>{summary?.roadmap_decision_count ?? 0} / {summary?.scenario_decision_count ?? 0} / {summary?.program_decision_count ?? 0} / {summary?.manager_decision_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No decision candidates" title="No accepted planning proposals currently require decision registration." description="Once proposals are ACCEPTED in /autonomy-planning-review, they appear here for manual-first decision packaging." /> : null}

        <SectionCard eyebrow="Candidates" title="Accepted proposals pending decision formalization" description="Each row preserves campaign → insight → advisory → backlog → intake → planning review traceability and exposes blockers/duplicates before manual registration.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Proposal</th><th>Backlog</th><th>Insight</th><th>Campaign</th><th>Target</th><th>Priority</th><th>Status</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => {
                  const decision = decisionByProposal.get(item.planning_proposal);
                  return (
                    <tr key={item.planning_proposal}>
                      <td>#{item.planning_proposal}</td>
                      <td>{item.backlog_item ? `#${item.backlog_item}` : 'n/a'}</td>
                      <td>{item.insight ? `#${item.insight}` : 'n/a'}</td>
                      <td>{item.campaign_title ?? (item.campaign ? `Campaign #${item.campaign}` : 'Cross-campaign')}</td>
                      <td>{item.target_scope}</td>
                      <td>{item.priority_level}</td>
                      <td><StatusBadge tone={tone(decision?.decision_status ?? (item.ready_for_decision ? 'READY' : 'BLOCKED'))}>{decision?.decision_status ?? (item.ready_for_decision ? 'READY' : 'BLOCKED')}</StatusBadge></td>
                      <td>{item.blockers.join(', ') || 'None'}</td>
                      <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=planning_proposal&root_id=${encodeURIComponent(String(item.planning_proposal))}`)}>Proposal</button>{item.backlog_item ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_backlog_item&root_id=${encodeURIComponent(String(item.backlog_item))}`)}>Backlog</button> : null}{item.advisory_artifact ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=advisory_artifact&root_id=${encodeURIComponent(String(item.advisory_artifact))}`)}>Advisory</button> : null}{item.insight ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=campaign_insight&root_id=${encodeURIComponent(String(item.insight))}`)}>Insight</button> : null}{item.campaign ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Campaign</button> : null}</td>
                      <td><div className="button-row"><button className="secondary-button" type="button" disabled={busy || !item.ready_for_decision} onClick={() => void registerDecision(item.planning_proposal)}>Register decision</button></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Decision history" title="Persisted governance decisions" description="Formal registry of accepted-proposal decision artifacts by target scope and status.">
            {!decisions.length ? <p className="muted-text">No decisions registered yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Status</th><th>Target</th><th>Priority</th><th>Registered</th><th>Summary</th><th>Action</th></tr></thead><tbody>{decisions.map((item) => (<tr key={item.id}><td>{item.decision_type}</td><td><StatusBadge tone={tone(item.decision_status)}>{item.decision_status}</StatusBadge></td><td>{item.target_scope}</td><td>{item.priority_level}</td><td>{item.registered_at ?? 'n/a'}</td><td>{item.summary}</td><td><button className="ghost-button" type="button" disabled={busy || item.decision_status === 'ACKNOWLEDGED'} onClick={() => void acknowledgeDecision(item.id)}>Acknowledge</button></td></tr>))}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Decision recommendations" description="Transparent recommendation queue for registration, duplicate skip, manual review, and priority reordering.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.planning_proposal ? `Proposal #${item.planning_proposal}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
